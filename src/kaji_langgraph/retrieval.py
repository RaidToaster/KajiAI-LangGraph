"""Bounded external retrieval with a complete, hash-addressed source ledger."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import re
from typing import Any, Protocol
import urllib.request
from urllib.parse import urlsplit

from kaji_langgraph.models import SourceRecord


class Retriever(Protocol):
    def search(self, query: str, *, max_results: int) -> list[dict[str, Any]]: ...


class DDGSRetriever:
    def search(self, query: str, *, max_results: int) -> list[dict[str, Any]]:
        from ddgs import DDGS

        with DDGS() as client:
            return list(client.text(query, max_results=max_results))


class StaticRetriever:
    """Deterministic source provider for tests and the offline smoke command."""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self.results = results or []

    def search(self, query: str, *, max_results: int) -> list[dict[str, Any]]:
        del query
        return self.results[:max_results]


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in {"script", "style"}:
            self.ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


def fetch_page(url: str, *, timeout: float, max_bytes: int, require_https: bool) -> tuple[str, int | None, str | None]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "", None, "invalid HTTP(S) URL"
    if require_https and parsed.scheme != "https":
        return "", None, "HTTPS is required"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "KajiSF-DJ/0.1 evidence-retriever"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None)
            body = response.read(max_bytes)
            charset = response.headers.get_content_charset() or "utf-8"
        parser = _HTMLText()
        parser.feed(body.decode(charset, errors="replace"))
        return parser.text(), status, None
    except Exception as exc:
        return "", None, f"{type(exc).__name__}: {exc}"


def normalize_result(item: dict[str, Any], query: str, provider: str = "ddgs") -> SourceRecord | None:
    url = str(item.get("href") or item.get("url") or "").strip()
    if not urlsplit(url).hostname:
        return None
    snippet = str(item.get("body") or item.get("snippet") or "").strip()
    timestamp = str(item.get("retrieved_at") or datetime.now(timezone.utc).isoformat())
    digest = hashlib.sha256(snippet.encode("utf-8")).hexdigest()
    return SourceRecord(
        title=str(item.get("title") or ""),
        url=url,
        snippet=snippet,
        retrieved_at=timestamp,
        content_hash=digest,
        query=query,
        provider=provider,
        lineage_id=hashlib.sha256(f"{provider}\0{query}\0{url}\0{timestamp}".encode()).hexdigest(),
    )


def annotate_duplicate_lineage(records: list[SourceRecord], threshold: float = 0.85) -> list[SourceRecord]:
    def tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}

    copies = [record.model_copy(deep=True) for record in records]
    for index, left in enumerate(copies):
        left_tokens = tokens(left.retrieved_text)
        left_host = (urlsplit(left.url).hostname or "").removeprefix("www.")
        for right in copies[index + 1 :]:
            right_host = (urlsplit(right.url).hostname or "").removeprefix("www.")
            right_tokens = tokens(right.retrieved_text)
            if not left_tokens or not right_tokens or left_host == right_host:
                continue
            similarity = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
            if similarity >= threshold:
                left.possible_duplicate_of.append(right.url)
                right.possible_duplicate_of.append(left.url)
    return copies


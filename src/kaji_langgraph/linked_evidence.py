"""Provisional ranking of outbound evidence leads from a retrieved page."""

import re
from urllib.parse import unquote, urlsplit


_COMMON = frozenset(
    "about after have been were what that this some they their from more than says said "
    "will with while under which most knows stating names state official report news page index home public".split()
)
_RECORD_CUES = {"roll", "vote", "record", "survey", "research", "crosstab"}
_PUBLIC_HOST = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}", re.I)


def _terms(text: str) -> set[str]:
    return {word.rstrip("s") for word in re.findall(r"[a-z]{4,}", text.lower()) if word not in _COMMON}


def rank_linked_evidence(claim: str, parent_url: str, parent_text: str, links: list[str]) -> list[str]:
    """Rank external document links with claim overlap and original-record cues."""
    parent_host = (urlsplit(parent_url).hostname or "").removeprefix("www.")
    claim_terms = _terms(claim)
    parent_terms = _terms(parent_text)
    words = re.findall(r"[a-z]+", claim.lower())
    compound_names = {a + b for a, b in zip(words, words[1:]) if len(a) + len(b) > 8}
    scores = {}
    for link in links:
        try:
            parsed = urlsplit(link)
            host = (parsed.hostname or "").removeprefix("www.")
            public = (_PUBLIC_HOST.fullmatch(host) and not host.endswith((".local", ".internal"))
                      and parsed.username is None and parsed.port is None)
        except ValueError:
            continue
        if parsed.scheme != "https" or not public or host == parent_host or not parsed.path.strip("/"):
            continue
        path = unquote(parsed.path).lower()
        terms = _terms(path)
        matches = len(terms & claim_terms)
        compound = any(name in path for name in compound_names)
        authority = host.endswith((".gov", ".edu"))
        record = bool(terms & _RECORD_CUES)
        if matches or compound or (authority and record):
            url = parsed._replace(fragment="").geturl()
            scores[url] = 3 * matches + 4 * compound + 2 * authority + 2 * record + min(2, len(terms & parent_terms))
    return sorted(scores, key=scores.get, reverse=True)

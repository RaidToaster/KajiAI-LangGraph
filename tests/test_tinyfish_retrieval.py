from __future__ import annotations

import io
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from kaji_langgraph.graph import run_claim
from kaji_langgraph.retrieval import TinyFishRetriever


class JsonResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_tinyfish_search_and_fetch_use_documented_api(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        if urlsplit(request.full_url).hostname == "api.search.tinyfish.ai":
            return JsonResponse(json.dumps({"results": [
                {"title": "Source", "url": "https://example.com/a", "snippet": "summary"},
                {"title": "Other", "url": "https://example.org/b", "snippet": "other"},
            ]}).encode())
        return JsonResponse(json.dumps({"results": [{
            "url": "https://example.com/a", "text": "# Source\nFull evidence.",
        }], "errors": []}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    retriever = TinyFishRetriever(api_key="test-key")
    assert retriever.search("claim evidence", max_results=1)[0]["url"] == "https://example.com/a"
    assert parse_qs(urlsplit(requests[0][0].full_url).query) == {"query": ["claim evidence"]}
    assert requests[0][0].get_header("X-api-key") == "test-key"
    assert retriever.fetch("https://example.com/a", timeout=10, max_bytes=1000, require_https=True) == (
        "# Source\nFull evidence.", None, None,
    )
    assert json.loads(requests[1][0].data) == {
        "urls": ["https://example.com/a"], "format": "markdown", "ttl": 0,
        "per_url_timeout_ms": 10000,
    }


def test_tinyfish_fetch_failure_is_audited_and_snippet_retained(backend, config, monkeypatch):
    def fake_urlopen(request, timeout):
        del timeout
        if urlsplit(request.full_url).hostname == "api.search.tinyfish.ai":
            return JsonResponse(json.dumps({"results": [
                {"url": "https://one.example/a", "snippet": "First source evidence."},
                {"url": "https://two.example/b", "snippet": "Second source evidence."},
            ]}).encode())
        return JsonResponse(json.dumps({"results": [], "errors": [
            {"url": "https://one.example/a", "error": "bot_blocked"},
        ]}).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    config["policy"]["full_page_retrieval"] = True
    result = run_claim(
        "Fixture claim", model=backend, retriever=TinyFishRetriever(api_key="test-key"), config=config,
    )
    assert result.retrieval_ledger[0].provider == "tinyfish"
    assert result.retrieval_ledger[0].retrieved_text == "First source evidence."
    assert result.budget.scrapes == 1
    assert any("bot_blocked" in error for error in result.errors)


def test_tinyfish_requires_key(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    with pytest.raises(ValueError, match="TINYFISH_API_KEY"):
        TinyFishRetriever().search("test", max_results=1)

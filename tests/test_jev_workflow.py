from __future__ import annotations

import json
import time

import httpx2
from typesafe_sdk import TypeSafeClient

from kaji_langgraph.graph import WorkflowNodes, run_claim
from kaji_langgraph.jev import JevClient
from kaji_langgraph.llm import DeterministicBackend
from kaji_langgraph.models import BudgetState, Classification
from kaji_langgraph.retrieval import StaticRetriever, normalize_result


class FakeJev:
    def __init__(self, *, relation="supports", confidence=0.99, fail_citations=False):
        self.relation = relation
        self.confidence = confidence
        self.fail_citations = fail_citations
        self.ranked = []

    def classify(self, claim, *, timeout):
        del claim, timeout
        return Classification(domain="political", confidence=0.95), 8

    def rank_results(self, claim, query, results, *, timeout):
        del claim, query, timeout
        self.ranked = results
        return [0.1, 0.9], 12

    def review_sources(self, claim, sources, *, timeout):
        del claim, timeout
        return [
            {"relevant": 0.9, "evidence": 0.9, "counterevidence": 0.1, "injection": 0.01}
            for _ in sources
        ], 14

    def check_citations(self, citations, *, timeout):
        del timeout
        if self.fail_citations:
            raise ConnectionError("fixture Jev outage")
        return [
            {"relation": self.relation, "confidence": self.confidence}
            for _ in citations
        ], 18


def test_jev_checks_citations_without_replacing_existing_gate(backend, two_source_retriever, config):
    result = run_claim(
        "The documented fixture event occurred", model=backend,
        retriever=two_source_retriever, jev=FakeJev(), config=config,
    )
    assert result.verdict == "TRUE"
    assert result.jev_audit["domain"]["used"] is True
    assert result.budget.tokens_used == 52  # domain + source reviews + two citation batches
    assert len(result.jev_audit["citations"]) == 2
    assert all(item["relation"] == "supports" for item in result.jev_audit["citations"])


def test_jev_rejects_unsupported_and_uncertain_citations(backend, two_source_retriever, config):
    for relation, confidence in [("unrelated", 0.99), ("supports", 0.4)]:
        result = run_claim(
            "The documented fixture event occurred", max_rounds=1, model=backend,
            retriever=two_source_retriever,
            jev=FakeJev(relation=relation, confidence=confidence), config=config,
        )
        assert result.verdict == "UNVERIFIED"
        assert any("Citation" in gap for gap in result.gaps)


def test_jev_failure_fails_closed(backend, two_source_retriever, config):
    result = run_claim(
        "The documented fixture event occurred", model=backend,
        retriever=two_source_retriever, jev=FakeJev(fail_citations=True), config=config,
    )
    assert result.verdict == "UNVERIFIED"
    assert result.stop_reason == "execution_error"
    assert any("Jev citation check failed" in error for error in result.errors)


def test_final_gate_rejects_missing_jev_review(backend, two_source_retriever, config):
    sources = [normalize_result(item, "fixture") for item in two_source_retriever.results]
    assessment, _ = backend.analyze(
        "Fixture claim", "general", ["Fixture claim"], sources, [], "2026-09-25", {},
    )
    nodes = WorkflowNodes(backend, two_source_retriever, config, FakeJev())
    result = nodes.finalize({
        "claim": "Fixture claim", "requested_domain": "general", "domain": "general",
        "assertions": ["Fixture claim"], "sources": sources, "assessment": assessment,
        "gaps": [], "semantic_gaps": [], "jev_audit": {"citations": []},
        "research_round": 1, "policy": config["policy"], "stop_reason": "evidence_sufficient",
        "research_history": [], "budgets": BudgetState(started_at_monotonic=time.monotonic()),
    })["result"]
    assert result.verdict == "UNVERIFIED"
    assert result.stop_reason == "final_gate_rejected"
    assert any("not checked" in gap for gap in result.gaps)


class TrackingRetriever(StaticRetriever):
    def __init__(self):
        super().__init__([
            {"url": "https://first.example/a", "snippet": "First source evidence."},
            {"url": "https://second.example/b", "snippet": "Second source evidence."},
        ])
        self.fetched = []

    def fetch(self, url, *, timeout, max_bytes, require_https):
        del timeout, max_bytes, require_https
        self.fetched.append(url)
        return "Full page evidence from " + url, None, None


def test_jev_ranking_selects_page_to_fetch(backend, config):
    retriever = TrackingRetriever()
    config["policy"]["full_page_retrieval"] = True
    result = run_claim(
        "Fixture claim", model=backend, retriever=retriever, jev=FakeJev(), config=config,
    )
    assert retriever.fetched[0] == "https://second.example/b"
    assert len(result.jev_audit["search_ranking"]) == 2
    assert result.retrieval_ledger[0].jev_scores["relevant"] == 0.9


class CapturingBackend(DeterministicBackend):
    def analyze(self, claim, domain, assertions, sources, prior_gaps, reference_date, domain_guidance):
        self.seen = [source.url for source in sources]
        return super().analyze(
            claim, domain, assertions, sources, prior_gaps, reference_date, domain_guidance
        )


class InjectionJev(FakeJev):
    def review_sources(self, claim, sources, *, timeout):
        reviews, tokens = super().review_sources(claim, sources, timeout=timeout)
        reviews[0]["injection"] = 0.99
        return reviews, tokens


def test_jev_source_review_excludes_prompt_injection(config, two_source_retriever):
    backend = CapturingBackend()
    result = run_claim(
        "Fixture claim", max_rounds=1, model=backend, retriever=two_source_retriever,
        jev=InjectionJev(), config=config,
    )
    assert backend.seen == ["https://one.example/record"]
    assert len(result.retrieval_ledger) == 2
    assert result.retrieval_ledger[0].url == "https://two.example/archive"
    assert result.retrieval_ledger[0].jev_scores["injection"] == 0.99


def test_jev_client_uses_typed_sdk_questions(monkeypatch):
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        assert request.url.path == "/v1/systemone"
        return httpx2.Response(200, json={
            "model": "jev-1.13.0",
            "answers": {"domain": {
                "type": "choice", "choice": "political", "confidence": 0.95,
                "probabilities": {"general": 0.05, "scientific": 0, "political": 0.95, "health_medical": 0},
            }},
            "usage": {"input_tokens": 5, "output_tokens": 2},
        })

    monkeypatch.setattr(
        "kaji_langgraph.jev.TypeSafeClient",
        lambda **kwargs: TypeSafeClient(transport=httpx2.MockTransport(handler), **kwargs),
    )
    classification, tokens = JevClient(api_key="fixture-key").classify(
        "The minister signed a law", timeout=3,
    )
    assert classification.domain == "political"
    assert tokens == 7
    assert captured["body"]["model"] == "jev-1.13.0"
    assert captured["body"]["questions"]["domain"]["type"] == "choice"

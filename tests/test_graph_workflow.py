from __future__ import annotations

from typing import Any

from kaji_langgraph.graph import run_claim
from kaji_langgraph.llm import DeterministicBackend
from kaji_langgraph.retrieval import StaticRetriever


def test_empty_claim_fails_closed(backend, config):
    result = run_claim("   ", model=backend, retriever=StaticRetriever(), config=config)
    assert result.verdict == "UNVERIFIED"
    assert result.stop_reason == "validation_error"
    assert "Claim must not be empty." in result.errors


def test_successful_graph_routes_to_accepted_report(backend, two_source_retriever, config):
    result = run_claim(
        "The documented fixture event occurred",
        model=backend,
        retriever=two_source_retriever,
        config=config,
    )
    assert result.verdict == "TRUE"
    assert result.stop_reason == "evidence_sufficient"
    assert result.research_history[-1].decision == "evidence_sufficient"
    assert len(result.retrieval_ledger) == 2
    assert all(record.query for record in result.retrieval_ledger)
    assert all(record.content_hash and record.lineage_id for record in result.retrieval_ledger)
    assert result.errors == []


def test_round_budget_exhaustion_returns_unverified(backend, config):
    result = run_claim(
        "An unsupported fixture claim",
        max_rounds=1,
        model=backend,
        retriever=StaticRetriever(),
        config=config,
    )
    assert result.verdict == "UNVERIFIED"
    assert result.stop_reason == "max_rounds"
    assert len(result.research_history) == 1


class TokenHungryBackend(DeterministicBackend):
    def __init__(self):
        self.analyze_called = False

    def decompose(self, claim):
        return [claim], 50

    def analyze(self, *args, **kwargs):
        self.analyze_called = True
        return super().analyze(*args, **kwargs)


def test_token_budget_prevents_further_model_analysis(config):
    config["policy"]["max_token_limit"] = 10
    backend = TokenHungryBackend()
    result = run_claim(
        "A token-limited claim",
        domain="general",
        model=backend,
        retriever=StaticRetriever(),
        config=config,
    )
    assert result.verdict == "UNVERIFIED"
    assert result.stop_reason == "token_budget_exhausted"
    assert backend.analyze_called is False


def test_stagnant_research_stops_after_two_rounds(backend, config):
    result = run_claim(
        "A claim with no discoverable records",
        max_rounds=4,
        model=backend,
        retriever=StaticRetriever(),
        config=config,
    )
    assert result.verdict == "UNVERIFIED"
    assert result.stop_reason == "stagnant_research"
    assert len(result.research_history) == 2


class BrokenRetriever:
    def search(self, query: str, *, max_results: int) -> list[dict[str, Any]]:
        del query, max_results
        raise ConnectionError("fixture network outage")


def test_retrieval_error_is_audited_and_fails_closed(backend, config):
    result = run_claim(
        "A claim whose retrieval fails",
        model=backend,
        retriever=BrokenRetriever(),
        config=config,
    )
    assert result.verdict == "UNVERIFIED"
    assert result.stop_reason == "execution_error"
    assert any("ConnectionError" in error for error in result.errors)


def test_graph_routing_research_then_stagnation(backend, config):
    result = run_claim(
        "A claim requiring repeated research",
        max_rounds=3,
        model=backend,
        retriever=StaticRetriever(),
        config=config,
    )
    assert [item.decision for item in result.research_history] == [
        "research_more",
        "stagnant_research",
    ]


def test_explicit_domain_skips_auto_classification(backend, two_source_retriever, config):
    result = run_claim(
        "A neutral fixture statement",
        domain="political",
        model=backend,
        retriever=two_source_retriever,
        config=config,
    )
    assert result.domain == "political"

from __future__ import annotations

import time
from typing import Any

from kaji_langgraph.graph import WorkflowNodes, run_claim
from kaji_langgraph.llm import DeterministicBackend
from kaji_langgraph.models import BudgetState, EvidenceAssessment, ResearchRound
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


class GuidanceCapturingBackend(DeterministicBackend):
    def __init__(self):
        self.domain_guidance = None

    def analyze(
        self,
        claim,
        domain,
        assertions,
        sources,
        prior_gaps,
        reference_date,
        domain_guidance,
    ):
        self.domain_guidance = domain_guidance
        return super().analyze(
            claim,
            domain,
            assertions,
            sources,
            prior_gaps,
            reference_date,
            domain_guidance,
        )


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


class FlakyRetriever(StaticRetriever):
    def __init__(self, results: list[dict[str, Any]], failures: int):
        super().__init__(results)
        self.failures = failures
        self.calls = 0

    def search(self, query: str, *, max_results: int) -> list[dict[str, Any]]:
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("temporary fixture outage")
        return super().search(query, max_results=max_results)


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


def test_retrieval_retries_without_consuming_extra_search_budget(backend, config):
    retriever = FlakyRetriever(
        [
            {"href": "https://one.example/a", "body": "The first record confirms the fixture."},
            {"href": "https://two.example/b", "body": "The second record independently confirms the fixture."},
        ],
        failures=2,
    )
    config["policy"]["max_retries"] = 2
    result = run_claim(
        "The retry fixture is confirmed",
        model=backend,
        retriever=retriever,
        config=config,
    )
    assert result.verdict == "TRUE"
    assert retriever.calls == 3
    assert result.budget.search_calls == 1
    assert result.errors == []


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


def test_graph_passes_selected_domain_guidance_to_model(two_source_retriever, config):
    backend = GuidanceCapturingBackend()
    run_claim(
        "A medical fixture statement",
        domain="health_medical",
        model=backend,
        retriever=two_source_retriever,
        config=config,
    )
    assert "clinical trials" in backend.domain_guidance["research"]
    assert "anecdotes" in backend.domain_guidance["analysis"]
    assert "strict medical evidence" in backend.domain_guidance["verification_standard"]


def test_finalize_revalidates_instead_of_trusting_stale_empty_gaps(backend, config):
    nodes = WorkflowNodes(backend, StaticRetriever(), config)
    state = {
        "claim": "An unsupported claim",
        "requested_domain": "general",
        "domain": "general",
        "assertions": ["An unsupported claim"],
        "sources": [],
        "assessment": EvidenceAssessment(proposed_verdict="TRUE", confidence="High"),
        "gaps": [],
        "policy": config["policy"],
        "stop_reason": "evidence_sufficient",
        "research_history": [
            ResearchRound(
                round_number=1,
                proposed_verdict="TRUE",
                confidence="High",
                decision="evidence_sufficient",
            )
        ],
        "budgets": BudgetState(started_at_monotonic=time.monotonic()),
        "errors": [],
    }
    result = nodes.finalize(state)["result"]
    assert result.verdict == "UNVERIFIED"
    assert result.stop_reason == "final_gate_rejected"
    assert result.gaps
    assert result.research_history[-1].decision == "final_gate_rejected"

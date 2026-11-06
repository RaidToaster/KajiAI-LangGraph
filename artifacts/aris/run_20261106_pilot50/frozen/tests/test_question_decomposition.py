from __future__ import annotations

from types import SimpleNamespace
import time

import pytest

from kaji_langgraph.cli import build_parser
from kaji_langgraph.graph import WorkflowNodes, build_graph, run_claim
from kaji_langgraph.llm import DeterministicBackend, OllamaBackend, heuristic_decomposition
from kaji_langgraph.models import BudgetState, EvidenceAssessment, QuestionDecomposition
from kaji_langgraph.report import format_report
from kaji_langgraph.retrieval import StaticRetriever


CLAIM = "The agency published the report in 2020 and the minister approved its release in 2020"
STATEMENTS = ["The agency published the report in 2020", "The minister approved its release in 2020"]
QUESTIONS = [
    "What dated agency record establishes whether the report was published in 2020?",
    "What record supports or contradicts the minister approving its release in 2020?",
    "Were the publication and approval dates different?",
]


class PlanningBackend(DeterministicBackend):
    def __init__(self, plan=None, tokens=17):
        self.plan = plan or {"assertions": STATEMENTS, "questions": QUESTIONS}
        self.tokens = tokens
        self.planning_calls = []
        self.analysis_called = False

    def decompose_with_questions(self, claim, *, reference_date):
        self.planning_calls.append((claim, reference_date))
        if isinstance(self.plan, Exception):
            raise self.plan
        return self.plan, self.tokens

    def analyze(self, *args, **kwargs):
        self.analysis_called = True
        return EvidenceAssessment(gaps=["No independently verified records."], next_queries=[]), 0


class QueryRecorder(StaticRetriever):
    def __init__(self):
        super().__init__()
        self.queries = []

    def search(self, query, *, max_results):
        self.queries.append(query)
        return []


def enable(config):
    config["model"]["decomposition_method"] = "statements_and_questions"
    return config


def test_questions_drive_bounded_retrieval_and_survive_output(config):
    enable(config)
    config["policy"].update(search_calls_per_round=2, max_search_calls=3)
    backend = PlanningBackend()
    search = QueryRecorder()
    result = run_claim(CLAIM, domain="general", reference_date="2020-12-31", max_rounds=2,
                       model=backend, retriever=search, config=config)
    assert backend.planning_calls == [(CLAIM, "2020-12-31")]
    assert search.queries == QUESTIONS
    assert result.budget.search_calls == 3
    assert result.budget.tokens_used == 17
    assert result.assertions == [CLAIM, *STATEMENTS]
    assert result.verification_questions == QUESTIONS
    assert result.decomposition_method == "statements_and_questions"
    assert result.verdict == "UNVERIFIED"  # Questions cannot establish evidence.
    assert QUESTIONS[0] in format_report(result)
    restored = type(result).model_validate_json(result.model_dump_json())
    assert restored.verification_questions == QUESTIONS


@pytest.mark.parametrize("plan", [ConnectionError("fixture unavailable"),
                                  {"assertions": STATEMENTS, "questions": ["   "]}])
def test_failed_or_invalid_plan_retains_claim_and_audits_fallback(config, plan):
    enable(config)
    result = run_claim(CLAIM, domain="general", max_rounds=1, model=PlanningBackend(plan),
                       retriever=StaticRetriever(), config=config)
    assert result.assertions == list(dict.fromkeys([CLAIM, *heuristic_decomposition(CLAIM)]))
    assert result.verification_questions == []
    assert result.decomposition_method == "statements_fallback"
    assert result.budget.token_usage_complete is False
    assert any("Decomposition model unavailable" in error for error in result.errors)


def test_exhausted_budget_skips_question_generation(config):
    enable(config)
    backend = PlanningBackend()
    nodes = WorkflowNodes(backend, StaticRetriever(), config)
    update = nodes.decompose({"claim": CLAIM, "policy": config["policy"],
                              "budgets": BudgetState(tokens_used=10, max_tokens=10,
                                                     started_at_monotonic=time.monotonic())})
    assert not backend.planning_calls
    assert update["verification_questions"] == []
    assert update["assertions"][0] == CLAIM


def test_planning_tokens_prevent_further_search_and_analysis(config):
    enable(config)
    config["policy"]["max_token_limit"] = 10
    search = QueryRecorder()
    backend = PlanningBackend(tokens=17)
    result = run_claim(CLAIM, domain="general", model=backend, retriever=search, config=config)
    assert result.stop_reason == "token_budget_exhausted"
    assert result.budget.tokens_used == 17
    assert not search.queries and not backend.analysis_called


def test_targeted_followups_precede_unused_deduplicated_questions(config):
    nodes = WorkflowNodes(DeterministicBackend(), StaticRetriever(), config)
    queries = nodes._research_queries({"claim": CLAIM, "assertions": [CLAIM],
                                      "verification_questions": [QUESTIONS[0], QUESTIONS[1], QUESTIONS[1]],
                                      "search_queries": [QUESTIONS[0]], "policy": config["policy"],
                                      "assessment": EvidenceAssessment(next_queries=["New official record?"])})
    assert queries[:2] == ["New official record?", QUESTIONS[1]]
    assert QUESTIONS[0] not in queries and queries.count(QUESTIONS[1]) == 1


def test_pending_question_prevents_query_exhaustion_stop(config):
    from kaji_langgraph.graph import _unused_queries
    state = {"claim": CLAIM, "assertions": [CLAIM], "policy": config["policy"]}
    state["search_queries"] = _unused_queries(state)
    state["verification_questions"] = [QUESTIONS[0]]
    state.update(gaps=["Need evidence"], sources=[], semantic_gaps=[],
                 research_round=1, research_history=[], stagnant_rounds=0,
                 budgets=BudgetState(started_at_monotonic=time.monotonic()))
    state["policy"]["stop_on_query_exhaustion"] = True
    assert WorkflowNodes(DeterministicBackend(), StaticRetriever(), config).route_research(state)["route"] == "research"


def test_default_keeps_statement_only_queries(config):
    search = QueryRecorder()
    backend = PlanningBackend()
    result = run_claim(CLAIM, domain="general", max_rounds=1,
                       model=backend, retriever=search, config=config)
    assert not backend.planning_calls
    assert result.verification_questions == []
    assert result.decomposition_method == "statements"
    assert search.queries == [f"{CLAIM} evidence"]


def test_ollama_generates_structured_plan_with_scope_context():
    captured = {}

    class Provider:
        def with_structured_output(self, schema, *, method, include_raw):
            assert schema is QuestionDecomposition and method == "json_mode" and include_raw

            def invoke(prompt):
                captured["prompt"] = prompt
                return {"parsed": QuestionDecomposition(assertions=STATEMENTS, questions=QUESTIONS),
                        "raw": SimpleNamespace(usage_metadata={"total_tokens": 17})}

            return SimpleNamespace(invoke=invoke)

    backend = OllamaBackend.__new__(OllamaBackend)
    backend._model = Provider()
    plan, tokens = backend.decompose_with_questions(CLAIM, reference_date="2020-12-31")
    assert plan.questions == QUESTIONS and tokens == 17
    assert CLAIM in captured["prompt"] and "2020-12-31" in captured["prompt"]
    assert "counterevidence" in captured["prompt"]


def test_invalid_method_rejected_before_any_model_call(config):
    config["model"]["decomposition_method"] = "unknown"
    with pytest.raises(ValueError, match="decomposition_method"):
        build_graph(model=PlanningBackend(), retriever=StaticRetriever(), config=config)


def test_cli_can_select_question_mode():
    args = build_parser().parse_args([CLAIM, "--decomposition-method", "statements_and_questions"])
    assert args.decomposition_method == "statements_and_questions"

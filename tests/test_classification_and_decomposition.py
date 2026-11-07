from types import SimpleNamespace

import pytest

from kaji_langgraph.config import load_config
from kaji_langgraph.graph import run_claim
from kaji_langgraph.llm import DeterministicBackend, OllamaBackend, heuristic_decomposition, keyword_classification
from kaji_langgraph.retrieval import StaticRetriever


def test_domain_classification_health_indonesian():
    result = keyword_classification("Vaksin dan obat ini menyembuhkan penyakit")
    assert result.domain == "health_medical"


def test_claim_decomposition_preserves_full_claim_and_parts():
    claim = "The agency published the report and the minister signed the order"
    parts = heuristic_decomposition(claim)
    assert parts == ["The agency published the report", "the minister signed the order"]


def test_short_clause_is_not_detached_from_context():
    claim = "The report exists and is false"
    assert heuristic_decomposition(claim) == [claim]


@pytest.mark.parametrize(
    ("mode", "reply", "expect_plan"),
    [
        ("statements", "", False),
        ("questions_as_guidance", '{"assertions":["The minister signed the order"],'
         '"questions":["Which official record shows who signed the order?"]}', True),
        ("questions_as_guidance", '{"assertions":["The minister signed the order"],"questions":[" "]}', False),
    ],
)
def test_question_planning_guides_search_or_falls_back(mode, reply, expect_plan, monkeypatch, config):
    monkeypatch.setenv("KAJI_DECOMPOSITION_METHOD", mode)
    config["model"].update(load_config()["model"])
    config["policy"]["search_calls_per_round"] = 2
    planner_calls = []
    actual_queries = []

    class PlanningModel:
        temperature = 0.0

        def bind(self, **kwargs):
            assert kwargs["format"] == "json"
            return self

        def invoke(self, prompt):
            planner_calls.append(prompt)
            return SimpleNamespace(content=reply, usage_metadata={"total_tokens": 17})

    class RecordingRetriever(StaticRetriever):
        def search(self, query, *, max_results):
            actual_queries.append(query)
            return super().search(query, max_results=max_results)

    class Backend(DeterministicBackend):
        def decompose_with_questions(self, claim, *, reference_date):
            return ollama.decompose_with_questions(claim, reference_date=reference_date)

    ollama = OllamaBackend.__new__(OllamaBackend)
    ollama._model = PlanningModel()
    claim = "The agency published the report and the minister signed the order"
    result = run_claim(
        claim, reference_date="2020-02-26", domain="general", max_rounds=2,
        model=Backend(), retriever=RecordingRetriever(), config=config,
    )

    assert result.assertions == [claim, *heuristic_decomposition(claim)]
    assert actual_queries == result.search_queries
    assert len(actual_queries) <= 4
    assert len(planner_calls) == (mode == "questions_as_guidance")
    assert result.budget.tokens_used == (17 if planner_calls else 0)
    assert (result.query_plan is not None) == expect_plan
    if result.query_plan:
        assert "Reference date: 2020-02-26" in planner_calls[0]
        assert actual_queries[:2] == [result.query_plan.questions[0], f"{claim} counterevidence"]
        assert "The minister signed the order evidence" in actual_queries[2:]
        assert result.query_plan_error is None
    else:
        assert actual_queries[:2] == [f"{claim} evidence", f"{claim} counterevidence"]
        assert bool(result.query_plan_error) == (mode == "questions_as_guidance")


from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from kaji_langgraph.graph import WorkflowNodes, run_claim
from kaji_langgraph.llm import DeterministicBackend, OllamaBackend
from kaji_langgraph.models import BudgetState, EvidenceAssessment, ResearchRound
from kaji_langgraph.retrieval import normalize_result


class Provider:
    """Count actual invoke boundaries, including the adapter's repair path."""
    def __init__(self, *, repair=False, fail=False):
        self.calls = 0
        self.assessments = 0
        self.repair = repair
        self.fail = fail

    def with_structured_output(self, schema, **kwargs):
        self.schema = schema
        return self

    def bind(self, **kwargs):
        return SimpleNamespace(invoke=self.repaired)

    def value(self):
        return self.schema(proposed_verdict="TRUE", confidence="Medium",
                           summary=f"assessment {self.assessments}",
                           gaps=["Evidence still incomplete."])

    def invoke(self, prompt):
        self.calls += 1
        self.assessments += 1
        if self.fail:
            raise ConnectionError("fixture provider failure")
        raw = SimpleNamespace(content="invalid", usage_metadata={"total_tokens": 10})
        return {"parsed": None if self.repair else self.value(), "raw": raw}

    def repaired(self, prompt):
        self.calls += 1
        return SimpleNamespace(content=self.value().model_dump_json(), usage_metadata={"total_tokens": 5})


class Search:
    def __init__(self):
        self.calls = 0

    def search(self, query, *, max_results):
        self.calls += 1
        texts = ["Official minutes confirm the meeting took place on Tuesday.",
                 "An independent archive establishes that the documented event occurred.",
                 "A contemporary newspaper reports additional details of the assembly."]
        return [{"url": f"https://source{self.calls}.example/a", "snippet": texts[(self.calls-1) % 3]}]


def execute(config, enabled, *, repair=False, fail=False):
    cfg = deepcopy(config)
    cfg["policy"].update(search_calls_per_round=2, max_search_calls=20,
                         stop_on_query_exhaustion=enabled)
    provider = Provider(repair=repair, fail=fail)
    backend = OllamaBackend.__new__(OllamaBackend)
    backend._model = provider
    backend.verdict_mode = "averitec"
    search = Search()
    result = run_claim("A fixture claim", domain="general", max_rounds=3,
                       model=backend, retriever=search, config=cfg)
    return result, provider, search


@pytest.mark.parametrize("repair,baseline_calls,candidate_calls", [(False,3,2),(True,6,4)])
def test_exhaustion_preserves_prior_output_and_counts_provider_calls(config, repair, baseline_calls, candidate_calls):
    baseline, bp, bs = execute(config, False, repair=repair)
    candidate, cp, cs = execute(config, True, repair=repair)
    assert (bp.calls, cp.calls) == (baseline_calls, candidate_calls)
    assert bs.calls == cs.calls == 3
    assert len(baseline.research_history) == 3
    assert len(candidate.research_history) == 2
    assert baseline.research_history[-1].queries == []
    assert candidate.research_history[-1].decision == candidate.stop_reason == "query_exhausted"
    prior = baseline.research_history[1].assessment
    assert candidate.research_history[-1].assessment == prior
    assert candidate.predicted_verdict == prior.proposed_verdict
    assert candidate.prediction_summary == prior.summary
    assert candidate.verdict == "UNVERIFIED"
    assert candidate.verification_status == "insufficient_evidence"
    assert candidate.budget.tokens_used == (30 if repair else 20)
    assert type(candidate).model_validate_json(candidate.model_dump_json()).model_dump(mode="json") == candidate.model_dump(mode="json")


def routing_state():
    claim = "A fixture claim"
    return dict(claim=claim, assertions=[claim], assessment=EvidenceAssessment(),
                search_queries=[f"{claim} evidence",f"{claim} counterevidence",f"{claim} original source fact check"],
                gaps=["incomplete"], semantic_gaps=[], sources=[], research_round=2,
                research_history=[ResearchRound(round_number=2)],
                policy={"stop_on_query_exhaustion":True},
                budgets=BudgetState(max_rounds=3,started_at_monotonic=time.monotonic()))


@pytest.mark.parametrize("pending", ["source", "citation", "query"])
def test_pending_work_prevents_exhaustion_stop(config, pending):
    state = routing_state()
    if pending == "source":
        state["sources"] = [normalize_result({"url":"https://one.example/a","snippet":"text"},"q")]
    elif pending == "citation":
        state["semantic_gaps"] = ["Citation support was not checked."]
    else:
        state["assessment"].next_queries = ["new targeted query"]
    nodes = WorkflowNodes(DeterministicBackend(), Search(), config, jev=object())
    assert nodes.route_research(state)["route"] == "research"


@pytest.mark.parametrize("field,value,reason", [("gaps",[],"evidence_sufficient"),
                                                 ("fatal_error",True,"execution_error"),
                                                 ("research_round",3,"max_rounds")])
def test_existing_acceptance_failure_budget_precedence(config, field, value, reason):
    state = routing_state()
    state[field] = value
    assert WorkflowNodes(DeterministicBackend(),Search(),config).route_research(state)["stop_reason"] == reason


def test_provider_failure_stays_execution_error(config):
    result, provider, _ = execute(config, True, fail=True)
    assert provider.calls == 1
    assert result.stop_reason == "execution_error"
    assert result.verdict == "UNVERIFIED"
    assert result.verification_status == "execution_error"


def test_acceptance_can_be_lost_by_skipping_reassessment(config):
    """Document the quality tradeoff; do not claim output equivalence to round 3."""
    class LaterAcceptance(DeterministicBackend):
        def __init__(self):
            self.calls = 0
        def analyze(self, *args, **kwargs):
            self.calls += 1
            value, tokens = super().analyze(*args, **kwargs)
            if self.calls < 3:
                value.gaps = ["Reassessment needed."]
            return value, tokens
    outputs = []
    for enabled in [False,True]:
        cfg = deepcopy(config)
        cfg["policy"].update(search_calls_per_round=2,max_search_calls=20,stop_on_query_exhaustion=enabled)
        outputs.append(run_claim("A fixture claim",domain="general",max_rounds=3,
                                 model=LaterAcceptance(),retriever=Search(),config=cfg))
    assert outputs[0].verdict == "TRUE"
    assert outputs[1].verdict == "UNVERIFIED"
    assert outputs[1].predicted_verdict == "TRUE"

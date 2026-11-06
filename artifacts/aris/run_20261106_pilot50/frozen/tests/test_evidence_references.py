from copy import deepcopy

from kaji_langgraph.graph import run_claim
from kaji_langgraph.llm import DeterministicBackend


def test_reference_search_uses_one_existing_slot_and_rejects_future_references(config):
    past = "Court order on Wisconsin voter rolls, Jan. 14, 2020."
    future = "Court order on Wisconsin voter rolls, Feb. 28, 2020."

    class Search:
        def search(self, query, *, max_results):
            if query.endswith(" evidence") and not query.endswith("counterevidence"):
                return [{"url": "https://source.example/report", "snippet": "An article about voter rolls."}]
            return []

        def fetch(self, url, **kwargs):
            return f"One relevant report.\n\n## Our Sources\n\n{future}\n\n{past}", 200, None

    outputs = {}
    for enabled in (False, True):
        cfg = deepcopy(config)
        cfg["policy"].update(full_page_retrieval=True, search_calls_per_round=2,
                             search_source_references=enabled)
        outputs[enabled] = run_claim(
            "Wisconsin changed its voter rolls", reference_date="2020-02-26",
            domain="general", config=cfg, model=DeterministicBackend(), retriever=Search(), max_rounds=2,
        )
    baseline, candidate = outputs[False], outputs[True]
    assert baseline.research_history[0].queries == candidate.research_history[0].queries
    assert baseline.research_history[1].queries[0] == candidate.research_history[1].queries[0]
    assert candidate.research_history[1].queries[1] == past
    assert past not in baseline.search_queries
    assert future not in candidate.search_queries
    assert baseline.budget.search_calls == candidate.budget.search_calls == 4
    assert baseline.budget.scrapes == candidate.budget.scrapes
    assert baseline.verdict == candidate.verdict == "UNVERIFIED"

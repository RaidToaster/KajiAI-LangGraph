from kaji_langgraph.gate import evidence_gaps
from kaji_langgraph.graph import run_claim


def test_round_trace_replays_gate_with_exact_source_versions(config, backend, two_source_retriever):
    result = run_claim("A documented fixture claim", model=backend,
                       retriever=two_source_retriever, config=config)
    round_trace = result.research_history[-1]
    records = {(s.url, s.content_hash): s for s in result.retrieval_ledger}
    sources = [records[key] for key in round_trace.usable_source_keys]
    assert round_trace.assessment is not None
    assert evidence_gaps(round_trace.assessment, result.assertions, sources,
                         config["policy"]) == round_trace.structural_gaps == []
    assert round_trace.semantic_gaps == []
    # JSON round-tripping must preserve lookup keys and the original assessment.
    restored = type(result).model_validate_json(result.model_dump_json())
    assert restored.research_history[-1] == round_trace

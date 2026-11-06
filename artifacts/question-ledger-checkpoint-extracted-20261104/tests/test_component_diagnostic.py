"""Checks that the diagnostic adapter cannot manufacture a clean assessment."""
import importlib
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"evaluation"))
diagnostic=importlib.import_module("flash_component_diagnostic")


def decision(**changes):
    data=dict(id="anchor",proposed_verdict="TRUE",confidence="High",summary="An assertion.",
              evidence=[dict(finding="An assertion.",source="A",passage="P1",stance="supports")],
              resolved=True,gaps=["A declared gap."],contradictions=["A declared contradiction."],
              counterevidence_searched=False,sources_independent=False,
              ledger=[dict(component="whole claim",question="What establishes it?",findings=[0],
                           event_or_data_date="not established",evidentiary_origin="not established",
                           unresolved_material_question="Which period?")])
    data.update(changes)
    return diagnostic.Decision.model_validate(data)


def test_adapter_retains_ledger_questions_and_original_gap_obligations():
    case={"claim":"whole claim","records":[{"id":"A","url":"https://a.test/","passages":{"P1":"exact text"}}]}
    result=diagnostic.adapt(decision(),case)
    assert result.gaps==["A declared gap.","Which period?"]
    assert result.contradictions==["A declared contradiction."]
    assert result.assertions[0].assertion=="whole claim"
    assert result.evidence[0].quotes=={"https://a.test/":"exact text"}
    assert not result.counterevidence_searched and not result.sources_independent


def test_adapter_does_not_invent_a_quote_for_unknown_reference():
    result=diagnostic.adapt(decision(),{"claim":"whole claim","records":[]})
    assert result.evidence[0].quotes=={"unresolved:A":""}
    assert result.evidence[0].source_urls==["unresolved:A"]
    assert result.gaps

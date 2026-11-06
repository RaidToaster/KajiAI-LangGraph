from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from kaji_langgraph.llm import OllamaBackend
from kaji_langgraph.models import EvidenceAssessment,SourceRecord
from kaji_langgraph.reference_assessment import paragraph_records
from kaji_langgraph.selected_assessment import SelectionLedger,SelectedDecision,SelectionAssessmentFailure,compile_selected,selected_ranges


CLAIM="Ara said the lake level fell."


def fixture():
    source=SourceRecord(url="https://example.test/transcript",page_text="Transcript: Ara said the lake level fell.\n\nNo level measurements are supplied.",content_hash="v1",retrieved_at="2026-11-04",query="q",provider="fixture")
    selection=SelectionLedger.model_validate(dict(references=[dict(id="L1",component="C0",question="Does this record attribute the words to Ara?",reference=dict(source="S1",first_paragraph="P1",last_paragraph="P2"))],unanswered_questions=[dict(component="C0",question="Are the underlying lake measurements available?")]))
    decision=SelectedDecision.model_validate(dict(findings=[dict(id="F1",reference=dict(source="S1",first_paragraph="P1",last_paragraph="P1"),finding="The transcript attributes these words to Ara.",stance="supports")],
        origins=[dict(source="S1",underlying_origin="Transcript",verification_action="unknown",passages=["P1"],unresolved_material_questions=[])],
        components=[dict(id="C0",resolved=True,findings=["F1"],questions=[],unresolved_material_questions=[])],
        proposed_verdict="TRUE",confidence="Medium",summary="An attributed utterance.",gaps=[],contradictions=[],counterevidence_searched=False,sources_independent=False,
        nonblocking_limitations=[dict(component="C0",issue="No lake measurements.",reason_nonblocking="This claim attributes words rather than asserting measured change.")]))
    return source,selection,decision


def backend(responses):
    class Queue:
        def __init__(self):self.prompts=[]
        def bind(self,**kwargs):return self
        def invoke(self,prompt):
            self.prompts.append(prompt);value=responses.pop(0)
            if isinstance(value,Exception):raise value
            return SimpleNamespace(content=value.model_dump_json(),usage_metadata={"total_tokens":19})
    b=OllamaBackend.__new__(OllamaBackend);b.assessment_mode="extractive";b._model=Queue()
    b.temperature=0;b.line_reasoning_effort=None;b.brief_assessment_tokens=6144
    return b


def run(b,source):
    return b.analyze_indexed(CLAIM,"general",[CLAIM],[source],[],"2024-06-30",{},verification_questions=["Did Ara say it?"],planning_statements=[CLAIM],executed_queries=["q"])


def test_selector_expands_a_literal_range_without_an_invented_finding():
    source,selection,decision=fixture();ranges=selected_ranges(selection,{"C0":CLAIM},paragraph_records([source]))
    assert ranges[0]["literal_quote"]==source.page_text
    assert not {"finding","confidence","proposed_verdict","materiality"}&set(selection.model_dump())


def test_unexpected_materiality_or_factual_fields_are_rejected_not_silently_dropped():
    source,selection,decision=fixture();data=selection.model_dump()
    data["gaps"]=["An unexpected material declaration."]
    with pytest.raises(ValidationError):SelectionLedger.model_validate(data)
    data=selection.model_dump();data['references'][0]['reference']['finding']='An invented fact.'
    with pytest.raises(ValidationError):SelectionLedger.model_validate(data)


def test_all_final_material_issues_still_block_despite_nonblocking_note():
    source,selection,decision=fixture();decision.gaps=["A material concern."]
    decision.components[0].unresolved_material_questions=["Missing substantive evidence."]
    decision.origins[0].unresolved_material_questions=["Origin unverified."]
    decision.nonblocking_limitations[0].issue="A material concern."
    result=compile_selected(selection,decision,{"C0":CLAIM},paragraph_records([source]))
    assert {"A material concern.","Missing substantive evidence.","Origin unverified."}<=set(result.gaps)
    assert result.confidence=="Medium" and not result.sources_independent


def test_two_native_calls_keep_all_original_and_selected_text_and_unanswered_questions():
    source,selection,decision=fixture();b=backend([selection,decision]);result,tokens=run(b,source)
    assert len(b._model.prompts)==2 and tokens==38
    assert '"proposed_verdict"' not in b._model.prompts[0]
    assert 'No level measurements are supplied.' in b._model.prompts[1]
    assert 'Are the underlying lake measurements available?' in b._model.prompts[1]
    saved=EvidenceAssessment.model_validate_json(result.model_dump_json())
    assert saved.indexed_input['selection_ledger']==selection.model_dump(mode='json')
    assert saved.assertions[0].assertion==CLAIM
    assert saved.indexed_input['selected_decision']==decision.model_dump(mode='json')


def test_invalid_first_range_stops_before_adjudication_and_preserves_selection():
    source,selection,decision=fixture();selection.references[0].reference.last_paragraph="P999"
    b=backend([selection,decision])
    with pytest.raises(SelectionAssessmentFailure) as caught:run(b,source)
    assert len(b._model.prompts)==1
    assert caught.value.partial_assessment.indexed_input['selection_ledger']==selection.model_dump(mode='json')


def test_second_stage_failure_keeps_first_stage_lookup_and_usage():
    source,selection,decision=fixture();b=backend([selection,ValueError('bad final')])
    with pytest.raises(SelectionAssessmentFailure) as caught:run(b,source)
    p=caught.value.partial_assessment
    assert p.proposed_verdict=='UNVERIFIED'
    assert p.indexed_input['records'][0]['paragraph_offsets']
    assert p.indexed_input['selection_first_stage_tokens']==19

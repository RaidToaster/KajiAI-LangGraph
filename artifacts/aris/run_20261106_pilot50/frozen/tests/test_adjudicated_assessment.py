from types import SimpleNamespace

from kaji_langgraph.adjudicated_assessment import AdjudicatedDecision,CLASSES,compile_adjudicated
from kaji_langgraph.llm import OllamaBackend
from kaji_langgraph.models import EvidenceAssessment,SourceRecord
from kaji_langgraph.reference_assessment import paragraph_records
from kaji_langgraph.selected_assessment import SelectionLedger


CLAIM="The independently measured city median in 2023 was below 30 minutes."


def fixture():
    sources=[SourceRecord(url=f"https://{host}.test/record",page_text=text,content_hash=host,retrieved_at="2026-11-04",query="q",provider="fixture") for host,text in [
        ('a','Lab A independently collected a 2023 citywide sample and calculated a median of 28 minutes.'),
        ('b','Lab B independently collected a 2023 citywide sample and calculated a median of 34 minutes. The discrepancy is unresolved.')]]
    def ref(id):return dict(source=id,first_paragraph='P1',last_paragraph='P1')
    raw=AdjudicatedDecision.model_validate(dict(findings=[dict(id=f'F{i}',reference=ref(f'S{i}'),finding=text,stance=stance) for i,text,stance in [(1,'Lab A reports a median of 28 minutes.','supports'),(2,'Lab B reports a median of 34 minutes.','refutes')]],
        origins=[dict(source=f'S{i}',origin=ref(f'S{i}'),verification_action=ref(f'S{i}'),unresolved_material_questions=[]) for i in [1,2]],
        components=[dict(id='C0',adjudication='conflicting',findings=['F1','F2'],rationale='The supplied estimates oppose the same threshold.',questions=[],unresolved_material_questions=[])],
        proposed_verdict='CONFLICTING',confidence='Medium',summary='Opposed reported estimates, not a significance claim.',gaps=[],contradictions=[],counterevidence_searched=False,sources_independent=False,nonblocking_limitations=[]))
    return sources,raw


def test_explicit_component_classes_encode_the_original_guard_without_changing_confidence():
    sources,raw=fixture()
    for outcome,label in CLASSES.items():
        raw.components[0].adjudication=outcome;raw.proposed_verdict=label
        result=compile_adjudicated(raw,{'C0':CLAIM},paragraph_records(sources))
        assert result.assertions[0].resolved==(outcome!='insufficient')
        assert result.assertions[0].assertion==CLAIM
        assert result.confidence=='Medium' and not result.sources_independent
        assert result.component_ledger[0]['explicit_adjudications']==[outcome]


def test_conflicting_class_does_not_clear_any_material_declaration():
    sources,raw=fixture();raw.gaps=['Declared gap.'];raw.contradictions=['Declared contradiction.']
    raw.components[0].unresolved_material_questions=['Component issue.']
    raw.origins[1].unresolved_material_questions=['Origin issue.']
    result=compile_adjudicated(raw,{'C0':CLAIM},paragraph_records(sources))
    assert result.assertions[0].resolved
    assert {'Declared gap.','Component issue.','Origin issue.'}<=set(result.gaps)
    assert result.contradictions==['Declared contradiction.']


def test_c0_global_mismatch_blocks_and_keeps_both_judgments():
    sources,raw=fixture();raw.components[0].adjudication='insufficient'
    result=compile_adjudicated(raw,{'C0':CLAIM},paragraph_records(sources))
    assert any('C0 adjudication differs' in g for g in result.gaps)
    assert result.proposed_verdict=='CONFLICTING' and not result.assertions[0].resolved
    assert result.indexed_input['explicit_adjudication_response']['components'][0]['adjudication']=='insufficient'


def test_origin_action_and_date_are_literal_and_roundtrip_preserves_roles():
    sources,raw=fixture();result=compile_adjudicated(raw,{'C0':CLAIM},paragraph_records(sources))
    saved=EvidenceAssessment.model_validate_json(result.model_dump_json())
    assert saved.source_origin_ledger[0]['underlying_origin']==sources[0].page_text
    assert saved.source_origin_ledger[0]['verification_action']==sources[0].page_text
    assert saved.source_origin_ledger[0]['event_or_data_date']==''
    assert saved.source_origin_ledger[0]['date_mentions'][0]['text']=='2023'
    assert saved.source_origin_ledger[0]['date_mentions'][0]['role']=='unassigned'
    assert saved.source_origin_ledger[0]['publication_date']==''
    assert saved.indexed_input['explicit_adjudication_response']==raw.model_dump(mode='json')


def test_invalid_role_reference_remains_blocked_without_pruning():
    sources,raw=fixture();raw.origins[0].verification_action.source='S2'
    raw.origins.append(raw.origins[1].model_copy(update={'source':'S9','unresolved_material_questions':['Uncited adverse issue.']}))
    result=compile_adjudicated(raw,{'C0':CLAIM},paragraph_records(sources))
    assert any('Invalid literal source action' in g for g in result.gaps)
    assert 'Uncited adverse issue.' in result.gaps
    assert len(result.evidence)==2


def test_native_two_call_dispatch_uses_the_new_class_contract():
    sources,raw=fixture();selection=SelectionLedger.model_validate(dict(references=[dict(id='L1',component='C0',question='What estimate is reported?',reference=dict(source='S1',first_paragraph='P1',last_paragraph='P1'))],unanswered_questions=[]))
    responses=[selection,raw]
    class Queue:
        def __init__(self):self.prompts=[]
        def bind(self,**kwargs):return self
        def invoke(self,prompt):
            self.prompts.append(prompt)
            return SimpleNamespace(content=responses.pop(0).model_dump_json(),usage_metadata={'total_tokens':23})
    b=OllamaBackend.__new__(OllamaBackend);b.assessment_mode='adjudicated';b._model=Queue();b.line_reasoning_effort=None;b.temperature=0;b.brief_assessment_tokens=6144
    result,tokens=b.analyze_indexed(CLAIM,'general',[CLAIM],sources,[],'2024-06-30',{},verification_questions=[],planning_statements=[])
    assert len(b._model.prompts)==2 and tokens==46
    assert 'Do NOT return a resolved' in b._model.prompts[1]
    assert result.indexed_input['assessment_mode']=='adjudicated'
    assert result.indexed_input['explicit_adjudication_response']['components'][0]['adjudication']=='conflicting'


def test_date_fields_are_rejected_instead_of_silently_repaired():
    import pytest
    from pydantic import ValidationError
    sources, raw = fixture()
    data = raw.model_dump()
    data['origins'][0]['event_or_data_date'] = {'text':'2023'}
    with pytest.raises(ValidationError):
        AdjudicatedDecision.model_validate(data)


def test_adjudication_inventory_keeps_unselected_sources_visible():
    from kaji_langgraph.adjudicated_assessment import adjudication_prompt,record_inventory
    sources,raw=fixture()
    records=paragraph_records(sources)
    selection=SelectionLedger(references=[],unanswered_questions=[])
    inventory=record_inventory(records,[])
    assert inventory['visible_source_ids']==['S1','S2']
    assert inventory['unselected_source_ids']==['S1','S2']
    prompt=adjudication_prompt({'records':records},selection,[])
    assert 'source_reported_publication_evidence' not in prompt
    assert 'record_inventory' in prompt and sources[1].page_text in prompt

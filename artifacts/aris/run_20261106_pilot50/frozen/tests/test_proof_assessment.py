import pytest
from pydantic import ValidationError
from types import SimpleNamespace

from kaji_langgraph.models import SourceRecord, EvidenceAssessment
from kaji_langgraph.reference_assessment import paragraph_records
from kaji_langgraph.selected_assessment import SelectionLedger
from kaji_langgraph.catalogued_assessment import CatalogueSelection, _catalogue
from kaji_langgraph.proof_assessment import ProofDecision, compile_proof
from kaji_langgraph.llm import OllamaBackend


def fixture():
    sources=[SourceRecord(url=f'https://{i}.test/record',page_text='Our own recording documents the vote as seven to two.',retrieved_at='2026-11-05',query='vote opposition',provider='fixture',content_hash=str(i)) for i in (1,2)]
    records=paragraph_records(sources)
    selection=SelectionLedger(references=[],unanswered_questions=[])
    raw=ProofDecision.model_validate(dict(findings=[dict(id='F1',reference='S1:P1:P1',finding='The source reports its own recording documents a seven-to-two vote.',stance='supports')],origins=[dict(source='S1',origin='S1:P1:P1',verification_action='S1:P1:P1')],components=[dict(id='C0',adjudication='supported',findings=['F1'])],proposed_verdict='TRUE',confidence='High',issues=[],counterevidence_searched=True,sources_independent=False))
    return sources,records,selection,raw


def test_status_summary_invents_no_source_method_and_keeps_model_decisions():
    _,records,selection,raw=fixture()
    result=compile_proof(selection,raw,{'C0':'Exact original claim.'},records)
    assert result.summary=='Model proposal: TRUE; confidence: High. See linked findings and retained issues.'
    assert result.proposed_verdict=='TRUE' and result.confidence=='High'
    assert not result.sources_independent and result.assertions[0].assertion=='Exact original claim.'
    saved=EvidenceAssessment.model_validate_json(result.model_dump_json())
    assert saved.indexed_input['proof_response']==raw.model_dump(mode='json')


def test_every_material_issue_blocks_and_retains_component_and_origin_mapping():
    _,records,selection,raw=fixture()
    from kaji_langgraph.proof_assessment import ProofIssue
    raw.issues=[ProofIssue(id='I1',component='C0',source='S1',question='Authenticated recording?',classification='material',reason='No authenticated primary record supplied.')]
    result=compile_proof(selection,raw,{'C0':'Claim'},records)
    issue='Authenticated recording? No authenticated primary record supplied.'
    assert issue in result.gaps
    assert issue in result.component_ledger[0]['unresolved_material_questions']
    assert issue in result.source_origin_ledger[0]['unresolved_material_questions']
    assert result.confidence=='High'  # Never silently change the model's judgment.


def test_nonblocking_classification_is_explicit_and_cannot_clear_another_material_issue():
    _,records,selection,raw=fixture()
    from kaji_langgraph.proof_assessment import ProofIssue
    raw.issues=[ProofIssue(id='I1',component='C0',question='Secondary issue?',classification='nonblocking',reason='Outside the exact speech target.'),ProofIssue(id='I2',component='C0',question='Same evidence authenticated?',classification='material',reason='This undermines the verdict.')]
    result=compile_proof(selection,raw,{'C0':'Claim'},records)
    assert any('This undermines' in g for g in result.gaps)
    assert len(result.indexed_input['proof_issue_registry'])==2
    assert len(result.indexed_input['selected_decision']['nonblocking_limitations'])==1


def test_factual_recaps_and_legacy_material_fields_are_rejected_not_discarded():
    _,_,_,raw=fixture()
    for key,value in [('summary','All sources independently verified it.'),('gaps',['A material gap.'])]:
        with pytest.raises(ValidationError):
            ProofDecision.model_validate({**raw.model_dump(),key:value})


def test_contextual_blockquote_citation_includes_its_immediate_heading_date():
    sources,_,_,_=fixture()
    sources[0].page_text="Here's the statement released on Feb. 26:\n\n> The response is effective."
    records=paragraph_records(sources)
    catalogue=_catalogue(records,[])
    assert 'S1:P2:P2' not in catalogue
    assert catalogue['S1:P1:P2']['literal_quote']==sources[0].page_text


def test_fixed_chunk_cannot_bypass_bound_heading_at_greedy_boundary():
    sources,_,_,_=fixture()
    sources[0].page_text='Earlier '*200+"\n\nStatement released Feb. 26:\n\n> "+'Body '*100+'\n\n'+'Later '*100
    records=paragraph_records(sources)
    catalogue=_catalogue(records,[])
    assert 'S1:P2:P3' in catalogue and 'S1:P4:P4' in catalogue
    for entry in catalogue.values():
        ref=entry['reference']
        if ref['source']=='S1' and int(ref['first_paragraph'][1:])<=3<=int(ref['last_paragraph'][1:]):
            assert int(ref['first_paragraph'][1:])<=2
    assert records[0]['visible_text']==sources[0].page_text.rstrip()


@pytest.mark.parametrize('mode',['catalogued','proof'])
def test_full_workflow_builder_accepts_the_new_modes_without_services(mode):
    from kaji_langgraph.config import load_config
    from kaji_langgraph.graph import build_graph
    config=load_config();config['model']['assessment_mode']=mode;config['jev']['enabled']=False
    assert build_graph(model=object(),retriever=object(),config=config) is not None


def test_native_proof_dispatch_uses_two_calls_and_retains_neutral_questions():
    sources,_,_,raw=fixture()
    selection=CatalogueSelection.model_validate({'references':[{'id':'L1','component':'C0','question':'What does the recording report?','reference':'S1:P1:P1'}],'unanswered_questions':[{'component':'C0','question':'Is it authenticated?'}]})
    responses=[selection,raw]
    class Queue:
        def bind(self,**kwargs):return self
        def invoke(self,prompt):return SimpleNamespace(content=responses.pop(0).model_dump_json(),usage_metadata={'total_tokens':10})
    b=OllamaBackend.__new__(OllamaBackend);b.assessment_mode='proof';b._model=Queue();b.line_reasoning_effort='high';b.temperature=0;b.brief_assessment_tokens=6144
    result,tokens=b.analyze_indexed('Claim','general',['Claim'],sources,[],'2024-01-01',{},verification_questions=[],planning_statements=[])
    assert tokens==20 and result.indexed_input['assessment_mode']=='proof'
    assert result.indexed_input['catalogue_selection']['unanswered_questions'][0]['question']=='Is it authenticated?'

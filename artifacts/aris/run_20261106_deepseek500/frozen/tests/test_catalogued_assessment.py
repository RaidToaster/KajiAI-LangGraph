import json
import pytest
from types import SimpleNamespace

from kaji_langgraph.catalogued_assessment import CatalogueDecision, passage_catalogue, compile_catalogue, catalogue_prompt
from kaji_langgraph.models import SourceRecord, EvidenceAssessment
from kaji_langgraph.reference_assessment import paragraph_records
from kaji_langgraph.selected_assessment import SelectionLedger
from kaji_langgraph.llm import OllamaBackend


def fixture():
    sources=[SourceRecord(url=f'https://{i}.test/a',page_text='Meeting 2023: 7 votes for.\n\nNo reversal; this is an independent attendance record.',content_hash=str(i),retrieved_at="2026-11-05",query="q",provider="fixture") for i in (1,2)]
    records=paragraph_records(sources)
    selection=SelectionLedger.model_validate({'references':[{'id':'L1','component':'C0','question':'What happened?', 'reference':{'source':'S1','first_paragraph':'P1','last_paragraph':'P2'}}],'unanswered_questions':[]})
    raw=CatalogueDecision.model_validate(dict(findings=[dict(id='F1',reference='S1:P1:P2',finding='The meeting record reports 7 votes for with no reversal.',stance='supports')],origins=[dict(source='S1',origin='S1:P1:P2',verification_action='S1:P2:P2',unresolved_material_questions=[])],components=[dict(id='C0',adjudication='supported',findings=['F1'])],proposed_verdict='TRUE',confidence='High',summary='Recorded.',gaps=[],contradictions=[],counterevidence_searched=True,sources_independent=False))
    return sources,records,selection,raw


def test_catalogue_retains_complete_selected_context_and_all_unselected_paragraphs():
    sources,records,selection,raw=fixture()
    catalogue=passage_catalogue(records,selection,{'C0':'Claim'})
    assert catalogue['S1:P1:P2']['literal_quote']==sources[0].page_text
    assert 'S2:P2:P2' in catalogue
    result=compile_catalogue(selection,raw,{'C0':'Claim'},records)
    saved=EvidenceAssessment.model_validate_json(result.model_dump_json())
    assert saved.evidence[0].quotes[sources[0].url]==sources[0].page_text
    assert saved.indexed_input['catalogue_response']==raw.model_dump(mode='json')
    assert saved.confidence=='High' and not saved.sources_independent


def test_unknown_id_is_retained_and_blocks_instead_of_nearest_match_repair():
    _,records,selection,raw=fixture();raw.findings[0].reference='S1:P1:P9'
    raw.gaps=['Material issue.']
    result=compile_catalogue(selection,raw,{'C0':'Claim'},records)
    assert 'Material issue.' in result.gaps
    assert any('Unknown passage catalogue ID' in g for g in result.gaps)
    assert result.indexed_input['catalogue_response']['findings'][0]['reference']=='S1:P1:P9'


def test_valid_catalogue_id_for_wrong_origin_source_still_blocks():
    _,records,selection,raw=fixture();raw.origins[0].origin='S2:P1:P1'
    result=compile_catalogue(selection,raw,{'C0':'Claim'},records)
    assert any('Invalid literal origin reference' in g for g in result.gaps)


def test_native_dispatch_preserves_two_call_selection_and_client_lookup():
    from kaji_langgraph.catalogued_assessment import CatalogueSelection
    sources,records,selection,raw=fixture()
    chosen=CatalogueSelection.model_validate({"references":[{"id":"L1","component":"C0","question":"What happened?","reference":"S1:P1:P2"}],"unanswered_questions":[]})
    responses=[chosen,raw]
    class Queue:
        def bind(self,**kwargs):return self
        def invoke(self,prompt):
            return SimpleNamespace(content=responses.pop(0).model_dump_json(),usage_metadata={'total_tokens':10})
    b=OllamaBackend.__new__(OllamaBackend);b.assessment_mode='catalogued';b._model=Queue();b.line_reasoning_effort=None;b.temperature=0;b.brief_assessment_tokens=6144
    result,tokens=b.analyze_indexed('Claim','general',['Claim'],sources,[],'2024-01-01',{},verification_questions=[],planning_statements=[])
    assert tokens==20 and result.indexed_input['assessment_mode']=='catalogued'
    assert 'S1:P1:P2' in result.indexed_input['passage_catalogue']


def test_prompt_catalogue_keeps_original_multiline_separators():
    from kaji_langgraph.selected_assessment import selected_ranges
    sources,records,selection,raw=fixture()
    source=sources[0];source.page_text=source.page_text.replace('\n\n','\n\n\n')
    records=paragraph_records(sources)
    ranges=selected_ranges(selection,{'C0':'Claim'},records)
    visible=[{k:v for k,v in r.items() if k not in {'visible_text','paragraph_offsets'}} for r in records]
    prompt=catalogue_prompt({'records':visible,'required_components':{'C0':'Claim'}},selection,ranges)
    payload=json.loads(prompt.split('{"records":',1)[1].rsplit('\nReturn ONLY JSON matching:',1)[0].join(['{"records":','']))
    assert payload['passage_catalogue']['S1:P1:P2']['literal_quote']==source.page_text


def test_request_schema_explicitly_separates_bound_id_namespaces():
    from kaji_langgraph.selected_assessment import selected_ranges
    _,records,selection,_=fixture()
    prompt=catalogue_prompt({'records':records,'required_components':{'C0':'Claim'}},selection,selected_ranges(selection,{'C0':'Claim'},records))
    schema=json.loads(prompt.split('\nReturn ONLY JSON matching:\n')[1])
    assert schema['$defs']['ComponentClass']['properties']['id']['enum']==['C0']
    assert schema['$defs']['CatalogueOrigin']['properties']['source']['enum']==['S1','S2']
    assert 'S1:P1:P2' in schema['$defs']['CatalogueFinding']['properties']['reference']['enum']


def test_fixed_chunks_are_intact_and_never_cross_a_long_paragraph():
    sources,_,selection,_=fixture()
    sources[0].page_text='A '*130+'\n\n'+'B '*130+'\n\n'+'C '*251+'\n\n'+'D '*20
    records=paragraph_records(sources)
    from kaji_langgraph.catalogued_assessment import _catalogue
    catalogue=_catalogue(records,[])
    assert 'S1:P1:P2' not in catalogue and 'S1:P3:P3' not in catalogue
    assert all(len(entry['literal_quote'].split())<=250 for entry in catalogue.values())
    assert catalogue['S1:P4:P4']['literal_quote']==records[0]['passages']['P4']


def test_invalid_first_stage_catalogue_id_stops_second_call_and_retains_raw():
    from kaji_langgraph.catalogued_assessment import CatalogueSelection
    from kaji_langgraph.selected_assessment import SelectionAssessmentFailure
    sources,_,_,_=fixture()
    chosen=CatalogueSelection.model_validate({'references':[{'id':'L1','component':'C0','question':'What happened?','reference':'S1:P1:P999'}],'unanswered_questions':[]})
    class Queue:
        calls=0
        def bind(self,**kwargs):return self
        def invoke(self,prompt):
            self.calls+=1
            return SimpleNamespace(content=chosen.model_dump_json(),usage_metadata={'total_tokens':13})
    b=OllamaBackend.__new__(OllamaBackend);b.assessment_mode='catalogued';b._model=Queue();b.line_reasoning_effort=None;b.temperature=0;b.brief_assessment_tokens=6144
    with pytest.raises(SelectionAssessmentFailure) as error:
        b.analyze_indexed('Claim','general',['Claim'],sources,[],'2024-01-01',{},verification_questions=[],planning_statements=[])
    assert b._model.calls==1
    partial=error.value.partial_assessment
    assert partial.indexed_input['selection_first_stage_tokens']==13
    assert partial.indexed_input['selection_ledger']['references'][0]['reference']=='S1:P1:P999'
    assert partial.indexed_input['records'][0]['visible_text']==sources[0].page_text

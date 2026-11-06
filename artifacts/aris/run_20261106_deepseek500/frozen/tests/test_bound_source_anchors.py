import json
from types import SimpleNamespace

import pytest

from test_evidence_adjudicated import inputs
from kaji_langgraph.jev import JevClient
from kaji_langgraph.source_paths import review_source_paths
from kaji_langgraph.evidence_adjudicated import BoundEvidencePaths
from kaji_langgraph.passage_decision import unit_table
from kaji_langgraph.llm import OllamaBackend


def verifier(*,wrong=False):
    client=JevClient()
    def ask(state,questions,*,timeout):
        if 'source_paths' in questions:
            assert 'U1' in questions['S1_origin']['criteria'] and 'U2' not in questions['S1_origin']['criteria']
            assert 'U2' in questions['S2_verification_action']['criteria'] and 'U1' not in questions['S2_verification_action']['criteria']
            result={'source_paths':dict(choice='shared',confidence=.9)}
            for source,unit in (('S1','U1'),('S2','U2')):
                for field in ('origin','verification_action'):
                    result[source+'_'+field]=dict(choice='U2' if wrong and source=='S1' else unit,confidence=.7)
            return result,7
        return {key:dict(choice='context',confidence=.99) for key in questions},7
    client._ask=ask
    return client


def test_source_bound_options_reject_cross_source_choice_before_any_adjudication():
    sources,_,_,_=inputs()
    with pytest.raises(ValueError):review_source_paths(verifier(wrong=True),'Claim',sources,timeout=12,bind_anchors=True)


def test_bound_catalogue_is_component_independent_and_all_semantic_choices_survive():
    sources,records,_,_=inputs()
    assert unit_table(records,{'C0':'Claim'})==unit_table(records,{'C0':'Claim','C1':'Fragment'})
    feedback,tokens=review_source_paths(verifier(),'Claim',sources,timeout=12,bind_anchors=True)
    assert tokens==7 and feedback['bound_origins'][1]['origin']=='U2'
    assert feedback['bound_origins'][0]['origin_confidence']==.7
    assert len(feedback['anchor_catalogue_sha256'])==64


def test_path_model_cannot_emit_or_override_source_bound_anchors():
    sources,_,selection,paths=inputs();client=verifier()
    feedback,_=review_source_paths(client,'Claim',sources,timeout=12,bind_anchors=True)
    class Queue:
        calls=0
        def bind(self,**kwargs):return self
        def invoke(self,text):
            self.calls+=1
            schema=json.loads(text.rsplit('\nReturn ONLY JSON matching:\n',1)[1])
            if self.calls==1:raw=selection
            else:
                assert 'origins' not in schema['properties']
                assert 'Do not emit or alter those fields' in text
                raw=BoundEvidencePaths.model_validate(paths.model_dump(exclude={'origins'}))
            return SimpleNamespace(content=raw.model_dump_json(),usage_metadata={'total_tokens':17})
    b=OllamaBackend.__new__(OllamaBackend);b.assessment_mode='evidence_adjudicated';b._model=Queue()
    b.line_reasoning_effort='high';b.temperature=0;b.brief_assessment_tokens=6144
    result,tokens=b.analyze_indexed('Claim','general',['Claim'],sources,[],'2024-01-01',{},
        verification_questions=[],planning_statements=[],source_path_review=feedback,relation_reviewer=client)
    assert tokens==41 and not result.sources_independent and result.confidence==selection.confidence
    assert 'origins' not in result.indexed_input['path_model_response']
    assert result.indexed_input['evidence_paths']['origins'][1]['source']=='S2'
    assert result.indexed_input['evidence_paths']['origins'][1]['origin']=='U2'
    assert result.indexed_input['source_path_review']==feedback
    bad={**feedback,'anchor_catalogue_sha256':'stale'}
    with pytest.raises(RuntimeError):
        b.analyze_indexed('Claim','general',['Claim'],sources,[],'2024-01-01',{},
            verification_questions=[],planning_statements=[],source_path_review=bad,relation_reviewer=client)
    assert b._model.calls==2

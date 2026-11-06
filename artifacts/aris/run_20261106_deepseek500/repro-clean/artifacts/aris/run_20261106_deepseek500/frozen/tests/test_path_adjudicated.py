import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from test_passage_decision import decision
from kaji_langgraph.path_adjudicated import ClaimDecision,PathDecision,compile_path_adjudicated
from kaji_langgraph.llm import OllamaBackend


def fixture():
    sources,records,old=decision()
    data=old.model_dump(exclude={'origins','sources_independent'})
    data['findings'].append(dict(unit='U2',stance='supports'))
    data['components'][0]['units'].append('U2')
    data['issues']=[dict(component='C0',classification='nonblocking',dependency='independence_unresolved',basis_units=['U1','U2'])]
    claim=ClaimDecision.model_validate(data)
    paths=PathDecision.model_validate(dict(origins=[dict(source=f'S{i}',origin=f'U{i}',verification_action=f'U{i}') for i in (1,2)],
        relations=[dict(left='S1',right='S2',evidence_origins='shared',obtaining_process='independent',basis_units=['U1','U2'])],
        sources_independent=False,
        issues=[dict(component='C0',classification='material',dependency='independence_unresolved',basis_units=['U1','U2'])]))
    return sources,records,claim,paths


def test_distinct_head_judgments_and_every_issue_survive_without_overrides():
    _,records,claim,paths=fixture()
    result=compile_path_adjudicated(claim,paths,{'C0':'Claim'},records)
    assert not result.sources_independent and result.confidence=='High' and result.proposed_verdict=='TRUE'
    assert len(result.evidence)==2 and len(result.indexed_input['passage_issue_registry'])==2
    assert result.indexed_input['issue_head_order']==['claim','paths']
    assert result.gaps and result.indexed_input['path_decision']==paths.model_dump(mode='json')
    assert result.indexed_input['path_relation_context'][0]['passages'][1]['quote']
    with pytest.raises(ValidationError):
        ClaimDecision.model_validate({**claim.model_dump(),'sources_independent':True})


@pytest.mark.parametrize('change',['boolean_contradiction','missing_pair','unknown_basis','duplicate_pair'])
def test_relational_contract_fails_without_repair(change):
    _,records,claim,paths=fixture();data=paths.model_dump()
    if change=='boolean_contradiction':data['sources_independent']=True
    if change=='missing_pair':data['relations']=[]
    if change=='unknown_basis':data['relations'][0]['basis_units']=['U999']
    if change=='duplicate_pair':data['relations'].append(data['relations'][0])
    with pytest.raises(ValueError):
        compile_path_adjudicated(claim,PathDecision.model_validate(data),{'C0':'Claim'},records)


def test_native_dispatch_uses_two_fixed_heads_and_withholds_class_from_path_head():
    sources,_,claim,paths=fixture()
    class Queue:
        calls=0
        def bind(self,**kwargs):return self
        def invoke(self,prompt):
            self.calls+=1
            schema=json.loads(prompt.rsplit('\nReturn ONLY JSON matching:\n',1)[1])
            if self.calls==1:
                assert 'sources_independent' not in schema['properties']
                raw=claim
            else:
                assert 'proposed_verdict' not in schema['properties']
                assert 'confidence' not in schema['properties']
                assert '"proposed_verdict": "TRUE"' not in prompt
                assert 'required_source_pairs' in prompt
                raw=paths
            return SimpleNamespace(content=raw.model_dump_json(),usage_metadata={'total_tokens':17})
    b=OllamaBackend.__new__(OllamaBackend);b.assessment_mode='path_adjudicated';b._model=Queue()
    b.line_reasoning_effort='high';b.temperature=0;b.brief_assessment_tokens=6144
    result,tokens=b.analyze_indexed('Claim','general',['Claim'],sources,[],'2024-01-01',{},
        verification_questions=[],planning_statements=[])
    assert b._model.calls==2 and tokens==34 and result.indexed_input['assessment_mode']=='path_adjudicated'

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from test_path_adjudicated import fixture
from kaji_langgraph.evidence_adjudicated import ClaimSelection,EvidencePaths,compile_evidence_adjudicated
from kaji_langgraph.llm import OllamaBackend
from kaji_langgraph.jev import JevClient


def inputs():
    sources,records,claim,old=fixture()
    selection=ClaimSelection.model_validate({**claim.model_dump(exclude={'findings'}),
        'findings':[{'unit':f.unit} for f in claim.findings]})
    paths=EvidencePaths.model_validate({**old.model_dump(exclude={'relations'}),
        'relations':[dict(left='S1',right='S2',evidence_paths='shared_origin',basis_units=['U1','U2'])],
        'next_queries':['primary original record verification']})
    return sources,records,selection,paths


def test_semantic_stances_are_owned_by_reviewer_without_pruning_or_class_override():
    _,records,selection,paths=inputs()
    reviews=[dict(stance='context',confidence=.98),dict(stance='supports',confidence=.7)]
    result=compile_evidence_adjudicated(selection,paths,reviews,{'C0':'Claim'},records)
    assert len(result.evidence)==2 and result.evidence[0].stance=='context'
    assert result.proposed_verdict=='TRUE' and result.confidence=='High'
    assert result.gaps and 'Claim-to-passage stance review remains uncertain.' in result.gaps
    assert len(result.indexed_input['passage_issue_registry'])==2
    assert result.next_queries[0]=='primary original record verification'
    assert result.indexed_input['stance_reviews']==reviews
    with pytest.raises(ValidationError):
        ClaimSelection.model_validate({**selection.model_dump(), 'findings':[dict(unit='U1',stance='refutes')]})
    data=paths.model_dump();data['relations'][0]['obtaining_process']='independent'
    with pytest.raises(ValidationError):EvidencePaths.model_validate(data)


def test_judgment_checks_exact_quote_against_claim_not_literal_reporting_caption():
    jev=JevClient()
    def ask(state,questions,*,timeout):
        assert state['claim']=='Graham said the quoted words.'
        assert state['candidates'][0]['quote']=='The tweet has been deleted and is circulating.'
        assert 'ONLY' in questions['stance_0']['instructions']
        assert 'Deletion/circulation metadata alone does not refute' in questions['stance_0']['instructions']
        return {'stance_0':dict(choice='context',confidence=.99)},7
    jev._ask=ask
    reviews,tokens=jev.classify_claim_relations('Graham said the quoted words.',
        [dict(unit='U13',quote='The tweet has been deleted and is circulating.')],timeout=12)
    assert reviews==[dict(stance='context',confidence=.99)] and tokens==7


def test_production_graph_runs_semantic_stance_between_heads_and_counts_all_tokens():
    from kaji_langgraph.graph import WorkflowNodes
    from kaji_langgraph.models import BudgetState
    from kaji_langgraph.config import load_config
    import time
    sources,_,selection,paths=inputs();calls=[]
    class Queue:
        def bind(self,**kwargs):return self
        def invoke(self,text):
            calls.append('flash')
            first=calls.count('flash')==1
            schema=json.loads(text.rsplit('\nReturn ONLY JSON matching:\n',1)[1])
            if first:assert 'stance' not in schema['$defs']['UnitPick']['properties']
            else:assert '"proposed_verdict": "TRUE"' not in text
            return SimpleNamespace(content=(selection if first else paths).model_dump_json(),usage_metadata={'total_tokens':17})
    class Jev:
        model='jev-1.13.0'
        def check_source_paths(self,*args,**kwargs):
            calls.append('paths');return dict(relation='shared',confidence=.9),7
        def classify_claim_relations(self,claim,candidates,*,timeout):
            calls.append('stance')
            assert [r['unit'] for r in candidates]==['U1','U2']
            return [dict(stance='context',confidence=.99),dict(stance='supports',confidence=.99)],7
    backend=OllamaBackend.__new__(OllamaBackend);backend.assessment_mode='evidence_adjudicated'
    backend._model=Queue();backend.line_reasoning_effort='high';backend.temperature=0;backend.brief_assessment_tokens=6144
    config=load_config();config['model'].update(assessment_mode='evidence_adjudicated',predecision_source_path_review=True)
    nodes=WorkflowNodes(backend,None,config,Jev());nodes.usable_sources=lambda state:sources
    state=dict(claim='Claim',domain='general',assertions=['Claim'],reference_date='2024-01-01',sources=sources,
        budgets=BudgetState(max_seconds=300,started_at_monotonic=time.monotonic()))
    result=nodes.analyze(state)
    assert calls==['paths','flash','stance','flash'] and result['budgets'].tokens_used==48
    assert result['assessment'].evidence[0].stance=='context'
    assert result['assessment'].indexed_input['assessment_mode']=='evidence_adjudicated'

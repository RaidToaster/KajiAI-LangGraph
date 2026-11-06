import json
from types import SimpleNamespace

from test_passage_decision import decision
from kaji_langgraph.source_paths import review_source_paths
from kaji_langgraph.jev import JevClient
from kaji_langgraph.llm import OllamaBackend


def test_path_review_is_a_separate_judgment_not_a_verdict_or_certified_fact():
    client=JevClient()
    def ask(state,questions,*,timeout):
        assert 'verdict' not in state and 'records' in state
        assert set(questions['source_paths']['criteria']) == {'independent','shared','unclear'}
        return {'source_paths':{'choice':'shared','confidence':.91}},7
    client._ask=ask
    sources,_,_=decision()
    feedback,tokens=review_source_paths(client,'Claim',sources,timeout=12)
    assert feedback['review'] == {'relation':'shared','confidence':.91}
    assert feedback['source_ids'] == ['S1','S2'] and tokens==7
    assert len(feedback['input_sha256'])==64


def test_feedback_reaches_model_but_does_not_override_its_judgments():
    sources,_,raw=decision()
    raw.sources_independent=True
    feedback={'review':{'relation':'shared','confidence':.91},'scope':'Automated judgment only'}
    class Queue:
        def bind(self,**kwargs):return self
        def invoke(self,prompt):
            assert json.dumps(feedback) in prompt
            return SimpleNamespace(content=raw.model_dump_json(),usage_metadata={'total_tokens':17})
    backend=OllamaBackend.__new__(OllamaBackend)
    backend.assessment_mode='passage_decision';backend._model=Queue()
    backend.line_reasoning_effort='high';backend.temperature=0;backend.brief_assessment_tokens=6144
    result,tokens=backend.analyze_indexed('Claim','general',['Claim'],sources,[],'2024-01-01',{},
        verification_questions=[],planning_statements=[],source_path_review=feedback)
    assert result.indexed_input['source_path_review']==feedback
    assert result.sources_independent is True and result.confidence==raw.confidence
    assert result.proposed_verdict==raw.proposed_verdict and tokens==17


def test_production_graph_checks_paths_before_adjudication_and_counts_tokens():
    from kaji_langgraph.graph import WorkflowNodes
    from kaji_langgraph.models import BudgetState
    from kaji_langgraph.config import load_config
    sources,_,_=decision()
    calls=[]
    class Jev:
        model='jev-1.13.0'
        def check_source_paths(self,claim,records,*,timeout):
            calls.append('paths');return {'relation':'unclear','confidence':.8},7
    class Backend:
        def analyze_indexed(self,*args,**kwargs):
            calls.append('adjudicate')
            assert kwargs['source_path_review']['review']['relation']=='unclear'
            from kaji_langgraph.models import EvidenceAssessment
            return EvidenceAssessment(),17
    config=load_config();config['model'].update(assessment_mode='passage_decision',predecision_source_path_review=True)
    nodes=WorkflowNodes(Backend(),None,config,Jev())
    nodes.usable_sources=lambda state:sources
    state=dict(claim='Claim',domain='general',assertions=['Claim'],reference_date='2024-01-01',
        sources=sources,budgets=BudgetState(max_seconds=300))
    import time
    state['budgets'].started_at_monotonic=time.monotonic()
    result=nodes.analyze(state)
    assert calls==['paths','adjudicate']
    assert result['budgets'].tokens_used==24

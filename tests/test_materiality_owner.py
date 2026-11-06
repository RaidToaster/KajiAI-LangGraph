import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from test_evidence_adjudicated import inputs
from test_bound_source_anchors import verifier
from kaji_langgraph.source_paths import review_source_paths
from kaji_langgraph.evidence_adjudicated import ClaimClassSelection,OwnedBoundEvidencePaths
from kaji_langgraph.llm import OllamaBackend


def run(*,assignment='material',class_effect='class_consistent',missing=False):
    sources,_,old,paths=inputs();client=verifier()
    claim=ClaimClassSelection.model_validate({**old.model_dump(exclude={'issues'}),
        'class_leads':[dict(**i.model_dump(exclude={'classification'}),class_effect=class_effect) for i in old.issues]})
    owned=OwnedBoundEvidencePaths.model_validate({**paths.model_dump(exclude={'origins'}),
        'lead_classifications':[] if missing else [dict(lead_index=1,classification=assignment)]})
    feedback,_=review_source_paths(client,'Claim',sources,timeout=12,bind_anchors=True)
    class Queue:
        calls=0
        def bind(self,**kwargs):return self
        def invoke(self,text):
            self.calls+=1
            schema=json.loads(text.rsplit('\nReturn ONLY JSON matching:\n',1)[1])
            if self.calls==1:
                assert 'class_leads' in schema['properties'] and 'issues' not in schema['properties']
                assert 'classification' not in schema['$defs']['ClaimLead']['properties']
                assert 'Materiality concerns ACCEPTANCE' not in text
                raw=claim
            else:
                assert 'claim_uncertainty_leads' in text and 'ONLY owner of ACCEPTANCE materiality' in text
                assert '"proposed_verdict": "TRUE"' not in text
                raw=owned
            return SimpleNamespace(content=raw.model_dump_json(),usage_metadata={'total_tokens':17})
    b=OllamaBackend.__new__(OllamaBackend);b.assessment_mode='evidence_adjudicated';b._model=Queue()
    b.line_reasoning_effort='high';b.temperature=0;b.brief_assessment_tokens=6144
    result,tokens=b.analyze_indexed('Claim','general',['Claim'],sources,[],'2024-01-01',{},
        verification_questions=[],planning_statements=[],source_path_review=feedback,
        relation_reviewer=client,single_materiality_owner=True)
    return result,claim


def test_one_acceptance_owner_adjudicates_every_lead_and_retains_raw_class_effect():
    result,claim=run()
    assert result.indexed_input['claim_selection']==claim.model_dump(mode='json')
    assert result.indexed_input['materiality_owner']=='paths'
    assert result.indexed_input['acceptance_lead_classifications']==[dict(lead_index=1,classification='material')]
    assert result.indexed_input['passage_issue_registry'][0]['classification']=='material'
    assert result.gaps and result.confidence=='High' and not result.sources_independent
    assert result.indexed_input['issue_head_order']==['paths_for_claim_lead','paths']
    with pytest.raises(ValidationError):
        ClaimClassSelection.model_validate({**claim.model_dump(),'issues':[]})


def test_missing_lead_classification_fails_instead_of_dropping_concern():
    with pytest.raises(RuntimeError,match='Missing/duplicate claim-lead materiality'):
        run(missing=True)


def test_class_undermining_concern_remains_blocking_even_if_path_owner_disagrees():
    result,claim=run(assignment='nonblocking',class_effect='class_undermining')
    assert any('Claim-class concern L1:' in gap for gap in result.gaps)
    assert result.indexed_input['claim_selection']['class_leads'][0]['class_effect']=='class_undermining'
    assert result.indexed_input['acceptance_lead_classifications'][0]['classification']=='nonblocking'
    assert result.proposed_verdict==claim.proposed_verdict and result.confidence==claim.confidence

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from test_proof_assessment import fixture
from kaji_langgraph.bound_proof_assessment import BoundProofDecision, BoundIssue, bound_proof_prompt, compile_bound_proof
from kaji_langgraph.catalogued_assessment import CatalogueSelection, passage_catalogue
from kaji_langgraph.llm import OllamaBackend


def decision():
    sources, records, selection, raw = fixture()
    raw = BoundProofDecision.model_validate(raw.model_dump())
    raw.issues = [BoundIssue(id='I1', component='C0', source='S1', question='Is the recording authenticated?',
        classification='material', dependency='authenticity_unresolved', basis_findings=['F1'])]
    return sources, records, selection, raw


def test_bound_contract_rejects_old_factual_reason_instead_of_dropping_it():
    _, _, _, raw = decision()
    data = raw.model_dump()
    data['issues'][0]['reason'] = 'Newsweek searched the social media pages.'
    with pytest.raises(ValidationError):
        BoundProofDecision.model_validate(data)


@pytest.mark.parametrize('dependency', ['support_missing', 'authenticity_unresolved', 'independence_unresolved',
    'scope_unaligned', 'opposing_evidence', 'outside_target', 'class_consistent', 'other_uncertainty'])
def test_all_model_materiality_judgments_survive_every_dependency(dependency):
    _, records, selection, raw = decision()
    raw.issues[0].dependency = dependency
    result = compile_bound_proof(selection, raw, {'C0': 'Claim'}, records)
    assert any('Is the recording authenticated?' in g for g in result.gaps)
    assert result.component_ledger[0]['unresolved_material_questions']
    assert result.source_origin_ledger[0]['unresolved_material_questions']
    assert result.indexed_input['bound_proof_response'] == raw.model_dump(mode='json')
    assert result.confidence == raw.confidence and result.sources_independent == raw.sources_independent


def test_unknown_basis_blocks_even_nonblocking_issue_and_missing_basis_is_permitted():
    _, records, selection, raw = decision()
    raw.issues[0].classification = 'nonblocking'
    raw.issues[0].basis_findings = ['NOT_A_FINDING']
    result = compile_bound_proof(selection, raw, {'C0': 'Claim'}, records)
    assert any('Unknown issue basis' in g for g in result.gaps)
    raw.issues[0].classification = 'material'
    raw.issues[0].basis_findings = []
    result = compile_bound_proof(selection, raw, {'C0': 'Claim'}, records)
    assert any('Is the recording authenticated?' in g for g in result.gaps)


def test_prompt_has_bound_schema_and_native_dispatch_preserves_raw_decision():
    sources, records, selection, raw = decision()
    context = {'required_components': {'C0': 'Claim'}, 'records': records,
        'passage_catalogue': passage_catalogue(records, selection, {'C0': 'Claim'})}
    schema = json.loads(bound_proof_prompt(context, selection, []).rsplit('\nReturn ONLY JSON matching:\n', 1)[1])
    assert 'reason' not in schema['$defs']['BoundIssue']['properties']
    assert schema['$defs']['BoundIssue']['properties']['component']['enum'] == ['C0']
    responses = [CatalogueSelection(references=[], unanswered_questions=[]), raw]
    class Queue:
        def bind(self, **kwargs): return self
        def invoke(self, prompt):
            return SimpleNamespace(content=responses.pop(0).model_dump_json(), usage_metadata={'total_tokens': 10})
    b = OllamaBackend.__new__(OllamaBackend)
    b.assessment_mode = 'bound_proof'; b._model = Queue(); b.line_reasoning_effort = 'high'
    b.temperature = 0; b.brief_assessment_tokens = 6144
    result, tokens = b.analyze_indexed('Claim', 'general', ['Claim'], sources, [], '2024-01-01', {},
        verification_questions=[], planning_statements=[])
    assert tokens == 20 and result.indexed_input['assessment_mode'] == 'bound_proof'
    assert result.indexed_input['bound_issue_registry'][0]['basis_findings'] == ['F1']
    from kaji_langgraph.config import load_config
    from kaji_langgraph.graph import build_graph
    config = load_config(); config['model']['assessment_mode'] = 'bound_proof'; config['jev']['enabled'] = False
    assert build_graph(model=object(), retriever=object(), config=config)

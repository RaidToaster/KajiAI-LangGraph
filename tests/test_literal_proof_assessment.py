import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from test_proof_assessment import fixture
from kaji_langgraph.literal_proof_assessment import (
    LiteralProofDecision, LiteralIssue, LiteralSelection, compile_literal_proof,
    literal_proof_prompt, catalogue_leads,
)
from kaji_langgraph.catalogued_assessment import passage_catalogue
from kaji_langgraph.llm import OllamaBackend


def decision():
    sources, records, selection, raw = fixture()
    data = raw.model_dump()
    data['findings'] = [dict(id='F1', reference='S1:P1:P1',
        extract='Our own recording documents the vote as seven to two.', stance='supports')]
    raw = LiteralProofDecision.model_validate(data)
    return sources, records, selection, raw


def test_literal_extraction_does_not_complete_a_date_from_outside_passage():
    _, records, selection, raw = decision()
    records[0]['visible_text'] = 'Statement released Feb. 26.'
    records[0]['passages'] = {'P1': 'Statement released Feb. 26.'}
    records[0]['paragraph_offsets'] = {'P1': [0, len(records[0]['visible_text'])]}
    raw.findings[0].extract = 'Statement released Feb. 26, 2020.'
    result = compile_literal_proof(selection, raw, {'C0': 'Claim'}, records)
    assert any('Nonliteral' in g for g in result.gaps)
    assert result.indexed_input['literal_proof_response']['findings'][0]['extract'].endswith('2020.')
    raw.findings[0].extract = 'Statement released Feb. 26.'
    result = compile_literal_proof(selection, raw, {'C0': 'Claim'}, records)
    assert not any('Nonliteral' in g for g in result.gaps)
    assert '2020' not in result.evidence[0].finding


def test_literal_source_methods_cannot_transfer_between_outlets():
    _, records, selection, raw = decision()
    raw.findings[0].extract = 'We searched social media.'
    result = compile_literal_proof(selection, raw, {'C0': 'Claim'}, records)
    assert any('Nonliteral' in g for g in result.gaps)
    assert 'We searched social media.' in result.evidence[0].finding  # Retain, never repair.


def test_custom_uncertainty_survives_any_category_and_materiality_never_clears():
    _, records, selection, raw = decision()
    raw.issues = [LiteralIssue(id='I1', component='C0', source='S1', classification='material',
        dependency='outside_target', basis_findings=[], custom_question='Was the recording edited?')]
    result = compile_literal_proof(selection, raw, {'C0': 'Claim'}, records)
    assert any('Was the recording edited?' in g for g in result.gaps)
    assert any('Was the recording edited?' in q for q in result.component_ledger[0]['unresolved_material_questions'])
    assert result.confidence == raw.confidence and result.proposed_verdict == raw.proposed_verdict
    assert result.indexed_input['literal_issue_registry'][0]['custom_question'] == 'Was the recording edited?'
    with pytest.raises(ValidationError):
        LiteralIssue(id='I2', component='C0', classification='material', dependency='other_uncertainty', basis_findings=[])


def test_native_selector_and_decision_keep_planning_questions_and_original_contract():
    sources, records, selection, raw = decision()
    native = LiteralSelection(references=[dict(id='L1', component='C0', reference='S1:P1:P1')], unanswered_components=['C0'])
    mapped = catalogue_leads(native)
    assert mapped.unanswered_questions[0].component == 'C0'
    context = {'required_components': {'C0': 'Claim'}, 'records': records,
        'passage_catalogue': passage_catalogue(records, selection, {'C0': 'Claim'})}
    schema = json.loads(literal_proof_prompt(context, selection, []).rsplit('\nReturn ONLY JSON matching:\n', 1)[1])
    assert 'extract' in schema['$defs']['LiteralFinding']['properties']
    assert 'finding' not in schema['$defs']['LiteralFinding']['properties']
    responses = [native, raw]
    class Queue:
        def bind(self, **kwargs): return self
        def invoke(self, prompt):
            return SimpleNamespace(content=responses.pop(0).model_dump_json(), usage_metadata={'total_tokens': 10})
    b = OllamaBackend.__new__(OllamaBackend)
    b.assessment_mode = 'literal_proof'; b._model = Queue(); b.line_reasoning_effort = 'high'
    b.temperature = 0; b.brief_assessment_tokens = 6144
    result, tokens = b.analyze_indexed('Claim', 'general', ['Claim'], sources, [], '2024-01-01', {},
        verification_questions=['Is it authenticated?'], planning_statements=['Unverified planning lead'])
    assert tokens == 20 and result.indexed_input['assessment_mode'] == 'literal_proof'
    assert result.indexed_input['literal_selection'] == native.model_dump(mode='json')
    assert result.indexed_input['verification_questions'] == ['Is it authenticated?']
    assert result.indexed_input['planning_statements'] == ['Unverified planning lead']
    assert result.indexed_input['literal_proof_response'] == raw.model_dump(mode='json')
    from kaji_langgraph.config import load_config
    from kaji_langgraph.graph import build_graph
    config = load_config(); config['model']['assessment_mode'] = 'literal_proof'; config['jev']['enabled'] = False
    assert build_graph(model=object(), retriever=object(), config=config)

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from test_literal_proof_assessment import decision
from kaji_langgraph.strict_literal_assessment import StrictLiteralDecision, compile_strict_literal, strict_literal_prompt
from kaji_langgraph.literal_proof_assessment import LiteralSelection
from kaji_langgraph.catalogued_assessment import passage_catalogue
from kaji_langgraph.llm import OllamaBackend


def issue(dependency='response_missing', **extra):
    return dict(id='I1', component='C0', source='S1', classification='material',
        dependency=dependency, basis_findings=['F1'], **extra)


def test_common_issue_cannot_append_a_factual_recital_and_other_can_express_new_uncertainty():
    _, _, _, raw = decision()
    data = raw.model_dump()
    data['issues'] = [issue(custom_question='All outlets searched separately; is this enough?')]
    with pytest.raises(ValidationError):
        StrictLiteralDecision.model_validate(data)
    data['issues'] = [issue('other_uncertainty', custom_question='Was the recording edited?')]
    assert StrictLiteralDecision.model_validate(data).issues[0].custom_question == 'Was the recording edited?'
    data['issues'] = [issue('other_uncertainty')]
    with pytest.raises(ValidationError):
        StrictLiteralDecision.model_validate(data)


def test_typed_and_arbitrary_material_issues_both_survive_without_changing_judgments():
    _, records, selection, raw = decision()
    data = raw.model_dump()
    data['issues'] = [issue(), {**issue('other_uncertainty', custom_question='Was the recording edited?'), 'id': 'I2'}]
    strict = StrictLiteralDecision.model_validate(data)
    result = compile_strict_literal(selection, strict, {'C0': 'Claim'}, records)
    assert any('missing response' in g for g in result.gaps)
    assert any('Was the recording edited?' in g for g in result.gaps)
    assert result.indexed_input['strict_literal_response'] == strict.model_dump(mode='json')
    assert result.confidence == raw.confidence and result.proposed_verdict == raw.proposed_verdict
    assert len(result.component_ledger[0]['unresolved_material_questions']) == 2


def test_native_strict_dispatch_uses_the_conditional_schema_and_keeps_questions():
    sources, records, selection, raw = decision()
    data = raw.model_dump(); data['issues'] = [issue()]
    strict = StrictLiteralDecision.model_validate(data)
    context = {'required_components': {'C0': 'Claim'}, 'records': records,
        'passage_catalogue': passage_catalogue(records, selection, {'C0': 'Claim'})}
    schema = json.loads(strict_literal_prompt(context, selection, []).rsplit('\nReturn ONLY JSON matching:\n', 1)[1])
    assert 'custom_question' not in schema['$defs']['TypedLiteralIssue']['properties']
    assert 'custom_question' in schema['$defs']['OtherLiteralIssue']['required']
    responses = [LiteralSelection(references=[], unanswered_components=['C0']), strict]
    class Queue:
        def bind(self, **kwargs): return self
        def invoke(self, prompt):
            return SimpleNamespace(content=responses.pop(0).model_dump_json(), usage_metadata={'total_tokens': 10})
    b = OllamaBackend.__new__(OllamaBackend)
    b.assessment_mode = 'strict_literal'; b._model = Queue(); b.line_reasoning_effort = 'high'
    b.temperature = 0; b.brief_assessment_tokens = 6144
    result, tokens = b.analyze_indexed('Claim', 'general', ['Claim'], sources, [], '2024-01-01', {},
        verification_questions=['Was the recording edited?'], planning_statements=[])
    assert tokens == 20 and result.indexed_input['assessment_mode'] == 'strict_literal'
    assert result.indexed_input['verification_questions'] == ['Was the recording edited?']
    from kaji_langgraph.config import load_config
    from kaji_langgraph.graph import build_graph
    config = load_config(); config['model']['assessment_mode'] = 'strict_literal'; config['jev']['enabled'] = False
    assert build_graph(model=object(), retriever=object(), config=config)

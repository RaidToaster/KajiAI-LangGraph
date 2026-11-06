import ast
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
from pydantic import ValidationError

from test_proof_assessment import fixture
from kaji_langgraph.passage_decision import PassageDecision, unit_table, passage_prompt, compile_passage_decision
from kaji_langgraph.llm import OllamaBackend


def decision():
    sources, records, _, _ = fixture()
    raw = PassageDecision.model_validate(dict(findings=[dict(unit='U1', stance='supports')],
        origins=[dict(source='S1', origin='U1', verification_action='U1')],
        components=[dict(id='C0', adjudication='supported', units=['U1'])],
        issues=[], proposed_verdict='TRUE', confidence='High', counterevidence_searched=True,
        sources_independent=False))
    return sources, records, raw


def test_client_copies_intact_unit_and_assigns_only_bookkeeping_ids():
    _, records, raw = decision()
    result = compile_passage_decision(raw, {'C0': 'Claim'}, records)
    text = unit_table(records, {'C0': 'Claim'})['U1']['literal_quote']
    assert result.evidence[0].quotes['https://1.test/record'] == text
    assert result.evidence[0].finding == f'Retained snippet record for https://1.test/record contains verbatim: {text}'
    assert result.component_ledger[0]['findings'] == ['F1']
    assert result.indexed_input['passage_decision_response'] == raw.model_dump(mode='json')
    assert result.proposed_verdict == raw.proposed_verdict and result.confidence == raw.confidence
    assert not result.sources_independent


@pytest.mark.parametrize('change', ['unknown', 'duplicate', 'undeclared_component', 'unknown_issue', 'duplicate_issue'])
def test_invalid_units_are_failures_not_repaired_or_normalized(change):
    _, records, raw = decision()
    data = raw.model_dump()
    if change == 'unknown': data['findings'][0]['unit'] = 'U999'
    if change == 'duplicate': data['findings'].append(data['findings'][0])
    if change == 'undeclared_component': data['components'][0]['units'] = ['U2']
    if change in {'unknown_issue', 'duplicate_issue'}:
        data['issues'] = [dict(component='C0', classification='material', dependency='support_missing',
            basis_units=['U999'] if change == 'unknown_issue' else ['U2', 'U2'])]
    with pytest.raises(ValueError):
        compile_passage_decision(PassageDecision.model_validate(data), {'C0': 'Claim'}, records)


def test_issue_context_can_cite_unselected_units_without_adding_verdict_findings():
    _, records, raw = decision()
    data = raw.model_dump()
    data['origins'].append(dict(source='S2', origin=None, verification_action=None))
    data['issues'] = [dict(component='C0', source='S2', classification='material',
        dependency='independence_unresolved', basis_units=['U1', 'U2'])]
    raw = PassageDecision.model_validate(data)
    result = compile_passage_decision(raw, {'C0': 'Claim'}, records)
    assert len(result.evidence) == 1
    assert result.component_ledger[0]['findings'] == ['F1']
    context = result.indexed_input['passage_issue_context'][0]
    assert context['id'] == 'I1' and context['classification'] == 'material'
    assert [p['unit'] for p in context['passages']] == ['U1', 'U2']
    assert context['passages'][1]['quote'] == unit_table(records, {'C0': 'Claim'})['U2']['literal_quote']
    assert context['passages'][1]['reference']['source'] == 'S2'
    assert result.component_ledger[0]['issue_context'] == [context]
    assert result.source_origin_ledger[1]['issue_context'] == [context]
    assert result.gaps and not result.sources_independent
    assert result.indexed_input['passage_issue_registry'] == [i.model_dump(mode='json') for i in raw.issues]
    assert result.proposed_verdict == raw.proposed_verdict and result.confidence == raw.confidence


def test_every_typed_and_arbitrary_material_issue_survives_without_filtering():
    _, records, raw = decision()
    data = raw.model_dump()
    data['issues'] = [dict(component='C0', source='S1', classification='material', dependency='outside_target', basis_units=['U1']),
        dict(component='C0', source='S1', classification='material', dependency='other_uncertainty', basis_units=[], custom_question='Was the recording edited?')]
    raw = PassageDecision.model_validate(data)
    result = compile_passage_decision(raw, {'C0': 'Claim'}, records)
    assert any('Was the recording edited?' in g for g in result.gaps)
    assert len(result.component_ledger[0]['unresolved_material_questions']) == 2
    assert len(result.source_origin_ledger[0]['unresolved_material_questions']) == 2
    assert result.indexed_input['passage_issue_registry'] == [i.model_dump(mode='json') for i in raw.issues]
    data['issues'][0]['custom_question'] = 'All outlets searched separately; enough?'
    with pytest.raises(ValidationError): PassageDecision.model_validate(data)


def test_context_text_is_not_repeated_in_unit_index_and_native_dispatch_is_one_call():
    sources, records, raw = decision()
    units = unit_table(records, {'C0': 'Claim'})
    context = {'required_components': {'C0': 'Claim'}, 'records': records}
    prompt = passage_prompt(context, units)
    # Use production context shape, with paragraph text only once.
    context['records'] = [{k: v for k, v in r.items() if k not in {'visible_text', 'paragraph_offsets'}} for r in records]
    prompt = passage_prompt(context, units)
    assert '"literal_quote"' not in prompt
    schema = json.loads(prompt.rsplit('\nReturn ONLY JSON matching:\n', 1)[1])
    assert 'id' not in schema['$defs']['UnitFinding']['properties']
    assert 'id' not in schema['$defs']['UnitIssue']['properties']
    assert 'extract' not in schema['$defs']['UnitFinding']['properties']
    class Queue:
        calls = 0
        def bind(self, **kwargs): return self
        def invoke(self, prompt):
            self.calls += 1
            return SimpleNamespace(content=raw.model_dump_json(), usage_metadata={'total_tokens': 17})
    b = OllamaBackend.__new__(OllamaBackend)
    b.assessment_mode = 'passage_decision'; b._model = Queue(); b.line_reasoning_effort = 'high'
    b.temperature = 0; b.brief_assessment_tokens = 6144
    result, tokens = b.analyze_indexed('Claim', 'general', ['Claim'], sources, [], '2024-01-01', {},
        verification_questions=['Was the recording edited?'], planning_statements=['Unverified planning statement'])
    assert b._model.calls == 1 and tokens == 17
    assert result.indexed_input['verification_questions'] == ['Was the recording edited?']
    assert result.indexed_input['planning_statements'] == ['Unverified planning statement']
    from kaji_langgraph.config import load_config
    from kaji_langgraph.graph import build_graph
    config = load_config(); config['model']['assessment_mode'] = 'passage_decision'; config['jev']['enabled'] = False
    assert build_graph(model=object(), retriever=object(), config=config)


def test_unknown_unit_failure_retains_raw_decision_and_original_record_view():
    sources, _, raw = decision()
    raw.findings[0].unit = 'U999'
    class Queue:
        def bind(self, **kwargs): return self
        def invoke(self, prompt): return SimpleNamespace(content=raw.model_dump_json(), usage_metadata={'total_tokens': 17})
    b = OllamaBackend.__new__(OllamaBackend)
    b.assessment_mode = 'passage_decision'; b._model = Queue(); b.line_reasoning_effort = 'high'
    b.temperature = 0; b.brief_assessment_tokens = 6144
    with pytest.raises(RuntimeError) as caught:
        b.analyze_indexed('Claim', 'general', ['Claim'], sources, [], '2024-01-01', {}, verification_questions=[], planning_statements=[])
    partial = caught.value.partial_assessment.indexed_input
    assert partial['passage_decision_response'] == raw.model_dump(mode='json')
    assert partial['records'][0]['visible_text'] == sources[0].page_text


def test_standard_analysis_and_model_schema_source_are_unchanged_from_prior_freeze():
    with zipfile.ZipFile('artifacts/strict-literal-native-20261105/source.zip') as z:
        assert z.read('src/kaji_langgraph/models.py').decode('utf-8') == Path('src/kaji_langgraph/models.py').read_text(encoding='utf-8')
        old = ast.parse(z.read('src/kaji_langgraph/llm.py').decode('utf-8'))
    new = ast.parse(Path('src/kaji_langgraph/llm.py').read_text(encoding='utf-8'))
    def method(tree):
        cls = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == 'OllamaBackend')
        return next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == 'analyze')
    assert ast.dump(method(old)) == ast.dump(method(new))

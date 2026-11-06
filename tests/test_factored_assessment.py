from types import SimpleNamespace

import pytest

from kaji_langgraph.factored_assessment import FactoredAssessmentFailure, LedgerDecision, SourceLedger, analyze_factored, compile_factored
from kaji_langgraph.llm import OllamaBackend
from kaji_langgraph.models import EvidenceAssessment, SourceRecord
from kaji_langgraph.reference_assessment import paragraph_records


CLAIM="Ara said the lake level fell."


def fixture():
    source=SourceRecord(url="https://example.test/transcript",page_text="Transcript: Ara said the lake level fell. No level measurements are supplied.",content_hash="v1",retrieved_at="2026-11-04",query="q",provider="fixture")
    ledger=SourceLedger.model_validate(dict(findings=[dict(id="F1",reference=dict(source="S1",first_paragraph="P1",last_paragraph="P1"),finding="The transcript records Ara saying the lake level fell.",stance="supports")],
        origins=[dict(source="S1",underlying_origin="Transcript",verification_action="unknown",passages=["P1"],unresolved_material_questions=[])],
        answers=[dict(component="C0",question="Does the record attribute these words to Ara?",observations=["F1"],answer="The transcript attributes these words to Ara.",status="answered")],declared_material_questions=[]))
    decision=LedgerDecision.model_validate(dict(components=[dict(id="C0",resolved=True,findings=["F1"],questions=[],unresolved_material_questions=[])],
        proposed_verdict="TRUE",confidence="Medium",summary="The record attributes the utterance.",gaps=[],contradictions=[],counterevidence_searched=False,sources_independent=False,
        nonblocking_limitations=[dict(component="C0",issue="Lake change is not measured.",reason_nonblocking="The target is an utterance.")]))
    return source,ledger,decision


def backend(responses):
    class Queue:
        def __init__(self):self.prompts=[]
        def bind(self,**kwargs):return self
        def invoke(self,prompt):
            self.prompts.append(prompt)
            value=responses.pop(0)
            if isinstance(value,Exception):raise value
            return SimpleNamespace(content=value.model_dump_json(),usage_metadata={"total_tokens":17})
    b=OllamaBackend.__new__(OllamaBackend);b.assessment_mode="factored";b._model=Queue()
    b.temperature=0;b.line_reasoning_effort=None;b.brief_assessment_tokens=6144
    return b


def run(b,source):
    return b.analyze_indexed(CLAIM,"general",[CLAIM],[source],[],"2024-06-30",{},verification_questions=["Did Ara say these words?"],planning_statements=[CLAIM],executed_queries=["q"])


def test_two_actual_calls_keep_first_stage_free_of_verdict_and_confidence():
    source,ledger,decision=fixture();b=backend([ledger,decision]);result,tokens=run(b,source)
    assert len(b._model.prompts)==2 and tokens==34
    assert '"proposed_verdict"' not in b._model.prompts[0] and '"confidence"' not in b._model.prompts[0]
    assert '"unverified_source_ledger"' in b._model.prompts[1]
    assert source.page_text in b._model.prompts[1]
    assert result.confidence=="Medium" and not result.sources_independent
    assert result.indexed_input["factored_stage_tokens"]=={"source_ledger":17,"adjudication":17}


def test_material_fields_from_both_stages_cannot_be_overridden_by_notes():
    source,ledger,decision=fixture();issue="Transcript authenticity unestablished."
    ledger.declared_material_questions=[issue]
    ledger.origins[0].unresolved_material_questions=["Adverse origin issue."]
    decision.gaps=["Second-stage issue."];decision.components[0].unresolved_material_questions=["Component issue."]
    decision.nonblocking_limitations[0].issue=issue
    result=compile_factored(ledger,decision,{"C0":CLAIM},paragraph_records([source]))
    assert {issue,"Adverse origin issue.","Second-stage issue.","Component issue."}<=set(result.gaps)
    assert len(result.evidence)==len(ledger.findings)


def test_failed_second_call_keeps_first_stage_and_known_usage():
    source,ledger,decision=fixture();b=backend([ledger,ValueError("malformed final")])
    with pytest.raises(FactoredAssessmentFailure) as caught:run(b,source)
    partial=caught.value.partial_assessment
    assert partial.indexed_input["factored_source_ledger"]==ledger.model_dump(mode="json")
    assert partial.indexed_input["factored_first_stage_tokens"]==17
    assert partial.indexed_input["records"][0]["paragraph_offsets"]
    assert partial.proposed_verdict=="UNVERIFIED" and partial.gaps


def test_invalid_first_binding_stops_before_second_dispatch():
    source,ledger,decision=fixture();ledger.findings[0].reference.first_paragraph="P999"
    b=backend([ledger,decision])
    with pytest.raises(FactoredAssessmentFailure):run(b,source)
    assert len(b._model.prompts)==1


def test_json_roundtrip_keeps_both_stages_original_target_and_literal_quote():
    source,ledger,decision=fixture();result=compile_factored(ledger,decision,{"C0":CLAIM},paragraph_records([source]))
    saved=EvidenceAssessment.model_validate_json(result.model_dump_json())
    assert saved.indexed_input["factored_source_ledger"]==ledger.model_dump(mode="json")
    assert saved.indexed_input["factored_decision"]==decision.model_dump(mode="json")
    assert saved.assertions[0].assertion==CLAIM
    assert saved.evidence[0].quotes[source.url]==source.page_text


def test_partial_first_stage_survives_graph_failure(config):
    from kaji_langgraph.graph import run_claim
    from kaji_langgraph.llm import DeterministicBackend
    from kaji_langgraph.retrieval import StaticRetriever
    source,ledger,decision=fixture()
    class Broken(DeterministicBackend):
        def analyze_indexed(self,*args,**kwargs):raise FactoredAssessmentFailure("Second stage failed",ledger)
    config["model"]["assessment_mode"]="factored"
    result=run_claim(CLAIM,domain="general",reference_date="2024-06-30",max_rounds=1,model=Broken(),retriever=StaticRetriever(),config=config)
    assert result.verification_status=="execution_error" and result.verdict=="UNVERIFIED"
    assert result.research_history[0].assessment.indexed_input["factored_source_ledger"]==ledger.model_dump(mode="json")

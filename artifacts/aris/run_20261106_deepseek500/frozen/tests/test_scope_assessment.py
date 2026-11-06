from kaji_langgraph.models import BudgetState, FinalResult, ResearchRound, SourceRecord
from kaji_langgraph.reference_assessment import paragraph_records
from kaji_langgraph.report import format_report
from kaji_langgraph.scope_assessment import ScopeAssessment, compile_scope


CLAIM="Speaker Ara said that the lake level fell."


def fixture():
    source=SourceRecord(url="https://example.test/transcript",page_text="Transcript: Ara said the lake level fell. No level measurements are supplied.",content_hash="v1",retrieved_at="2026-11-04",query="transcript",provider="fixture")
    records=paragraph_records([source])
    raw=ScopeAssessment.model_validate(dict(obligations=[dict(component="C0",target="Whether Ara spoke the words",proof_needed="A direct utterance record",observations=["F1"],material_uncertainties=[])],
        assessment=dict(findings=[dict(id="F1",reference=dict(source="S1",first_paragraph="P1",last_paragraph="P1"),finding="The transcript records Ara saying the lake level fell.",stance="supports")],
            origins=[dict(source="S1",underlying_origin="Transcript",verification_action="unknown",passages=["P1"],unresolved_material_questions=[])],
            components=[dict(id="C0",resolved=True,findings=["F1"],questions=[],unresolved_material_questions=[])],
            proposed_verdict="TRUE",confidence="Medium",summary="The record attributes the utterance.",gaps=[],contradictions=[],counterevidence_searched=False,sources_independent=False),
        nonblocking_limitations=[dict(component="C0",issue="Actual lake change is unmeasured.",reason_nonblocking="The target asks only whether the words were spoken.")]))
    return raw,records


def test_nonblocking_label_never_overrides_a_declared_material_issue():
    raw,records=fixture();issue="Is this transcript authentic?"
    raw.obligations[0].material_uncertainties=[issue]
    raw.nonblocking_limitations[0].issue=issue
    result=compile_scope(raw,{"C0":CLAIM},records)
    assert issue in result.gaps
    assert result.confidence=="Medium" and not result.sources_independent
    assert result.assertions[0].assertion==CLAIM
    assert result.indexed_input["scope_first_response"]["nonblocking_limitations"][0]["issue"]==issue


def test_all_older_adverse_fields_survive_scope_compilation():
    raw,records=fixture()
    raw.assessment.gaps=["Original gap."]
    raw.assessment.contradictions=["Unresolved contradiction."]
    raw.assessment.components[0].unresolved_material_questions=["Missing dataset."]
    raw.assessment.origins.append(raw.assessment.origins[0].model_copy(update={"source":"S9","unresolved_material_questions":["Shared adverse origin."]}))
    result=compile_scope(raw,{"C0":CLAIM},records)
    assert {"Original gap.","Missing dataset.","Shared adverse origin."}<=set(result.gaps)
    assert result.contradictions==["Unresolved contradiction."]


def test_unknown_scope_row_cannot_hide_its_material_question():
    raw,records=fixture();raw.obligations[0].component="C9"
    raw.obligations[0].material_uncertainties=["Adverse qualification."]
    result=compile_scope(raw,{"C0":CLAIM},records)
    assert {"Adverse qualification.","Unknown scope component: C9","Missing scope obligation: C0"}<=set(result.gaps)


def test_duplicate_scope_and_unknown_findings_block():
    raw,records=fixture();raw.obligations.append(raw.obligations[0].model_copy(update={"observations":["unknown"]}))
    result=compile_scope(raw,{"C0":CLAIM},records)
    assert "Duplicate scope component: C0" in result.gaps
    assert "Unknown scope observation for C0" in result.gaps


def test_roundtrip_and_report_keep_nonblocking_notes_beside_verdict():
    raw,records=fixture();assessment=compile_scope(raw,{"C0":CLAIM},records)
    result=FinalResult(claim=CLAIM,domain="general",budget=BudgetState(),research_history=[ResearchRound(round_number=1,assessment=assessment)])
    saved=FinalResult.model_validate_json(result.model_dump_json())
    restored=saved.research_history[0].assessment
    assert restored.indexed_input["scope_first_response"]==raw.model_dump(mode="json")
    assert restored.indexed_input["scope_component_lookup"]=={"C0":CLAIM}
    assert "Actual lake change is unmeasured." in format_report(saved)
    assert "target asks only whether the words were spoken" in format_report(saved)


def test_native_scope_dispatch_preserves_original_and_judgments():
    from kaji_langgraph.llm import OllamaBackend
    raw,records=fixture()
    class Response:
        content=raw.model_dump_json();usage_metadata={"total_tokens":29}
    class Capture:
        def bind(self,**kwargs):return self
        def invoke(self,prompt):
            assert "scope-first response contract" in prompt
            assert "infinite chain of authentication" in prompt
            assert "A source's conclusion is an attributed report" not in prompt
            return Response()
    backend=OllamaBackend.__new__(OllamaBackend);backend.assessment_mode="scope_first"
    backend._model=Capture();backend.line_reasoning_effort=None;backend.temperature=0;backend.brief_assessment_tokens=6144
    source=SourceRecord(url=records[0]["url"],page_text=records[0]["visible_text"],content_hash="v1",retrieved_at="2026-11-04",query="q",provider="fixture")
    assessment,tokens=backend.analyze_indexed(CLAIM,"general",[CLAIM],[source],[],"2024-06-30",{},verification_questions=[],planning_statements=[])
    assert tokens==29 and assessment.confidence=="Medium"
    assert assessment.indexed_input["components"]=={"C0":CLAIM}
    assert assessment.indexed_input["assessment_mode"]=="scope_first"

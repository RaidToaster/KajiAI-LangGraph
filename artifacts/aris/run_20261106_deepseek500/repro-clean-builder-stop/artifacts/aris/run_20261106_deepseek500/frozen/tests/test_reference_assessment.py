from kaji_langgraph.models import EvidenceAssessment, SourceRecord
from kaji_langgraph.reference_assessment import ReferenceAssessment, compile_references, paragraph_records


def source(text):
    return SourceRecord(url="https://example.test/record",page_text=text,content_hash="version",retrieved_at="2026-11-04",query="q",provider="fixture")


def assessment(**changes):
    data=dict(findings=[dict(id="F1",reference=dict(source="S1",first_paragraph="P1",last_paragraph="P2"),finding="The record reports seven votes and independently recorded observations.",stance="supports")],
        proposed_verdict="TRUE",confidence="Medium",summary="A supplied report.",
        components=[dict(id="C0",resolved=True,findings=["F1"],unresolved_material_questions=["Was the date matched?"])],
        origins=[dict(source="S1",underlying_origin="unknown",verification_action="unknown",passages=["P1"],unresolved_material_questions=["Is this original?"])],
        gaps=["An earlier limitation."],contradictions=[],counterevidence_searched=False,sources_independent=False)
    data.update(changes)
    return ReferenceAssessment.model_validate(data)


def test_contiguous_range_preserves_original_separator_and_middle_qualification():
    text="The clerk recorded seven votes.\n\nThis is provisional.\n\nA separate observer recorded seven votes."
    records=paragraph_records([source(text)])
    raw=assessment();raw.findings[0].reference.last_paragraph="P3"
    result=compile_references(raw,{"C0":"The plan passed."},records)
    assert result.evidence[0].quotes[records[0]["url"]]==text
    assert result.confidence=="Medium" and not result.sources_independent
    assert set(result.gaps)=={"Was the date matched?","Is this original?","An earlier limitation."}
    assert "This is provisional." in result.evidence[0].quotes[records[0]["url"]]


def test_reverse_unknown_and_oversized_ranges_block_without_replacing_findings():
    for first,last in [("P2","P1"),("P1","P999"),("P1","P2")]:
        records=paragraph_records([source(" ".join(["word"]*251)+"\n\nEnd.")])
        raw=assessment();raw.findings[0].reference.first_paragraph=first;raw.findings[0].reference.last_paragraph=last
        result=compile_references(raw,{"C0":"Original"},records)
        assert len(result.evidence)==1 and result.evidence[0].quotes[records[0]["url"]]==""
        assert any("Invalid or over-250-word" in g for g in result.gaps)


def test_visible_boundary_drops_incomplete_paragraph_and_records_omission():
    text="Complete paragraph.\n\n"+"x"*3500
    record=paragraph_records([source(text)])[0]
    assert record["visible_text"]=="Complete paragraph."
    assert record["omitted_characters"]==len(text)-len(record["visible_text"])
    assert list(record["passages"].values())==["Complete paragraph."]


def test_roundtrip_retains_raw_range_and_literal_offsets():
    records=paragraph_records([source("Seven votes.\n\nIndependent observations.")])
    result=compile_references(assessment(),{"C0":"Original claim"},records)
    restored=EvidenceAssessment.model_validate_json(result.model_dump_json())
    ref=restored.indexed_input["reference_first_response"]["findings"][0]["reference"]
    record=restored.indexed_input["records"][0]
    a=record["paragraph_offsets"][ref["first_paragraph"]][0];b=record["paragraph_offsets"][ref["last_paragraph"]][1]
    assert restored.evidence[0].quotes[record["url"]]==record["visible_text"][a:b]


def test_one_paragraph_is_a_valid_reference_range():
    records=paragraph_records([source("A complete single paragraph.")]);raw=assessment()
    raw.findings[0].reference.last_paragraph="P1"
    result=compile_references(raw,{"C0":"Original"},records)
    assert result.evidence[0].quotes[records[0]["url"]]=="A complete single paragraph."


def test_new_mode_dispatches_through_native_adapter_without_baseline_schema_change():
    from kaji_langgraph.llm import OllamaBackend
    class Response:
        content=assessment().model_dump_json();usage_metadata={"total_tokens":12}
    class Capture:
        def bind(self,**kwargs):return self
        def invoke(self,prompt):
            assert "first_paragraph" in prompt and "at most 250 words" in prompt
            return Response()
    backend=OllamaBackend.__new__(OllamaBackend)
    backend.assessment_mode="reference_first";backend._model=Capture();backend.line_reasoning_effort=None
    backend.temperature=0;backend.brief_assessment_tokens=6144
    result,tokens=backend.analyze_indexed("Original","general",["Original"],[source("Seven votes.\n\nIndependent observations.")],[],"2024-06-30",{},verification_questions=["Which record?"],planning_statements=["Unverified plan."])
    assert result.indexed_input["assessment_mode"]=="reference_first"
    assert result.indexed_input["verification_questions"]==["Which record?"]
    assert result.indexed_input["components"]=={"C0":"Original"}
    assert tokens==12

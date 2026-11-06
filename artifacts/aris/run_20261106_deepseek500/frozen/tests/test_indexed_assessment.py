import time

from kaji_langgraph.gate import evidence_gaps
from kaji_langgraph.graph import run_claim
from kaji_langgraph.indexed_assessment import IndexedAssessment,compile_assessment
from kaji_langgraph.llm import DeterministicBackend,indexed_records
from kaji_langgraph.models import EvidenceAssessment,QuestionDecomposition,SourceRecord
from kaji_langgraph.retrieval import StaticRetriever


CLAIM='The council approved the plan by seven votes to two on 1 June 2024.'
RECORDS=[{"id":"S1","url":"https://a.test/record","passages":{"P1":"On 1 June 2024 the council approved the plan, seven votes to two."}},
         {"id":"S2","url":"https://b.test/record","passages":{"P1":"An independent reporter recorded seven votes to two on 1 June 2024."}}]


def raw(**changes):
    data=dict(proposed_verdict="TRUE",confidence="High",summary="The supplied records report approval.",
        findings=[dict(id="F0",finding="The council approved the plan by seven votes to two on 1 June 2024.",source="S1",passage="P1",stance="supports"),
                  dict(id="F1",finding="An independent reporter recorded the same vote.",source="S2",passage="P1",stance="supports")],
        components=[dict(id="C0",resolved=True,findings=["F0","F1"],questions=[],unresolved_material_questions=[])],
        origins=[],gaps=[],contradictions=[],counterevidence_searched=True,sources_independent=True)
    data.update(changes)
    return IndexedAssessment.model_validate(data)


def sources():
    return [SourceRecord(url=r["url"],page_text=r["passages"]["P1"],content_hash=r["id"],retrieved_at="2026-11-04",query="",provider="fixture") for r in RECORDS]


def test_component_ids_preserve_original_qualification_without_copying_it():
    result=compile_assessment(raw(),{"C0":CLAIM},RECORDS)
    assert result.assertions[0].assertion==CLAIM and result.assertions[0].resolved
    assert set(result.assertions[0].source_urls)=={r["url"] for r in RECORDS}
    assert not evidence_gaps(result,[CLAIM],sources(),{})
    assert result.component_ledger[0]["assertion"]==CLAIM


def test_unresolved_component_and_cited_origin_remain_blocking():
    result=compile_assessment(raw(
        components=[dict(id="C0",resolved=True,findings=["F0","F1"],unresolved_material_questions=["Was approval later reversed?"])],
        origins=[dict(source="S2",underlying_origin="unknown",verification_action="unknown",passages=["P1"],unresolved_material_questions=["Is this independently recorded?"])],
        gaps=["An original declared gap."],contradictions=["An unresolved contradiction."]),{"C0":CLAIM},RECORDS)
    gaps=evidence_gaps(result,[CLAIM],sources(),{})
    assert all(text in gaps for text in ["Was approval later reversed?","Is this independently recorded?","An original declared gap.","An unresolved contradiction."])


def test_unknown_and_missing_ids_never_supply_required_resolution():
    result=compile_assessment(raw(components=[dict(id="C9",resolved=True,findings=["F0"]) ]),{"C0":CLAIM},RECORDS)
    gaps=evidence_gaps(result,[CLAIM],sources(),{})
    assert any("Missing required component" in g for g in gaps)
    assert any("Resolve and cite" in g for g in gaps)
    result=compile_assessment(raw(components=[dict(id="C0",resolved=True,findings=["missing"]) ]),{"C0":CLAIM},RECORDS)
    assert any("Resolve and cite" in g for g in evidence_gaps(result,[CLAIM],sources(),{}))


def test_unknown_passage_stays_an_invalid_citation():
    parsed=raw();parsed.findings[0].passage="P999"
    result=compile_assessment(parsed,{"C0":CLAIM},RECORDS)
    assert result.evidence[0].quotes[RECORDS[0]["url"]]==""
    assert any("exact quote" in g for g in evidence_gaps(result,[CLAIM],sources(),{}))


def test_uncited_origin_cannot_hide_a_declared_material_question():
    extra={"id":"S3","url":"https://c.test/adverse","passages":{"P1":"The source reports an unresolved qualification."}}
    result=compile_assessment(raw(origins=[dict(source="S3",underlying_origin="unknown",verification_action="unknown",passages=["P1"],unresolved_material_questions=["Does this qualification undermine the original claim?"])]),{"C0":CLAIM},[*RECORDS,extra])
    assert "Does this qualification undermine the original claim?" in result.gaps


def test_baseline_wire_schema_excludes_ledger_storage_fields():
    schema=EvidenceAssessment.model_json_schema()
    assert "component_ledger" not in schema["properties"] and "source_origin_ledger" not in schema["properties"]
    assert "raw_indexed_assessment" not in schema["properties"] and "indexed_input" not in schema["properties"]
    result=compile_assessment(raw(),{"C0":CLAIM},RECORDS)
    assert result.model_dump()["component_ledger"]


def test_saved_assessment_self_resolves_component_finding_and_passage_ids():
    result=compile_assessment(raw(),{"C0":CLAIM},RECORDS)
    restored=EvidenceAssessment.model_validate_json(result.model_dump_json())
    finding=next(f for f in restored.raw_indexed_assessment["findings"] if f["id"]==restored.component_ledger[0]["findings"][0])
    source=next(r for r in restored.indexed_input["records"] if r["id"]==finding["source"])
    assert source["passages"][finding["passage"]]==restored.evidence[0].quotes[source["url"]]
    assert restored.indexed_input["components"]["C0"]==CLAIM


def test_indexed_windows_are_literal_source_spans():
    source=sources()[0];source.page_text=" ".join(str(i) for i in range(1000))
    records=indexed_records([source])
    assert all(q in source.retrieved_text and len(q.split())<=120 for q in records[0]["passages"].values())


def test_advisory_plan_retained_without_turning_meta_statements_into_obligations(config):
    class Backend(DeterministicBackend):
        seen=None
        def decompose_with_questions(self,claim,*,reference_date):
            return QuestionDecomposition(assertions=["The claim's reference date is 2024."],questions=["What record establishes the vote and date?"]),17
        def analyze_indexed(self,claim,domain,assertions,sources,prior_gaps,reference_date,guidance,**kwargs):
            self.seen=(assertions,kwargs)
            return EvidenceAssessment(gaps=["Fixture remains unresolved."],component_ledger=[{"id":"C0","unresolved_material_questions":["Fixture remains unresolved."]}]),11
    backend=Backend();config["model"].update(decomposition_method="questions_as_guidance",assessment_mode="ledger")
    result=run_claim(CLAIM,domain="general",reference_date="2024-06-30",max_rounds=1,model=backend,retriever=StaticRetriever(),config=config)
    assert result.assertions==[CLAIM]
    assert result.planning_statements==["The claim's reference date is 2024."]
    assert backend.seen[1]["planning_statements"]==result.planning_statements
    assert backend.seen[1]["verification_questions"]==result.verification_questions
    assert result.research_history[0].assessment.component_ledger
    assert result.verdict=="UNVERIFIED"

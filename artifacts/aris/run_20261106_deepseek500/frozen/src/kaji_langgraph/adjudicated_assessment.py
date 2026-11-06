"""Explicit component classes and literal provenance anchors.

This adapter translates explicit model classes into the existing adjudicated
boolean. It never infers a class from IDs or the overall proposal, and every
material question still blocks. Literal metadata is unverified source content.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kaji_langgraph.indexed_assessment import IndexedComponent, IndexedOrigin
from kaji_langgraph.models import Confidence
from kaji_langgraph.reference_assessment import ReferenceAssessment, ReferenceFinding, compile_references
from kaji_langgraph.publication_dates import source_publications, source_date_mentions
from kaji_langgraph.scope_assessment import NonblockingLimitation
from kaji_langgraph.selected_assessment import StrictReference, selected_decision_prompt, selected_ranges


CLASSES = {"supported": "TRUE", "refuted": "FALSE", "conflicting": "CONFLICTING", "insufficient": "NOT_ENOUGH_EVIDENCE"}


class ComponentClass(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    adjudication: Literal["supported", "refuted", "conflicting", "insufficient"]
    findings: list[str]
    rationale: str = ""
    questions: list[str] = Field(default_factory=list)
    unresolved_material_questions: list[str] = Field(default_factory=list)


class QuotedOrigin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    origin: StrictReference | None = None
    verification_action: StrictReference | None = None
    unresolved_material_questions: list[str] = Field(default_factory=list)


class AdjudicatedDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    findings: list[ReferenceFinding]
    origins: list[QuotedOrigin]
    components: list[ComponentClass]
    proposed_verdict: Literal["TRUE", "FALSE", "CONFLICTING", "NOT_ENOUGH_EVIDENCE"]
    confidence: Confidence
    summary: str
    gaps: list[str]
    contradictions: list[str]
    counterevidence_searched: bool
    sources_independent: bool
    peer_reviewed_sources: bool = False
    next_queries: list[str] = Field(default_factory=list)
    nonblocking_limitations: list[NonblockingLimitation] = Field(default_factory=list)


def compile_adjudicated(raw, components, records):
    lookup = {r["id"]: r for r in records}
    publication_evidence = source_publications(records)
    gaps = list(raw.gaps)
    if len({row.source for row in raw.origins}) != len(raw.origins):
        gaps.append("Duplicate literal source-origin rows.")

    def quote(ref, source_id, label):
        if ref is None:
            return ""
        source = lookup.get(ref.source, {})
        offsets = source.get("paragraph_offsets", {})
        a, b = offsets.get(ref.first_paragraph), offsets.get(ref.last_paragraph)
        if ref.source != source_id or not a or not b or a[0] > b[0]:
            gaps.append(f"Invalid literal {label} reference for {source_id}")
            return ""
        value = source["visible_text"][a[0]:b[1]]
        if len(value.split()) > 250:
            gaps.append(f"Over-250-word literal {label} for {source_id}")
            return ""
        return value

    origins = []
    for row in raw.origins:
        origin = quote(row.origin, row.source, "origin")
        action = quote(row.verification_action, row.source, "source action")
        refs = [row.origin, row.verification_action]
        passage_ids = []
        source = lookup.get(row.source, {})
        keys = list(source.get("paragraph_offsets", {}))
        for ref in refs:
            if ref and ref.source == row.source and ref.first_paragraph in keys and ref.last_paragraph in keys:
                i, j = keys.index(ref.first_paragraph), keys.index(ref.last_paragraph)
                passage_ids.extend(keys[i:j + 1])
        origins.append(IndexedOrigin(source=row.source, underlying_origin=origin,
            verification_action=action, passages=list(dict.fromkeys(passage_ids)),
            event_or_data_date="",
            publication_date=publication_evidence.get(row.source, {}).get("text") or "",
            unresolved_material_questions=row.unresolved_material_questions))
    classified = []
    for row in raw.components:
        if row.id == "C0" and CLASSES[row.adjudication] != raw.proposed_verdict:
            gaps.append("C0 adjudication differs from the whole-claim proposed label; both raw judgments retained.")
        classified.append(IndexedComponent(id=row.id,
            resolved=row.adjudication in {"supported", "refuted", "conflicting"},
            findings=row.findings, questions=row.questions,
            unresolved_material_questions=row.unresolved_material_questions))
    converted = ReferenceAssessment.model_validate({**raw.model_dump(),
        "components": [c.model_dump() for c in classified],
        "origins": [o.model_dump() for o in origins], "gaps": gaps})
    result = compile_references(converted, components, records)
    result.indexed_input["explicit_adjudication_response"] = raw.model_dump(mode="json")
    result.indexed_input["adjudication_class_mapping"] = dict(CLASSES)
    result.indexed_input["source_publication_evidence"] = publication_evidence
    result.indexed_input["source_date_mentions"] = source_date_mentions(records)
    for origin in result.source_origin_ledger:
        origin["publication_date_evidence"] = publication_evidence.get(origin["source"], {})
        origin["date_mentions"] = result.indexed_input["source_date_mentions"].get(origin["source"], [])
    for row in result.component_ledger:
        choices = [c.adjudication for c in raw.components if c.id == row["id"]]
        row["explicit_adjudications"] = choices
        row["adjudication_rationales"] = [c.rationale for c in raw.components if c.id == row["id"]]
    for note in raw.nonblocking_limitations:
        if note.component not in components:
            result.gaps.append(f"Unknown limitation component: {note.component}")
    return result


def record_inventory(records, ranges):
    visible = [r["id"] for r in records]
    selected = list(dict.fromkeys(r["reference"]["source"] for r in ranges))
    return {"visible_source_ids": visible, "visible_source_count": len(visible),
        "selected_source_ids": selected, "selected_source_count": len(selected),
        "unselected_source_ids": [s for s in visible if s not in selected],
        "meaning": "Selected ranges are a subset of the full records below. Counts do not certify evidentiary independence."}


def adjudication_prompt(context, selection, ranges):
    context = {**context, "record_inventory": record_inventory(context.get("records", []), ranges)}
    base = selected_decision_prompt(context, selection, ranges).split("\nReturn ONLY JSON matching:\n", 1)[0]
    return """Use explicit per-component evidentiary adjudication classes. Each ID is
bound by the client to its exact original assertion. supported/refuted/conflicting
means that component has been adjudicated in that class; insufficient means it
has not been adjudicated in any of those three classes. Do NOT return a resolved
boolean. Do not use conflicting merely for missing evidence or different targets.
C0 is the exact whole claim, so its class must agree with the proposed whole-claim
class. Other components may have different classes. Explain their evidence class
in a short rationale when needed. The client encodes the explicit class as the
existing adjudicated boolean; it never chooses the class or confidence for you.

For conflict, distinguish the current evidentiary classification from settlement
of the underlying real value. Comparable supported opposed observations can
adjudicate the evidence as conflicting. You may retain actual precision,
reconciliation or source-quality uncertainty and conservatively withhold final
acceptance; do not simultaneously declare the established evidence-class opposition
unadjudicated. A genuine uncertainty undermining alignment, reliability or the
existence of a side stays material. Do not hide it, force confidence, or assert
statistical significance/logically incompatible population facts without evidence.

Origin rows contain ONLY source IDs and literal anchors, not written captions.
origin selects text documenting the underlying record/origin. verification_action
selects the SOURCE'S reported action, never your act of checking input text.
Select origin/action ranges within that same source; all intervening text
stays, at most250words. Unknown anchors are null, not invented descriptions.
Do not generate separate date metadata. Dates and their qualifications remain
in the original records and must be judged for the exact claim. A document date
does not establish a measurement date. Any material temporal uncertainty stays
blocking; omitting a metadata field never resolves a claim's date component.
The client retains literal date context separately for audit without assigning
an event/data role from an unlabeled date. A source's reported interviewing,
recording, collecting or calculating is a source action, not external certification.
Each one-source finding must describe that cited record. Do not call it the only
record/source in the whole packet when other supplied records exist, or quantify
over other records without directly supported source evidence. Keep findings
free of cross-case references; each fixture is assessed from its own packet.
Literal copied text is still unverified source content, not certified provenance.
Judge independence for evidentiary paths relevant to the exact target; independent
recordings of an utterance are not independent measurements of its embedded statistic.
All material origin questions, component questions, gaps and contradictions still
block, including if you classify a component adjudicated. Confidence and actual
source independence remain your own judgments; no enum or anchor certifies them.

""" + base + "\nReturn ONLY JSON matching:\n" + json.dumps(AdjudicatedDecision.model_json_schema(), separators=(",", ":"))


def compile_adjudicated_selection(selection, decision, components, records):
    ranges = selected_ranges(selection, components, records)
    result = compile_adjudicated(decision, components, records)
    result.indexed_input.update({"selection_ledger": selection.model_dump(mode="json"),
        "selected_literal_ranges": ranges,
        "selected_decision": {"nonblocking_limitations": [n.model_dump() for n in decision.nonblocking_limitations]}})
    return result

"""Compile explicit component/finding references into the unchanged gate input.

IDs identify supplied strings and passages. They do not infer resolution,
confidence, semantic support or source independence.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel,Field

from kaji_langgraph.models import AssertionAssessment,Confidence,EvidenceAssessment,EvidenceItem


class IndexedFinding(BaseModel):
    id: str
    finding: str=Field(min_length=1)
    source: str
    passage: str
    stance: Literal["supports","refutes","context"]


class IndexedComponent(BaseModel):
    id: str
    resolved: bool
    findings: list[str]
    questions: list[str]=Field(default_factory=list)
    unresolved_material_questions: list[str]=Field(default_factory=list)


class IndexedOrigin(BaseModel):
    source: str
    underlying_origin: str
    verification_action: str
    passages: list[str]
    event_or_data_date: str = ""
    publication_date: str = ""
    unresolved_material_questions: list[str]=Field(default_factory=list)


class IndexedAssessment(BaseModel):
    proposed_verdict: Literal["TRUE","FALSE","CONFLICTING","NOT_ENOUGH_EVIDENCE"]
    confidence: Confidence
    summary: str
    findings: list[IndexedFinding]
    components: list[IndexedComponent]
    origins: list[IndexedOrigin]=Field(default_factory=list)
    gaps: list[str]
    contradictions: list[str]
    counterevidence_searched: bool
    sources_independent: bool
    peer_reviewed_sources: bool=False
    next_queries: list[str]=Field(default_factory=list)


def compile_assessment(raw: IndexedAssessment,components: dict[str,str],records: list[dict], *, require_ledger: bool=False) -> EvidenceAssessment:
    sources={r["id"]:r for r in records};findings={f.id:f for f in raw.findings}
    gaps=list(raw.gaps)
    if len(findings)!=len(raw.findings):gaps.append("Duplicate finding IDs are not allowed.")
    if len({c.id for c in raw.components})!=len(raw.components):gaps.append("Duplicate component IDs are not allowed.")
    evidence=[]
    for finding in raw.findings:
        record=sources.get(finding.source,{})
        url=record.get("url","unresolved:"+finding.source)
        quote=record.get("passages",{}).get(finding.passage,"")
        evidence.append(EvidenceItem(finding=finding.finding,source_urls=[url],quotes={url:quote},stance=finding.stance))
    assertions=[]
    for row in raw.components:
        gaps.extend(row.unresolved_material_questions)
        if row.id not in components:
            gaps.append(f"Unknown component ID: {row.id}")
            continue
        urls=[]
        for id in row.findings:
            if id not in findings:
                gaps.append(f"Unknown finding ID for {row.id}: {id}")
                continue
            source_id=findings[id].source
            urls.append(sources.get(source_id,{}).get("url","unresolved:"+source_id))
        assertions.append(AssertionAssessment(assertion=components[row.id],resolved=row.resolved,
                                              source_urls=list(dict.fromkeys(urls))))
    for id in components:
        if id not in {row.id for row in raw.components}:gaps.append(f"Missing required component: {id}")
    cited={f.source for f in raw.findings}
    if require_ledger:
        for id in cited-{o.source for o in raw.origins}:
            gaps.append(f"Missing cited-source origin ledger: {id}")
    for origin in raw.origins:
        source=sources.get(origin.source)
        if not source:gaps.append(f"Unknown source in origin ledger: {origin.source}")
        elif any(p not in source["passages"] for p in origin.passages):gaps.append(f"Unknown passage in origin ledger: {origin.source}")
        # A declared material issue cannot be cleared by omitting its source
        # from the findings. Preserve adverse/uncited provenance questions too.
        gaps.extend(origin.unresolved_material_questions)
    return EvidenceAssessment(proposed_verdict=raw.proposed_verdict,confidence=raw.confidence,summary=raw.summary,
        evidence=evidence,assertions=assertions,gaps=list(dict.fromkeys(gaps)),contradictions=raw.contradictions,
        counterevidence_searched=raw.counterevidence_searched,sources_independent=raw.sources_independent,
        peer_reviewed_sources=raw.peer_reviewed_sources,next_queries=raw.next_queries,
        component_ledger=[{**row.model_dump(),"assertion":components.get(row.id)} for row in raw.components],
        source_origin_ledger=[row.model_dump() for row in raw.origins],
        raw_indexed_assessment=raw.model_dump(mode="json"),
        indexed_input={"components":dict(components),"records":records})

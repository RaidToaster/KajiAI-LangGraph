"""Deterministic evidence acceptance checks; model confidence is never enough."""

from __future__ import annotations

from urllib.parse import urlsplit

from kaji_langgraph.models import EvidenceAssessment, EvidenceItem, SourceRecord
from kaji_langgraph.retrieval import annotate_duplicate_lineage


def _host(url: str) -> str:
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"}:
            return ""
        return (parsed.hostname or "").removeprefix("www.")
    except ValueError:
        return ""


def evidence_gaps(
    assessment: EvidenceAssessment,
    assertions: list[str],
    sources: list[SourceRecord],
    policy: dict,
) -> list[str]:
    gaps = [*assessment.gaps, *assessment.contradictions]
    retrieved = {source.url: source for source in sources if _host(source.url) and source.retrieved_text}
    cited = {url for item in assessment.evidence for url in item.source_urls}

    if assessment.proposed_verdict not in {"TRUE", "FALSE", "MISLEADING"}:
        gaps.append("No supported verdict yet.")
    if assessment.confidence != "High":
        gaps.append("Evidence confidence remains below High.")
    if not assessment.evidence or any(not item.finding.strip() or not item.source_urls for item in assessment.evidence):
        gaps.append("Every finding needs retrieved citations.")
    if not cited <= set(retrieved):
        gaps.append("Some citations were not retrieved.")

    if policy.get("require_evidence_quotes", True):
        for item in assessment.evidence:
            for url in item.source_urls:
                quote = item.quotes.get(url, "").strip()
                record = retrieved.get(url)
                if not quote or record is None or quote not in record.retrieved_text:
                    gaps.append("Each citation needs an exact quote from its retrieved text.")

    if len({_host(url) for url in cited if url in retrieved}) < 2:
        gaps.append("Find relevant evidence from at least two source hosts.")

    annotated = annotate_duplicate_lineage(list(retrieved.values()))
    if any(record.possible_duplicate_of and record.url in cited for record in annotated):
        gaps.append("Some cited hosts repeat substantially similar text; verify original-source lineage.")

    if policy.get("require_https") and any(urlsplit(url).scheme != "https" for url in cited):
        gaps.append("This domain requires HTTPS citations.")
    if policy.get("require_peer_reviewed") and not assessment.peer_reviewed_sources:
        gaps.append("This domain requires peer-reviewed evidence.")

    if len(assessment.assertions) != len({item.assertion for item in assessment.assertions}):
        gaps.append("Duplicate assertion assessments are not allowed.")
    by_assertion = {item.assertion: item for item in assessment.assertions}
    for assertion in assertions:
        item = by_assertion.get(assertion)
        if (
            item is None
            or not item.resolved
            or not item.source_urls
            or not set(item.source_urls) <= (set(retrieved) & cited)
        ):
            gaps.append(f"Resolve and cite the assertion: {assertion}")

    if not assessment.counterevidence_searched:
        gaps.append("Search for evidence against the proposed conclusion.")
    if not assessment.sources_independent:
        gaps.append("Establish source independence; copied reporting is not corroboration.")
    return list(dict.fromkeys(gap for gap in gaps if gap.strip()))


def retained_evidence(assessment: EvidenceAssessment, sources: list[SourceRecord]) -> list[EvidenceItem]:
    retrieved = {source.url: source for source in sources if source.retrieved_text and _host(source.url)}
    retained: list[EvidenceItem] = []
    for item in assessment.evidence:
        urls = [url for url in item.source_urls if url in retrieved]
        quotes = {
            url: quote
            for url, quote in item.quotes.items()
            if url in urls and quote.strip() and quote in retrieved[url].retrieved_text
        }
        if item.finding.strip() and urls:
            retained.append(item.model_copy(update={"source_urls": urls, "quotes": quotes}))
    return retained


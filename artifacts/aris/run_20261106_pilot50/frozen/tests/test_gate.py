from datetime import datetime, timezone
import hashlib

from kaji_langgraph.gate import evidence_gaps
from kaji_langgraph.models import AssertionAssessment, EvidenceAssessment, EvidenceItem, SourceRecord


def source(url: str, text: str) -> SourceRecord:
    return SourceRecord(
        url=url,
        snippet=text,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        query="test query",
        provider="fixture",
        lineage_id=hashlib.sha256(url.encode()).hexdigest(),
    )


def valid_assessment(assertion: str, records: list[SourceRecord]) -> EvidenceAssessment:
    urls = [record.url for record in records]
    return EvidenceAssessment(
        proposed_verdict="TRUE",
        confidence="High",
        evidence=[EvidenceItem(
            finding="Both records support the assertion.",
            source_urls=urls,
            quotes={record.url: record.snippet for record in records},
            stance="supports",
        )],
        assertions=[AssertionAssessment(assertion=assertion, resolved=True, source_urls=urls)],
        counterevidence_searched=True,
        sources_independent=True,
    )


def test_evidence_gate_accepts_complete_provenance():
    assertion = "A test event happened"
    records = [source("https://a.example/x", "Primary source confirms event A."), source("https://b.example/y", "Independent source verifies event A differently.")]
    assert evidence_gaps(valid_assessment(assertion, records), [assertion], records, {"require_evidence_quotes": True}) == []


def test_evidence_gate_rejects_quote_not_in_retrieved_text():
    assertion = "A test event happened"
    records = [source("https://a.example/x", "Text A"), source("https://b.example/y", "Text B")]
    assessment = valid_assessment(assertion, records)
    assessment.evidence[0].quotes[records[0].url] = "Invented quotation"
    assert "Each citation needs an exact quote from its retrieved text." in evidence_gaps(assessment, [assertion], records, {"require_evidence_quotes": True})


def test_citation_provenance_rejects_unretrieved_url():
    assertion = "A test event happened"
    records = [source("https://a.example/x", "Text A"), source("https://b.example/y", "Text B")]
    assessment = valid_assessment(assertion, records)
    assessment.evidence[0].source_urls.append("https://invented.example/z")
    assessment.evidence[0].quotes["https://invented.example/z"] = "Fabricated"
    assert "Some citations were not retrieved." in evidence_gaps(assessment, [assertion], records, {"require_evidence_quotes": True})


"""Typed domain records for retrieval, assessment, budgets, and reports."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

Domain = Literal["auto", "general", "scientific", "political", "health_medical"]
Verdict = Literal["TRUE", "FALSE", "MISLEADING", "CONFLICTING", "NOT_ENOUGH_EVIDENCE", "UNVERIFIED"]
Confidence = Literal["Low", "Medium", "High"]


class Classification(BaseModel):
    domain: Literal["general", "scientific", "political", "health_medical"] = "general"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""
    risk_level: Literal["low", "medium", "high"] = "low"


class Decomposition(BaseModel):
    assertions: list[str] = Field(default_factory=list)


class QuestionDecomposition(BaseModel):
    """Unverified statements and search questions, never evidence or answers."""

    assertions: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]] = Field(
        min_length=1, max_length=6,
    )
    questions: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]] = Field(
        min_length=1, max_length=8,
    )


class SourceRecord(BaseModel):
    title: str = ""
    url: str
    snippet: str = ""
    page_text: str = ""
    retrieved_at: str
    content_hash: str
    query: str
    provider: str
    cached: bool = False
    retrieval_kind: Literal["snippet", "full_page"] = "snippet"
    status_code: int | None = None
    lineage_id: str = ""
    possible_duplicate_of: list[str] = Field(default_factory=list)
    jev_scores: dict[str, float] = Field(default_factory=dict)

    @property
    def retrieved_text(self) -> str:
        return self.page_text or self.snippet


class EvidenceItem(BaseModel):
    finding: str = ""
    source_urls: list[str] = Field(default_factory=list)
    quotes: dict[str, str] = Field(default_factory=dict)
    stance: Literal["supports", "refutes", "context"] = "context"


class AssertionAssessment(BaseModel):
    assertion: str
    resolved: bool = False
    source_urls: list[str] = Field(default_factory=list)
    rationale: str = ""


class EvidenceAssessment(BaseModel):
    proposed_verdict: Verdict = "UNVERIFIED"
    confidence: Confidence = "Low"
    summary: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    assertions: list[AssertionAssessment] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    counterevidence_searched: bool = False
    sources_independent: bool = False
    peer_reviewed_sources: bool = False
    next_queries: list[str] = Field(default_factory=list)


class BenchmarkAssessment(EvidenceAssessment):
    """A factual four-class decision; operational failures stay outside this schema."""

    proposed_verdict: Literal["TRUE", "FALSE", "CONFLICTING", "NOT_ENOUGH_EVIDENCE"] = Field(...)


class BudgetState(BaseModel):
    max_rounds: int = Field(default=10, ge=1, le=10)
    max_search_calls: int = Field(default=20, ge=0)
    max_scrapes: int = Field(default=20, ge=0)
    max_tokens: int = Field(default=250000, ge=0)
    max_seconds: float = Field(default=1800.0, ge=0)
    search_calls: int = 0
    scrapes: int = 0
    tokens_used: int = 0
    token_usage_complete: bool = True
    started_at_monotonic: float = 0.0


class ResearchRound(BaseModel):
    round_number: int
    queries: list[str] = Field(default_factory=list)
    new_sources: int = 0
    proposed_verdict: Verdict = "UNVERIFIED"
    confidence: Confidence = "Low"
    gaps: list[str] = Field(default_factory=list)
    decision: str = ""
    # Preserve the unfiltered model proposal and the exact source versions used
    # by the gate. This permits policy replay without new model/search calls.
    assessment: EvidenceAssessment | None = None
    usable_source_keys: list[tuple[str, str]] = Field(default_factory=list)
    structural_gaps: list[str] = Field(default_factory=list)
    semantic_gaps: list[str] = Field(default_factory=list)
    fatal_error: bool = False
    budget: BudgetState | None = None
    elapsed_seconds: float = 0.0


class FinalResult(BaseModel):
    claim: str
    domain: str
    verdict: Verdict = "UNVERIFIED"
    predicted_verdict: Verdict = "UNVERIFIED"
    prediction_confidence: Confidence = "Low"
    prediction_summary: str = ""
    verification_status: Literal["verified", "insufficient_evidence", "execution_error", "invalid_input"] = "insufficient_evidence"
    confidence: Confidence = "Low"
    summary: str = ""
    stop_reason: str = ""
    reference_date: str = ""
    reference_timezone: str = ""
    execution_id: str = ""
    elapsed_seconds: float = 0.0
    evidence: list[EvidenceItem] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    retrieval_ledger: list[SourceRecord] = Field(default_factory=list)
    assertions: list[str] = Field(default_factory=list)
    verification_questions: list[str] = Field(default_factory=list)
    decomposition_method: str = "statements"
    gaps: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    research_history: list[ResearchRound] = Field(default_factory=list)
    budget: BudgetState
    errors: list[str] = Field(default_factory=list)
    jev_audit: dict[str, Any] = Field(default_factory=dict)

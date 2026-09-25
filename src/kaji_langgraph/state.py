"""LangGraph state shared by all workflow nodes."""

from __future__ import annotations

from typing import Any, TypedDict

from kaji_langgraph.models import (
    BudgetState,
    EvidenceAssessment,
    FinalResult,
    ResearchRound,
    SourceRecord,
)


class ClaimState(TypedDict, total=False):
    claim: str
    requested_domain: str
    domain: str
    classification: dict[str, Any]
    assertions: list[str]
    sources: list[SourceRecord]
    research_round: int
    research_history: list[ResearchRound]
    assessment: EvidenceAssessment
    gaps: list[str]
    contradictions: list[str]
    budgets: BudgetState
    stop_reason: str
    verdict: str
    report: str
    result: FinalResult
    errors: list[str]
    fatal_error: bool
    budget_blocked: bool
    search_queries: list[str]
    stagnant_rounds: int
    last_new_sources: int
    route: str
    reference_date: str
    reference_datetime: str
    reference_timezone: str
    execution_id: str
    policy: dict[str, Any]
    jev_audit: dict[str, Any]
    semantic_gaps: list[str]

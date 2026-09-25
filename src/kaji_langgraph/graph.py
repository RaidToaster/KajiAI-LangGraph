"""Graph API orchestration for bounded evidence-driven claim analysis."""

from __future__ import annotations

from datetime import datetime
import hashlib
import os
import time
from typing import Any, Literal
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langgraph.graph import END, START, StateGraph

from kaji_langgraph.config import effective_policy, load_config
from kaji_langgraph.gate import evidence_gaps, retained_evidence
from kaji_langgraph.jev import JevClient
from kaji_langgraph.llm import ModelBackend, OllamaBackend, heuristic_decomposition, keyword_classification
from kaji_langgraph.models import (
    BudgetState,
    EvidenceAssessment,
    FinalResult,
    ResearchRound,
    SourceRecord,
)
from kaji_langgraph.report import format_report
from kaji_langgraph.retrieval import TinyFishRetriever, Retriever, annotate_duplicate_lineage, fetch_page, normalize_result
from kaji_langgraph.state import ClaimState


def _clock() -> tuple[str, str, str]:
    import os

    timezone_name = os.getenv("KAJI_TIMEZONE", "Asia/Jakarta")
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone = datetime.now().astimezone().tzinfo
    now = datetime.now(timezone)
    date = os.getenv("KAJI_CURRENT_DATE", "").strip() or now.date().isoformat()
    datetime.strptime(date, "%Y-%m-%d")
    return date, now.isoformat(timespec="seconds"), str(timezone)


def _elapsed(state: ClaimState) -> float:
    budget = state["budgets"]
    return max(0.0, time.monotonic() - budget.started_at_monotonic)


def _budget_reason(state: ClaimState) -> str:
    budget = state["budgets"]
    if state.get("research_round", 0) >= budget.max_rounds:
        return "max_rounds"
    if budget.search_calls >= budget.max_search_calls:
        return "search_budget_exhausted"
    if budget.tokens_used >= budget.max_tokens:
        return "token_budget_exhausted"
    if _elapsed(state) >= budget.max_seconds:
        return "time_budget_exhausted"
    return ""


def _record_tokens(state: ClaimState, tokens: int | None) -> BudgetState:
    budget = state["budgets"].model_copy(deep=True)
    if tokens is None:
        budget.token_usage_complete = False
    else:
        budget.tokens_used += max(0, tokens)
    return budget


def _add_tokens(budget: BudgetState, tokens: int | None) -> BudgetState:
    updated = budget.model_copy(deep=True)
    if tokens is None:
        updated.token_usage_complete = False
    else:
        updated.tokens_used += max(0, tokens)
    return updated


def _remaining(state: ClaimState, budget: BudgetState) -> float:
    return max(0.0, budget.max_seconds - _elapsed({**state, "budgets": budget}))


def _citation_key(finding: str, url: str, quote: str, content_hash: str) -> str:
    value = f"{finding}\0{url}\0{quote}\0{content_hash}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class WorkflowNodes:
    def __init__(
        self, model: ModelBackend, retriever: Retriever, config: dict[str, Any],
        jev: JevClient | None = None,
    ) -> None:
        self.model = model
        self.retriever = retriever
        self.config = config
        self.jev = jev

    def usable_sources(self, state: ClaimState) -> list[SourceRecord]:
        sources = list(state.get("sources", []))
        if not self.jev:
            return sources
        cfg = self.config["jev"]
        return [
            source for source in sources
            if source.jev_scores.get("injection", 0) < cfg.get("injection_cutoff", 0.9)
            and not all(
                source.jev_scores.get(field, 1) < cfg.get("irrelevant_cutoff", 0.1)
                for field in ("relevant", "evidence", "counterevidence")
            )
        ]

    def citation_review_gaps(self, state: ClaimState) -> list[str]:
        if not self.jev:
            return []
        reviews = {
            item.get("key"): item
            for item in state.get("jev_audit", {}).get("citations", [])
            if item.get("round") == state.get("research_round", 0)
        }
        sources = {source.url: source for source in self.usable_sources(state)}
        gaps = []
        for evidence in state.get("assessment", EvidenceAssessment()).evidence:
            for url in evidence.source_urls:
                source = sources.get(url)
                quote = evidence.quotes.get(url, "")
                if not source or not quote or quote not in source.retrieved_text:
                    continue  # The structural gate handles these citations.
                key = _citation_key(evidence.finding, url, quote, source.content_hash)
                review = reviews.get(key)
                if review is None:
                    gaps.append(f"Citation support was not checked for {url}.")
                elif review["confidence"] < self.config["jev"].get("citation_min_confidence", 0.8):
                    gaps.append(f"Citation support is uncertain for {url}.")
                elif review["relation"] != "supports":
                    gaps.append(f"Citation {review['relation']} the finding: {url}.")
        return list(dict.fromkeys(gaps))

    def validate(self, state: ClaimState) -> dict[str, Any]:
        claim = state.get("claim", "").strip()
        requested = state.get("requested_domain", "auto")
        if requested not in {"auto", "general", "scientific", "political", "health_medical"}:
            return {"errors": [f"Unsupported domain: {requested}"], "stop_reason": "validation_error"}
        if not claim:
            return {"errors": ["Claim must not be empty."], "stop_reason": "validation_error"}
        date, timestamp, timezone = _clock()
        return {
            "claim": claim,
            "sources": [],
            "assertions": [],
            "research_round": 0,
            "research_history": [],
            "assessment": EvidenceAssessment(),
            "gaps": [],
            "contradictions": [],
            "errors": [],
            "jev_audit": {"search_ranking": [], "citations": []},
            "semantic_gaps": [],
            "fatal_error": False,
            "budget_blocked": False,
            "search_queries": [],
            "stagnant_rounds": 0,
            "stop_reason": "",
            "verdict": "UNVERIFIED",
            "reference_date": date,
            "reference_datetime": timestamp,
            "reference_timezone": timezone,
            "execution_id": str(uuid4()),
        }

    def classify(self, state: ClaimState) -> dict[str, Any]:
        requested = state.get("requested_domain", "auto")
        budget = state["budgets"]
        errors = list(state.get("errors", []))
        jev_audit = dict(state.get("jev_audit", {}))
        parsed = None
        if requested != "auto":
            domain = requested
            classification = {"domain": domain, "reasoning": "Explicit CLI override."}
        elif _elapsed(state) >= budget.max_seconds:
            parsed = keyword_classification(state["claim"])
            domain = parsed.domain
            classification = parsed.model_dump()
            classification["reasoning"] += " Classification model skipped because the time budget was exhausted."
        else:
            if self.jev:
                try:
                    candidate, tokens = self.jev.classify(
                        state["claim"], timeout=min(10.0, _remaining(state, budget))
                    )
                    budget = _add_tokens(budget, tokens)
                    accepted = candidate.confidence >= self.config["jev"].get("domain_min_confidence", 0.6)
                    jev_audit["domain"] = {
                        "domain": candidate.domain,
                        "confidence": candidate.confidence,
                        "used": accepted,
                        "model": getattr(self.jev, "model", ""),
                    }
                    if accepted:
                        parsed = candidate
                except Exception as exc:
                    errors.append(f"Jev domain routing failed: {type(exc).__name__}: {exc}")
            if parsed is None and _remaining(state, budget) > 0 and budget.tokens_used < budget.max_tokens:
                try:
                    parsed, tokens = self.model.classify(state["claim"])
                    budget = _add_tokens(budget, tokens)
                except Exception as exc:
                    errors.append(f"Classification model unavailable: {type(exc).__name__}: {exc}")
                    budget = _add_tokens(budget, None)
            if parsed is None:
                parsed = keyword_classification(state["claim"])
                parsed.reasoning += " Model classification was unavailable."
            domain = parsed.domain
            classification = parsed.model_dump()
        policy = effective_policy(self.config, domain)
        budget = budget.model_copy(
            update={
                "max_search_calls": policy["max_search_calls"],
                "max_scrapes": policy["max_scrapes"],
                "max_tokens": policy["max_token_limit"],
                "max_seconds": policy["max_execution_time_seconds"],
                "max_rounds": state["budgets"].max_rounds,
            }
        )
        update: dict[str, Any] = {
            "domain": domain,
            "classification": classification,
            "policy": policy,
            "budgets": budget,
            "errors": errors,
            "jev_audit": jev_audit,
        }
        return update

    def decompose(self, state: ClaimState) -> dict[str, Any]:
        if _budget_reason(state) in {"token_budget_exhausted", "time_budget_exhausted"}:
            assertions, tokens = heuristic_decomposition(state["claim"]), 0
        else:
            try:
                assertions, tokens = self.model.decompose(state["claim"])
            except Exception as exc:
                assertions, tokens = heuristic_decomposition(state["claim"]), None
                errors = [
                    *state.get("errors", []),
                    f"Decomposition model unavailable: {type(exc).__name__}: {exc}",
                ]
        assertions = [item.strip() for item in assertions if item.strip()]
        assertions = list(dict.fromkeys([state["claim"], *assertions]))
        update: dict[str, Any] = {"assertions": assertions, "budgets": _record_tokens(state, tokens)}
        if "errors" in locals():
            update["errors"] = errors
        return update

    def retrieve(self, state: ClaimState) -> dict[str, Any]:
        budget = state["budgets"].model_copy(deep=True)
        if _budget_reason(state):
            return {"last_new_sources": 0, "budget_blocked": True}
        assessment = state.get("assessment", EvidenceAssessment())
        previous = set(state.get("search_queries", []))
        if assessment.next_queries:
            candidates = assessment.next_queries
        else:
            candidates = [
                *[f"{assertion} evidence" for assertion in state["assertions"]],
                f"{state['claim']} counterevidence",
            ]
        queries = [query for query in candidates if query.strip() and query not in previous]
        if not queries:
            queries = [f"{state['claim']} evidence counterevidence"] if not previous else []
        allowed = min(
            state["policy"].get("search_calls_per_round", 2),
            max(0, budget.max_search_calls - budget.search_calls),
        )
        queries = queries[:allowed]
        existing = list(state.get("sources", []))
        seen = {(record.url, record.content_hash) for record in existing}
        new_records: list[SourceRecord] = []
        errors = list(state.get("errors", []))
        jev_audit = dict(state.get("jev_audit", {}))
        search_ranking = list(jev_audit.get("search_ranking", []))
        deadline_reached = False
        for query in queries:
            if _elapsed({**state, "budgets": budget}) >= budget.max_seconds:
                deadline_reached = True
                break
            budget.search_calls += 1
            max_retries = (
                max(0, int(state["policy"].get("max_retries", 0)))
                if state["policy"].get("retry_on_failure", True)
                else 0
            )
            retry_delay = max(0.0, float(state["policy"].get("retry_delay_seconds", 0)))
            results = None
            last_error: Exception | None = None
            attempts = 0
            for attempt in range(max_retries + 1):
                if _elapsed({**state, "budgets": budget}) >= budget.max_seconds:
                    deadline_reached = True
                    break
                attempts += 1
                try:
                    results = self.retriever.search(
                        query,
                        max_results=state["policy"].get("max_results_per_search", 5),
                    )
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt >= max_retries:
                        break
                    delay = retry_delay * (attempt + 1)
                    remaining = budget.max_seconds - _elapsed({**state, "budgets": budget})
                    if delay >= remaining:
                        deadline_reached = True
                        break
                    if delay:
                        time.sleep(delay)
            if results is None:
                if deadline_reached:
                    errors.append(f"Retrieval deadline reached after {attempts} attempt(s) for query: {query}")
                elif last_error is not None:
                    errors.append(
                        f"Retrieval failed after {attempts} attempt(s): "
                        f"{type(last_error).__name__}: {last_error}"
                    )
                continue
            if self.jev and len(results) > 1 and _remaining(state, budget) > 1 and budget.tokens_used < budget.max_tokens:
                try:
                    scores, tokens = self.jev.rank_results(
                        state["claim"], query, results,
                        timeout=min(10.0, _remaining(state, budget)),
                    )
                    if len(scores) != len(results):
                        raise ValueError("Jev returned an incomplete search ranking")
                    budget = _add_tokens(budget, tokens)
                    search_ranking.extend(
                        {"query": query, "url": str(item.get("url") or item.get("href") or ""), "score": score}
                        for item, score in zip(results, scores)
                    )
                    results = [item for _, item in sorted(
                        zip(scores, results), key=lambda pair: pair[0], reverse=True
                    )]
                except Exception as exc:
                    errors.append(f"Jev search ranking failed: {type(exc).__name__}: {exc}")
            page_attempted = False
            for item in results:
                record = normalize_result(
                    item, query, provider=getattr(self.retriever, "provider", "custom")
                )
                if record is None or (record.url, record.content_hash) in seen:
                    continue
                if (
                    state["policy"].get("full_page_retrieval")
                    and not page_attempted
                    and budget.scrapes < budget.max_scrapes
                ):
                    page_attempted = True
                    budget.scrapes += 1
                    fetch = getattr(self.retriever, "fetch", fetch_page)
                    try:
                        text, status, error = fetch(
                            record.url,
                            timeout=min(
                                state["policy"].get("page_fetch_timeout_seconds", 30),
                                max(0.001, budget.max_seconds - _elapsed({**state, "budgets": budget})),
                            ),
                            max_bytes=state["policy"].get("page_max_bytes", 1_000_000),
                            require_https=state["policy"].get("require_https", False),
                        )
                    except Exception as exc:
                        text, status, error = "", None, f"{type(exc).__name__}: {exc}"
                    if text:
                        record.page_text = text[: state["policy"].get("page_text_limit", 20_000)]
                        record.retrieval_kind = "full_page"
                        record.status_code = status
                        record.content_hash = hashlib.sha256(text.encode()).hexdigest()
                    elif error:
                        errors.append(f"Page fetch failed for {record.url}: {error}")
                new_records.append(record)
                seen.add((record.url, record.content_hash))
        all_sources = annotate_duplicate_lineage([*existing, *new_records])
        if self.jev and _remaining(state, budget) > 1 and budget.tokens_used < budget.max_tokens:
            pending = [record for record in all_sources if not record.jev_scores]
            pending = pending[: self.config["jev"].get("max_source_reviews_per_round", 12)]
            if pending:
                try:
                    reviews, tokens = self.jev.review_sources(
                        state["claim"], pending, timeout=min(12.0, _remaining(state, budget))
                    )
                    if len(reviews) != len(pending):
                        raise ValueError("Jev returned incomplete source reviews")
                    budget = _add_tokens(budget, tokens)
                    for record, review in zip(pending, reviews):
                        record.jev_scores = review
                except Exception as exc:
                    errors.append(f"Jev source review failed: {type(exc).__name__}: {exc}")
        jev_audit["search_ranking"] = search_ranking
        stagnant = state.get("stagnant_rounds", 0) + 1 if not new_records else 0
        return {
            "sources": all_sources,
            "jev_audit": jev_audit,
            "search_queries": [*state.get("search_queries", []), *queries],
            "budgets": budget,
            "last_new_sources": len(new_records),
            "stagnant_rounds": stagnant,
            "research_round": state.get("research_round", 0) + 1,
            "errors": errors,
            "fatal_error": bool(errors and not all_sources),
            "budget_blocked": deadline_reached,
        }

    def analyze(self, state: ClaimState) -> dict[str, Any]:
        if state.get("budget_blocked"):
            return {"assessment": state.get("assessment", EvidenceAssessment())}
        if state.get("errors") and not state.get("sources"):
            assessment = EvidenceAssessment(gaps=["Research execution failed before evidence could be analyzed."])
            return {"assessment": assessment, "fatal_error": True}
        try:
            sources = self.usable_sources(state)
            assessment, tokens = self.model.analyze(
                state["claim"], state["domain"], state["assertions"], sources,
                state.get("gaps", []), state["reference_date"],
                self.config.get("domain_guidance", {}).get(state["domain"], {}),
            )
            return {"assessment": assessment, "budgets": _record_tokens(state, tokens)}
        except Exception as exc:
            errors = [*state.get("errors", []), f"Analysis failed: {type(exc).__name__}: {exc}"]
            return {
                "assessment": EvidenceAssessment(gaps=["The model did not return a valid evidence assessment."]),
                "errors": errors,
                "fatal_error": True,
                "budgets": _record_tokens(state, None),
            }

    def check_evidence(self, state: ClaimState) -> dict[str, Any]:
        assessment = state["assessment"]
        gaps = evidence_gaps(assessment, state["assertions"], self.usable_sources(state), state["policy"])
        budget = state["budgets"].model_copy(deep=True)
        errors = list(state.get("errors", []))
        semantic_gaps: list[str] = []
        fatal_error = state.get("fatal_error", False)
        jev_audit = dict(state.get("jev_audit", {}))
        citation_audit = list(jev_audit.get("citations", []))
        if self.jev and assessment.evidence:
            sources = {source.url: source for source in self.usable_sources(state)}
            candidates = []
            for item in assessment.evidence:
                for url in item.source_urls:
                    source = sources.get(url)
                    quote = item.quotes.get(url, "")
                    if not source or not quote or quote not in source.retrieved_text:
                        continue  # The deterministic gate reports missing or altered quotes.
                    offset = source.retrieved_text.index(quote)
                    context = source.retrieved_text[max(0, offset - 1200): offset + len(quote) + 1200]
                    candidates.append({
                        "finding": item.finding,
                        "url": url,
                        "quote": quote,
                        "context": context,
                        "key": _citation_key(item.finding, url, quote, source.content_hash),
                    })
            batch_size = max(1, int(self.config["jev"].get("citation_batch_size", 6)))
            for start in range(0, len(candidates), batch_size):
                batch = candidates[start:start + batch_size]
                if _remaining(state, budget) <= 1 or budget.tokens_used >= budget.max_tokens:
                    semantic_gaps.append("Jev could not check every citation within the resource budget.")
                    break
                try:
                    reviews, tokens = self.jev.check_citations(
                        batch, timeout=min(12.0, _remaining(state, budget))
                    )
                    if len(reviews) != len(batch):
                        raise ValueError("Jev returned incomplete citation checks")
                    budget = _add_tokens(budget, tokens)
                except Exception as exc:
                    errors.append(f"Jev citation check failed: {type(exc).__name__}: {exc}")
                    semantic_gaps.append("Citation support could not be checked by Jev.")
                    fatal_error = True
                    break
                for candidate, review in zip(batch, reviews):
                    citation_audit.append({
                        "round": state.get("research_round", 0),
                        "finding": candidate["finding"],
                        "url": candidate["url"],
                        "key": candidate["key"],
                        **review,
                    })
        jev_audit["citations"] = citation_audit
        semantic_gaps.extend(self.citation_review_gaps({**state, "jev_audit": jev_audit}))
        gaps = list(dict.fromkeys([*gaps, *semantic_gaps]))
        history = list(state.get("research_history", []))
        if state.get("research_round", 0) > 0:
            history.append(
                ResearchRound(
                    round_number=state["research_round"],
                    queries=state.get("search_queries", [])[-state["policy"].get("search_calls_per_round", 2) :],
                    new_sources=state.get("last_new_sources", 0),
                    proposed_verdict=assessment.proposed_verdict,
                    confidence=assessment.confidence,
                    gaps=gaps,
                )
            )
        return {
            "gaps": gaps, "semantic_gaps": semantic_gaps,
            "contradictions": assessment.contradictions, "research_history": history,
            "budgets": budget, "errors": errors, "fatal_error": fatal_error,
            "jev_audit": jev_audit,
        }

    def route_research(self, state: ClaimState) -> dict[str, Any]:
        if not state.get("gaps"):
            stop_reason, route = "evidence_sufficient", "finalize"
        elif state.get("fatal_error"):
            stop_reason, route = "execution_error", "finalize"
        elif state.get("stagnant_rounds", 0) >= state["policy"].get("max_stagnant_rounds", 2):
            stop_reason, route = "stagnant_research", "finalize"
        elif reason := _budget_reason(state):
            stop_reason, route = reason, "finalize"
        else:
            stop_reason, route = "", "research"
        history = list(state["research_history"])
        if history:
            history[-1] = history[-1].model_copy(update={"decision": stop_reason or "research_more"})
        return {"stop_reason": stop_reason, "route": route, "research_history": history}

    def finalize(self, state: ClaimState) -> dict[str, Any]:
        assessment = state.get("assessment", EvidenceAssessment())
        gaps = list(state.get("gaps", []))
        stop_reason = state.get("stop_reason") or "validation_error"
        history = list(state.get("research_history", []))
        if stop_reason == "evidence_sufficient":
            gaps = [*evidence_gaps(
                assessment,
                state.get("assertions", []),
                self.usable_sources(state),
                state.get("policy", {}),
            ), *state.get("semantic_gaps", []), *self.citation_review_gaps(state)]
            gaps = list(dict.fromkeys(gaps))
            if gaps:
                stop_reason = "final_gate_rejected"
                if history:
                    history[-1] = history[-1].model_copy(
                        update={"gaps": gaps, "decision": stop_reason}
                    )
        accepted = stop_reason == "evidence_sufficient" and not gaps
        evidence = retained_evidence(assessment, self.usable_sources(state))
        verdict = assessment.proposed_verdict if accepted else "UNVERIFIED"
        confidence = assessment.confidence if accepted else "Low"
        if accepted:
            summary = assessment.summary
        else:
            detail = " ".join(gaps)
            summary = "The evidence did not meet the verification criteria."
            if detail:
                summary += f" {detail}"
        cited = {url for item in evidence for url in item.source_urls}
        result = FinalResult(
            claim=state.get("claim", ""),
            domain=state.get("domain", state.get("requested_domain", "auto")),
            verdict=verdict,
            confidence=confidence,
            summary=summary,
            stop_reason=stop_reason,
            reference_date=state.get("reference_date", ""),
            reference_timezone=state.get("reference_timezone", ""),
            execution_id=state.get("execution_id", ""),
            elapsed_seconds=_elapsed(state),
            evidence=evidence,
            sources=[source for source in state.get("sources", []) if source.url in cited],
            retrieval_ledger=state.get("sources", []),
            assertions=state.get("assertions", []),
            gaps=gaps,
            contradictions=assessment.contradictions,
            search_queries=state.get("search_queries", []),
            research_history=history,
            budget=state["budgets"],
            errors=state.get("errors", []),
            jev_audit=state.get("jev_audit", {}),
        )
        return {"verdict": verdict, "result": result, "report": format_report(result)}


def _after_validation(state: ClaimState) -> Literal["classify", "finalize"]:
    return "finalize" if state.get("stop_reason") else "classify"


def _after_routing(state: ClaimState) -> Literal["retrieve", "finalize"]:
    return "retrieve" if state.get("route") == "research" else "finalize"


def build_graph(
    *,
    model: ModelBackend | None = None,
    retriever: Retriever | None = None,
    jev: JevClient | None = None,
    config: dict[str, Any] | None = None,
):
    config = config or load_config()
    model_cfg = config["model"]
    backend = model or OllamaBackend(
        model=model_cfg["name"],
        base_url=model_cfg["base_url"],
        temperature=model_cfg.get("temperature", 0.0),
    )
    jev_cfg = config.get("jev", {})
    jev_backend = jev
    if jev_backend is None and jev_cfg.get("enabled", True) and os.getenv("TYPESAFE_API_KEY"):
        jev_backend = JevClient(model=jev_cfg.get("model", "jev-1.13.0"))
    nodes = WorkflowNodes(backend, retriever or TinyFishRetriever(), config, jev_backend)
    builder = StateGraph(ClaimState)
    builder.add_node("validate", nodes.validate)
    builder.add_node("classify", nodes.classify)
    builder.add_node("decompose", nodes.decompose)
    builder.add_node("retrieve", nodes.retrieve)
    builder.add_node("analyze", nodes.analyze)
    builder.add_node("check_evidence", nodes.check_evidence)
    builder.add_node("route_research", nodes.route_research)
    builder.add_node("finalize", nodes.finalize)
    builder.add_edge(START, "validate")
    builder.add_conditional_edges("validate", _after_validation)
    builder.add_edge("classify", "decompose")
    builder.add_edge("decompose", "retrieve")
    builder.add_edge("retrieve", "analyze")
    builder.add_edge("analyze", "check_evidence")
    builder.add_edge("check_evidence", "route_research")
    builder.add_conditional_edges("route_research", _after_routing)
    builder.add_edge("finalize", END)
    return builder.compile()


def run_claim(
    claim: str,
    *,
    domain: str = "auto",
    max_rounds: int = 3,
    model: ModelBackend | None = None,
    retriever: Retriever | None = None,
    jev: JevClient | None = None,
    config: dict[str, Any] | None = None,
) -> FinalResult:
    config = config or load_config()
    default_policy = config["policy"]
    initial = ClaimState(
        claim=claim,
        requested_domain=domain,
        budgets=BudgetState(
            max_rounds=max_rounds,
            max_search_calls=default_policy["max_search_calls"],
            max_scrapes=default_policy["max_scrapes"],
            max_tokens=default_policy["max_token_limit"],
            max_seconds=default_policy["max_execution_time_seconds"],
            started_at_monotonic=time.monotonic(),
        ),
    )
    state = build_graph(model=model, retriever=retriever, jev=jev, config=config).invoke(
        initial,
        config={"recursion_limit": max(25, max_rounds * 8 + 10)},
    )
    return state["result"]

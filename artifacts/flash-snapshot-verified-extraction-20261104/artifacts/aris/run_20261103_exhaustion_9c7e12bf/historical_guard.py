"""Stratify the preserved replay by known current-policy blockers.

Use the completed audit's exact selection and outcome data. Missing prior
source-review state makes the remaining rows a possible-eligibility envelope.
"""

import csv
import json
from pathlib import Path

from kaji_langgraph.graph import _unused_queries
from kaji_langgraph.models import EvidenceAssessment


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
REPLAY = ROOT / "evaluation/aris/20261102_120247/stopping-replay.csv"
STUDY = ROOT / "evaluation/results/study-20261009-v3/full/results.jsonl"


def known_blockers(result):
    prior = result["research_history"][1]
    budget = prior["budget"]
    queries = [query for step in result["research_history"][:2] for query in step["queries"]]
    state = {"claim": result["claim"], "assertions": result["assertions"], "search_queries": queries,
             "assessment": EvidenceAssessment.model_validate(prior["assessment"])}
    checks = {
        "evidence_sufficient": not prior["gaps"],
        "fatal_error": prior["fatal_error"],
        "semantic_gaps": bool(prior["semantic_gaps"]),
        "unused_query": bool(_unused_queries(state)),
        "max_rounds": budget["max_rounds"] <= 2,
        "search_budget": budget["search_calls"] >= budget["max_search_calls"],
        "token_budget": budget["tokens_used"] >= budget["max_tokens"],
        "time_budget": prior["elapsed_seconds"] >= budget["max_seconds"],
    }
    return [name for name, blocked in checks.items() if blocked]


def summarize(rows):
    return {
        "n": len(rows),
        "gains_from_reassessment": sum(r["before"] != r["gold"] == r["after"] for r in rows),
        "losses_from_reassessment": sum(r["before"] == r["gold"] != r["after"] for r in rows),
        "new_acceptances": sum(r["accepted_before"] == "ABSTAIN" != r["accepted_after"] for r in rows),
        "new_correct_acceptances": sum(
            r["accepted_before"] == "ABSTAIN" and r["accepted_after"] == r["gold"] for r in rows
        ),
        "execution_errors": sum(r["fatal_final"] == "True" for r in rows),
        "observed_token_delta": sum(int(r["observed_token_delta"]) for r in rows),
    }


def main():
    with REPLAY.open(encoding="utf-8", newline="") as file:
        selected = {row["claim_id"]: row for row in csv.DictReader(file)}
    rows = []
    with STUDY.open(encoding="utf-8") as file:
        for line in file:
            saved = json.loads(line)
            if str(saved["claim_id"]) in selected:
                row = selected[str(saved["claim_id"])]
                rows.append({**row, "known_blockers": known_blockers(saved["result"])})
    assert len(rows) == len(selected) == len({row["claim_id"] for row in rows})
    report = {
        "scope": "Exploratory eligibility screen of existing no-search replay, no new inference",
        "total": summarize(rows),
        "known_blocker": summarize([r for r in rows if r["known_blockers"]]),
        "semantic_blocker": summarize([r for r in rows if "semantic_gaps" in r["known_blockers"]]),
        "no_recorded_blocker": summarize([r for r in rows if not r["known_blockers"]]),
        "limitations": [
            "Round-two pending source review is unavailable; no-recorded-blocker rows are only possibly eligible.",
            "Search inventory is reconstructed from trace queries and current query builder.",
            "Runtime outcomes, stopping incidence, and savings under deployment cannot be inferred from this screen.",
        ],
        "rows": rows,
    }
    with (WORK / "historical-guard.json").open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()

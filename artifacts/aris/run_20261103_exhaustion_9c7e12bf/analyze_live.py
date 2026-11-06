"""Reconcile paired results and the durable transport records for a live batch."""

import argparse
import json
from math import comb
from pathlib import Path

from challenge import MODELS, RUN, save


def read(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def reference_interval(k, n):
    """Two-sided exact binomial reference interval for a fixed sample of size n."""
    if not n:
        return None

    def endpoint(successes):
        low, high = 0.0, 1.0
        for _ in range(55):
            mid = (low + high) / 2
            tail = sum(comb(n, i) * mid ** i * (1 - mid) ** (n - i) for i in range(successes, n + 1))
            if tail < 0.025:
                low = mid
            else:
                high = mid
        return (low + high) / 2

    return [endpoint(k) if k else 0, 1 - endpoint(n - k) if k < n else 1]


def account(cell, tag):
    records = []
    exit_usage = read(cell / "usage.json", [])
    for request in sorted(cell.glob("request-*.json")):
        index = int(request.stem.split("-")[-1])
        row = dict(exit_usage[index - 1]) if index <= len(exit_usage) else {}
        response = cell / f"response-{index}.body"
        if response.exists():
            try:
                terminal = json.loads(response.read_bytes().splitlines()[-1])
                row.update({key: terminal.get(key) for key in
                            ("done", "model", "prompt_eval_count", "eval_count")})
            except (ValueError, IndexError):
                row["body_unparseable"] = True
        row["response_recorded"] = response.exists()
        row["requested_model"] = read(request)["model"]
        row["exact_model_confirmed"] = row["requested_model"] == tag and row.get("model") in {tag, MODELS[tag]}
        row["disposition"] = ("completed" if row.get("done") and row["exact_model_confirmed"] else
                              "http_error" if row.get("status", 0) >= 400 else "unknown")
        records.append(row)
    return records


def summarize(rows):
    verified = [r for r in rows if r["status"] == "complete"]
    accepted_losses = [r for r in verified if r["metrics"]["potential_correct_acceptance_loss"]]
    audited = all(r.get("acceptance_loss_verified") is not None for r in accepted_losses)
    eligible = [r for r in verified if r["metrics"]["candidate_stop"] == "query_exhausted"]
    losses = sum(r.get("acceptance_loss_verified") is True for r in eligible)
    sends = [request for r in rows for request in r["transport"]]
    counted = [r for r in sends if isinstance(r.get("prompt_eval_count"), int)
               and isinstance(r.get("eval_count"), int)]
    return {
        "planned": len(rows),
        "complete": len(verified),
        "failed_or_incomplete": sum(r["status"] == "failed_or_incomplete" for r in rows),
        "not_attempted": sum(r["status"] == "not_attempted" for r in rows),
        "early_stops": len(eligible),
        "correct_proposals_baseline": sum(r["metrics"]["baseline_prediction"] == r["metrics"]["gold"] for r in verified),
        "correct_proposals_candidate": sum(r["metrics"]["candidate_prediction"] == r["metrics"]["gold"] for r in verified),
        "accepted_baseline": sum(r["metrics"]["baseline_accepted"] != "UNVERIFIED" for r in verified),
        "accepted_candidate": sum(r["metrics"]["candidate_accepted"] != "UNVERIFIED" for r in verified),
        "potential_correct_acceptance_losses": len(accepted_losses),
        "verified_correct_acceptance_losses": losses,
        "adjudication_complete_for_losses": audited,
        "reference_interval_for_eligible_loss": reference_interval(losses, len(eligible)) if audited else None,
        "durable_reservations": len(sends),
        "completed_responses": sum(r["disposition"] == "completed" for r in sends),
        "unknown_dispositions": sum(r["disposition"] == "unknown" for r in sends),
        "responses_with_token_usage": len(counted),
        "input_tokens": sum(r["prompt_eval_count"] for r in counted),
        "output_tokens": sum(r["eval_count"] for r in counted),
        "skipped_policy_sends_in_complete_pairs": sum(len(r["transport"]) for r in eligible),
        "skipped_policy_tokens_in_complete_pairs": sum(
            send["prompt_eval_count"] + send["eval_count"] for r in eligible for send in r["transport"]
            if send in counted
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("batches", nargs="+", choices=["batch1", "batch2"])
    opts = parser.parse_args()
    rows = []
    for batch in opts.batches:
        directory = RUN / batch
        adjudication = read(directory / "adjudication.json", {})
        for entry in read(directory / "schedule.json"):
            tag = entry["model"]
            cell = directory / f"{entry['case']}-{tag.replace(':', '_')}"
            metrics = read(cell / "metrics.json")
            transport = account(cell, tag)
            if metrics and metrics["trace_pass"] and not metrics["errors"]:
                status = "complete"
            else:
                status = "failed_or_incomplete" if cell.exists() else "not_attempted"
            rows.append({**entry, "batch": batch, "metrics": metrics, "transport": transport, "status": status,
                         "acceptance_loss_verified": adjudication.get(cell.name, {}).get("loss_verified")})
    report = {"overall_usage_and_counts": summarize(rows),
              "by_model": {tag: summarize([r for r in rows if r["model"] == tag]) for tag in MODELS},
              "reference_interval_note": "Fixed-n binomial reference only. Designed cases and sequential selection preclude population coverage interpretation.",
              "rows": rows}
    save(opts.output, report)
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()

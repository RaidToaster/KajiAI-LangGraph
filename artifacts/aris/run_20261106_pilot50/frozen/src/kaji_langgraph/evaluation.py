"""Reproducible AVeriTeC label evaluation; never substitutes for its official evidence scorer."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import sys

from kaji_langgraph.config import load_config
from kaji_langgraph.graph import run_claim

LABELS = ("Supported", "Refuted", "Not Enough Evidence", "Conflicting Evidence/Cherrypicking")
LABEL_MAP = dict(zip(("TRUE", "FALSE", "NOT_ENOUGH_EVIDENCE", "CONFLICTING"), LABELS))
ABSTAIN = "ABSTAIN"


def load_dataset(path: Path) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Dataset must be a nonempty JSON array")
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("claim"), str) or not row["claim"].strip():
            raise ValueError(f"Invalid claim at index {index}")
        if row.get("label") not in LABELS:
            raise ValueError(f"Unknown AVeriTeC label at index {index}")
    return rows


def prediction_label(verdict: str) -> str:
    # Generic misleading framing is not necessarily conflicting evidence/cherry-picking.
    # Operational failure and gate rejection are not the factual NEI class.
    return LABEL_MAP.get(verdict, ABSTAIN)


def classification_metrics(gold: list[str], predicted: list[str]) -> dict:
    if len(gold) != len(predicted):
        raise ValueError("Predictions and references must have equal length")
    if any(label not in LABELS for label in gold) or any(label not in (*LABELS, ABSTAIN) for label in predicted):
        raise ValueError("Unknown evaluation label")
    matrix = {label: dict.fromkeys((*LABELS, ABSTAIN), 0) for label in LABELS}
    for actual, prediction in zip(gold, predicted):
        matrix[actual][prediction] += 1
    per_class = {}
    for label in LABELS:
        tp = matrix[label][label]
        support = sum(matrix[label].values())
        calls = sum(matrix[other][label] for other in LABELS)
        precision = tp / calls if calls else 0.0
        recall = tp / support if support else 0.0
        per_class[label] = {"precision": precision, "recall": recall,
                            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                            "support": support}
    correct = sum(a == b for a, b in zip(gold, predicted))
    covered = sum(label != ABSTAIN for label in predicted)
    return {"n": len(gold), "accuracy": correct / len(gold) if gold else 0.0,
            "macro_f1": sum(item["f1"] for item in per_class.values()) / len(LABELS),
            "coverage": covered / len(gold) if gold else 0.0,
            "selective_accuracy": correct / covered if covered else None,
            "per_class": per_class, "confusion_matrix": matrix}


def summarize(rows: list[dict]) -> dict:
    gold = [row["gold_label"] for row in rows]
    raw = classification_metrics(gold, [row["predicted_label"] for row in rows])
    accepted = classification_metrics(gold, [row["accepted_label"] for row in rows])
    failure_inclusive = classification_metrics(gold, [
        ABSTAIN if row["result"]["verification_status"] == "execution_error" else row["predicted_label"]
        for row in rows])
    results = [row["result"] for row in rows]
    n = len(rows)
    return {
        "metric_scope": "Local label-only metrics, NOT the official AVeriTeC evidence score",
        "predictions": raw, "failure_inclusive_predictions": failure_inclusive, "verified": accepted,
        "execution_error_rate": sum(r["verification_status"] == "execution_error" for r in results) / n if n else 0,
        "stop_reasons": dict(Counter(r["stop_reason"] for r in results)),
        "verification_statuses": dict(Counter(r["verification_status"] for r in results)),
        "gap_counts": dict(Counter(gap for r in results for gap in set(r["gaps"]))),
        "mean_elapsed_seconds": statistics.mean(r["elapsed_seconds"] for r in results) if n else 0,
        "total_searches": sum(r["budget"]["search_calls"] for r in results),
        "total_page_fetches": sum(r["budget"]["scrapes"] for r in results),
        "total_observed_tokens": sum(r["budget"]["tokens_used"] for r in results),
        "token_usage_complete": all(r["budget"]["token_usage_complete"] for r in results),
    }


def write_reports(output: Path, rows: list[dict], planned: int) -> dict:
    metrics = summarize(rows)
    metrics["planned_claims"] = planned
    metrics["completed_claims"] = len(rows)
    metrics["complete"] = len(rows) == planned
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    with (output / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["claim_id", "gold_label", "predicted_label", "accepted_label", "verification_status", "stop_reason", "seconds"])
        for row in rows:
            r = row["result"]
            writer.writerow([row["claim_id"], row["gold_label"], row["predicted_label"], row["accepted_label"],
                             r["verification_status"], r["stop_reason"], r["elapsed_seconds"]])
    lines = ["# KajiAI AVeriTeC evaluation", "", f"Completed {len(rows)} of {planned} selected claims.", "",
             metrics["metric_scope"] + ".", "",
             "| Output | Accuracy | Macro F1 (4 classes) | Coverage | Accuracy on covered claims |",
             "|---|---:|---:|---:|---:|"]
    for name in ("predictions", "failure_inclusive_predictions", "verified"):
        m = metrics[name]
        selective = "N/A" if m["selective_accuracy"] is None else f"{m['selective_accuracy']:.3f}"
        lines.append(f"| {name} | {m['accuracy']:.3f} | {m['macro_f1']:.3f} | {m['coverage']:.3f} | {selective} |")
    lines.extend(["", "Abstentions count as incorrect in overall accuracy. Raw predictions preserve an available model "
                  "assessment even if a later service fails; failure-inclusive predictions count execution failures as abstentions. "
                  "Selective accuracy excludes abstentions and must be reported alongside coverage. "
                  "Missing selected claims are not yet scored; partial runs are not full benchmark results.", "",
                  "## Prediction performance by class", "",
                  "| Class | Precision | Recall | F1 | Support |", "|---|---:|---:|---:|---:|"])
    for label, m in metrics["predictions"]["per_class"].items():
        lines.append(f"| {label} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | {m['support']} |")
    lines.extend(["", "## Execution", "", f"- Error rate: {metrics['execution_error_rate']:.3f}",
                  f"- Mean elapsed seconds: {metrics['mean_elapsed_seconds']:.1f}",
                  f"- Searches / page fetches: {metrics['total_searches']} / {metrics['total_page_fetches']}",
                  f"- Observed tokens: {metrics['total_observed_tokens']}",
                  f"- Complete token accounting: {metrics['token_usage_complete']}", "", "## Stop reasons", ""])
    lines.extend(f"- {reason}: {count}" for reason, count in metrics["stop_reasons"].items())
    lines.extend(["", "## Most frequent verification gaps", ""])
    lines.extend(f"- {gap}: {count}" for gap, count in Counter(metrics["gap_counts"]).most_common(15))
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics


def dataset_report(dataset: list[dict]) -> dict:
    gold = [row["label"] for row in dataset]
    counts = Counter(gold)
    majority = counts.most_common(1)[0][0]
    return {"claims": len(dataset), "label_counts": dict(counts),
            "majority_label": majority,
            "majority_baseline": classification_metrics(gold, [majority] * len(gold)),
            "note": "Majority selected on this split: descriptive class-imbalance baseline, not trained model performance."}


def model_input(row: dict) -> dict:
    """Explicit allowlist: gold labels, justifications, QA and fact-check URLs never reach inference."""
    date = row.get("claim_date")
    return {"claim": row["claim"],
            "reference_date": datetime.strptime(date, "%d-%m-%Y").date().isoformat() if date else None}


def code_digest() -> str:
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def read_completed(path: Path, dataset: list[dict], ids: list[int]) -> list[dict]:
    if not path.exists():
        return []
    # JSONL records end at LF/CRLF, not at Unicode separators inside source text.
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    seen = set()
    for row in rows:
        index = row["claim_id"]
        if index not in ids or index in seen or row["gold_label"] != dataset[index]["label"]:
            raise ValueError("Results have duplicate, mismatched, or unexpected claim IDs")
        if row["result"]["claim"] != dataset[index]["claim"]:
            raise ValueError("Result claim does not match dataset")
        if row["predicted_label"] != prediction_label(row["result"]["predicted_verdict"]):
            raise ValueError("Saved prediction does not match result")
        if row["accepted_label"] != prediction_label(row["result"]["verdict"]):
            raise ValueError("Saved accepted verdict does not match result")
        seen.add(index)
    return rows


def run_evaluation(args, dataset: list[dict]) -> None:
    config = deepcopy(load_config(args.config))
    config["model"]["verdict_mode"] = "averitec"
    config["policy"]["max_execution_time_seconds"] = args.max_seconds
    if args.no_jev:
        config["jev"]["enabled"] = False
    if args.snippets_only:
        config["policy"]["full_page_retrieval"] = False
    if args.ids:
        ids = [int(value) for value in args.ids.split(",")]
    else:
        ids = list(range(len(dataset)))
        random.Random(args.seed).shuffle(ids)
        ids = ids[:args.limit]
    if not ids or len(set(ids)) != len(ids) or any(i < 0 or i >= len(dataset) for i in ids):
        raise ValueError("Select unique, valid claim IDs")
    # Validate every input before starting a potentially long paid run.
    inputs = {index: model_input(dataset[index]) for index in ids}
    manifest = {"schema_version": 1, "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                "code_sha256": code_digest(), "claim_ids": ids, "seed": args.seed,
                "max_rounds": args.max_rounds, "config": config,
                "jev_active": bool(config.get("jev", {}).get("enabled") and os.getenv("TYPESAFE_API_KEY")),
                "mode": "live_web", "reference_date_policy": "claim_date; runtime date if missing",
                "temporal_cutoff_enforced": False, "gold_evidence_used": False}
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    results_path = output / "results.jsonl"
    if manifest_path.exists():
        if not args.resume:
            raise ValueError("Output already has a run; choose a new directory or use --resume")
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        comparable = {k: v for k, v in saved.items() if k != "created_at"}
        if comparable != manifest:
            raise ValueError("Resume requires identical dataset, code, IDs, options, and active Jev setting")
    else:
        if results_path.exists():
            raise ValueError("Results exist without a manifest; choose a new output directory")
        manifest["created_at"] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    rows = read_completed(results_path, dataset, ids)
    done = {row["claim_id"] for row in rows}
    write_reports(output, rows, len(ids))
    for index in ids:
        if index in done:
            continue
        print(f"Claim {index} ({len(rows) + 1}/{len(ids)})", file=sys.stderr, flush=True)
        result = run_claim(**inputs[index], config=config, max_rounds=args.max_rounds,
                           progress=lambda message: print(message, file=sys.stderr, flush=True))
        row = {"claim_id": index, "gold_label": dataset[index]["label"],
               "predicted_label": prediction_label(result.predicted_verdict),
               "accepted_label": prediction_label(result.verdict), "result": result.model_dump()}
        with results_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
        rows.append(row)
        write_reports(output, rows, len(ids))
        print(f"Prediction={row['predicted_label']}; verification={result.verification_status}", file=sys.stderr)
        if result.verification_status == "execution_error" and not args.continue_on_error:
            print("Stopped after execution failure. Fix the service and use a new output directory for a clean rerun. "
                  "Completed failures remain in this run's denominator.", file=sys.stderr)
            raise SystemExit(1)
    print(output / "report.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect = subparsers.add_parser("inspect", help="Offline dataset audit and majority baseline")
    inspect.add_argument("--dataset", type=Path, default=Path("evaluation/data/averitec_dev.json"))
    inspect.add_argument("--output", type=Path)
    run = subparsers.add_parser("run", help="Run live inference without exposing gold annotations")
    run.add_argument("--dataset", type=Path, default=Path("evaluation/data/averitec_dev.json"))
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--config", type=Path)
    run.add_argument("--limit", type=int, default=10)
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--ids", help="Explicit comma-separated zero-based dataset row IDs (overrides limit)")
    run.add_argument("--max-rounds", type=int, default=3, choices=range(1, 11))
    run.add_argument("--max-seconds", type=float, default=300)
    run.add_argument("--no-jev", action="store_true")
    run.add_argument("--snippets-only", action="store_true")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()
    try:
        dataset = load_dataset(args.dataset)
        if args.command == "inspect":
            report = json.dumps(dataset_report(dataset), indent=2)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(report + "\n", encoding="utf-8")
            print(report)
        else:
            if args.limit < 1 or args.max_seconds <= 0:
                raise ValueError("limit and max-seconds must be positive")
            run_evaluation(args, dataset)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Evaluation error: {exc}\n")


if __name__ == "__main__":
    main()

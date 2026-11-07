"""Frozen, resumable study: live verification and a model-only control.

Labels enter scoring only. Intermediate traces enable offline, fixed-evidence
acceptance-policy comparisons; those are not independent ungated pipelines.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import random
import time
from typing import Literal
import zipfile

from pydantic import BaseModel

from kaji_langgraph.config import load_config
from kaji_langgraph.evaluation import code_digest, load_dataset, model_input, prediction_label, write_reports
from kaji_langgraph.graph import run_claim
from kaji_langgraph.llm import OllamaBackend
from kaji_langgraph.models import BudgetState, FinalResult


class ClosedBookAssessment(BaseModel):
    proposed_verdict: Literal["TRUE", "FALSE", "CONFLICTING", "NOT_ENOUGH_EVIDENCE"]
    confidence: Literal["Low", "Medium", "High"]
    summary: str


def closed_book_prompt(claim: str, reference_date: str | None) -> str:
    """Shared verbatim control prompt for opt-in incremental experiments."""
    return f"""Assess the factual claim using your existing knowledge only.
Claim: {claim}
Claim reference date: {reference_date or 'not supplied'}
Use TRUE for supported claims, FALSE for refuted claims, CONFLICTING for genuine
conflicting evidence/cherry-picking, and NOT_ENOUGH_EVIDENCE when you cannot
resolve the claim. Missing knowledge is not FALSE. Give your best assessment
and honest Low, Medium, or High confidence. Do not invent citations."""


def closed_book(claim: str, reference_date: str | None, config: dict) -> FinalResult:
    """Same model and JSON adapter; no retrieval, domain routing, or acceptance."""
    started = time.monotonic()
    cfg = config["model"]
    backend = OllamaBackend(model=cfg["name"], base_url=cfg["base_url"],
                            temperature=cfg.get("temperature", 0), verdict_mode="averitec")
    budget = BudgetState(max_rounds=1, max_search_calls=0, max_scrapes=0,
                         max_seconds=config["policy"]["max_execution_time_seconds"])
    try:
        assessment, tokens = backend._structured(ClosedBookAssessment, closed_book_prompt(claim, reference_date))
        budget.tokens_used = tokens or 0
        budget.token_usage_complete = tokens is not None
        return FinalResult(claim=claim, domain="not_classified", budget=budget,
                           predicted_verdict=assessment.proposed_verdict,
                           prediction_confidence=assessment.confidence,
                           prediction_summary=assessment.summary,
                           reference_date=reference_date or "", stop_reason="model_only_control",
                           elapsed_seconds=time.monotonic() - started)
    except Exception as exc:
        budget.token_usage_complete = False
        return FinalResult(claim=claim, domain="not_classified", budget=budget,
                           verification_status="execution_error", stop_reason="execution_error",
                           errors=[f"Model-only analysis failed: {type(exc).__name__}: {exc}"],
                           elapsed_seconds=time.monotonic() - started)


def execute(condition: str, index: int, row: dict, config: dict, output: Path,
            max_rounds: int) -> dict:
    inputs = model_input(row)
    started = time.monotonic()
    try:
        if condition == "closed_book":
            result = closed_book(**inputs, config=config)
        else:
            log_path = output / "logs" / f"{condition}-{index}.log"
            with log_path.open("w", encoding="utf-8") as log:
                def progress(message):
                    log.write(f"{datetime.now(timezone.utc).isoformat()} {message}\n")
                    log.flush()
                result = run_claim(**inputs, config=config, max_rounds=max_rounds, progress=progress)
    except Exception as exc:
        # Unexpected adapter/graph failures must remain in the denominator too.
        result = FinalResult(claim=inputs["claim"], domain="auto",
                             budget=BudgetState(max_rounds=max_rounds, token_usage_complete=False),
                             verification_status="execution_error", stop_reason="execution_error",
                             errors=[f"Unhandled execution failure: {type(exc).__name__}: {exc}"],
                             elapsed_seconds=time.monotonic() - started)
    return {"claim_id": index, "gold_label": row["label"],
            "predicted_label": prediction_label(result.predicted_verdict),
            "accepted_label": prediction_label(result.verdict), "result": result.model_dump()}


def load_saved(path: Path, dataset: list[dict], ids: list[int]) -> list[dict]:
    from kaji_langgraph.evaluation import read_completed
    return read_completed(path, dataset, ids)


def run(args) -> None:
    dataset = load_dataset(args.dataset)
    config = deepcopy(load_config())
    config["model"]["verdict_mode"] = "averitec"
    config["policy"]["max_execution_time_seconds"] = args.max_seconds
    if not os.getenv("TINYFISH_API_KEY") or not os.getenv("TYPESAFE_API_KEY"):
        raise ValueError("This full-system protocol requires both retrieval and Jev credentials")
    ids = list(range(len(dataset)))
    random.Random(args.seed).shuffle(ids)
    ids = ids[:args.limit]
    for index in ids:
        model_input(dataset[index])  # Validate all dates before service calls.
    manifest = {"schema_version": 1, "code_sha256": code_digest(),
                "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
                "dataset_path": str(args.dataset.resolve()),
                "claim_ids": ids, "seed": args.seed, "config": config,
                "max_rounds": args.max_rounds, "workers": args.workers,
                "conditions": ["full", "closed_book"],
                "versions": {p: version(p) for p in ["langgraph", "langchain-ollama", "typesafe-sdk", "pydantic"]},
                "scope": "Development-set, contemporary open-web, label-only evaluation",
                "temporal_cutoff_enforced": False, "gold_evidence_used": False,
                "model_only_acceptance": "No evidence gate; score predictions only",
                "offline_comparisons": "First-round truncation and acceptance-policy replay on exact saved assessments",
                "live_drift": "Seed fixes task order; remote model and web responses may change",
                "development_pilot": "Separate earlier-code pilot; never merged into study results"}
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        if {k: v for k, v in saved.items() if k != "created_at"} != manifest:
            raise ValueError("Study resume requires identical code, data, selection, settings and versions")
        if not args.resume:
            raise ValueError("Existing study requires --resume")
    else:
        if any((output / c / "results.jsonl").exists() for c in manifest["conditions"]):
            raise ValueError("Results exist without study manifest")
        manifest["created_at"] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # Archive the evaluated split so later analysis cannot silently use new data.
        (output / "dataset-snapshot.json").write_bytes(args.dataset.read_bytes())
        with zipfile.ZipFile(output / "source-snapshot.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(Path("src").rglob("*")):
                if path.is_file() and path.suffix in {".py", ".yaml"}:
                    archive.write(path, path.as_posix())
            for name in ["pyproject.toml", "uv.lock"]:
                archive.write(name, name)
    (output / "logs").mkdir(exist_ok=True)
    rows = {}
    tasks = []
    for condition in manifest["conditions"]:
        folder = output / condition
        folder.mkdir(exist_ok=True)
        rows[condition] = load_saved(folder / "results.jsonl", dataset, ids)
        done = {row["claim_id"] for row in rows[condition]}
        tasks.extend((condition, index) for index in ids if index not in done)
        write_reports(folder, rows[condition], len(ids))
    random.Random(args.seed).shuffle(tasks)
    # Each worker owns one graph. Only this main thread writes shared artifacts.
    pending = iter(tasks)
    futures = {}
    halted = False
    error_streak = Counter()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        def submit_next():
            try:
                condition, index = next(pending)
            except StopIteration:
                return False
            future = executor.submit(execute, condition, index, dataset[index],
                                     config, output, args.max_rounds)
            futures[future] = (condition, index)
            print(f"START {condition} claim={index}", flush=True)
            return True
        for _ in range(args.workers):
            submit_next()
        while futures:
            done, _ = wait(futures, timeout=30, return_when=FIRST_COMPLETED)
            if not done:
                print(f"ACTIVE {len(futures)} tasks; completed={sum(map(len, rows.values()))}/{2*len(ids)}", flush=True)
                continue
            for future in done:
                condition, index = futures.pop(future)
                row = future.result()
                rows[condition].append(row)
                with (output / condition / "results.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()
                write_reports(output / condition, rows[condition], len(ids))
                result = row["result"]
                failed = result["verification_status"] == "execution_error"
                error_streak[condition] = error_streak[condition] + 1 if failed else 0
                print(f"DONE {condition} {len(rows[condition])}/{len(ids)} claim={index} "
                      f"prediction={row['predicted_label']} status={result['verification_status']} "
                      f"seconds={result['elapsed_seconds']:.1f}", flush=True)
                if error_streak[condition] >= 3 or code_digest() != manifest["code_sha256"]:
                    halted = True
                if not halted:
                    submit_next()
            status = {"complete": all(len(v) == len(ids) for v in rows.values()),
                      "completed": {k: len(v) for k, v in rows.items()},
                      "planned_per_condition": len(ids), "halted": halted,
                      "updated_at": datetime.now(timezone.utc).isoformat()}
            (output / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    if halted:
        raise RuntimeError("Study stopped after repeated execution errors or source changes; inspect logs before resuming")
    from kaji_langgraph.study_analysis import analyze
    analyze(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("evaluation/data/averitec_dev.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261009)
    parser.add_argument("--workers", type=int, default=3, choices=range(1, 5))
    parser.add_argument("--max-rounds", type=int, default=3, choices=range(1, 11))
    parser.add_argument("--max-seconds", type=float, default=300)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.limit < 1 or args.max_seconds <= 0:
        parser.error("limit and max-seconds must be positive")
    run(args)


if __name__ == "__main__":
    main()

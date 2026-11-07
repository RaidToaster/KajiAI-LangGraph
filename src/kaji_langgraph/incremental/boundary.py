"""Identity-only exposure audit and allowlisted, separately materialized inputs.

This module is the controller boundary. Inference imports method, not this module.
Scheduled historical final inputs are not attempts. Development files and every
started/reserved historical DeepSeek attempt are conservatively excluded.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path: Path, value):
    """Atomic and fsynced; never leave a partial committed JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def _claims(value):
    if isinstance(value, dict):
        if isinstance(value.get("claim"), str):
            yield value["claim"]
        for child in value.values():
            yield from _claims(child)
    elif isinstance(value, list):
        for child in value:
            yield from _claims(child)


def audit(root: Path, dataset: Path, own_run: Path | None = None):
    # Only hashes/identities leave this function. No label is accessed.
    data = read(dataset)
    lookup = defaultdict(set)
    for i, row in enumerate(data):
        lookup[hashlib.sha256(row["claim"].encode()).hexdigest()].add(i)
    exposure = defaultdict(set)
    records, unresolved = [], []

    def record(path, ids, reason):
        if ids:
            ids = set(ids)
            for i in list(ids):
                ids.update(lookup[hashlib.sha256(data[i]["claim"].encode()).hexdigest()])
            rel = str(path.relative_to(root)).replace("\\", "/")
            records.append({"path": rel, "sha256": sha(path), "ids": sorted(ids), "reason": reason})
            for i in ids:
                exposure[i].add(rel)

    # Historical restored studies and the earlier DeepSeek/pilot experiments.
    for base in (root / "evaluation/results", root / "artifacts/aris"):
        if not base.exists():
            continue
        for run in sorted(base.iterdir()):
            if not run.is_dir() or not any(s in run.name.lower() for s in ("deepseek", "pilot50")):
                continue
            if own_run and run.resolve() == own_run.resolve():
                continue
            for path in sorted((run / "attempts").glob("*/attempt.json")):
                value = read(path)
                i = value.get("claim_id")
                case = value.get("case", "")
                if type(i) is not int and re.fullmatch(r"dev-\d+", case):
                    i = int(case[4:])
                ids = {i} if type(i) is int and 0 <= i < len(data) else set()
                if not ids:
                    unresolved.append(str(path.relative_to(root)))
                record(path, ids, "reserved_or_started_DeepSeek_attempt")
            # Incremental workers use opaque IDs; only this controller mapping
            # connects a reserved attempt to the dataset identity for auditing.
            if (run / "split.json").exists():
                for phase in ("calibration", "selection", "final"):
                    mapping_path = run / f"{phase}-mapping.json"
                    if not mapping_path.exists():
                        continue
                    for opaque, i in read(mapping_path).items():
                        job = run / "attempts" / f"{phase}-{opaque}" / "job.json"
                        if job.exists():
                            record(job, {i}, "reserved_incremental_DeepSeek_attempt_via_opaque_mapping")

    # Development claims, including other-model diagnostics, are conservatively
    # excluded. Read small structured claim-bearing artifacts, never raw replies,
    # benchmark annotations, archived full datasets or unexecuted final schedules.
    names = {"protocol.json", "result.json", "case.json", "task.json", "job.json",
             "development-cases.json", "confirmation-cases.json", "train-slice.json",
             "inputs.json", "claims.json", "cases.json"}
    for base in (root / "artifacts", root / "evaluation/results"):
        if not base.exists():
            continue
        for directory, dirs, files in os.walk(base):
            folder = Path(directory)
            dirs[:] = sorted(d for d in dirs if d not in {
                "__pycache__", "frozen", "src", "node_modules", "tectonic-local-cache",
                "verified-47-cell-snapshot", "verified-80-cell-snapshot"}
                and not (own_run and (folder / d).resolve() == own_run.resolve()))
            # Restored study results are handled by identity, not read as development.
            if "deepseek-restored" in str(folder) or "study-20261009" in str(folder):
                dirs[:] = []
                continue
            # Versioned revisions may live inside another run. Their opaque
            # mappings must contribute reserved attempts to all FUTURE audits,
            # even when their result records intentionally omit claim text.
            nested_deepseek = (folder.parent != base and "split.json" in files
                and any("deepseek" in part.casefold() for part in folder.relative_to(root).parts))
            if nested_deepseek:
                for phase in ("calibration", "selection", "final"):
                    mapping_path = folder / f"{phase}-mapping.json"
                    if not mapping_path.exists():
                        continue
                    for opaque, i in read(mapping_path).items():
                        job = folder / "attempts" / f"{phase}-{opaque}" / "job.json"
                        if job.exists():
                            if type(i) is int and 0 <= i < len(data):
                                record(job, {i}, "nested_reserved_incremental_DeepSeek_attempt_via_opaque_mapping")
                            else:
                                unresolved.append(str(mapping_path.relative_to(root)))
            for name in sorted(files):
                if name not in names and not re.fullmatch(r"baseline-claim-\d+(?:-live)?\.json", name):
                    continue
                if name == "inputs.json" and "attempts" not in folder.parts:
                    continue
                path = folder / name
                try:
                    value = read(path)
                except (ValueError, OSError) as exc:
                    unresolved.append(f"{path.relative_to(root)}: {type(exc).__name__}")
                    continue
                ids = set()
                for claim in _claims(value):
                    ids.update(lookup.get(hashlib.sha256(claim.encode()).hexdigest(), set()))
                record(path, ids, "conservative_prior_development_or_executed_claim")
    excluded = sorted(exposure)
    eligible = sorted(set(range(len(data))) - set(excluded))
    return {"created_at": now(), "dataset_sha256": sha(dataset), "dataset_n": len(data),
            "rule": "Exclude any reserved/started historical DeepSeek attempt and any matching prior structured development/executed claim; identity/hash only; scheduled unstarted final inputs do not count.",
            "excluded_ids": excluded, "eligible_ids": eligible,
            "records": records, "unresolved": unresolved,
            "prior_exposure": "All 500 claims appeared in historical Gemma evaluation. This is a reused development dataset, not a pristine external test set.",
            "concurrency": "Reaudit before dispatch. Any selected identity newly exposed by another study blocks this run; never substitute after development."}


def prepare(root: Path, dataset: Path, output: Path, protocol: Path, seed=20261107,
            selection_size=30, amendment: Path | None = None):
    if (output / "split.json").exists():
        raise ValueError("Existing split is immutable; use its saved manifest")
    required = {"final": 100, "calibration": 30, "selection": selection_size}
    if type(selection_size) is not int or not 1 <= selection_size <= 30:
        raise ValueError("Selection size must be 1..30")
    if selection_size != 30:
        approved = read(amendment) if amendment else {}
        if approved.get("approved_split") != required or not approved.get("user_approval"):
            raise ValueError("Changed selection size requires an explicit user-approved split amendment")
    exposure = audit(root, dataset, output)
    eligible = exposure["eligible_ids"]
    order = random.Random(seed).sample(eligible, len(eligible))
    # Do not silently substitute or shrink any required evaluation stage.
    final = order[:100] if len(order) >= 100 else []
    calibration = order[100:130] if len(order) >= 130 else []
    needed = 130 + selection_size
    selection = order[130:needed] if len(order) >= needed else []
    save(output / "exposure-audit.json", exposure)
    save(output / "split.json", {
        "schema_version": 1, "seed": seed, "sampling": f"Python random.Random(seed).sample(sorted(eligible), len(eligible)); first 100 final, next 30 calibration, next {selection_size} selection",
        "dataset_path": str(dataset.resolve()), "dataset_sha256": sha(dataset),
        "audit_sha256": sha(output / "exposure-audit.json"), "protocol_sha256": sha(protocol),
        "eligible_ids": eligible, "final_ids": final, "calibration_ids": calibration,
        "selection_ids": selection, "required": required,
        "amendment_sha256": sha(amendment) if amendment else None,
        "shortfall": max(0, needed - len(eligible)), "complete_split": len(eligible) >= needed,
        "protected": "Final claim text, gold labels and predictions are not materialized before method freeze."})
    return {"eligible": len(eligible), "final": len(final), "calibration": len(calibration),
            "selection": len(selection), "shortfall": max(0, needed - len(eligible))}


def assert_unexposed(root, output):
    split = read(output / "split.json")
    dataset = Path(split["dataset_path"])
    if sha(dataset) != split["dataset_sha256"]:
        raise ValueError("Dataset changed")
    current = audit(root, dataset, output)
    save(output / "latest-exposure-audit.json", current)
    selected = set(split["final_ids"] + split["calibration_ids"] + split["selection_ids"])
    new = selected & set(current["excluded_ids"])
    if split.get("development_reuse_sha256"):
        receipt_path = output / "development-reuse.json"
        if sha(receipt_path) != split["development_reuse_sha256"]:
            raise ValueError("Development reuse receipt changed")
        receipt = read(receipt_path)
        parent = Path(receipt["parent_run"])
        for name, digest in receipt["parent_commitments"].items():
            if sha(parent / name) != digest:
                raise ValueError("Parent development commitment changed")
        reusable = set(receipt["calibration_ids"] + receipt["selection_ids"])
        if reusable != set(split["calibration_ids"] + split["selection_ids"]):
            raise ValueError("Development reuse identities differ")
        allowed_prefix = receipt["parent_relative"] + "/"
        for i in list(new & reusable):
            evidence = [r for r in current["records"] if i in r["ids"]]
            if evidence and all(r["path"].startswith(allowed_prefix) for r in evidence):
                new.remove(i)
    if new or current["unresolved"]:
        raise ValueError(f"Exposure boundary changed: {len(new)} selected identities exposed; {len(current['unresolved'])} unresolved audit records")
    return current


def input_for(row):
    # Reuse date conversion/allowlist without exposing the row to a worker.
    from kaji_langgraph.evaluation import model_input
    return model_input(row)

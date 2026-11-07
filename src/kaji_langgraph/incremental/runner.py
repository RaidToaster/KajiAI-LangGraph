"""Single-worker controller and gold-free subprocess entry point."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import zipfile

from kaji_langgraph.incremental.boundary import assert_unexposed, audit, input_for, now, prepare, read, save, sha

THREADS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


@contextmanager
def lock(path, historical=False):
    """Use OS locks; a stale lock filename alone does not imply a running worker."""
    handle = path.open("rb" if historical else "a+b")
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBRLCK if historical else msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, (fcntl.LOCK_SH if historical else fcntl.LOCK_EX) | fcntl.LOCK_NB)
        acquired = True
        yield
    finally:
        if acquired:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


def historical_locks(root, output):
    paths = []
    for base in (root / "evaluation/results", root / "artifacts/aris"):
        if not base.exists():
            continue
        for run in base.iterdir():
            if run.is_dir() and run.resolve() != output.resolve():
                paths.extend(p for p in run.glob("*.lock") if "coordinator" in p.name)
    return paths


def source_hashes(root):
    paths = [p for p in (root / "src/kaji_langgraph").rglob("*") if p.suffix in {".py", ".yaml"}]
    paths += [root / name for name in ("pyproject.toml", "uv.lock")]
    return {str(p.relative_to(root)).replace("\\", "/"): sha(p) for p in sorted(paths)}


def verify_hashes(root, freeze):
    if source_hashes(root) != freeze["source_hashes"]:
        raise ValueError("Frozen source inventory changed")
    for name, digest in freeze["source_hashes"].items():
        if sha(root / name) != digest:
            raise ValueError(f"Frozen source changed: {name}")


def preflight(root, output, do_audit=True):
    findings = {"at": now(), "historical_coordinators": [], "blockers": []}
    for path in historical_locks(root, output):
        try:
            with lock(path, historical=True):
                state = "not_held"
        except OSError:
            state = "held_or_inaccessible"
            findings["blockers"].append("Historical coordinator lock held: " + str(path.relative_to(root)))
        findings["historical_coordinators"].append({"path": str(path.relative_to(root)), "state": state})
    split = read(output / "split.json")
    if not split["complete_split"]:
        findings["blockers"].append(f"Eligible sample shortfall: {split['shortfall']}")
    if do_audit:
        try:
            current = assert_unexposed(root, output)
            findings["eligible_now"] = len(current["eligible_ids"])
        except ValueError as exc:
            findings["blockers"].append(str(exc))
            latest = output / "latest-exposure-audit.json"
            if latest.exists():
                findings["eligible_now"] = len(read(latest)["eligible_ids"])
    resource = output / "resource-release.json"
    if not resource.exists():
        findings["blockers"].append("Current existing-credit balances and zero-rated retrieval headroom have no run-bound resource receipt")
    else:
        receipt = read(resource)
        if (receipt.get("split_sha256") != sha(output / "split.json") or not receipt.get("existing_credits_only")
                or not receipt.get("zero_rated_retrieval_verified") or receipt.get("billing_changes", True)):
            findings["blockers"].append("Resource receipt is not bound to this split/current free retrieval")
        for service in ("ollama", "jev", "search", "fetch"):
            cap = receipt.get("caps_usd", {}).get(service)
            if type(cap) not in {int, float} or cap < 0:
                findings["blockers"].append(f"Missing resource cap: {service}")
        if receipt.get("caps_usd", {}).get("search") != 0 or receipt.get("caps_usd", {}).get("fetch") != 0:
            findings["blockers"].append("This protocol permits only zero-rated retrieval")
        try:
            expires = datetime.fromisoformat(receipt["valid_until"])
            if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
                findings["blockers"].append("Resource/headroom receipt expired")
        except (KeyError, ValueError, TypeError):
            findings["blockers"].append("Resource/headroom receipt requires a timezone-aware valid_until")
        for service in ("ollama", "jev"):
            balance = receipt.get("remaining_existing_credit_usd", {}).get(service,
                receipt.get("user_confirmed_credit_headroom_usd", {}).get(service))
            if type(balance) not in {int, float} or balance < receipt.get("caps_usd", {}).get(service, float("inf")):
                findings["blockers"].append(f"Current {service} credits do not cover the run reservation")
        findings["resource_receipt_sha256"] = sha(resource)
    findings["ready"] = not findings["blockers"]
    save(output / "preflight.json", findings)
    return findings


def snapshot(root, output):
    from kaji_langgraph.config import load_config
    config = load_config()
    config["model"].update(name="deepseek-v4.1-flash:cloud", temperature=0, verdict_mode="averitec")
    config["policy"]["max_execution_time_seconds"] = 300
    config["policy"]["retry_on_failure"] = False
    if (output / "method-settings.json").exists():
        settings = read(output / "method-settings.json")
        if set(settings) != {"material_resolution"} or type(settings["material_resolution"]) is not bool:
            raise ValueError("Unsupported method settings")
        config["incremental"] = settings
    from kaji_langgraph.incremental.method import PLAN_PROMPT, ASSESS_PROMPT, MATERIAL_ASSESS_PROMPT, ADJUDICATE_PROMPT
    from kaji_langgraph.study import closed_book_prompt
    save(output / "prompts.json", {"initial_template": closed_book_prompt("{claim}", "{reference_date}"),
        "planner": PLAN_PROMPT, "assessor": ASSESS_PROMPT, "adjudicator": ADJUDICATE_PROMPT,
        "material_assessor": MATERIAL_ASSESS_PROMPT,
        "schema_note": "The frozen provider adapter appends the exact Pydantic JSON schema and uses one counted format repair."})
    hashes = source_hashes(root)
    target = output / "implementation-snapshot.zip"
    if target.exists():
        raise ValueError("Implementation snapshot already exists")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in hashes:
            archive.write(root / name, name)
        archive.write(output / "PROTOCOL.md", "PROTOCOL.md")
        archive.write(output / "split.json", "split.json")
        archive.write(output / "prompts.json", "prompts.json")
        archive.write(output / "exposure-audit.json", "exposure-audit.json")
        if (output / "protocol-amendment.json").exists():
            archive.write(output / "protocol-amendment.json", "protocol-amendment.json")
        for name in ("development-reuse.json", "method-settings.json"):
            if (output / name).exists():
                archive.write(output / name, name)
        archive.write(root / "src/kaji_langgraph/incremental/README.md", "INCREMENTAL-GUIDE.md")
        for path in sorted((root / "tests").glob("*.py")):
            archive.write(path, str(path.relative_to(root)))
    save(output / "implementation.json", {"at": now(), "source_hashes": hashes,
        "config": config, "snapshot_sha256": sha(target),
        "protocol_sha256": sha(output / "PROTOCOL.md"), "split_sha256": sha(output / "split.json"),
        "prompts_sha256": sha(output / "prompts.json"),
        "python": sys.version, "packages": {d.metadata["Name"]: d.version for d in distributions()},
        "workers": 1, "numerical_threads": 2, "claim_hard_timeout_seconds": 300,
        "model_options": {"temperature": 0, "num_predict": 8192, "think": "omitted; native provider default"},
        "revisions": 0})


def materialize(root, output, phase, rule):
    split = read(output / "split.json")
    if phase == "final" and not (output / "method-freeze.json").exists():
        raise ValueError("Final inputs require a frozen method")
    data = read(Path(split["dataset_path"]))
    ids = split[phase + "_ids"]
    if len(ids) != split["required"][phase]:
        raise ValueError("Required phase sample is incomplete")
    path = output / f"{phase}-mapping.json"
    if not path.exists():
        save(path, {uuid.uuid4().hex: i for i in ids})
    mapping = read(path)
    if sorted(mapping.values()) != sorted(ids) or len(mapping) != len(ids):
        raise ValueError("Identity mapping changed")
    phase_dir = output / phase
    phase_dir.mkdir(exist_ok=True)
    for opaque, i in mapping.items():
        path = phase_dir / f"{opaque}-input.json"
        inputs = input_for(data[i])
        if path.exists() and read(path) != inputs:
            raise ValueError("Saved allowlisted input changed")
        if not path.exists():
            save(path, inputs)
    return mapping


def worker(job_path):
    # No dataset, gold files, split manifest, row ID or scoring imports here.
    from kaji_langgraph.incremental.method import execute
    from kaji_langgraph.incremental.providers import Journal, Providers, accounting
    job = read(job_path)
    directory = job_path.parent
    if job["nonce"] != os.environ.pop("KAJI_INCREMENTAL_NONCE", None):
        raise ValueError("Worker must be started by the coordinator")
    if (directory / "worker-start.json").exists():
        raise ValueError("Started worker cannot be replayed")
    save(directory / "worker-start.json", {"at": now(), "pid": os.getpid()})
    inputs = read(Path(job["input_path"]))
    started = time.monotonic()
    journal = Journal(directory, Path(job["output"]), started + job["remaining_seconds"])
    provider = Providers(journal, job["config"]["model"]["base_url"])
    def commit_initial(initial):
        inherited = read(Path(job["development_reuse"]["initial_path"])) if job.get("development_reuse") else None
        save(directory / "initial.json", {"prediction": initial,
            "accounting": inherited["accounting"] if inherited else accounting(directory),
            "elapsed_seconds": inherited["elapsed_seconds"] if inherited else time.monotonic() - started,
            "reused_from_sha256": job["development_reuse"]["initial_sha256"] if inherited else None})
    if job.get("development_reuse"):
        from kaji_langgraph.incremental.revision import cached_execution, combine_accounts
        result = cached_execution(job, inputs, provider, journal, commit_initial)
        result["elapsed_seconds"] = time.monotonic() - started
        result["deployed_accounting"] = combine_accounts(job["development_reuse"]["inherited_policy_accounting"], accounting(directory))
        result["policy_elapsed_seconds"] = job["development_reuse"]["inherited_elapsed_seconds"] + result["elapsed_seconds"]
        result["development_scope"] = "Single permitted fixed-evidence exploratory reassessment; original initial reused without a send"
    else:
        result = execute(inputs, provider, job["config"], job["rule"], commit_initial)
    saved = read(directory / "initial.json") if (directory / "initial.json").exists() else {}
    result.update(opaque_id=job["opaque_id"], initial_accounting=saved.get("accounting", accounting(directory)),
                  initial_elapsed_seconds=saved.get("elapsed_seconds", result["elapsed_seconds"]),
                  accounting=accounting(directory))
    save(directory / "result.json", result)


def complete_or_refuse(directory):
    if (directory / "result.json").exists():
        return read(directory / "result.json")
    if directory.exists():
        raise ValueError("Started attempt lacks a committed result; reconcile without replay: " + directory.name)
    return None


def launch_one(root, output, phase, opaque, config, rule):
    from kaji_langgraph.incremental.method import fallback
    from kaji_langgraph.incremental.providers import accounting
    directory = output / "attempts" / f"{phase}-{opaque}"
    result = complete_or_refuse(directory)
    if result is not None:
        return result
    directory.mkdir(parents=True)
    nonce = uuid.uuid4().hex
    job = {"opaque_id": opaque, "input_path": str(output / phase / f"{opaque}-input.json"),
        "output": str(output), "config": config, "rule": rule,
        "remaining_seconds": 300, "nonce": nonce}
    if phase == "selection" and (output / "selection-reuse.json").exists():
        reuse = read(output / "selection-reuse.json")[opaque]
        job.update(development_reuse=reuse, remaining_seconds=max(1, 300 - reuse["inherited_elapsed_seconds"]))
    save(directory / "job.json", job)
    env = {**os.environ, **dict.fromkeys(THREADS, "2"), "KAJI_INCREMENTAL_NONCE": nonce}
    started = time.monotonic()
    with (directory / "worker.log").open("wb") as log:
        proc = subprocess.Popen([sys.executable, "-m", "kaji_langgraph.incremental", "worker", str(directory / "job.json")],
            cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            proc.wait(timeout=job["remaining_seconds"])
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            save(directory / "provider-stop.json", {"reason": "300-second supervisor timeout; reconcile any uncertain send", "at": now()})
    if not (directory / "result.json").exists():
        saved = read(directory / "initial.json") if (directory / "initial.json").exists() else {}
        result = fallback(saved.get("prediction"), "worker terminated; saved initial fallback", "timeout_or_worker_failure")
        result.update(opaque_id=opaque, elapsed_seconds=time.monotonic()-started,
            initial_accounting=saved.get("accounting", accounting(directory)),
            initial_elapsed_seconds=saved.get("elapsed_seconds", time.monotonic()-started), accounting=accounting(directory))
        if job.get("development_reuse"):
            from kaji_langgraph.incremental.revision import combine_accounts
            result["deployed_accounting"] = combine_accounts(job["development_reuse"]["inherited_policy_accounting"], accounting(directory))
            result["policy_elapsed_seconds"] = job["development_reuse"]["inherited_elapsed_seconds"] + result["elapsed_seconds"]
        save(directory / "result.json", result)
    result = read(directory / "result.json")
    save(directory / "terminal.json", {"at": now(), "returncode": proc.returncode, "result_sha256": sha(directory / "result.json")})
    return result


def load_keys(root):
    path = root / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                name, value = line.split("=", 1)
                if name.strip() in {"TINYFISH_API_KEY", "TYPESAFE_API_KEY"}:
                    os.environ.setdefault(name.strip(), value.strip().strip("\"'"))
    if not all(os.getenv(k) for k in ("TINYFISH_API_KEY", "TYPESAFE_API_KEY")):
        raise ValueError("Existing retrieval/Jev credentials are unavailable")


def phase_rule(output, phase):
    if phase == "calibration":
        return "none"
    if phase == "selection":
        if not (output / "calibration-report.json").exists():
            raise ValueError("Complete and score calibration first")
        return "all"
    freeze = read(output / "method-freeze.json")
    return freeze["final_research_rule"]


def run_phase(root, output, phase, limit):
    initial_check = preflight(root, output)
    if not initial_check["ready"]:
        raise ValueError("; ".join(initial_check["blockers"]))
    # Hold historical shared locks throughout dispatch to prevent races with
    # their exclusive coordinators, as well as this run's exclusive lock.
    with ExitStack() as stack:
        stack.enter_context(lock(output / "coordinator.lock"))
        for path in historical_locks(root, output):
            stack.enter_context(lock(path, historical=True))
        # Close the interval between the preflight audit and acquiring the
        # historical locks. A final old attempt may have started in that interval.
        assert_unexposed(root, output)
        if (output / f"{phase}-commit.json").exists():
            raise ValueError("Phase already committed; score saved predictions without rerunning")
        if not (output / "implementation.json").exists():
            snapshot(root, output)
        implementation = read(output / "implementation.json")
        final_freeze = verify_freeze(root, output) if phase == "final" else None
        verify_hashes(root, final_freeze if final_freeze else implementation)
        if sha(output / "PROTOCOL.md") != implementation["protocol_sha256"]:
            raise ValueError("Protocol changed after implementation freeze")
        if (sha(output / "split.json") != implementation["split_sha256"] or
                sha(output / "prompts.json") != implementation["prompts_sha256"]):
            raise ValueError("Split or prompts changed after implementation freeze")
        packages = {d.metadata["Name"]: d.version for d in distributions()}
        if packages != implementation["packages"] or sys.version != implementation["python"]:
            raise ValueError("Frozen Python environment changed")
        load_keys(root)
        rule = phase_rule(output, phase)
        mapping = materialize(root, output, phase, rule)
        started = 0
        for opaque in mapping:
            directory = output / "attempts" / f"{phase}-{opaque}"
            if (directory / "provider-stop.json").exists():
                raise ValueError("Provider stop requires reconciliation before more dispatch: " + str(directory))
            if (directory / "result.json").exists():
                continue
            if started >= limit:
                break
            verify_hashes(root, final_freeze if final_freeze else implementation)
            active_config = final_freeze.get("final_config", implementation["config"]) if final_freeze else implementation["config"]
            result = launch_one(root, output, phase, opaque, active_config, rule)
            started += 1
            print(json.dumps({"phase": phase, "opaque_id": opaque, "status": result["research_status"],
                              "completed_now": started}), flush=True)  # no labels/interim correctness
            if (directory / "provider-stop.json").exists() or result["accounting"]["uncertain_sends"]:
                raise ValueError("Provider/uncertain-send boundary; inspect journal before further dispatch")
        paths = [output / "attempts" / f"{phase}-{opaque}" / "result.json" for opaque in mapping]
        if all(p.exists() for p in paths):
            save(output / f"{phase}-commit.json", {"at": now(), "n": len(paths),
                "prediction_hashes": {str(p.relative_to(output)): sha(p) for p in paths},
                "mapping_sha256": sha(output / f"{phase}-mapping.json"),
                "implementation_sha256": sha(output / "implementation.json"),
                "method_freeze_sha256": sha(output / "method-freeze.json") if phase == "final" else None})


def scored_rows(output, phase):
    commit = read(output / f"{phase}-commit.json")
    if phase == "final" and commit.get("method_freeze_sha256") != sha(output / "method-freeze.json"):
        raise ValueError("Final method freeze differs from prediction commitment")
    if sha(output / f"{phase}-mapping.json") != commit["mapping_sha256"]:
        raise ValueError("Mapping changed after predictions committed")
    if sha(output / "implementation.json") != commit["implementation_sha256"]:
        raise ValueError("Implementation commitment changed")
    mapping = read(output / f"{phase}-mapping.json")
    if len(commit["prediction_hashes"]) != len(mapping):
        raise ValueError("Prediction commitment is incomplete")
    for name, digest in commit["prediction_hashes"].items():
        if sha(output / name) != digest:
            raise ValueError("Committed predictions changed")
    split = read(output / "split.json")
    dataset = Path(split["dataset_path"])
    if sha(dataset) != split["dataset_sha256"]:
        raise ValueError("Dataset hash differs")
    # First and only point gold labels enter the pipeline, AFTER all commitments.
    data = read(dataset)
    return [{**read(output / "attempts" / f"{phase}-{opaque}" / "result.json"),
             "gold_label": data[i]["label"]} for opaque, i in mapping.items()]


def score(output, phase):
    from kaji_langgraph.incremental.analysis import calibration, compare, final_comparison
    rows = scored_rows(output, phase)
    if phase == "calibration":
        report = calibration(rows)
    else:
        routing = read(output / "calibration-report.json")["routing_rule"]
        report = compare(rows, routing) if phase == "selection" else final_comparison(rows, read(output / "method-freeze.json")["final_research_rule"])
    save(output / f"{phase}-report.json", report)
    return report


def freeze(root, output):
    if (output / "method-freeze.json").exists():
        raise ValueError("Method already frozen")
    implementation = read(output / "implementation.json")
    source = implementation
    infrastructure = output / "final-infrastructure-amendment.json"
    if infrastructure.exists():
        amendment = read(infrastructure)
        if amendment["development_implementation_sha256"] != sha(output / "implementation.json"):
            raise ValueError("Final infrastructure amendment has wrong development commitment")
        if amendment["development_blocked_source_count"] != 0:
            raise ValueError("Infrastructure control affected development; do not silently reuse selection")
        source = {"source_hashes": amendment["final_source_hashes"]}
        verify_hashes(root, source)
    else:
        verify_hashes(root, source)
    selection = read(output / "selection-report.json")
    expected = read(output / "split.json")["required"]["selection"]
    if selection["n"] != expected:
        raise ValueError(f"Selection must include all {expected} declared claims")
    calibration = read(output / "calibration-report.json")
    from kaji_langgraph.incremental.analysis import calibration as calibrate, compare
    if calibration != calibrate(scored_rows(output, "calibration")):
        raise ValueError("Calibration report does not reproduce from committed predictions")
    if selection != compare(scored_rows(output, "selection"), calibration["routing_rule"]):
        raise ValueError("Selection report does not reproduce from committed predictions")
    best = selection["best_research_candidate"]
    choice = None
    if (output / "final-method-choice.json").exists():
        choice = read(output / "final-method-choice.json")
        if (sha(output / "selection-report.json") != choice["revision_selection_report_sha256"] or
                sha(Path(choice["parent_selection_report"])) != choice["parent_selection_report_sha256"]):
            raise ValueError("Final method choice reports changed")
        best = choice["best_research_candidate"]
    paths = ["split.json", "PROTOCOL.md", "prompts.json", "implementation.json", "implementation-snapshot.zip",
             "calibration-report.json", "selection-report.json", "calibration-commit.json", "selection-commit.json"]
    if (output / "protocol-amendment.json").exists():
        paths.append("protocol-amendment.json")
    for name in ("development-reuse.json", "method-settings.json", "selection-reuse.json", "final-method-choice.json"):
        if (output / name).exists():
            paths.append(name)
    if infrastructure.exists():
        paths.extend(["final-infrastructure-amendment.json", "final-source-snapshot.zip"])
    final_config = json.loads(json.dumps(implementation["config"]))
    if choice:
        final_config["incremental"] = {"material_resolution": choice["selected_version"] == "material"}
    save(output / "method-freeze.json", {"at": now(), "source_hashes": source["source_hashes"],
        "artifacts": {p: sha(output / p) for p in paths}, "best_research_candidate": best,
        "deployment": choice["deployment"] if choice else selection["selected_deployment"],
        "promoted_on_development": choice["promoted"] if choice else selection["promoted"],
        "final_config": final_config, "selected_version": choice["selected_version"] if choice else "original",
        "final_research_rule": "all" if best == "A" else calibration["routing_rule"],
        "comparison": "Frozen best research challenger vs shared initial, including if challenger lost development",
        "final_policy": "Once only, no interim scoring; no further method revision in this cycle"})


def verify_freeze(root, output):
    frozen = read(output / "method-freeze.json")
    verify_hashes(root, frozen)
    for name, digest in frozen["artifacts"].items():
        if sha(output / name) != digest:
            raise ValueError("Frozen artifact changed: " + name)
    return frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "preflight", "run", "score", "freeze", "snapshot"):
        p = subs.add_parser(name)
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--root", type=Path, default=Path.cwd())
        if name == "prepare":
            p.add_argument("--dataset", type=Path, default=Path("evaluation/data/averitec_dev.json"))
            p.add_argument("--selection-size", type=int, default=30)
            p.add_argument("--amendment", type=Path)
        if name in {"run", "score"}:
            p.add_argument("--phase", choices=("calibration", "selection", "final"), required=True)
        if name == "run":
            p.add_argument("--limit", type=int, default=1)
    p = subs.add_parser("worker")
    p.add_argument("job", type=Path)
    args = parser.parse_args()
    if args.command == "worker":
        worker(args.job)
        return
    output, root = args.output.resolve(), args.root.resolve()
    if args.command == "prepare":
        result = prepare(root, args.dataset.resolve(), output, output / "PROTOCOL.md",
                         selection_size=args.selection_size, amendment=args.amendment)
    elif args.command == "preflight":
        result = preflight(root, output)
    elif args.command == "run":
        if args.limit < 1:
            parser.error("limit must be positive")
        run_phase(root, output, args.phase, args.limit)
        result = {"phase": args.phase, "committed": (output / f"{args.phase}-commit.json").exists()}
    elif args.command == "score":
        if args.phase == "final":
            verify_freeze(root, output)
        result = score(output, args.phase)
    elif args.command == "freeze":
        freeze(root, output)
        result = {"method_frozen": True}
    else:
        snapshot(root, output)
        result = {"implementation_snapshot": True}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

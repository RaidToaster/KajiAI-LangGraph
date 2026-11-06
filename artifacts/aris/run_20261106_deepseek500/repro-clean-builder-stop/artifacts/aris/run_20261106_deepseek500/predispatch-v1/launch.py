"""Run the archived pilot worker one untouched DeepSeek cell at a time."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import time

import pilot50 as pilot

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
read, save, digest = pilot.read, pilot.save, pilot.digest
fs = pilot.fs
MODEL = fs.MODELS["deepseek"]


def verify():
    protocol = read(RUN / "protocol.json")
    approval = read(RUN / "approval.json")
    assert approval == {"protocol_sha256": digest(RUN / "protocol.json"), "user_authorized_fresh": 953}
    assert protocol["models"] == {"deepseek": MODEL}
    assert protocol["schedule"] == read(RUN / "schedule.json")
    assert len(protocol["schedule"]) == len({fs.task_id(t) for t in protocol["schedule"]}) == 1000
    assert protocol["caps"] == fs.CAPS and protocol["max_attempt_seconds"] == 300
    assert protocol["scheduling_cost_caps_usd"] == {"ollama": 30, "jev": 2.5}
    assert pilot.code_digest() == protocol["candidate_source_sha256"]
    for module in (pilot.graph, pilot.llm, pilot.jev):
        assert Path(module.__file__).resolve().is_relative_to(RUN / "frozen/src")
    for name, sha in protocol["freeze_files"].items():
        assert digest(RUN / name) == sha, name
    return protocol


def prior_check():
    references = read(RUN / "reused.json")
    assert len(references) == 47
    for reference in references.values():
        directory = ROOT / reference["path"]
        for name, sha in reference["files"].items():
            assert digest(directory / name) == sha, (directory, name)
    return references


def account(protocol):
    receipt = read(RUN / "account-confirmation.json")
    assert receipt["protocol_sha256"] == digest(RUN / "protocol.json")
    for service, ceiling in protocol["scheduling_cost_caps_usd"].items():
        assert receipt["existing_credits_usd"][service] >= ceiling
    assert receipt["tinyfish"]["search_per_query_usd"] == receipt["tinyfish"]["fetch_per_url_usd"] == 0
    assert receipt["tinyfish"]["auto_reload"] == "unconfigured"


def sends(directory, state):
    rows = pilot.usage(directory, MODEL)
    problems = []
    if Counter(r["service"] for r in rows) != +Counter(state["counts"]):
        problems.append("reservation/journal mismatch")
    for row in rows:
        service = row["service"]
        if not row.get("usage_known") or row.get("transport_error") or row.get("status") != 200:
            problems.append(f"{service}/{row['request_id']} unresolved or HTTP failure")
        if service in ("ollama", "jev") and (
            not row.get("model_verified") or row["requested_model"] != (MODEL if service == "ollama" else "jev-1.13.0")
            or row.get("estimated_usd", 0) > (row.get("reservation_usd") or 0)
        ):
            problems.append(f"{service}/{row['request_id']} model or accounting mismatch")
    return rows, problems


def snapshot(protocol, references):
    stage = RUN / "attempts"
    costs = {"ollama": 0.0, "jev": 0.0}
    retrieval = read(RUN / "prior-retrieval-ledger.json")
    pending = []
    started = {p.name for p in stage.iterdir()} if stage.exists() else set()
    valid = {fs.task_id(t) for t in protocol["schedule"]} - references.keys()
    assert started <= valid and len(started) <= protocol["fresh_attempt_limit"]
    for task in protocol["schedule"]:
        identity = fs.task_id(task)
        if identity in references:
            continue
        if identity not in started:
            pending.append(task)
            continue
        directory = stage / identity
        job_path = directory / "job.json"
        if not job_path.is_file():
            raise RuntimeError(f"Started without terminal record: {identity}. Reconcile before continuing.")
        job = read(job_path)
        if job["operational_stop"]:
            raise RuntimeError(f"Unresolved operational stop: {identity}")
        attempt = read(directory / "attempt.json")
        assert all(attempt[k] == v for k, v in task.items())
        assert attempt["protocol_sha256"] == digest(RUN / "protocol.json")
        rows, problems = sends(directory, read(directory / "live-state.json"))
        if problems:
            raise RuntimeError((identity, problems))
        accumulate(rows, costs, retrieval)
    assert not any(fs.task_id(t) in started for t in pending)
    # Started cells must be a prefix of the fresh schedule.
    assert started == set(list(fs.task_id(t) for t in protocol["schedule"] if fs.task_id(t) in valid)[:len(started)])
    return costs, retrieval, pending


def accumulate(rows, costs, retrieval):
    for row in rows:
        service = row["service"]
        if service in costs:
            costs[service] += row.get("estimated_usd", row.get("reservation_usd") or 0)
        else:
            retrieval.append(row)


def set_status(status, **fields):
    save(RUN / "status.json", dict(status=status, updated_at=pilot.now(), **fields))


def run_attempt(task, costs, protocol):
    identity = fs.task_id(task)
    directory = RUN / "attempts" / identity
    directory.mkdir()
    save(directory / "attempt.json", dict(**task, started_at=pilot.now(), protocol_sha256=digest(RUN / "protocol.json")))
    save(directory / "budget-at-entry.json", costs)
    save(directory / "live-state.json", dict(counts=dict.fromkeys(protocol["caps"], 0), deadline=time.time()+285, stop=None))
    set_status("running", attempt=identity)
    begin = time.monotonic()
    with (directory / "stdout.log").open("wb") as out, (directory / "stderr.log").open("wb") as err:
        try:
            code = subprocess.run(
                [sys.executable, str(Path(__file__)), "--worker", identity],
                stdout=out, stderr=err, timeout=300, cwd=ROOT,
                env={**os.environ, **fs.THREADS, "PYTHONUTF8": "1"},
            ).returncode
        except subprocess.TimeoutExpired:
            code = None
    state = read(directory / "live-state.json")
    rows, problems = sends(directory, state)
    completed = (directory / "result.json").exists()
    if not rows and not completed:
        problems.append("worker failed before first send")
    if state["stop"]:
        problems.append(state["stop"])
    save(directory / "usage.json", rows)
    save(directory / "job.json", dict(exit_code=code, elapsed_seconds=time.monotonic()-begin, finished_at=pilot.now(),
        workflow_completed=completed, timeout=code is None, operational_stop=bool(problems), problems=problems))
    return rows, problems


def launch(protocol, references):
    account(protocol)
    assert not (RUN / "STOP.json").exists(), "Review the recorded stop"
    stage = RUN / "attempts"
    stage.mkdir(exist_ok=True)
    lock = RUN / "running.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
        stream.flush()
        os.fsync(stream.fileno())
    try:
        costs, retrieval, pending = snapshot(protocol, references)
        for task in pending:
            identity = fs.task_id(task)
            if (RUN / "STOP.json").exists():
                return
            until = pilot.quota_until(retrieval, protocol)
            if until > time.time():
                # Exit cleanly between attempts. No child or helper must survive this wait.
                boundary = dict(next_untouched=identity, resume_at=datetime.fromtimestamp(until, timezone.utc).isoformat(),
                                wait_observed_at=pilot.now(), accounted=1000-len(pending)+pending.index(task))
                history = RUN / "quota-boundaries"
                history.mkdir(exist_ok=True)
                save(history / f"{time.time_ns()}.json", boundary)
                set_status("quota_checkpoint", **boundary)
                return
            rows, problems = run_attempt(task, costs, protocol)
            accumulate(rows, costs, retrieval)
            if problems:
                save(RUN / "STOP.json", dict(attempt=identity, problems=problems, timestamp=pilot.now()))
                set_status("operational_stop", attempt=identity, problems=problems)
                return
            print(identity, "accounted", flush=True)
        set_status("complete", accounted=1000)
    finally:
        lock.unlink()


class ExactLedger(pilot.PilotLedger):
    def before(self, service, request):
        if service == "tinyfish_fetch":
            urls = (request.get("body") or {}).get("urls", [])
            # The archived retriever dispatches one URL per transport call.
            if len(urls) != 1:
                raise pilot.LimitReached("Unexpected Fetch URL count")
        return super().before(service, request)


def worker(protocol, identity):
    account(protocol)
    lock = RUN / "running.lock"
    assert lock.read_text(encoding="ascii") == str(os.getppid())
    assert identity not in read(RUN / "reused.json")
    directory = RUN / "attempts" / identity
    attempt = read(directory / "attempt.json")
    assert attempt["protocol_sha256"] == digest(RUN / "protocol.json")
    assert not (RUN / "STOP.json").exists()
    pilot.PilotLedger = ExactLedger
    pilot.verify = lambda: protocol
    pilot.worker(identity)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--worker")
    args = parser.parse_args()
    protocol = verify()
    if args.worker:
        worker(protocol, args.worker)
        return
    refs = prior_check()
    if args.verify:
        costs, retrieval, pending = snapshot(protocol, refs)
        print(dict(reused=len(refs), next_untouched=fs.task_id(pending[0]) if pending else None,
                   fresh_remaining=len(pending), costs=costs, retrieval_reservations=len(retrieval),
                   earliest_quota=datetime.fromtimestamp(pilot.quota_until(retrieval, protocol), timezone.utc).isoformat()))
    else:
        launch(protocol, refs)


if __name__ == "__main__":
    main()


"""Zero-network witness for the real frozen launcher and ledger."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

import launch

read, save, pilot = launch.read, launch.save, launch.pilot


def main():
    protocol = launch.verify()
    launch.account(protocol)
    refs = launch.prior_check()
    _, retrieval, pending = launch.snapshot(protocol, refs)
    checks = []
    assert len(refs) == 47 and len(pending) == 953
    assert launch.fs.task_id(pending[0]) == "dev-296-deepseek-candidate"
    checks.append("isolated imports, 47 immutable journal references and 953 untouched cells")
    assert launch.quota_until(retrieval, protocol) > time.time()
    checks.append("live quota gate requires a clean between-attempt checkpoint")

    with tempfile.TemporaryDirectory(dir=launch.ROOT / "tmp") as tmp:
        workspace = Path(tmp)
        original_worker = workspace / "child.py"
        original_worker.write_text(
            "import json, os, sys, httpx2\n"
            "print(json.dumps(dict(parent=os.getppid(), prefix=sys.prefix)), flush=True)\n",
            encoding="utf8")
        child = subprocess.run([sys._base_executable, str(original_worker)], check=True, text=True,
                               capture_output=True, env={**os.environ, "__PYVENV_LAUNCHER__": sys.executable})
        assert json.loads(child.stdout) == {"parent": os.getpid(), "prefix": sys.prefix}
        checks.append("direct worker executable binds to real coordinator PID and existing virtualenv")
        original_worker.write_text("import time\ntime.sleep(30)\n", encoding="utf8")
        with subprocess.Popen([sys._base_executable, str(original_worker)],
                              env={**os.environ, "__PYVENV_LAUNCHER__": sys.executable}) as child:
            try:
                child.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                child.kill()
                assert child.wait(timeout=5) != 0
            else:
                raise AssertionError("timeout did not fire")
        checks.append("timeout kills the actual child interpreter")

        def ledger(name, model_budget=0):
            d = workspace / name
            d.mkdir()
            save(d/"live-state.json", dict(counts=dict.fromkeys(protocol["caps"], 0), deadline=time.time()+60, stop=None))
            save(d/"budget-at-entry.json", {"ollama": model_budget, "jev": 0})
            return launch.ExactLedger(d, {**protocol, "num_predict": 6144}, launch.MODEL)

        payload = {"body": {"model": launch.MODEL, "options": {"num_predict": 6144}}}
        known = ledger("known")
        n = known.before("ollama", payload)
        reply = {"model": launch.MODEL.removesuffix(":cloud"), "done": True, "prompt_eval_count": 100, "eval_count": 50}
        known.response(n, 200, json.dumps(reply).encode())
        rows, problems = launch.sends(known.directory, read(known.directory/"live-state.json"))
        assert not problems and rows[0]["reservation_usd"] == 1.572864 and rows[0]["estimated_usd"] < 0.001
        checks.append("exact tag and suffix-free terminal ID release only observed peak-uncached usage")

        def blocked(record, service, request):
            try:
                record.before(service, request)
            except pilot.LimitReached:
                return
            raise AssertionError("unexpected dispatch reservation")

        blocked(ledger("ceiling", 29), "ollama", payload)
        blocked(ledger("identity"), "ollama", {"body": {"model": "wrong"}})
        blocked(ledger("fetch-batch"), "tinyfish_fetch", {"body": {"urls": ["a", "b"]}})
        unknown = ledger("unknown")
        unknown.before("tinyfish_fetch", {"body": {"urls": ["https://example.com"]}})
        blocked(unknown, "ollama", payload)
        checks.append("model, spend, unknown-response and one-URL Fetch gates block dispatch")

        def witness(directory, settings, task, case):
            assert settings["caps"] == protocol["caps"]
            assert settings["rounds"] == 3
            assert case["label"] == "" and case.keys() <= {"claim", "claim_date", "label"}
            if task["arm"] == "candidate":
                assert settings["num_predict"] == 6144
                assert settings["config"]["model"]["single_materiality_owner"]
                assert settings["require_independent_provenance_review"]
            else:
                assert settings["num_predict"] == 4096
                assert not settings["require_independent_provenance_review"]
                assert not settings["compiled_ledger_candidate"]

        # Drive the archived worker entry point to the exact run_cell interface.
        for task in pending[:2]:
            identity = launch.fs.task_id(task)
            target = workspace / "attempts" / identity
            target.mkdir(parents=True)
            save(target/"attempt.json", task)
        with patch.object(pilot, "RUN", workspace), patch.object(pilot, "verify", return_value=protocol), patch.object(
            launch.fs, "run_cell", side_effect=witness
        ) as dispatched:
            for name in (*protocol["configurations"].values(), "selected-inference.json"):
                (workspace / name).write_bytes((launch.RUN / name).read_bytes())
            for task in pending[:2]:
                pilot.worker(launch.fs.task_id(task))
            assert dispatched.call_count == 2
        checks.append("archived worker passes frozen arm settings and claim/date only to inference")

    save(launch.RUN/"offline-check.json", {"checks": checks, "live_service_calls": 0,
        "protocol_sha256": launch.digest(launch.RUN/"protocol.json")})
    print("\n".join(checks))


if __name__ == "__main__":
    main()


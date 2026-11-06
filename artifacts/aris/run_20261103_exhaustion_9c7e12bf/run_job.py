"""Run one local job with recorded commands, a deadline and session budget."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]


def main():
    name, *command = sys.argv[1:]
    ledger = WORK / "jobs.jsonl"
    used = sum(json.loads(line)["elapsed_seconds"] for line in ledger.read_text().splitlines()) if ledger.exists() else 0
    remaining = 900 - used
    if remaining <= 0:
        raise SystemExit("Offline budget exhausted")
    if (WORK / f"{name}.job.json").exists() or (WORK / f"{name}.json").exists():
        raise SystemExit("Use a unique job name to preserve prior records")
    env = {**os.environ, "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2", "PYTHONUTF8": "1"}
    start = time.monotonic()
    record = {"name": name, "command": command, "cwd": str(ROOT), "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "timeout_seconds": min(300, remaining), "threads": 2}
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=record["timeout_seconds"])
        stdout, stderr = result.stdout, result.stderr
        record.update(exit_code=result.returncode, timed_out=False)
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        record.update(exit_code=None, timed_out=True)
    record["elapsed_seconds"] = time.monotonic() - start
    (WORK / f"{name}.stdout.log").write_bytes(stdout)
    (WORK / f"{name}.stderr.log").write_bytes(stderr)
    (WORK / f"{name}.job.json").write_text(json.dumps(record, indent=2), encoding="utf8")
    with ledger.open("a", encoding="utf8") as f:
        f.write(json.dumps(record) + "\n")
    print(json.dumps(record, indent=2))
    print(stdout.decode("utf8", errors="replace")[-4000:])
    print(stderr.decode("utf8", errors="replace")[-2000:])
    raise SystemExit(record["exit_code"] if not record["timed_out"] else 124)


if __name__ == "__main__":
    main()

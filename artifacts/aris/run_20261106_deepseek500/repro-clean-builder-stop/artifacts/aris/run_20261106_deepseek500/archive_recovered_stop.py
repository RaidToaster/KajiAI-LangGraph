"""Archive a stop after its only unresolved send is independently reconciled."""
from pathlib import Path
import sys

import builder_paid
import launch
import recover_fetch

RUN = launch.RUN


def main():
    assert not (RUN/"running.lock").exists()
    builder_paid.amendment()
    protocol = launch.verify()
    stop = RUN/"STOP.json"
    value = launch.read(stop)
    attempt = value["attempt"]
    assert attempt in {launch.fs.task_id(t) for t in protocol["schedule"]}
    directory = RUN/"attempts"/attempt
    job = launch.read(directory/"job.json")
    assert value["problems"] == job["problems"]
    recover_fetch.install()
    recovered = launch.read(directory/"job.json")
    if not recovered.get("provider_outcome_reconciled"):
        return 2
    assert not launch.sends(directory,launch.read(directory/"live-state.json"))[1]
    _, _, pending = launch.snapshot(protocol,launch.prior_check())
    status = RUN/"status.json"
    status_archive = RUN/f"status-{attempt}-fetch-reconciled.json"
    stop_archive = RUN/f"stop-{attempt}-fetch-reconciled.json"
    assert not status_archive.exists() and not stop_archive.exists()
    status_archive.write_bytes(status.read_bytes())
    stop.rename(stop_archive)
    print(f"Preserved {attempt} failure; next untouched: {launch.fs.task_id(pending[0]) if pending else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


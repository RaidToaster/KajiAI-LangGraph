"""Resume the frozen schedule on Hobby with zero-rated retrieval and the original quota guard."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import time

import builder_paid
import launch
import recover_fetch

RUN = launch.RUN
read, save, digest = launch.read, launch.save, launch.digest
original_account = launch.account
original_attempt = launch.run_attempt


def amendment(protocol):
    record = read(RUN/"hobby-amendment.json")
    builder_paid.amendment()
    for field, name in (
        ("protocol_sha256", "protocol.json"),
        ("previous_paid_amendment_sha256", "builder-paid-amendment.json"),
        ("launcher_sha256", "hobby.py"),
        ("wrapper_sha256", "run-hobby.ps1"),
        ("supervisor_sha256", "keep-hobby.ps1"),
    ):
        assert record[field] == digest(RUN/name), name
    assert record["quota_windows"] == protocol["quota_windows"]
    assert record["fresh_retrieval_ceiling_usd"] == "0"
    return record


def account(protocol):
    original_account(protocol)
    amendment(protocol)
    assert not (RUN/"PAUSE_REQUESTED.json").exists()
    receipt = read(RUN/"hobby-wallet-current.json")
    assert receipt["amendment_sha256"] == digest(RUN/"hobby-amendment.json")
    assert receipt["currency"] == "USD" and receipt["auto_reload"] == "unconfigured"
    checked = datetime.fromisoformat(receipt["checked_at"]).timestamp()
    assert 0 <= time.time()-checked < 86400
    assert set(receipt["rates"]) == {"search", "fetch"}
    assert all(Decimal(rate) == 0 for rate in receipt["rates"].values())
    return receipt


def run_attempt(task, costs, protocol):
    identity = launch.fs.task_id(task)
    receipt = account(protocol)
    save(RUN/"hobby-next-tariff.json", {
        **receipt, "attempt": identity, "reserved_max_usd": "0", "phase": "hobby",
    })
    rows, problems = original_attempt(task, costs, protocol)
    path = RUN/"attempts"/identity/"builder-tariff.json"
    if not path.exists():
        save(path, read(RUN/"hobby-next-tariff.json"))
    return rows, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--checkpoint", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--worker")
    args = parser.parse_args()
    protocol = launch.verify()
    amendment(protocol)
    recover_fetch.install()
    if args.worker:
        tariff = read(RUN/"hobby-next-tariff.json")
        assert tariff["attempt"] == args.worker
        assert tariff["amendment_sha256"] == digest(RUN/"hobby-amendment.json")
        assert (RUN/"running.lock").read_text(encoding="ascii") == str(os.getppid())
        directory = RUN/"attempts"/args.worker
        save(directory/"builder-tariff.json", tariff)
        launch.account = account
        launch.worker(protocol, args.worker)
        return

    references = launch.prior_check()
    if args.verify or args.checkpoint:
        account(protocol)
        _, retrieval, pending = launch.snapshot(protocol, references)
        until = launch.quota_until(retrieval, protocol)
        if args.checkpoint:
            assert not (RUN/"running.lock").exists() and not (RUN/"STOP.json").exists()
            assert pending and until > time.time()
            launch.checkpoint(launch.fs.task_id(pending[0]), until, 1000-len(pending))
        print(dict(next=launch.fs.task_id(pending[0]) if pending else None,
                   remaining=len(pending), quota_at=datetime.fromtimestamp(until, timezone.utc).isoformat()))
        return

    launch.account = account
    launch.run_attempt = run_attempt
    launch.__file__ = __file__
    launch.launch(protocol, references)


if __name__ == "__main__":
    main()


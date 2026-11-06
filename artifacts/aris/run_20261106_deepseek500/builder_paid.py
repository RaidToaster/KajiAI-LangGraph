"""Apply the authorized Builder retrieval amendment to the frozen coordinator."""
from datetime import datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import time

import launch
import recover_fetch

RUN = launch.RUN
read, save, digest = launch.read, launch.save, launch.digest
EFFECTIVE = datetime.fromisoformat("2026-11-06T04:00:00+00:00").timestamp()
RATE_KEYS = {"tinyfish_search": "search", "tinyfish_fetch": "fetch"}
original_attempt = launch.run_attempt
original_account = launch.account
original_set_status = launch.set_status


class Checkpoint(Exception):
    pass


def amendment():
    record = read(RUN / "builder-paid-amendment.json")
    assert record["parent_protocol_sha256"] == digest(RUN / "protocol.json")
    assert record["builder_launcher_sha256"] == digest(Path(__file__))
    assert record["wrapper_sha256"] == digest(RUN / "run-builder-paid.ps1")
    assert record["wallet_ceiling_usd"] == "12"
    assert record["recovery_overlay_sha256"] == digest(RUN / "recover_fetch.py")
    assert record["previous_builder_amendment_sha256"] == digest(RUN / "builder-amendment.json")
    assert record["carry_unknown_search_sha256"] == digest(RUN / "carry-unknown-search.json")
    assert record["previous_paid_amendment_sha256"] == digest(
        RUN / "builder-paid-before-search-resume/builder-paid-amendment.json")
    assert record["unknown_fetch_policy_sha256"] == digest(RUN / "unknown-fetch-policy.json")
    assert record["previous_fetch_amendment_sha256"] == digest(
        RUN / "builder-paid-before-fetch-carry/builder-paid-amendment.json")
    assert record["dns_policy_sha256"] == digest(RUN / "dns-carry-policy.json")
    assert record["previous_dns_amendment_sha256"] == digest(
        RUN / "builder-paid-before-dns-carry/builder-paid-amendment.json")
    return record


def terms():
    record = read(RUN / "builder-paid-wallet-current.json")
    assert record["amendment_sha256"] == digest(RUN / "builder-paid-amendment.json")
    assert record["currency"] == "USD" and record["auto_reload"] == "unconfigured"
    stamp = datetime.fromisoformat(record["checked_at"]).timestamp()
    assert (stamp < EFFECTIVE) == (time.time() < EFFECTIVE), "Wallet terms must match this side of the tariff transition"
    assert 0 <= time.time() - stamp < 86400, "Wallet receipt expired"
    assert Decimal(record["balance"]) >= 0
    rates = {key: Decimal(value) for key, value in record["rates"].items()}
    assert set(rates) == set(RATE_KEYS.values())
    assert all(v.is_finite() and v >= 0 for v in rates.values())
    if stamp < EFFECTIVE:
        assert all(value == 0 for value in rates.values())
    elif datetime.fromisoformat(record["rates_as_of"]).timestamp() < EFFECTIVE:
        raise RuntimeError("Wallet still returns the pre-transition pricing snapshot")
    return record, rates


def account(protocol):
    original_account(protocol)
    amendment()
    terms()


def stop_at_boundary(task, until, reason):
    launch.set_status("builder_checkpoint", next_untouched=launch.fs.task_id(task),
                      resume_at=datetime.fromtimestamp(until, timezone.utc).isoformat() if until else None,
                      reason=reason)
    print(f"BUILDER_CHECKPOINT {launch.fs.task_id(task)} {reason}", flush=True)
    raise Checkpoint


def reserved_cost(sends, rates):
    return sum((rates[RATE_KEYS[row["service"]]] * row.get("url_attempts", 1)
                for row in sends if row["service"] in RATE_KEYS), Decimal("0"))


def restore_spend():
    # Every started cell needs its tariff snapshot, and every recorded send is charged at most once.
    reservations = {}
    for path in (RUN / "attempts").glob("*/attempt.json"):
        directory = path.parent
        tariff_path = directory / "builder-tariff.json"
        assert tariff_path.exists(), f"Missing tariff snapshot for {directory.name}"
        tariff = read(tariff_path)
        assert tariff["amendment_sha256"] in {
            digest(RUN / "builder-paid-amendment.json"), digest(RUN / "builder-amendment.json"),
            digest(RUN / "builder-paid-before-search-resume/builder-paid-amendment.json"),
            digest(RUN / "builder-paid-before-fetch-carry/builder-paid-amendment.json"),
            digest(RUN / "builder-paid-before-dns-carry/builder-paid-amendment.json")
        }
        rates = {k: Decimal(v) for k, v in tariff["rates"].items()}
        usage = launch.pilot.usage(directory, launch.MODEL)
        reservations[directory.name] = reserved_cost(usage, rates)
    return reservations


def run_attempt(task, costs, protocol):
    if time.time() < EFFECTIVE and time.time()+protocol["max_attempt_seconds"]+10 >= EFFECTIVE:
        stop_at_boundary(task, EFFECTIVE+1, "awaiting effective Builder wallet rates")
    receipt, rates = terms()
    projected = sum(rates[name] * protocol["caps"][service] for service, name in RATE_KEYS.items())
    spend_before = sum(spend.values(), Decimal("0"))
    if spend_before+projected > Decimal(amendment()["wallet_ceiling_usd"]):
        stop_at_boundary(task, None, "next cell's conservative retrieval reservation exceeds the $12 authorized cap")
    # Check the wallet as of this startup. Usage from earlier startup receipts
    # is already reflected in its balance.
    if spend_before-initial_spend+projected > Decimal(receipt["balance"]):
        stop_at_boundary(task, None, "next cell's retrieval reservation exceeds the existing wallet balance")

    identity = launch.fs.task_id(task)
    # The worker is allowed to read a separately staged tariff only after the
    # coordinator owns the run lock and has journaled this exact cell.
    save(RUN / "builder-next-tariff.json", {**receipt, "attempt": identity,
        "reserved_max_usd": str(projected), "prior_total_reserved_usd": str(spend_before)})
    rows, problems = original_attempt(task, costs, protocol)
    path = RUN / "attempts" / identity / "builder-tariff.json"
    if not path.exists():
        save(path, read(RUN / "builder-next-tariff.json"))
    spend[identity] = reserved_cost(rows, rates)
    save(RUN / "builder-spend.json", {"reserved_usd": str(sum(spend.values())),
        "cap_usd": "12", "per_attempt": {k:str(v) for k,v in spend.items()}})
    return rows, problems


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--worker")
    args = parser.parse_args()
    protocol = launch.verify()
    policy = amendment()
    protocol = {**protocol, "quota_windows": policy["quota_windows"]}
    recover_fetch.install()
    if args.verify:
        refs = launch.prior_check()
        account(protocol)
        _, retrieval, pending = launch.snapshot(protocol, refs)
        print(dict(next=launch.fs.task_id(pending[0]) if pending else None,
                   remaining=len(pending), quota_at=datetime.fromtimestamp(
                       launch.quota_until(retrieval, protocol), timezone.utc).isoformat()))
        return
    if args.worker:
        tariff = read(RUN / "builder-next-tariff.json")
        assert tariff["attempt"] == args.worker
        assert tariff["amendment_sha256"] == digest(RUN / "builder-paid-amendment.json")
        assert (RUN / "running.lock").read_text(encoding="ascii") == str(os.getppid())
        directory = RUN / "attempts" / args.worker
        save(directory / "builder-tariff.json", tariff)
        launch.account = account
        launch.worker(protocol, args.worker)
        return
    refs = launch.prior_check()
    account(protocol)
    global spend, initial_spend
    spend = restore_spend()
    initial_spend = sum(spend.values(), Decimal("0"))
    launch.run_attempt = run_attempt
    launch.account = account
    launch.__file__ = __file__
    try:
        launch.launch(protocol, refs)
    except Checkpoint:
        pass


if __name__ == "__main__":
    main()


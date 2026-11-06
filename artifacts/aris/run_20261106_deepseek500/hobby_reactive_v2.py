"""Dispatch only untouched frozen cells, with waits triggered by provider replies."""
import argparse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import os
import time
from urllib.parse import urlsplit
import urllib.request

import hobby
import launch
import recover_fetch

RUN = launch.RUN
read, save, digest = launch.read, launch.save, launch.digest
POLICY = "hobby-reactive-amendment-v2.json"
RETRIEVAL = {"tinyfish_search", "tinyfish_fetch"}
RESET_HEADERS = {"retry-after", "retry-after-ms", "ratelimit-reset", "x-ratelimit-reset"}
OVERLAYS = RUN / "reactive-outcomes"
WALLET = RUN / "hobby-reactive-wallet-v2.json"


def policy(protocol):
    hobby.amendment(protocol)
    record = read(RUN / POLICY)
    assert record["protocol_sha256"] == digest(RUN / "protocol.json")
    assert record["prior_hobby_amendment_sha256"] == digest(RUN / "hobby-amendment.json")
    for name, sha in record["files"].items():
        assert digest(RUN / name) == sha, name
    assert record["zero_rated_only"] and record["local_retrieval_pacing"] is False
    for name, sha in record.get("previous_policies", {}).items():
        assert digest(RUN / name) == sha, name


def valid_policy_hashes():
    return {digest(RUN / POLICY), *read(RUN / POLICY).get("previous_policies", {}).values()}


def refresh_wallet():
    from reconcile_reactive_v2 import NoRedirect

    key = next(line.split("=", 1)[1].strip().strip('"').strip("'")
               for line in (launch.ROOT / ".env").read_text(encoding="utf8").splitlines()
               if line.split("=", 1)[0].strip() == "TINYFISH_API_KEY")
    request = urllib.request.Request("https://agent.tinyfish.ai/v1/wallet", headers={"X-API-Key": key})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=20) as response:
        wallet = json.load(response)
    rates = {}
    for product in ("search", "fetch"):
        meters = [item for item in wallet["rates"]["meters"] if item["label"] == f"TinyFish {product}"]
        assert len(meters) == 1
        rates[product] = str(meters[0]["unit_amount"])
    receipt = {"amendment_sha256": digest(RUN / POLICY), "checked_at": launch.pilot.now(),
               "currency": wallet["currency"], "auto_reload": wallet["auto_reload"]["state"],
               "balance": str(wallet["available_balance"]), "rates_as_of": wallet["rates"]["as_of"], "rates": rates}
    save(RUN / f"hobby-reactive-wallet-{time.time_ns()}.json", receipt)
    save(WALLET, receipt)
    return receipt


def account(protocol, refresh=False):
    launch_account(protocol)
    assert not (RUN / "PAUSE_REQUESTED.json").exists()
    receipt = read(WALLET)
    age = time.time() - timestamp(receipt["checked_at"]).timestamp()
    if refresh and age >= 4*3600:
        try:
            receipt = refresh_wallet()
            age = time.time() - timestamp(receipt["checked_at"]).timestamp()
        except (OSError, ValueError, KeyError) as exc:
            # The prior verified receipt is still valid up to 24 h. Log only
            # the error type and retry this read-only check at the next cell.
            save(RUN / "wallet-refresh-error.json",
                 {"type": type(exc).__name__, "observed_at": launch.pilot.now()})
    assert receipt["amendment_sha256"] == digest(RUN / POLICY)
    assert receipt["currency"] == "USD" and receipt["auto_reload"] == "unconfigured"
    assert set(receipt["rates"]) == {"search", "fetch"}
    assert all(float(rate) == 0 for rate in receipt["rates"].values())
    assert 0 <= age < 86400, "The zero-rate wallet receipt expired."
    return receipt


launch_account = launch.account


def timestamp(value):
    stamp = datetime.fromisoformat(value)
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def retry_at(headers, observed):
    candidates = []
    for name, value in headers.items():
        try:
            amount = float(value)
            if name == "retry-after-ms":
                amount /= 1000
            if name == "x-ratelimit-reset" and amount > 1e12:
                amount /= 1000
            absolute = name.endswith("reset") and amount > 1e9
            candidate = datetime.fromtimestamp(amount, timezone.utc) if absolute else observed + timedelta(seconds=amount)
        except (ValueError, OverflowError, OSError):
            try:
                candidate = parsedate_to_datetime(value)
            except (ValueError, TypeError, OverflowError):
                try:
                    candidate = timestamp(value)
                except (ValueError, TypeError):
                    continue
        if candidate.tzinfo is not None:
            candidates.append(candidate)
    return max(candidates) if candidates else None


def capture_headers(directory, status, headers):
    if status not in {402, 403, 429} and status < 500:
        return
    req = max(directory.glob("request-*.json"))
    values = {k.lower(): v for k, v in headers.items() if k.lower() in RESET_HEADERS}
    save(req.with_name(req.name.replace("request-", "rate-headers-")),
         {"status": status, "headers": values, "observed_at": launch.pilot.now()})


def install_capture(directory):
    # The frozen transports dispatch synchronously. Observe the reply headers
    # without changing the request, body, SDK retry settings or capture limits.
    import httpx
    import httpx2

    for module in (httpx, httpx2):
        original = module.HTTPTransport.handle_request

        def handle(self, request, original=original):
            response = original(self, request)
            capture_headers(directory, response.status_code, response.headers)
            return response

        module.HTTPTransport.handle_request = handle

    class Capture(urllib.request.BaseHandler):
        handler_order = 490

        def http_response(self, request, response):
            if urlsplit(request.full_url).hostname in {
                "api.search.tinyfish.ai", "api.fetch.tinyfish.ai",
            }:
                capture_headers(directory, response.status, response.headers)
            return response

        https_response = http_response

    build = urllib.request.build_opener
    urllib.request.build_opener = lambda *handlers: build(*handlers, Capture())


def overlay(directory):
    path = OVERLAYS / f"{directory.name}.json"
    if directory.parent != RUN / "attempts" or not path.exists():
        return None
    record = read(path)
    assert record["attempt"] == directory.name
    assert record["policy_sha256"] in valid_policy_hashes()
    for name, sha in record["files"].items():
        assert digest(directory / name) == sha, (directory, name)
    return record


def overlay_read(path):
    value = recover_fetch.recover_read(path)
    if path.name == "job.json" and value["operational_stop"] and overlay(path.parent):
        return {**value, "operational_stop": False}
    return value


def overlay_sends(directory, state):
    rows, problems = recover_fetch.recover_sends(directory, state)
    record = overlay(directory) if problems else None
    if record:
        for row in rows:
            outcome = record["outcomes"].get(row["request_id"])
            if outcome:
                problems.remove(f"{row['service']}/{row['request_id']} unresolved or HTTP failure")
                mismatch = f"{row['service']}/{row['request_id']} model or accounting mismatch"
                if mismatch in problems:
                    problems.remove(mismatch)
                row.update(outcome)
                row["reconciliation_receipt"] = f"reactive-outcomes/{directory.name}.json"
    return rows, problems


def classify(directory, row):
    number, service, status = row["request_id"], row["service"], row["status"]
    header_file = directory / f"rate-headers-{number}.json"
    observed = timestamp(row["finished_at"] or row["sent_at"])
    resume = None
    if header_file.exists():
        rate = read(header_file)
        assert status in {None, rate["status"]}
        status = rate["status"]
        observed = timestamp(rate["observed_at"])
        resume = retry_at(rate["headers"], observed)

    error_code = None
    if service in RETRIEVAL and status in {402, 403, 429}:
        body = directory / f"response-{number}.body"
        if body.exists():
            try:
                value = json.loads(body.read_bytes())
                error_code = value["error"]["code"]
            except (ValueError, TypeError, KeyError):
                pass
    daily = status == 402 and error_code == "FREE_ALLOWANCE_EXHAUSTED"
    is_rate = status == 429 or (status == 403 and error_code == "RATE_LIMIT_EXCEEDED") or daily
    if is_rate:
        basis = "response_headers"
        delay = None
        if daily:
            midnight = observed.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            resume = max(resume, midnight) if resume else midnight
            basis = "documented_daily_reset"
        elif resume is None:
            basis = "headerless_provider_rejection_backoff"
            previous = sorted(OVERLAYS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            delay = 60
            if previous:
                prior = read(previous[0])
                if prior.get("resume_at") and observed - timestamp(prior["resume_at"]) < timedelta(minutes=10):
                    delay = min(3600, 2 * (prior.get("fallback_seconds") or 30))
            resume = observed + timedelta(seconds=delay)
        return {"provider_outcome": "RATE_REJECTED", "retry_basis": basis}, resume, delay
    if status in {401, 402, 403} or (status is not None and status < 500 and status != 200):
        return None
    if service in RETRIEVAL:
        from reconcile_reactive_v2 import lookup
        outcome, history_deadline = lookup(directory, row)
        deadlines = [d for d in (resume, history_deadline) if d is not None]
        return outcome, max(deadlines) if deadlines else None, None
    if row.get("transport_error") or row.get("incomplete") or (status is not None and status >= 500):
        # Model usage has no request-matched read-only history in this setup.
        return {"provider_outcome": "UNKNOWN"}, resume, None
    return None


def resolve_stop(directory, problems):
    job = read(directory / "job.json")
    allowed = {"transport failure; no retry"}
    rows = launch.pilot.usage(directory, launch.MODEL)
    outcomes, deadlines, files = {}, [], {"job.json": digest(directory / "job.json")}
    fallback = None
    for row in rows:
        number = row["request_id"]
        problem = f"{row['service']}/{number} unresolved or HTTP failure"
        if problem not in problems:
            continue
        resolution = classify(directory, row)
        if resolution is None:
            return False
        outcome, resume, delay = resolution
        mismatch = f"{service}/{number} model or accounting mismatch" if (service := row["service"]) in {"ollama", "jev"} else None
        if mismatch in problems:
            expected = launch.MODEL if service == "ollama" else "jev-1.13.0"
            invalid_response = row.get("returned_model") and not row.get("model_verified")
            invalid_accounting = row.get("estimated_usd", 0) > (row.get("reservation_usd") or 0)
            if invalid_response or invalid_accounting or row["requested_model"] != expected or not row.get("reservation_usd"):
                return False
            allowed.add(mismatch)
        outcomes[number] = outcome
        if resume:
            deadlines.append(resume)
            allowed.add(f"HTTP {row['status']}; auth/quota/infrastructure failure")
        if row["status"] is not None and row["status"] >= 500:
            allowed.add(f"HTTP {row['status']}; auth/quota/infrastructure failure")
        if delay is not None:
            fallback = delay
        allowed.add(problem)
        for prefix in ("request", "response", "rate-headers", "history"):
            path = directory / f"{prefix}-{number}.json"
            if path.exists():
                files[path.name] = digest(path)
    state = read(directory / "live-state.json")
    if state["stop"] and state["stop"].endswith(" request cap"):
        service = state["stop"].removesuffix(" request cap")
        if state["counts"].get(service) == launch.fs.CAPS.get(service) and service in launch.fs.CAPS:
            allowed.add(state["stop"])
            files["live-state.json"] = digest(directory / "live-state.json")
    if not set(problems) <= allowed or job["problems"] != problems:
        return False
    if not outcomes and "live-state.json" not in files:
        return False
    OVERLAYS.mkdir(exist_ok=True)
    save(OVERLAYS / f"{directory.name}.json",
         {"attempt": directory.name, "policy_sha256": digest(RUN / POLICY),
          "outcomes": outcomes, "files": files,
          "resume_at": max(deadlines).isoformat() if deadlines else None,
          "fallback_seconds": fallback})
    return True


def wait_for_provider(next_cell, accounted):
    deadlines = [timestamp(record["resume_at"]) for path in OVERLAYS.glob("*.json")
                 if (record := read(path))["resume_at"]]
    if not deadlines:
        return
    until = max(deadlines)
    if until.timestamp() > time.time():
        launch.set_status("provider_rate_wait", next_untouched=next_cell, accounted=accounted,
                          resume_at=until.isoformat())
    while until.timestamp() > time.time():
        if (RUN / "PAUSE_REQUESTED.json").exists():
            raise SystemExit(0)
        time.sleep(max(0, min(15, until.timestamp() - time.time())))


def dispatch(protocol, references):
    stage = RUN / "attempts"
    lock = RUN / "running.lock"
    with lock.open("x", encoding="ascii") as stream:
        stream.write(str(os.getpid()))
        stream.flush()
        os.fsync(stream.fileno())
    try:
        stop_path = RUN / "STOP.json"
        if stop_path.exists():
            stop = read(stop_path)
            directory = stage / stop["attempt"]
            if not (directory / "builder-tariff.json").exists():
                raise RuntimeError("The stopped attempt has no recorded tariff.")
            if read(directory / "builder-tariff.json")["amendment_sha256"] not in valid_policy_hashes():
                raise RuntimeError("Inspect the historical operational stop.")
            if not overlay(directory) and not resolve_stop(directory, stop["problems"]):
                raise SystemExit(2)
            stop_path.rename(OVERLAYS / f"{directory.name}.stop")
        costs, retrieval, pending = launch.snapshot(protocol, references)
        for accounted, task in enumerate(pending, 1000-len(pending)):
            identity = launch.fs.task_id(task)
            wait_for_provider(identity, accounted)
            if (RUN / "PAUSE_REQUESTED.json").exists():
                return
            receipt = account(protocol, refresh=True)
            save(RUN / "hobby-reactive-next-tariff.json",
                 {**receipt, "attempt": identity, "reserved_max_usd": "0", "phase": "hobby"})
            rows, problems = launch.run_attempt(task, costs, protocol)
            if problems:
                save(stop_path, {"attempt": identity, "problems": problems, "timestamp": launch.pilot.now()})
                launch.set_status("operational_stop", attempt=identity, accounted=accounted+1, problems=problems)
                directory = stage / identity
                if not resolve_stop(directory, problems):
                    raise SystemExit(2)
                stop_path.rename(OVERLAYS / f"{identity}.stop")
            launch.accumulate(rows, costs, retrieval)
            print(identity, "accounted", accounted+1, flush=True)
        launch.set_status("complete", accounted=1000)
    finally:
        lock.unlink()


def main():
    modes = argparse.ArgumentParser(description=__doc__)
    group = modes.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--worker")
    args = modes.parse_args()
    protocol = launch.verify()
    policy(protocol)
    launch.account = account
    if args.worker:
        tariff = read(RUN / "hobby-reactive-next-tariff.json")
        assert tariff["attempt"] == args.worker and tariff["amendment_sha256"] == digest(RUN / POLICY)
        assert (RUN / "running.lock").read_text(encoding="ascii") == str(os.getppid())
        directory = RUN / "attempts" / args.worker
        save(directory / "builder-tariff.json", tariff)
        install_capture(directory)
        launch.worker(protocol, args.worker)
        return
    launch.read, launch.sends = overlay_read, overlay_sends
    launch.__file__ = __file__
    references = launch.prior_check()
    if args.verify:
        costs, _, pending = launch.snapshot(protocol, references)
        print(dict(accounted=1000-len(pending), next_untouched=launch.fs.task_id(pending[0]) if pending else None,
                   remaining=len(pending), costs=costs))
    else:
        account(protocol, refresh=True)
        dispatch(protocol, references)


if __name__ == "__main__":
    main()


"""Accept only uniquely reconciled terminal TinyFetch records during resume."""
from datetime import datetime, timedelta, timezone

import launch

RUN = launch.RUN
original_read = launch.read
original_sends = launch.sends


def confirmed(directory):
    if directory.parent != RUN / "attempts":
        return {}
    accepted = {}
    for path in sorted(RUN.glob(f"fetch-reconciliation-{directory.name}-*.json")):
        receipt = original_read(path)
        if (receipt["http_status"] != 200 or receipt["has_more"] is not False
            or len(receipt["matching_rows"]) != 1):
            continue
        number = receipt["request_number"]
        request = directory / f"request-{number:03}.json"
        assert launch.digest(request) == receipt["request_sha256"]
        raw = original_read(request)
        assert raw["service"] == "tinyfish_fetch"
        metadata = original_read(directory / f"response-{number:03}.json")
        match = receipt["matching_rows"][0]
        supported_error = (
            metadata.get("error") == "TimeoutError: The read operation timed out"
            or (metadata.get("status") == 200 and
                metadata.get("error") == "RuntimeError: TinyFish HTTP 200; response size 2000001")
        )
        if not supported_error:
            continue
        assert match["request_origin"] == "api" and match["status"] in {"completed", "failed"}
        assert match["url"] in raw["request"]["body"]["urls"]
        assert match["format"] == raw["request"]["body"]["format"]
        stamp = datetime.fromisoformat(match["created_at"])
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        sent = datetime.fromisoformat(raw["timestamp"])
        finished = datetime.fromisoformat(original_read(directory / "job.json")["finished_at"])
        assert sent-timedelta(seconds=2) <= stamp <= finished+timedelta(seconds=120)
        accepted[f"{number:03}"] = (match["status"], path.name)
    return accepted


def carried_search(directory):
    path = RUN / "carry-unknown-search.json"
    if directory.parent != RUN / "attempts" or not path.exists():
        return {}
    record = original_read(path)
    if record["attempt"] != directory.name:
        return {}
    assert record["service"] == "tinyfish_search" and record["provider_outcome"] == "UNKNOWN"
    assert record["no_replay"] and record["reserved_usd"] == "0.005"
    number = record["request_id"]
    request = directory / f"request-{number}.json"
    response = directory / f"response-{number}.json"
    assert launch.digest(request) == record["request_sha256"]
    assert launch.digest(response) == record["response_sha256"]
    assert launch.digest(directory / "job.json") == record["job_sha256"]
    assert original_read(request)["service"] == "tinyfish_search"
    metadata = original_read(response)
    assert "WinError 10054" in metadata["error"] and metadata.get("status") is None
    for name, expected in record["history_receipt_sha256"].items():
        receipt = RUN / name
        assert launch.digest(receipt) == expected
        history = original_read(receipt)
        assert history["request_sha256"] == record["request_sha256"]
        assert history["http_status"] == 200 and history["has_more"] is False and not history["matches"]
        assert any(c["provider_matches"] for c in history["controls"])
    return {number: ("UNKNOWN", path.name)}


def carried_fetch(directory):
    if directory.parent != RUN / "attempts":
        return {}
    root = RUN / "unknown-fetch-carried"
    records = {}
    for path in root.glob(f"{directory.name}-*.json"):
        record = original_read(path)
        number = record["request_id"]
        assert record["policy_sha256"] == launch.digest(RUN / "unknown-fetch-policy.json")
        assert record["attempt"] == directory.name and record["provider_outcome"] == "UNKNOWN"
        request = directory / f"request-{number}.json"
        response = directory / f"response-{number}.json"
        assert launch.digest(request) == record["request_sha256"]
        assert launch.digest(response) == record["response_sha256"]
        assert launch.digest(directory / "job.json") == record["job_sha256"]
        raw = original_read(request)
        metadata = original_read(response)
        assert raw["service"] == "tinyfish_fetch" and len(raw["request"]["body"]["urls"]) == 1
        assert metadata.get("status") is None and metadata["error"] == "TimeoutError: The read operation timed out"
        assert len(record["history_receipt_sha256"]) >= 3
        for name, expected in record["history_receipt_sha256"].items():
            receipt_path = RUN / name
            assert launch.digest(receipt_path) == expected
            receipt = original_read(receipt_path)
            assert receipt["request_sha256"] == record["request_sha256"]
            assert receipt["http_status"] == 200 and receipt["has_more"] is False and not receipt["matching_rows"]
            assert any(c["provider_terminal_matches"] for c in receipt["local_terminal_controls"])
        records[number] = ("UNKNOWN", str(path.relative_to(RUN)))
    return records


def carried_dns(directory):
    if directory.parent != RUN / "attempts":
        return {}
    records = {}
    for path in (RUN / "dns-reservation-carried").glob(f"{directory.name}-*.json"):
        record = original_read(path)
        number = record["request_id"]
        service = record["service"]
        assert service in {"tinyfish_search", "tinyfish_fetch"}
        assert record["attempt"] == directory.name and record["outcome"] == "DNS_RESOLUTION_FAILURE"
        assert record["policy_sha256"] == launch.digest(RUN / "dns-carry-policy.json")
        req = directory / f"request-{number}.json"
        rsp = directory / f"response-{number}.json"
        assert launch.digest(req) == record["request_sha256"]
        assert launch.digest(rsp) == record["response_sha256"]
        assert launch.digest(directory / "job.json") == record["job_sha256"]
        assert original_read(req)["service"] == service
        metadata = original_read(rsp)
        assert metadata.get("status") is None and "getaddrinfo failed" in metadata["error"]
        receipt_path = RUN / record["dns_receipt"]
        assert launch.digest(receipt_path) == record["dns_receipt_sha256"]
        receipt = original_read(receipt_path)
        assert receipt["resolved"] and receipt["attempt"] == directory.name
        assert receipt["host"] == f"api.{service.removeprefix('tinyfish_')}.tinyfish.ai"
        assert datetime.fromisoformat(receipt["checked_at"]) >= datetime.fromisoformat(original_read(directory / "job.json")["finished_at"])
        records[(service,number)] = ("DNS_RESOLUTION_FAILURE", str(path.relative_to(RUN)))
    return records


def recover_read(path):
    value = original_read(path)
    if path.name != "job.json" or value.get("operational_stop") is not True:
        return value
    resolved = confirmed(path.parent)
    allowed = {f"tinyfish_fetch/{number} unresolved or HTTP failure" for number in resolved}
    carried = carried_search(path.parent)
    fetch_carried = carried_fetch(path.parent)
    allowed.update(f"tinyfish_search/{number} unresolved or HTTP failure" for number in carried)
    allowed.update(f"tinyfish_fetch/{number} unresolved or HTTP failure" for number in fetch_carried)
    dns = carried_dns(path.parent)
    allowed.update(f"{service}/{number} unresolved or HTTP failure" for service,number in dns)
    problems = set(value.get("problems", ()))
    if (resolved or carried or fetch_carried or dns) and problems == allowed | {"transport failure; no retry"}:
        return {**value, "operational_stop":False, "provider_outcome_reconciled":bool(resolved), "unknown_reservation_carried":bool(carried or fetch_carried or dns)}
    return value


def recover_sends(directory, state):
    rows, problems = original_sends(directory, state)
    resolved = confirmed(directory) if problems else {}
    carried = carried_search(directory) if problems else {}
    if problems:
        resolved = {**carried_fetch(directory), **resolved}
    dns = carried_dns(directory) if problems else {}
    for row in rows:
        number = row["request_id"]
        records = {"tinyfish_fetch": resolved, "tinyfish_search": carried}.get(row["service"], {})
        resolution = records.get(number) or dns.get((row["service"],number))
        if not resolution:
            continue
        problem = f"{row['service']}/{number} unresolved or HTTP failure"
        if problem in problems:
            problems.remove(problem)
            row["provider_outcome"], row["reconciliation_receipt"] = resolution
    return rows, problems


def install():
    launch.read = recover_read
    launch.sends = recover_sends


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


def recover_read(path):
    value = original_read(path)
    if path.name != "job.json" or value.get("operational_stop") is not True:
        return value
    resolved = confirmed(path.parent)
    allowed = {f"tinyfish_fetch/{number} unresolved or HTTP failure" for number in resolved}
    problems = set(value.get("problems", ()))
    if resolved and problems == allowed | {"transport failure; no retry"}:
        return {**value, "operational_stop":False, "provider_outcome_reconciled":True}
    return value


def recover_sends(directory, state):
    rows, problems = original_sends(directory, state)
    resolved = confirmed(directory) if problems else {}
    for row in rows:
        number = row["request_id"]
        if row["service"] != "tinyfish_fetch" or number not in resolved:
            continue
        problem = f"tinyfish_fetch/{number} unresolved or HTTP failure"
        if problem in problems:
            problems.remove(problem)
            row["provider_outcome"], row["reconciliation_receipt"] = resolved[number]
    return rows, problems


def install():
    launch.read = recover_read
    launch.sends = recover_sends


"""Archive a stop after its only unresolved send is independently reconciled."""
import argparse
import re
import socket
import sys
from urllib.parse import urlsplit

import builder_paid
import launch
import recover_fetch

RUN = launch.RUN


def record_unknown_fetch(attempt, directory, stop, value):
    if len(value["problems"]) != 2 or value["problems"][1] != "transport failure; no retry":
        return False
    match = re.fullmatch(r"tinyfish_fetch/([0-9]{3}) unresolved or HTTP failure", value["problems"][0])
    if not match:
        return False
    number = match.group(1)
    request = directory / f"request-{number}.json"
    response = directory / f"response-{number}.json"
    metadata = launch.read(response)
    if metadata.get("status") is not None or metadata.get("error") != "TimeoutError: The read operation timed out":
        return False
    request_sha = launch.digest(request)
    receipts = {}
    for path in RUN.glob(f"fetch-reconciliation-{attempt}-{number}*.json"):
        receipt = launch.read(path)
        if receipt["matching_rows"]:
            return False
        if (receipt["http_status"] == 200 and receipt["has_more"] is False
            and receipt["request_sha256"] == request_sha
            and any(c["provider_terminal_matches"] for c in receipt["local_terminal_controls"])):
            receipts[path.name] = launch.digest(path)
    if len(receipts) < 3:
        return False
    root = RUN / "unknown-fetch-carried"
    root.mkdir(exist_ok=True)
    path = root / f"{attempt}-{number}.json"
    if not path.exists():
        launch.save(path, {
            "attempt": attempt, "request_id": number, "provider_outcome": "UNKNOWN",
            "policy_sha256": launch.digest(RUN / "unknown-fetch-policy.json"),
            "request_sha256": request_sha, "response_sha256": launch.digest(response),
            "job_sha256": launch.digest(directory / "job.json"), "stop_sha256": launch.digest(stop),
            "history_receipt_sha256": receipts, "recorded_at": launch.pilot.now(),
        })
    return True


def record_dns(attempt, directory, stop, value):
    if len(value["problems"]) != 2 or value["problems"][1] != "transport failure; no retry":
        return False
    match = re.fullmatch(r"(tinyfish_search|tinyfish_fetch)/([0-9]{3}) unresolved or HTTP failure", value["problems"][0])
    if not match:
        return False
    service, number = match.groups()
    request = directory / f"request-{number}.json"
    response = directory / f"response-{number}.json"
    raw = launch.read(request)
    metadata = launch.read(response)
    if metadata.get("status") is not None or "getaddrinfo failed" not in metadata.get("error", ""):
        return False
    host = f"api.{service.removeprefix('tinyfish_')}.tinyfish.ai"
    assert raw["service"] == service and urlsplit(raw["request"]["url"]).hostname == host
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    if not addresses:
        return False
    root = RUN / "dns-reservation-carried"
    root.mkdir(exist_ok=True)
    path = root / f"{attempt}-{number}.json"
    if not path.exists():
        receipt = RUN / f"dns-resolved-{attempt}-{number}.json"
        launch.save(receipt, {"attempt": attempt, "host": host, "resolved": True, "checked_at": launch.pilot.now()})
        launch.save(path, {
            "attempt": attempt, "request_id": number, "service": service, "outcome": "DNS_RESOLUTION_FAILURE",
            "policy_sha256": launch.digest(RUN / "dns-carry-policy.json"),
            "request_sha256": launch.digest(request), "response_sha256": launch.digest(response),
            "job_sha256": launch.digest(directory / "job.json"), "stop_sha256": launch.digest(stop),
            "dns_receipt": receipt.name, "dns_receipt_sha256": launch.digest(receipt),
        })
    return True


def main():
    if (RUN / "PAUSE_REQUESTED.json").exists():
        print("User pause is active; no recovery restart.")
        return 3
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carry-unknown-fetch", action="store_true")
    parser.add_argument("--carry-dns", action="store_true")
    args = parser.parse_args()
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
    if args.carry_unknown_fetch:
        record_unknown_fetch(attempt, directory, stop, value)
    if args.carry_dns:
        record_dns(attempt, directory, stop, value)
    recover_fetch.install()
    recovered = launch.read(directory/"job.json")
    if not (recovered.get("provider_outcome_reconciled") or recovered.get("unknown_reservation_carried")):
        return 2
    assert not launch.sends(directory,launch.read(directory/"live-state.json"))[1]
    _, _, pending = launch.snapshot(protocol,launch.prior_check())
    status = RUN/"status.json"
    category = "fetch-reconciled"
    if recovered.get("unknown_reservation_carried"):
        category = "dns-unknown" if recover_fetch.carried_dns(directory) else "fetch-unknown"
    status_archive = RUN/f"status-{attempt}-{category}.json"
    stop_archive = RUN/f"stop-{attempt}-{category}.json"
    assert not status_archive.exists() and not stop_archive.exists()
    status_archive.write_bytes(status.read_bytes())
    stop.rename(stop_archive)
    print(f"Preserved {attempt} failure; next untouched: {launch.fs.task_id(pending[0]) if pending else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


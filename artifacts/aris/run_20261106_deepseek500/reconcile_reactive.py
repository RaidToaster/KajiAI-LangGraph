"""Use TinyFish GET usage history without replaying any workflow request."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import launch


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def timestamp(value):
    stamp = datetime.fromisoformat(value)
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def lookup(directory, row):
    number = row["request_id"]
    path = directory / f"request-{number}.json"
    request = launch.pilot.read(path)["request"]
    product = row["service"].removeprefix("tinyfish_")
    endpoint = f"https://api.{product}.tinyfish.ai/usage"
    key = next(line.split("=", 1)[1].strip().strip('"').strip("'")
               for line in Path(".env").read_text(encoding="utf8").splitlines()
               if line.split("=", 1)[0].strip() == "TINYFISH_API_KEY")
    sent = timestamp(row["sent_at"])
    lower = sent - timedelta(seconds=2)
    upper = timestamp(launch.pilot.read(directory / "job.json")["finished_at"]) + timedelta(seconds=5)
    query = urlencode({"start_after": (sent-timedelta(minutes=1)).isoformat(),
                       "end_before": upper.isoformat(), "limit": 100})
    lookup_request = Request(f"{endpoint}?{query}", headers={"X-API-Key": key, "Accept": "application/json"})
    if product == "fetch":
        def matches(item):
            return (item.get("url") in request["body"]["urls"] and item.get("format") == request["body"]["format"]
                    and item.get("status") in {"completed", "failed"})
    else:
        expected = parse_qs(urlsplit(request["url"]).query)["query"][0]

        def matches(item):
            return item.get("query") == expected

    receipts = []
    for index in range(2):
        try:
            with build_opener(NoRedirect()).open(lookup_request, timeout=20) as response:
                result = json.load(response)
                found = [item for item in result["items"] if item.get("request_origin", "api") == "api"
                         and matches(item) and lower <= timestamp(item["created_at"]) <= upper]
                receipts.append({"status": response.status, "has_more": result.get("has_more"), "matches": found})
        except (URLError, OSError, ValueError, KeyError) as exc:
            receipts.append({"error_type": type(exc).__name__, "status": getattr(exc, "code", None)})
        receipts[-1]["checked_at"] = launch.pilot.now()
        result = receipts[-1]
        if result.get("has_more") is False and len(result["matches"]) == 1:
            outcome = result["matches"][0].get("status") or "PROVIDER_RECORD_FOUND"
            break
        if index == 0:
            time.sleep(10)
    else:
        outcome = "UNKNOWN"
    launch.save(directory / f"history-{number}.json",
                {"endpoint": endpoint, "request_sha256": launch.digest(path), "outcome": outcome, "lookups": receipts})
    return {"provider_outcome": outcome}

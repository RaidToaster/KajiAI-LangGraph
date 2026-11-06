"""Query read-only TinySearch usage for the reset connection."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

RUN = Path(__file__).resolve().parent
ATTEMPT = "dev-427-deepseek-candidate"
NUMBER = 7


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def stamp(value):
    t = datetime.fromisoformat(value)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def main():
    directory = RUN/"attempts"/ATTEMPT
    request = directory/f"request-{NUMBER:03}.json"
    raw = json.loads(request.read_bytes())
    assert raw["service"] == "tinyfish_search"
    params = parse_qs(urlsplit(raw["request"]["url"]).query)
    requested = params["query"][0]
    key = next(line.split("=",1)[1].strip().strip('"').strip("'")
               for line in Path(".env").read_text(encoding="utf8").splitlines()
               if line.split("=",1)[0].strip() == "TINYFISH_API_KEY")
    sent = stamp(raw["timestamp"])
    begin, end = sent-timedelta(minutes=2), sent+timedelta(minutes=3)
    endpoint = "https://api.search.tinyfish.ai/usage"
    query = urlencode({"start_after":begin.isoformat(),"end_before":end.isoformat(),"limit":100})
    lookup = Request(f"{endpoint}?{query}",headers={"X-API-Key":key,"Accept":"application/json"})
    with build_opener(NoRedirect()).open(lookup,timeout=20) as response:
        status, result = response.status,json.load(response)
    rows = result["items"]
    matches = [r for r in rows if r.get("query") == requested and
               sent-timedelta(seconds=2) <= stamp(r["created_at"]) <= end]
    controls = []
    for path in sorted(directory.glob("request-*.json")):
        if path == request:
            continue
        req = json.loads(path.read_bytes())
        if req["service"] != "tinyfish_search":
            continue
        q = parse_qs(urlsplit(req["request"]["url"]).query)["query"][0]
        controls.append({"request":path.name,"provider_matches":sum(r.get("query")==q for r in rows)})
    receipt = dict(checked_at=datetime.now(timezone.utc).isoformat(),endpoint=endpoint,http_status=status,
        request_sha256=hashlib.sha256(request.read_bytes()).hexdigest(),has_more=result.get("has_more"),
        records=len(rows),matches=matches,controls=controls)
    name = RUN/f"search-reconciliation-{ATTEMPT}-{NUMBER:03}-{datetime.now(timezone.utc):%H%M%S}.json"
    with name.open("x",encoding="utf8") as stream:
        json.dump(receipt,stream,indent=2)
    print(json.dumps(dict(matches=len(matches),records=len(rows),controls=controls,
        statuses=[{k:r[k] for k in ("status","status_code","request_origin") if k in r} for r in matches])))


if __name__ == "__main__":
    main()


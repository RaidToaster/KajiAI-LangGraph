"""Physical-send journal; no retry of an uncertain request, no hidden SDK retries."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from urllib.parse import unquote, urlencode, urlsplit

from kaji_langgraph.incremental.boundary import now, read, save
from kaji_langgraph.jev import JevClient
from kaji_langgraph.llm import OllamaBackend

MODEL = "deepseek-v4.1-flash:cloud"
CAPS = {"ollama": 8, "jev": 12, "search": 2, "fetch": 4}
RATES = {"ollama": [0.30, 1.20], "jev": [0.042, 0], "search": [0, 0], "fetch": [0, 0]}
MAX_REQUEST_BYTES = 65536


def benchmark_source(url, title=""):
    """Data boundary: reject identifiable benchmark mirrors/answer-key repositories."""
    value = unquote(unquote(str(url))).casefold()
    parsed = urlsplit(value)
    host = (parsed.hostname or "").removeprefix("www.")
    if "averitec" in value or "averitec" in str(title).casefold():
        return True
    if host == "huggingface.co" and "/datasets/" in parsed.path:
        return True
    repository = host in {"github.com", "raw.githubusercontent.com", "gitlab.com"}
    dataset_file = parsed.path.endswith(("/dev.json", "/train.json", "/test.json", "/dev.jsonl", "/train.jsonl", "/test.jsonl"))
    return repository and (dataset_file or "/datasets/" in parsed.path)


class ProviderBoundary(RuntimeError):
    pass


class ParseFailure(ValueError):
    pass


def durable_bytes(path, body):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def accounting(directory):
    counts, tokens, costs = Counter(), Counter(), Counter()
    complete, uncertain = True, []
    for path in sorted(directory.glob("request-*.json")):
        request = read(path)
        service = request["service"]
        counts[service] += request["units"]
        response_path = path.with_name(path.name.replace("request-", "response-"))
        response = read(response_path) if response_path.exists() else {}
        if response.get("outcome") != "completed":
            uncertain.append(path.name)
        if service in ("ollama", "jev"):
            inp, out = response.get("input_tokens"), response.get("output_tokens")
            if type(inp) is not int or type(out) is not int:
                complete = False
            else:
                tokens[service] += inp + out
        costs[service] += response.get("estimated_usd", request["reserved_usd"])
    return {"calls": dict(counts), "observed_tokens": dict(tokens),
            "token_usage_complete": complete, "estimated_or_reserved_usd": dict(costs),
            "uncertain_sends": uncertain, "cost_scope": "Peak uncached public rates; not a provider invoice. Unknown usage reserves its bound."}


class Journal:
    def __init__(self, directory: Path, output: Path, deadline: float):
        self.directory, self.output, self.deadline = directory, output, deadline
        previous = accounting(directory)
        self.counts = Counter(previous["calls"])
        self.stopped = bool(previous["uncertain_sends"])

    def halt(self, reason):
        self.stopped = True
        save(self.directory / "provider-stop.json", {"reason": reason, "at": now()})
        raise ProviderBoundary(reason)

    def remaining(self, maximum=120):
        left = self.deadline - time.monotonic()
        if left <= 1:
            self.halt("claim hard deadline")
        return min(maximum, left)

    def reserve(self, service, body, url):
        if self.stopped:
            raise ProviderBoundary("provider dispatch halted")
        self.remaining()
        raw = json.dumps(body or {}, ensure_ascii=False).encode()
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("Request exceeds frozen 65536-byte input ceiling")
        units = len(body["urls"]) if service == "fetch" else 1
        if self.counts[service] + units > CAPS[service]:
            raise ValueError(f"{service} physical send ceiling")
        if service in {"ollama", "jev"}:
            expected = MODEL if service == "ollama" else "jev-1.13.0"
            if body.get("model") != expected:
                self.halt("unexpected requested model ID")
        input_bound = 2 * len(raw) + 4096
        output_bound = 8192 if service == "ollama" else 0
        reserve = (input_bound * RATES[service][0] + output_bound * RATES[service][1]) / 1e6
        receipt = read(self.output / "resource-release.json")
        try:
            expires = datetime.fromisoformat(receipt["valid_until"])
            if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
                self.halt("resource/headroom receipt expired")
        except (KeyError, ValueError, TypeError):
            self.halt("resource/headroom receipt expiry unavailable")
        # One coordinator holds the run lock. All attempts, including failures,
        # count against the same spend reservation, not just successful outputs.
        spent = sum(accounting(d)["estimated_or_reserved_usd"].get(service, 0)
                    for d in (self.output / "attempts").iterdir() if d.is_dir())
        if spent + reserve > receipt["caps_usd"][service]:
            self.halt(f"{service} resource reservation cap")
        n = len(list(self.directory.glob("request-*.json"))) + 1
        save(self.directory / f"request-{n:03}.json", {"service": service, "units": units,
            "number": n, "at": now(), "url": url, "body": body,
            "reserved_usd": reserve, "outcome": "reserved_outcome_unknown"})
        self.counts[service] += units
        return n

    def response(self, n, status, body):
        durable_bytes(self.directory / f"response-{n:03}.body", body)
        request = read(self.directory / f"request-{n:03}.json")
        service = request["service"]
        meta = {"status": status, "at": now(), "bytes": len(body), "outcome": "completed",
                "input_tokens": None, "output_tokens": None, "estimated_usd": request["reserved_usd"]}
        reason = None
        if status in {401, 402, 403, 429} or status >= 500:
            reason = f"{service} HTTP {status}: auth/quota/infrastructure boundary"
        if status == 200 and service in {"ollama", "jev"}:
            try:
                value = json.loads(body)
                model = value.get("model")
                allowed = {MODEL, MODEL.removesuffix(":cloud")} if service == "ollama" else {"jev-1.13.0"}
                meta["returned_model"] = model
                if model not in allowed:
                    reason = "unexpected returned model ID"
                if service == "ollama":
                    meta.update(input_tokens=value.get("prompt_eval_count"), output_tokens=value.get("eval_count"),
                                done=value.get("done"), done_reason=value.get("done_reason"))
                    if not value.get("done") or value.get("error"):
                        reason = "unresolved Ollama response"
                    if type(value.get("eval_count")) is int and value["eval_count"] > 8192:
                        reason = "provider exceeded requested output ceiling"
                else:
                    usage = value.get("usage", {})
                    meta.update(input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"))
                inp, out = meta["input_tokens"], meta["output_tokens"]
                if type(inp) is int and type(out) is int:
                    if inp < 0 or out < 0:
                        reason = "invalid negative token counters"
                    else:
                        meta["estimated_usd"] = (inp * RATES[service][0] + out * RATES[service][1]) / 1e6
                    if meta["estimated_usd"] > request["reserved_usd"]:
                        reason = "observed usage exceeded spend reservation"
            except (ValueError, TypeError, AttributeError):
                reason = "unresolved provider response"
        save(self.directory / f"response-{n:03}.json", meta)
        if reason:
            self.halt(reason)

    def unknown(self, n, exc):
        path = self.directory / f"response-{n:03}.json"
        if path.exists() and read(path).get("outcome") == "completed":
            return  # A completed HTTP error/parse failure is not an unknown send.
        save(path, {"outcome": "unknown", "error_type": type(exc).__name__, "at": now()})
        if not self.stopped:
            self.halt("uncertain send outcome; reconcile before any dispatch")


def jev_transport(journal):
    import httpx2

    class Transport(httpx2.BaseTransport):
        def __init__(self):
            self.inner = httpx2.HTTPTransport(retries=0)

        def handle_request(self, request):
            if request.url.host != "api.typesafe.ai" or request.url.scheme != "https":
                journal.halt("unexpected Jev destination")
            payload = json.loads(request.content)
            n = journal.reserve("jev", payload, str(request.url.copy_with(query=None)))
            try:
                response = self.inner.handle_request(request)
                body = response.read()
                if len(body) > 2000000:
                    journal.halt("Jev response capture ceiling")
                journal.response(n, response.status_code, body)
                return response
            except ProviderBoundary:
                raise
            except Exception as exc:
                journal.unknown(n, exc)
                raise

        def close(self):
            self.inner.close()

    return Transport()


class JournalJev(JevClient):
    def __init__(self, journal):
        super().__init__(model="jev-1.13.0")
        self.journal = journal

    def _ask(self, state, questions, *, timeout):
        from typesafe_sdk import Choice, Noul, RetryPolicy, TypeSafeClient
        typed = {name: Choice(instructions=q["instructions"], criteria=q["criteria"])
                 if q["type"] == "choice" else Noul(instructions=q["instructions"], criteria=q.get("criteria"))
                 for name, q in questions.items()}
        with TypeSafeClient(api_key=os.environ["TYPESAFE_API_KEY"], model=self.model,
                           base_url="https://api.typesafe.ai", retry=RetryPolicy(max_retries=0),
                           transport=jev_transport(self.journal)) as client:
            response = client.system_one(state=state, questions=typed, timeout=self.journal.remaining(timeout))
        answers = {name: answer.model_dump() for name, answer in response.answers.items()}
        if set(answers) != set(questions):
            raise ValueError("Incomplete Jev answers")
        inp, out = response.usage.input_tokens, response.usage.output_tokens
        return answers, inp + out if type(inp) is int and type(out) is int else None


class Providers:
    def __init__(self, journal, base_url):
        self.journal, self.base_url = journal, base_url.rstrip("/")
        self.jev = JournalJev(journal)

    def remaining(self, maximum=120):
        return self.journal.remaining(maximum)

    def request(self, service, url, body=None):
        import httpx
        parsed = urlsplit(url)
        if service == "ollama":
            if parsed.hostname not in {"localhost", "127.0.0.1"} or parsed.path != "/api/chat":
                self.journal.halt("Ollama must use the existing local cloud relay")
        elif parsed.scheme != "https" or parsed.hostname != {
                "search": "api.search.tinyfish.ai", "fetch": "api.fetch.tinyfish.ai"}[service]:
            self.journal.halt("unexpected retrieval destination")
        n = self.journal.reserve(service, body, url)
        headers = {"X-API-Key": os.environ["TINYFISH_API_KEY"]} if service != "ollama" else {}
        try:
            with httpx.Client(follow_redirects=False, trust_env=False, timeout=self.remaining()) as client:
                response = client.request("GET" if body is None else "POST", url, json=body, headers=headers)
            if len(response.content) > 2000000:
                self.journal.halt("response capture ceiling exceeded")
            self.journal.response(n, response.status_code, response.content)
            response.raise_for_status()
            return response.json()
        except ProviderBoundary:
            raise
        except Exception as exc:
            self.journal.unknown(n, exc)
            raise

    def structured(self, schema, prompt, stage):
        schema_json = schema.model_json_schema()
        text = (f"{prompt}\n\nReturn ONLY one JSON object matching this JSON Schema. "
            "Do not use Markdown fences or explanatory text. The first character must "
            f"be '{{' and the last must be '}}'.\nJSON Schema:\n{json.dumps(schema_json)}")
        def send(message, format_value):
            value = self.request("ollama", self.base_url + "/api/chat", {
                "model": MODEL, "messages": [{"role": "user", "content": message}],
                "stream": False, "format": format_value,
                "options": {"temperature": 0, "num_predict": 8192}})
            return value.get("message", {}).get("content", "")
        raw = send(text, "json")
        try:
            parsed = OllamaBackend._parse_json(schema, raw)
        except ValueError:
            repair = ("Convert the draft below into ONLY valid JSON matching the supplied schema. "
                "Preserve only statements supported by the draft; do not invent evidence.\n"
                f"JSON Schema:\n{json.dumps(schema_json)}\nDraft:\n{raw}")
            raw = send(repair, schema_json)
            try:
                parsed = OllamaBackend._parse_json(schema, raw)
            except ValueError as exc:
                raise ParseFailure(f"{stage} schema failed after one counted repair") from exc
        save(self.journal.directory / f"parsed-{stage}.json", parsed.model_dump())
        return parsed

    def search(self, query):
        value = self.request("search", "https://api.search.tinyfish.ai?" + urlencode({"query": query}))
        if not isinstance(value.get("results"), list):
            raise ValueError("Search response missing results")
        results = [x for x in value["results"][:5] if isinstance(x, dict)]
        rejected = [x for x in results if benchmark_source(x.get("url") or x.get("href") or "", x.get("title", ""))]
        if rejected:
            path = self.journal.directory / "source-boundary-rejections.json"
            previous = read(path) if path.exists() else []
            save(path, previous + [{"at": now(), "url": item.get("url") or item.get("href"),
                "reason": "Identifiable benchmark mirror/answer-key source excluded before inference"} for item in rejected])
        return [x for x in results if not benchmark_source(x.get("url") or x.get("href") or "", x.get("title", ""))]

    def fetch(self, url):
        parsed = urlsplit(url)
        if benchmark_source(url):
            return "", None, "benchmark-source URL rejected before Fetch dispatch"
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return "", None, "invalid HTTP(S) search-result URL"
        value = self.request("fetch", "https://api.fetch.tinyfish.ai", {
            "urls": [url], "format": "markdown", "ttl": 0,
            "per_url_timeout_ms": int(self.remaining(30) * 1000)})
        pages = value.get("results", [])
        if pages and isinstance(pages[0].get("text"), str):
            return pages[0]["text"][:20000], None, None
        return "", None, "TinyFetch returned no page text"

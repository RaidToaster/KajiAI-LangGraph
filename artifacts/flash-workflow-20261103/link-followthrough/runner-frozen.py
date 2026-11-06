"""Fetch and journal the frozen development-only outbound link shortlist."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx

from flash_study import THREADS, digest, read, recorded_retrieval_sends, retrieval_pause_until, save
from runtime_pilot import Ledger, load_keys, transport


def prepare(root):
    shortlist = root.parent / "link-probe/shortlist-offline.json"
    cases = read(shortlist)["cases"]
    schedule = [
        {"id": f"{case}-{rank}", "case": case, "url": url}
        for case, row in cases.items()
        for rank, url in enumerate(row["shortlist"], 1)
    ]
    root.mkdir(exist_ok=False)
    save(root / "protocol.json", {
        "schedule": schedule, "shortlist_sha256": digest(shortlist),
        "runner_sha256": digest(Path(__file__)),
        "screen": "At least two distinct claims gain a readable, directly material passage at the claim's event scope, absent from the corresponding saved evidence. This is an availability screen; matched Fetch slot utility and acceptance are separate.",
        "scope": "One free TinyFish Fetch per listed public URL. No Search, inference, link recursion or retries.",
    })


def worker(root):
    protocol = read(root / "protocol.json")
    if (protocol["runner_sha256"] != digest(Path(__file__))
            or protocol["shortlist_sha256"] != digest(root.parent / "link-probe/shortlist-offline.json")):
        raise ValueError("Frozen inputs changed")
    load_keys()
    sends = recorded_retrieval_sends(root.parent)
    for task in protocol["schedule"]:
        directory = root / task["id"]
        if directory.exists():
            if not (directory / "result.json").is_file():
                raise SystemExit(f"Unresolved started cell: {directory}")
            continue
        now = time.time()
        if retrieval_pause_until(sends, {"tinyfish_fetch": [[60, 150], [86400, 1000]]}, now) > now:
            raise SystemExit("Wait for free Fetch window")
        directory.mkdir()
        save(directory / "attempt.json", {**task, "protocol_sha256": digest(root / "protocol.json")})
        save(directory / "live-state.json", {"counts": {"tinyfish_fetch": 0}, "deadline": now + 35, "stop": None})
        ledger = Ledger(directory, {"caps": {"tinyfish_fetch": 1}})
        ledger.task = task["id"]
        with httpx.Client(transport=transport(httpx, ledger, "tinyfish_fetch"), timeout=27,
                          trust_env=False, follow_redirects=False) as client:
            reply = client.post("https://api.fetch.tinyfish.ai",
                                headers={"X-API-Key": os.environ["TINYFISH_API_KEY"]},
                                json={"urls": [task["url"]], "format": "markdown", "ttl": 0,
                                      "per_url_timeout_ms": 20000})
            reply.raise_for_status()
        value = reply.json()
        if read(directory / "live-state.json")["stop"]:
            raise SystemExit(f"Provider stop: {directory}")
        pages = value["results"]
        page = pages[0] if pages else {}
        if page and page["url"] != task["url"]:
            raise ValueError("Fetch returned an unexpected requested URL")
        text = page.get("text") or ""
        save(directory / "result.json", {
            "final_url": page.get("final_url"), "published_date": page.get("published_date"),
            "title": page.get("title"), "characters": len(text),
            "text_sha256": hashlib.sha256(text.encode()).hexdigest() if text else None,
            "errors": value["errors"],
        })
        send = read(directory / "request-001.json")
        sends.append({"service": "tinyfish_fetch", "sent_at": send["timestamp"]})
        print(task["id"], len(text), page.get("final_url"), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.prepare:
        prepare(args.root)
    elif args.worker:
        worker(args.root)
    else:
        lock = args.root / "running.lock"
        with lock.open("x", encoding="utf-8") as handle:
            print(os.getpid(), file=handle)
        try:
            subprocess.run([sys.executable, __file__, str(args.root), "--worker"],
                           env={**os.environ, **THREADS, "PYTHONUTF8": "1"}, timeout=300, check=True)
        finally:
            lock.unlink()

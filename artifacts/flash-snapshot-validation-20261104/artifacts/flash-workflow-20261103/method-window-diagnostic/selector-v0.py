"""Offline diagnostic: retain explicit replication methods in compact packets.

This does not modify the runtime selector or re-score a completed attempt. The
anchor case is development evidence; the output is not a prospective result.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re

from flash_study import MODELS, attempt_path, digest, read, save
from kaji_langgraph.llm import _compact_records
from kaji_langgraph.study_analysis import replay_sources


# Deliberately narrow: a mere quote, shared dataset, or survey is not an
# independent replication. These cues select text, never grant independence.
METHOD = re.compile(r"\b(?:replicat\w*|recomput\w*|independent\s+(?:calculat\w*|analys\w*|verif\w*))", re.I)


def method_window(text: str, claim: str) -> str | None:
    words = list(re.finditer(r"\S+", text))
    terms = set(re.findall(r"\w{3,}", claim.casefold()))
    candidates = []
    for cue in METHOD.finditer(text):
        index = next(i for i, word in enumerate(words) if word.end() > cue.start())
        start = max(0, index - 16)
        stop = min(len(words), start + 72)
        window = text[words[start].start():words[stop - 1].end()]
        candidates.append((len(METHOD.findall(window)),
                           len(terms.intersection(re.findall(r"\w{3,}", window.casefold()))),
                           -start, window))
    return max(candidates)[-1] if candidates else None


def select(claim, sources):
    original, lookup = _compact_records(claim, sources)
    records = deepcopy(original)
    full = {s.url: s for s in sources}
    for record in records:
        passage = method_window(full[record["url"]].retrieved_text, claim)
        if passage and passage not in record["passages"].values():
            record["passages"]["P2"] = passage
    return original, records


def run(root):
    protocol = read(root / "revision-8/development.json")
    cases = read(Path(protocol["cases"]))
    rows = []
    for task in protocol["schedule"]:
        if task["arm"] != "candidate":
            continue
        directory = attempt_path(root / "revision-8", "development", protocol, task)
        if not (directory / "result.json").is_file():
            continue
        result = read(directory / "result.json")["result"]
        requests = []
        for path in sorted(directory.glob("request-*.json")):
            request = read(path)
            if request["service"] != "ollama":
                continue
            prompt = request["request"]["body"]["messages"][-1]["content"]
            if "Retrieved records:\n" in prompt:
                saved, _ = json.JSONDecoder().raw_decode(prompt.split("Retrieved records:\n", 1)[1])
                requests.append((path, saved))
        assert len(requests) == len(result["research_history"])
        for trace, (request, saved) in zip(result["research_history"], requests):
            sources = replay_sources(result, trace)
            original, candidate = select(cases[task["case"]]["claim"], sources)
            assert original == saved, f"Cannot reconstruct sent packet: {request}"
            changed = []
            full = {s.url: s.retrieved_text for s in sources}
            for old, new in zip(original, candidate):
                assert old["passages"]["P1"] == new["passages"]["P1"]
                for passage in new["passages"].values():
                    assert passage in full[new["url"]] and len(passage.split()) <= 72
                assert len(new["passages"]) <= 2
                if old != new:
                    changed.append({"url": new["url"], "id": new["id"],
                                    "old_passages": old["passages"], "new_passages": new["passages"]})
            rows.append({**task, "round": trace["round_number"],
                         "request": request.as_posix(), "request_sha256": digest(request),
                         "original_reconstructed": True, "changed_sources": changed,
                         "original_records": original, "candidate_records": candidate})
    return {"scope": "Post hoc development-only packet diagnostic; no live calls, labels or acceptance gains.",
            "method": "Preserve P1; reserve P2 only when an explicit replication/recomputation cue exists. At most two contiguous 72-word windows per source; same source ordering and selection.",
            "guards": "Cues select passages only; scientific independence, dates and verdict support still require unchanged semantic audit.",
            "packets": rows,
            "packet_count": len(rows),
            "changed_packet_count": sum(bool(row["changed_sources"]) for row in rows),
            "changed_source_count": sum(len(row["changed_sources"]) for row in rows)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    output = args.root / "method-window-diagnostic"
    output.mkdir(exist_ok=True)
    report = run(args.root)
    save(output / "replay.json", report)
    print({key: value for key, value in report.items() if key != "packets"})

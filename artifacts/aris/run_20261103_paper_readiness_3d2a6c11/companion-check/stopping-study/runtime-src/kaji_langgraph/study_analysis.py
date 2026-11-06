"""Offline study analysis, uncertainty, policy replay and a human-audit worksheet."""
from __future__ import annotations

import csv
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import re
from urllib.parse import urlsplit

from kaji_langgraph.config import effective_policy
from kaji_langgraph.evaluation import ABSTAIN, classification_metrics, load_dataset, prediction_label, summarize
from kaji_langgraph.gate import evidence_gaps
from kaji_langgraph.graph import _citation_key
from kaji_langgraph.models import EvidenceAssessment, SourceRecord


def source_host(url: str) -> str:
    """Compare original source hosts, including Wayback-wrapped gold URLs."""
    parsed = urlsplit(url)
    if parsed.hostname == "web.archive.org":
        archived = re.match(r"/web/[^/]+/(https?://.+)", parsed.path)
        if archived:
            parsed = urlsplit(archived.group(1))
    return (parsed.hostname or "").removeprefix("www.")


def wilson(correct: int, n: int) -> list[float] | None:
    if not n:
        return None
    z = 1.959963984540054
    p = correct / n
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/(1 + z*z/n)
    return [max(0.0, center-half), min(1.0, center+half)]


def scored(gold: list[str], labels: list[str]) -> dict:
    metrics = classification_metrics(gold, labels)
    correct = sum(g == p for g, p in zip(gold, labels))
    covered = sum(p != ABSTAIN for p in labels)
    metrics["accuracy_ci95"] = wilson(correct, len(gold))
    metrics["coverage_ci95"] = wilson(covered, len(gold))
    metrics["selective_accuracy_ci95"] = wilson(correct, covered)
    return metrics


def paired_accuracy(gold: list[str], a: list[str], b: list[str], seed=20261009) -> dict:
    if not gold:
        return {"n": 0, "delta_b_minus_a": None, "ci95": None}
    differences = [int(y == g)-int(x == g) for g, x, y in zip(gold, a, b)]
    rng = random.Random(seed)
    boot = sorted(sum(rng.choices(differences, k=len(differences)))/len(differences)
                  for _ in range(2000))
    return {"n": len(gold), "delta_b_minus_a": sum(differences)/len(differences),
            "ci95": [boot[49], boot[1949]]}


def replay_sources(result: dict, trace: dict) -> list[SourceRecord]:
    records = {(s["url"], s["content_hash"]): SourceRecord.model_validate(s)
               for s in result["retrieval_ledger"]}
    return [records[tuple(key)] for key in trace["usable_source_keys"]]


def semantic_pass(result: dict, trace: dict, threshold: float) -> bool:
    sources = {s.url: s for s in replay_sources(result, trace)}
    reviews = {r["key"]: r for r in result["jev_audit"].get("citations", [])
               if r["round"] == trace["round_number"]}
    for item in trace["assessment"]["evidence"]:
        for url in item["source_urls"]:
            source = sources.get(url)
            quote = item["quotes"].get(url, "")
            if source is None or not quote or quote not in source.retrieved_text:
                return False
            review = reviews.get(_citation_key(item["finding"], url, quote, source.content_hash))
            if not review or review["relation"] != "supports" or review["confidence"] < threshold:
                return False
    return bool(trace["assessment"]["evidence"])


RULE_PREFIXES = {
    "without_high_confidence": ("Evidence confidence remains below High.",),
    "without_exact_quotes": ("Each citation needs an exact quote",),
    "without_host_diversity": ("Find relevant evidence from at least two source hosts.",),
    "without_duplicate_check": ("Some cited hosts repeat substantially similar text;",),
    "without_independence_flag": ("Establish source independence;",),
    "without_assertion_coverage": ("Resolve and cite the assertion:",),
    "without_counterevidence_flag": ("Search for evidence against",),
    "without_peer_review_flag": ("This domain requires peer-reviewed evidence.",),
}


def policy_names() -> list[str]:
    return ["structural_only", "full_policy", "first_round_prediction", "first_round_verified",
            *(f"semantic_threshold_{t:.2f}" for t in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]),
            *RULE_PREFIXES]


def replay_labels(row: dict, config: dict) -> dict[str, str]:
    result = row["result"]
    history = result["research_history"]
    if not history:
        if row["accepted_label"] != ABSTAIN:
            raise ValueError("Accepted result has no research history")
        return dict.fromkeys(policy_names(), ABSTAIN)
    if any(not trace.get("assessment") for trace in history):
        raise ValueError(f"Claim {row['claim_id']} is missing the assessment required for replay")
    trace = history[-1]
    assessment = EvidenceAssessment.model_validate(trace["assessment"])
    sources = replay_sources(result, trace)
    policy = effective_policy(config, result["domain"])
    structural = evidence_gaps(assessment, result["assertions"], sources, policy)
    if structural != trace["structural_gaps"]:
        raise ValueError(f"Structural replay diverged on claim {row['claim_id']}")
    proposed = prediction_label(assessment.proposed_verdict)
    decisive = assessment.proposed_verdict in {"TRUE", "FALSE", "CONFLICTING", "MISLEADING"}
    labels = {"structural_only": proposed if decisive and not structural else ABSTAIN,
              "full_policy": row["accepted_label"],
              "first_round_prediction": prediction_label(history[0]["assessment"]["proposed_verdict"])}
    first = history[0]
    first_pass = not first["structural_gaps"] and not first["semantic_gaps"] and not first["fatal_error"]
    labels["first_round_verified"] = labels["first_round_prediction"] if first_pass else ABSTAIN
    for threshold in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
        labels[f"semantic_threshold_{threshold:.2f}"] = proposed if (
            decisive and not structural and semantic_pass(result, trace, threshold)) else ABSTAIN
    for name, prefixes in RULE_PREFIXES.items():
        remaining = [gap for gap in structural if not gap.startswith(prefixes)]
        labels[name] = proposed if decisive and not remaining and not trace["semantic_gaps"] and not trace["fatal_error"] else ABSTAIN
    return labels


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def percent(value):
    return "N/A" if value is None else f"{100*value:.1f}%"


def human_audit(rows: list[dict], output: Path) -> None:
    rng = random.Random(20261009)
    selected = []
    for accepted in [True, False]:
        group = [r for r in rows if (r["accepted_label"] != ABSTAIN) == accepted
                 and r["result"]["research_history"]
                 and r["result"]["research_history"][-1]["assessment"]["evidence"]]
        rng.shuffle(group)
        selected.extend(group[:50])
    rng.shuffle(selected)
    fields = ["audit_id", "claim", "finding", "url", "quote", "context",
              "human_supports_finding", "human_source_credibility", "human_notes"]
    key = []
    with (output / "human-citation-audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(selected):
            result = row["result"]
            trace = result["research_history"][-1]
            sources = {s.url: s for s in replay_sources(result, trace)}
            for finding_index, item in enumerate(trace["assessment"]["evidence"]):
                for url_index, url in enumerate(item["source_urls"]):
                    quote = item["quotes"].get(url, "")
                    text = sources[url].retrieved_text if url in sources else ""
                    offset = text.find(quote) if quote else -1
                    context = text[max(0, offset-1200):offset+len(quote)+1200] if offset >= 0 else text[:2400]
                    audit_id = f"audit-{index:03d}-{finding_index}-{url_index}"
                    writer.writerow({"audit_id": audit_id, "claim": result["claim"],
                                     "finding": item["finding"], "url": url,
                                     "quote": quote, "context": context})
                    key.append({"audit_id": audit_id, "claim_id": row["claim_id"],
                                "accepted": row["accepted_label"] != ABSTAIN,
                                "gold_label": row["gold_label"]})
    (output / "human-audit-key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")


def analyze(output: Path) -> dict:
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    full = read_rows(output / "full" / "results.jsonl")
    closed = read_rows(output / "closed_book" / "results.jsonl")
    expected = set(manifest["claim_ids"])
    if len(full) != len(expected) or len(closed) != len(expected) or {r["claim_id"] for r in full} != expected or {r["claim_id"] for r in closed} != expected:
        raise ValueError("Final analysis requires both complete, matching conditions")
    full.sort(key=lambda r: r["claim_id"])
    closed.sort(key=lambda r: r["claim_id"])
    gold = [r["gold_label"] for r in full]
    raw = [r["predicted_label"] for r in full]
    baseline = [r["predicted_label"] for r in closed]
    end_to_end = [ABSTAIN if r["result"]["verification_status"] == "execution_error" else r["predicted_label"] for r in full]
    policies = [replay_labels(r, manifest["config"]) for r in full]
    metrics = {"full_predictions": scored(gold, raw), "full_failure_inclusive": scored(gold, end_to_end),
               "closed_book_predictions": scored(gold, baseline)}
    for name in policies[0]:
        metrics[name] = scored(gold, [p[name] for p in policies])
    majority = Counter(gold).most_common(1)[0][0]
    metrics["majority_baseline"] = scored(gold, [majority]*len(gold))
    comparisons = {"full_minus_closed_book": paired_accuracy(gold, baseline, raw),
                   "full_minus_first_round": paired_accuracy(gold, [p["first_round_prediction"] for p in policies], raw)}
    citations = Counter()
    relation_counts = Counter()
    for row in full:
        result = row["result"]
        if not result["research_history"]:
            continue
        trace = result["research_history"][-1]
        sources = {s.url: s for s in replay_sources(result, trace)}
        reviews = {r["key"]:r for r in result["jev_audit"].get("citations",[]) if r["round"] == trace["round_number"]}
        for item in trace["assessment"]["evidence"]:
            for url in item["source_urls"]:
                citations["total"] += 1
                source = sources.get(url); quote = item["quotes"].get(url, "")
                if source and quote and quote in source.retrieved_text:
                    citations["exact_quote"] += 1
                    review=reviews.get(_citation_key(item["finding"],url,quote,source.content_hash))
                    if review:
                        citations["reviewed"] += 1
                        relation_counts[review["relation"]] += 1
                        if review["relation"] != "supports":
                            citations["exact_quote_but_jev_does_not_support"] += 1
                        elif review["confidence"] < manifest["config"]["jev"]["citation_min_confidence"]:
                            citations["exact_quote_but_jev_uncertain"] += 1
    dataset_path = output / "dataset-snapshot.json"
    if hashlib.sha256(dataset_path.read_bytes()).hexdigest() != manifest["dataset_sha256"]:
        raise ValueError("Archived dataset does not match study manifest")
    dataset = load_dataset(dataset_path)
    exposure = []
    for row in full:
        gold_host=source_host(dataset[row["claim_id"]].get("fact_checking_article", ""))
        history = row["result"]["research_history"]
        cited={url for e in history[-1]["assessment"]["evidence"] for url in e["source_urls"]} if history else set()
        exposed=bool(gold_host and any(source_host(url)==gold_host for url in cited))
        exposure.append(exposed)
    payload = {"complete": True, "n": len(full), "scope": manifest["scope"],
               "metrics": metrics, "paired_accuracy_comparisons": comparisons,
               "full_execution": summarize(full), "closed_book_execution": summarize(closed),
               "citations": dict(citations), "jev_relations": dict(relation_counts),
               "same_host_as_gold_fact_check_cited": sum(exposure),
               "exposure_caveat": "Archive wrappers are unwrapped before hostname comparison. Host match is an imperfect audit proxy, not a complete contamination detector",
               "human_audit_performed": False}
    (output / "study-metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with (output / "policy-replay.csv").open("w", newline="", encoding="utf-8") as handle:
        writer=csv.writer(handle); writer.writerow(["claim_id","gold_label",*policies[0]])
        for row, policy in zip(full,policies):
            writer.writerow([row["claim_id"],row["gold_label"],*policy.values()])
    human_audit(full,output)
    lines=["# Completed LangGraph computational evaluation", "", f"Claims per live condition: {len(full)}.", "",
           "Development-set, contemporary open-web results; local label metrics, not the official AVeriTeC evidence score.", "",
           "| Condition | Accuracy | Macro F1 | Coverage | Accuracy among covered outputs |", "|---|---:|---:|---:|---:|"]
    for name,m in metrics.items():
        lines.append(f"| {name} | {percent(m['accuracy'])} | {m['macro_f1']:.3f} | {percent(m['coverage'])} | {percent(m['selective_accuracy'])} |")
    lines.extend(["", "## Interpretation boundaries", "",
                  "- Model-only control has no verification gate; use its prediction metrics.",
                  "- Structural-only, rule-removal and threshold results replay the SAME final assessments and evidence. They measure acceptance policy, not complete alternative workflows.",
                  "- First-round results truncate the same saved live trace. They isolate additional research on that trace rather than rerunning changing web searches.",
                  "- NEI remains a factual prediction but is outside decisive acceptance; accepted NEI recall is zero by design.",
                  "- Full predictions preserve model assessments even if a later service fails. Failure-inclusive metrics count those operational failures as abstentions.",
                  "- Threshold curves are descriptive development analyses, not independently validated optimal thresholds.",
                  "- Confidence intervals and paired accuracy bootstrap use claims as units. API/model/search drift is not captured by these intervals.",
                  "- Jev citation judgments are automated measurements, not human ground truth. Human audit fields remain blank.",
                  "- Published fact checks and later documents can be retrieved; no historical cutoff was enforced.",
                  "", "## Citation checks", "",
                  f"Final-assessment citations: {citations['total']}; exact quotations: {citations['exact_quote']}; Jev-reviewed: {citations['reviewed']}.",
                  f"Exact quotations whose Jev review did not support the finding: {citations['exact_quote_but_jev_does_not_support']}; uncertain support: {citations['exact_quote_but_jev_uncertain']}.",
                  f"Claims citing the same host as their dataset fact-check article: {sum(exposure)}/{len(full)} (proxy only).",
                  "", "## Paired accuracy differences", "", "```json", json.dumps(comparisons,indent=2), "```", "",
                  "## Artifacts", "", "- study-metrics.json: metrics, Wilson intervals, paired bootstrap, execution and citation diagnostics.",
                  "- policy-replay.csv: per-claim policy decisions.", "- human-citation-audit.csv: blinded worksheet, with unfilled human judgments.",
                  "- human-audit-key.json: keep separate from human reviewers.", "- source-snapshot.zip and manifest.json: frozen source and run settings."])
    (output / "RESULTS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    analyze(parser.parse_args().output)

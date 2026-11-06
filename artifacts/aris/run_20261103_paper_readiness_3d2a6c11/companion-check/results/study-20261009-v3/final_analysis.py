"""Validate and extend complete-study analysis without modifying frozen inference."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from kaji_langgraph.evaluation import ABSTAIN, load_dataset
from kaji_langgraph.study_analysis import paired_accuracy, read_rows, replay_labels, scored

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
status = json.loads((ROOT / "status.json").read_text(encoding="utf-8"))
assert status["complete"] and not status["halted"], "Finish the frozen live study first"
full = sorted(read_rows(ROOT / "full/results.jsonl"), key=lambda r: r["claim_id"])
control = sorted(read_rows(ROOT / "closed_book/results.jsonl"), key=lambda r: r["claim_id"])
expected = set(manifest["claim_ids"])
for rows in [full, control]:
    assert len(rows) == len(expected) == 500
    assert {r["claim_id"] for r in rows} == expected
assert all(f["claim_id"] == c["claim_id"] and f["gold_label"] == c["gold_label"] for f, c in zip(full, control))
dataset_path = ROOT / "dataset-snapshot.json"
assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == manifest["dataset_sha256"]
dataset = load_dataset(dataset_path)
assert all(row["gold_label"] == dataset[row["claim_id"]]["label"] for row in full)
assert all((r["result"]["verification_status"] == "verified") == (r["accepted_label"] != ABSTAIN) for r in full)
metrics_path = ROOT / "study-metrics.json"
original_path = ROOT / "study-metrics-original.json"
if not original_path.exists():
    original_path.write_bytes(metrics_path.read_bytes())
payload = json.loads(original_path.read_text(encoding="utf-8"))
assert payload["complete"] and payload["n"] == 500
diagnostics = json.loads((ROOT / "diagnostics.json").read_text(encoding="utf-8"))
assert diagnostics["complete"] and diagnostics["paired_n"] == 500
policies = {r["claim_id"]: replay_labels(r, manifest["config"]) for r in full}
assert all(policies[r["claim_id"]]["semantic_threshold_0.80"] == r["accepted_label"] for r in full), "Threshold replay must reproduce live acceptance"
gold = [r["gold_label"] for r in full]
assert scored(gold, [r["predicted_label"] for r in full]) == payload["metrics"]["full_predictions"]
assert scored(gold, [r["accepted_label"] for r in full]) == payload["metrics"]["full_policy"]
assert scored(gold, [r["predicted_label"] for r in control]) == payload["metrics"]["closed_book_predictions"]

def host(url):
    parsed = urlsplit(url)
    if parsed.hostname == "web.archive.org":
        archived = re.match(r"/web/[^/]+/(https?://.+)", parsed.path)
        if archived:
            parsed = urlsplit(archived.group(1))
    return (parsed.hostname or "").removeprefix("www.")

assert host("https://web.archive.org/web/20201130144023id_/https://www.example.com/a") == "example.com"
exposure = {}
for row in full:
    history = row["result"]["research_history"]
    cited = {u for e in history[-1]["assessment"]["evidence"] for u in e["source_urls"]} if history else set()
    gold_host = host(dataset[row["claim_id"]].get("fact_checking_article", ""))
    exposure[row["claim_id"]] = bool(gold_host and any(host(u) == gold_host for u in cited))
groups = {}
for exposed in [True, False]:
    subset = [(f, c) for f, c in zip(full, control) if exposure[f["claim_id"]] == exposed]
    ys = [f["gold_label"] for f, c in subset]
    groups["host_match" if exposed else "no_host_match"] = {
        "n": len(subset),
        "full": scored(ys, [f["predicted_label"] for f, c in subset]),
        "model_only": scored(ys, [c["predicted_label"] for f, c in subset]),
        "caveat": "Post hoc descriptive grouping; absence of a host match does not establish no exposure or no contamination.",
    }
nonfatal = [r for r in full if r["result"]["verification_status"] != "execution_error"]
matched_nonfatal = [(f, c) for f, c in zip(full, control)
                    if all(r["result"]["verification_status"] != "execution_error" for r in (f, c))]
payload["runtime_incidents"] = json.loads((ROOT / "runtime-incidents.json").read_text(encoding="utf-8"))
correction_path = ROOT / "analysis-correction.json"
if correction_path.exists():
    payload["analysis_correction"] = json.loads(correction_path.read_text(encoding="utf-8"))
payload["paired_accuracy_comparisons"]["nonfatal_full_minus_closed_book"] = paired_accuracy(
    [f["gold_label"] for f, c in matched_nonfatal],
    [c["predicted_label"] for f, c in matched_nonfatal],
    [f["predicted_label"] for f, c in matched_nonfatal])
payload["paired_accuracy_comparisons"]["first_round_minus_closed_book"] = paired_accuracy(
    gold, [r["predicted_label"] for r in control],
    [policies[r["claim_id"]]["first_round_prediction"] for r in full])
payload["paired_accuracy_comparisons"]["nonfatal_full_minus_first_round"] = paired_accuracy(
    [r["gold_label"] for r in nonfatal],
    [policies[r["claim_id"]]["first_round_prediction"] for r in nonfatal],
    [r["predicted_label"] for r in nonfatal])
structural = [r for r in full if policies[r["claim_id"]]["structural_only"] != ABSTAIN]
removed = [r for r in structural if r["accepted_label"] == ABSTAIN]
payload.update({
    "same_host_as_gold_fact_check_cited": sum(exposure.values()),
    "exposure_caveat": "Wayback archive wrappers are unwrapped before hostname comparison. Host equality is only an exposure proxy, not proof of exact-article leakage; unmatched hosts do not establish contamination-free evaluation.",
    "descriptive_exposure_groups": groups,
    "gold_distribution": dict(Counter(gold)),
    "accepted_label_distribution": dict(Counter(r["accepted_label"] for r in full if r["accepted_label"] != ABSTAIN)),
    "semantic_gate_removed": {"total": len(removed), "correct_labels": sum(r["predicted_label"] == r["gold_label"] for r in removed), "wrong_labels": sum(r["predicted_label"] != r["gold_label"] for r in removed)},
    "diagnostics": diagnostics,
    "execution_errors": {condition: [{"claim_id": r["claim_id"], "errors": r["result"]["errors"]} for r in rows if r["result"]["verification_status"] == "execution_error"] for condition, rows in [("full", full), ("model_only", control)]},
    "analysis_provenance": {
        "revision": "Complete-study postprocessing with archive-aware host audit",
        "original_metrics_sha256": hashlib.sha256(original_path.read_bytes()).hexdigest(),
        "analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "frozen_inference_source_sha256": manifest["code_sha256"],
        "dataset_sha256": manifest["dataset_sha256"],
        "full_results_sha256": hashlib.sha256((ROOT / "full/results.jsonl").read_bytes()).hexdigest(),
        "model_only_results_sha256": hashlib.sha256((ROOT / "closed_book/results.jsonl").read_bytes()).hexdigest(),
        "completed_at": status["updated_at"],
        "note": "Corrects only the postprocessing host audit and adds diagnostics. No inference records, labels, gates, frozen source, or settings changed. Original computed metrics are preserved separately.",
    },
})
with (ROOT / "per-claim-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
    fields = ["claim_id", "claim", "gold", "model_only", "raw_prediction", "accepted_label", "verification_status", "rounds", "searches", "fetches", "observed_tokens", "elapsed_seconds", "fact_check_host_match", *next(iter(policies.values()))]
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for f, c in zip(full, control):
        result = f["result"]
        writer.writerow(dict(claim_id=f["claim_id"], claim=result["claim"], gold=f["gold_label"], model_only=c["predicted_label"], raw_prediction=f["predicted_label"], accepted_label=f["accepted_label"], verification_status=result["verification_status"], rounds=len(result["research_history"]), searches=result["budget"]["search_calls"], fetches=result["budget"]["scrapes"], observed_tokens=result["budget"]["tokens_used"], elapsed_seconds=result["elapsed_seconds"], fact_check_host_match=exposure[f["claim_id"]], **policies[f["claim_id"]]))
audit_key = json.loads((ROOT / "human-audit-key.json").read_text(encoding="utf-8"))
accepted_audit = {r["claim_id"] for r in audit_key if r["accepted"]}
rejected_audit = {r["claim_id"] for r in audit_key if not r["accepted"]}
payload["human_audit_sample"] = {"citation_rows": len(audit_key), "accepted_claims": len(accepted_audit), "rejected_claims": len(rejected_audit), "annotation_status": "Blank worksheet; independent human validation has not been performed"}
metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def pct(value):
    return "undefined" if value is None else f"{100*value:.1f}%"

def ci(bounds):
    return "undefined" if bounds is None else f"{pct(bounds[0])} to {pct(bounds[1])}"

m = payload["metrics"]
paired = payload["paired_accuracy_comparisons"]
lines = ["# Completed KajiAI-LangGraph evaluation", "", "**Complete: 500 full-workflow attempts and 500 model-only attempts on the same 500 AVeriTeC development claims.**", "", "Failed attempts remain in the denominator. No different-source exploratory runs were pooled. These are local label-only results with contemporary web access, not official AVeriTeC evidence scores.", "", "| Condition | Accuracy (95% Wilson interval) | Macro F1 | Coverage | Accuracy among covered outputs |", "|---|---:|---:|---:|---:|"]
for name in ["majority_baseline", "closed_book_predictions", "first_round_prediction", "full_predictions", "full_failure_inclusive", "structural_only", "full_policy"]:
    value = m[name]
    lines.append(f"| {name} | {pct(value['accuracy'])} ({ci(value['accuracy_ci95'])}) | {value['macro_f1']:.3f} | {pct(value['coverage'])} | {pct(value['selective_accuracy'])} |")
diff = paired["full_minus_closed_book"]
extra = paired["full_minus_first_round"]
nf = paired["nonfatal_full_minus_first_round"]
gate = m["full_policy"]
d = diagnostics["extra_research"]
lines += ["", f"Paired workflow-minus-control accuracy: {100*diff['delta_b_minus_a']:.2f} percentage points; 95% paired bootstrap interval {100*diff['ci95'][0]:.2f} to {100*diff['ci95'][1]:.2f}; exact two-sided McNemar p={diagnostics['accuracy_mcnemar_exact_two_sided_p']:.8g}.", "", f"Accepted-label accuracy interval: {ci(gate['selective_accuracy_ci95'])}; coverage interval: {ci(gate['coverage_ci95'])}. Accepted label counts: {json.dumps(payload['accepted_label_distribution'])}. Jev removed {len(removed)} structurally accepted outputs: {payload['semantic_gate_removed']['wrong_labels']} wrong and {payload['semantic_gate_removed']['correct_labels']} correct labels.", "", f"Saved final-minus-first accuracy: {100*extra['delta_b_minus_a']:.2f} percentage points (95% bootstrap {100*extra['ci95'][0]:.2f} to {100*extra['ci95'][1]:.2f}); on {len(nonfatal)} nonfatal trajectories: {100*nf['delta_b_minus_a']:.2f} ({100*nf['ci95'][0]:.2f} to {100*nf['ci95'][1]:.2f}). This is trajectory truncation, not a separately run one-round experiment.", "", f"Additional research: {d['predictions_changed']} changed predictions, {d['wrong_to_correct']} wrong-to-correct, {d['correct_to_wrong']} correct-to-wrong; {d['extra_rounds']} extra rounds, {d['extra_rounds_without_new_sources']} without new ledger records; {d['searches_after_first_round']} extra searches, {d['fetches_after_first_round']} extra fetch attempts, {d['observed_tokens_after_first_round']:,} extra observed tokens.", "", "## Operational and citation measurements", ""]
for field in ["full_execution", "closed_book_execution", "citations", "jev_relations", "human_audit_sample"]:
    lines += [f"### {field}", "", "```json", json.dumps(payload[field], indent=2), "```", ""]
clean = paired["nonfatal_full_minus_closed_book"]
lines += [f"Nonfatal matched-pair sensitivity: n={clean['n']}, workflow-minus-control {100*clean['delta_b_minus_a']:.2f} percentage points, 95% paired bootstrap {100*clean['ci95'][0]:.2f} to {100*clean['ci95'][1]:.2f}. This excludes operational failures post hoc; the primary denominator remains 500.", "", "The resumed study also encountered cloud concurrent-slot timeouts and two pending control requests were interrupted by restarting the task-owned local Ollama daemon. All these failed attempts remain recorded. See runtime-incidents.json for recovery details; inference settings and source were unchanged.", ""]
lines += [f"Archive-aware host audit: {sum(exposure.values())}/500 claims cite a host matching the gold fact-check article's host. This descriptive proxy does not prove exact-article exposure or exclude other exposure routes. The previous postprocessing missed Wayback-wrapped gold URLs; original metrics are preserved in study-metrics-original.json.", "", "| Descriptive host group | Claims | Full prediction accuracy | Model-only accuracy |", "|---|---:|---:|---:|"]
for name, group in groups.items():
    lines.append(f"| {name} | {group['n']} | {pct(group['full']['accuracy'])} | {pct(group['model_only']['accuracy'])} |")
lines += ["", "Groups are defined post hoc by workflow citations, not randomized conditions. An unmatched host does not establish no exposure, so this is not a contamination-free score or causal ablation.", "", "## Interpretation limits", "", "- This is a reused development split with current web access and no historical evidence cutoff, not a pristine held-out evaluation.", "- The control comparison measures the combined prompting/retrieval/review workflow, not LangGraph's causal advantage over another framework.", "- Policy and threshold variants replay identical evidence and assessments; they are not independent live ablations or validated optimal thresholds.", "- NEI is excluded from decisive acceptance by design; accepted NEI recall is zero.", "- Jev confidence and support relations are automated judgments, not human ground truth. The human audit remains unannotated.", "- Reported tokens aggregate providers and are incomplete; they do not yield an exact billed cost.", "- Claim-level intervals do not account for provider drift, current-web changes, correlated topics or resumption across a quota interruption.", "", "## Reproducibility and outputs", "", "study-metrics.json contains complete metrics and corrected host-audit provenance. per-claim-results.csv contains all 500 matched predictions and policy decisions. human-citation-audit.csv is blinded; keep human-audit-key.json separate from annotators. Manifest, source archive, dataset snapshot and JSONL outputs preserve the evaluated version.", "", f"Frozen inference hash: {manifest['code_sha256']}. Dataset hash: {manifest['dataset_sha256']}.", ""]
original_report = ROOT / "RESULTS-original.md"
if not original_report.exists():
    original_report.write_bytes((ROOT / "RESULTS.md").read_bytes())
(ROOT / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"complete": True, "n": len(full), "full_accuracy": m["full_predictions"]["accuracy"], "control_accuracy": m["closed_book_predictions"]["accuracy"], "gate_coverage": gate["coverage"], "gate_selective_accuracy": gate["selective_accuracy"], "host_exposure": sum(exposure.values()), "human_audit": payload["human_audit_sample"]}, indent=2))

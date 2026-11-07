"""Scoring-only utilities; never imported by inference workers."""
from __future__ import annotations

from collections import Counter
import math
import random

from kaji_langgraph.evaluation import classification_metrics, prediction_label
from kaji_langgraph.study_analysis import wilson


def metrics(gold, predictions):
    result = classification_metrics(gold, predictions)
    result["accuracy_ci95_wilson"] = wilson(sum(g == p for g, p in zip(gold, predictions)), len(gold))
    return result


def paired(gold, initial, final, seed=20261107):
    deltas = [int(f == g) - int(i == g) for g, i, f in zip(gold, initial, final)]
    gain, loss = deltas.count(1), deltas.count(-1)
    n = len(deltas)
    rng = random.Random(seed)
    samples = sorted(sum(rng.choices(deltas, k=n)) / n for _ in range(10000)) if n else []
    discordant = gain + loss
    exact = min(1.0, 2 * sum(math.comb(discordant, i) for i in range(min(gain, loss) + 1)) / 2**discordant) if discordant else 1.0
    return {"n": n, "initial_wrong_final_correct": gain, "initial_correct_final_wrong": loss,
            "accuracy_difference": sum(deltas) / n if n else None,
            "bootstrap_ci95": [samples[249], samples[9749]] if n else None,
            "bootstrap_seed": seed, "bootstrap_resamples": 10000,
            "exact_mcnemar_two_sided_p": exact}


def calibration(rows):
    categories = {}
    for category in ("Low", "Medium", "High", "missing"):
        selected = [r for r in rows if (r["initial"] or {}).get("confidence", "missing") == category]
        correct = sum(prediction_label((r["initial"] or {}).get("proposed_verdict")) == r["gold_label"] for r in selected)
        categories[category] = {"n": len(selected), "correct": correct,
            "accuracy": correct / len(selected) if selected else None,
            "accuracy_ci95": wilson(correct, len(selected))}
    medium = categories["Medium"]["accuracy"]
    return {"n": len(rows), "by_confidence": categories,
            "routing_rule": "low_medium" if medium is None or medium < 0.8 else "low",
            "criterion": "Predeclared: research Medium if its calibration accuracy is <0.80 or category absent; always research Low.",
            "limitation": "Self-reported confidence reliability on 30 claims; not an estimate of research treatment effect."}


def _sum_resources(rows, key):
    out = {"calls": Counter(), "observed_tokens": Counter(), "estimated_or_reserved_usd": Counter(),
           "token_usage_complete": True, "elapsed_seconds": 0}
    for r in rows:
        account = r.get(key, {})
        for name in ("calls", "observed_tokens", "estimated_or_reserved_usd"):
            out[name].update(account.get(name, {}))
        out["token_usage_complete"] &= account.get("token_usage_complete", False)
        out["elapsed_seconds"] += r.get("elapsed_seconds", 0) if key == "accounting" else r.get("initial_elapsed_seconds", 0)
    return {k: dict(v) if isinstance(v, Counter) else v for k, v in out.items()}


def compare(rows, rule):
    from kaji_langgraph.incremental.method import route
    gold = [r["gold_label"] for r in rows]
    initial = [prediction_label((r["initial"] or {}).get("proposed_verdict")) for r in rows]
    result = {"n": len(rows), "model_only": metrics(gold, initial),
              "physical_resources": _sum_resources(rows, "accounting"), "candidates": {}}
    for name, candidate_rule in (("A", "all"), ("B", rule)):
        routed = [route(r["initial"], candidate_rule) for r in rows]
        predictions = [prediction_label(r["final_label"]) if yes else start
                       for r, yes, start in zip(rows, routed, initial)]
        accepted = [yes and r.get("evidence_accepted", False) for r, yes in zip(rows, routed)]
        accepted_correct = sum(a and p == g for a, p, g in zip(accepted, predictions, gold))
        policy_rows = [{**r, "policy_account": r.get("deployed_accounting", r.get("accounting", {})) if yes else r.get("initial_accounting", {}),
                        "elapsed_seconds": r.get("policy_elapsed_seconds", r.get("elapsed_seconds", 0)) if yes else r.get("initial_elapsed_seconds", 0)}
                       for r, yes in zip(rows, routed)]
        # Resource accumulator uses policy wall latency, not physical shared cost.
        resources = _sum_resources(policy_rows, "policy_account")
        resources["elapsed_seconds"] = sum(r["elapsed_seconds"] for r in policy_rows)
        groups = {}
        for confidence in ("Low", "Medium", "High", "missing"):
            indices = [i for i, r in enumerate(rows) if (r["initial"] or {}).get("confidence", "missing") == confidence]
            groups[confidence] = {"metrics": metrics([gold[i] for i in indices], [predictions[i] for i in indices]),
                "n_researched": sum(routed[i] for i in indices)}
        failures = Counter()
        for row, yes in zip(rows, routed):
            if yes or row["initial"] is None:
                for error in row.get("errors", []):
                    key = ("parse" if any(t in error for t in ("ParseFailure", "ValidationError", "schema")) else
                           "timeout" if "timeout" in error.casefold() else
                           "retrieval" if any(t in error.casefold() for t in ("search", "fetch", "retrieval")) else
                           "provider" if any(t in error for t in ("ProviderBoundary", "HTTP", "Connection")) else "other")
                    failures[key] += 1
        result["candidates"][name] = {
            "rule": candidate_rule, "metrics": metrics(gold, predictions), "paired": paired(gold, initial, predictions),
            "research_rate": sum(routed) / len(rows) if rows else 0,
            "skip_rate": sum(bool(r["initial"]) and not yes for r, yes in zip(rows, routed)) / len(rows) if rows else 0,
            "update_frequency": sum(a != b for a, b in zip(initial, predictions)) / len(rows) if rows else 0,
            "update_reasons": dict(Counter(r["decision_reason"] for r, yes in zip(rows, routed) if yes)),
            "acceptance_coverage": sum(accepted) / len(rows) if rows else 0,
            "accepted_n": sum(accepted), "accepted_accuracy": accepted_correct / sum(accepted) if any(accepted) else None,
            "execution_failures": sum(not r["initial"] for r in rows),
            "research_failures": sum(yes and r["research_status"] == "operational_fallback" for r, yes in zip(rows, routed)),
            "failure_error_categories": dict(failures),
            "by_confidence": groups, "policy_resources": resources,
            "paired_changes": [{"opaque_id": r["opaque_id"], "initial": a, "final": b,
                "initial_correct": a == g, "final_correct": b == g, "research": yes,
                "reason": r["decision_reason"] if yes else "research skipped"}
                for r, a, b, g, yes in zip(rows, initial, predictions, gold, routed)]}
    def rank(name):
        c = result["candidates"][name]
        calls = c["policy_resources"]["calls"]
        return (c["metrics"]["accuracy"], c["metrics"]["macro_f1"], -calls.get("ollama", 0),
                -calls.get("fetch", 0), -calls.get("search", 0), name == "B")
    best = max(("A", "B"), key=rank)
    improved = result["candidates"][best]["metrics"]["accuracy"] > result["model_only"]["accuracy"]
    result.update(best_research_candidate=best, promoted=improved,
                  selected_deployment=best if improved else "model_only",
                  selection_scope=f"{len(rows)}-claim development selection; no protected-final feedback")
    return result


def final_comparison(rows, rule):
    # Only the frozen challenger has actually run in final. Do not fabricate A
    # results for claims skipped by frozen B.
    if rule == "all":
        report = compare(rows, "low_medium")
        report["candidates"] = {"frozen": report["candidates"]["A"]}
    else:
        report = compare(rows, rule)
        report["candidates"] = {"frozen": report["candidates"]["B"]}
    for k in ("best_research_candidate", "promoted", "selected_deployment", "selection_scope"):
        report.pop(k, None)
    report["scope"] = "Once-only protected 100-claim shared-initial evaluation on a previously exposed development dataset"
    return report

"""One declared fixed-evidence development revision; no new target data."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import shutil

from kaji_langgraph.incremental.boundary import read, save, sha, now


def combine_accounts(*accounts):
    result = {"calls": Counter(), "observed_tokens": Counter(),
              "estimated_or_reserved_usd": Counter(), "token_usage_complete": True, "uncertain_sends": []}
    for account in accounts:
        for key in ("calls", "observed_tokens", "estimated_or_reserved_usd"):
            result[key].update(account.get(key, {}))
        result["token_usage_complete"] &= account.get("token_usage_complete", False)
        result["uncertain_sends"].extend(account.get("uncertain_sends", []))
    return {key: dict(value) if isinstance(value, Counter) else value for key, value in result.items()}


def retrieval_prefix(directory):
    """Deployed work reused from parent; unused first-pass judgments stay physical only."""
    from kaji_langgraph.incremental.method import PLAN_PROMPT, ASSESS_PROMPT, ADJUDICATE_PROMPT
    retained = []
    first_plan = first_assessment = None
    last_stage = None
    for path in sorted(directory.glob("request-*.json")):
        req = read(path)
        body = req["body"] or {}
        service = req["service"]
        stage = "retrieval"
        if service == "ollama":
            content = body["messages"][0]["content"]
            if content.startswith("Convert the draft below"):
                stage = last_stage
            elif content.startswith(PLAN_PROMPT):
                stage = "plan"
                first_plan = first_plan or req["at"]
            elif content.startswith(ASSESS_PROMPT):
                stage = "assessment"
                first_assessment = first_assessment or req["at"]
            elif content.startswith(ADJUDICATE_PROMPT):
                stage = "adjudicator"
            elif content.startswith("Assess the factual claim using your existing knowledge only."):
                stage = "initial"
            else:
                raise ValueError("Unknown parent Ollama role; do not guess policy cost")
            last_stage = stage
        elif service == "jev":
            state = body.get("state", {})
            stage = "citations" if isinstance(state, dict) and "citations" in state else "retrieval"
        if stage in {"assessment", "adjudicator", "citations"}:
            continue
        response = read(path.with_name(path.name.replace("request-", "response-")))
        if response.get("outcome") != "completed":
            raise ValueError("Cannot reuse a prefix with an uncertain send")
        inp, output = response.get("input_tokens"), response.get("output_tokens")
        complete = service not in {"ollama", "jev"} or (type(inp) is int and type(output) is int)
        retained.append({"calls": {service: req["units"]},
            "observed_tokens": {service: inp + output} if complete and service in {"ollama", "jev"} else {},
            "token_usage_complete": complete,
            "estimated_or_reserved_usd": {service: response.get("estimated_usd", req["reserved_usd"])}})
    initial = read(directory / "initial.json")
    retrieval_seconds = ((datetime.fromisoformat(first_assessment) - datetime.fromisoformat(first_plan)).total_seconds()
                         if first_assessment and first_plan else 0)
    return combine_accounts(*retained), initial["elapsed_seconds"] + max(0, retrieval_seconds)


def prepare_revision(root: Path, parent: Path, output: Path):
    from kaji_langgraph.incremental import runner
    from kaji_langgraph.incremental.providers import accounting
    if (output / "split.json").exists() or (output / "implementation.json").exists():
        raise ValueError("Revision preparation is immutable")
    if not (output / "PROTOCOL.md").exists():
        raise ValueError("Declare revision protocol first")
    # Verify both complete parent commitments before reusing any predictions.
    runner.scored_rows(parent, "calibration")
    runner.scored_rows(parent, "selection")
    original = read(parent / "split.json")
    if (parent / "final").exists() or (parent / "final-commit.json").exists():
        raise ValueError("Revision must precede any protected-final inference")
    parent_rel = str(parent.relative_to(root)).replace("\\", "/")
    receipt = {"at": now(), "parent_run": str(parent), "parent_relative": parent_rel,
        "authorization": "Original user request permits one documented research/adjudication revision after the first selection comparison; same-selection reuse is exploratory.",
        "calibration_ids": original["calibration_ids"], "selection_ids": original["selection_ids"],
        "parent_commitments": {name: sha(parent / name) for name in
            ("split.json", "calibration-commit.json", "selection-commit.json", "calibration-report.json", "selection-report.json", "implementation.json")},
        "permitted_reuse": "Exact calibration initials and selection initials/retrieval; no parent judgment, gold or correctness reaches revised inference.",
        "revision_number": 1, "maximum_method_revisions": 1, "exploratory_selection": True}
    save(output / "development-reuse.json", receipt)
    split = deepcopy(original)
    shutil.copy2(parent / "exposure-audit.json", output / "exposure-audit.json")
    shutil.copy2(parent / "protocol-amendment.json", output / "protocol-amendment.json")
    split.update(protocol_sha256=sha(output / "PROTOCOL.md"),
                 development_reuse_sha256=sha(output / "development-reuse.json"))
    save(output / "split.json", split)
    save(output / "method-settings.json", {"material_resolution": True})
    inherited = Counter()
    for directory in (parent / "attempts").iterdir():
        if directory.is_dir():
            inherited.update(accounting(directory)["estimated_or_reserved_usd"])
    release = read(parent / "resource-release.json")
    release.update(at=now(), split_sha256=sha(output / "split.json"),
        caps_usd={name: value - inherited.get(name, 0) for name, value in release["caps_usd"].items()},
        parent_physical_consumption_usd=dict(inherited), parent_release_sha256=sha(parent / "resource-release.json"),
        basis=release["basis"] + " Same allocation, reduced by ALL parent physical consumption before the single revision.")
    if any(value < 0 for value in release["caps_usd"].values()):
        raise ValueError("Parent already exceeded shared resource allocation")
    save(output / "resource-release.json", release)
    # Freeze revised code/config/prompts before any revised provider call.
    runner.snapshot(root, output)
    empty = {"calls": {}, "observed_tokens": {}, "estimated_or_reserved_usd": {},
             "token_usage_complete": True, "uncertain_sends": []}
    for phase in ("calibration", "selection"):
        mapping = read(parent / f"{phase}-mapping.json")
        save(output / f"{phase}-mapping.json", mapping)
        (output / phase).mkdir(exist_ok=True)
        for opaque in mapping:
            shutil.copy2(parent / phase / f"{opaque}-input.json", output / phase / f"{opaque}-input.json")
            if phase == "calibration":
                prior = parent / "attempts" / f"{phase}-{opaque}" / "result.json"
                row = read(prior)
                row.update(accounting=empty, elapsed_seconds=0,
                    reused_calibration_from=str(prior), reused_calibration_sha256=sha(prior))
                target = output / "attempts" / f"{phase}-{opaque}"
                save(target / "result.json", row)
                save(target / "terminal.json", {"at": now(), "reused_without_sends": True, "result_sha256": sha(target / "result.json")})
    calibration_paths = [output / "attempts" / f"calibration-{opaque}" / "result.json"
                         for opaque in read(output / "calibration-mapping.json")]
    save(output / "calibration-commit.json", {"at": now(), "n": len(calibration_paths),
        "prediction_hashes": {str(path.relative_to(output)): sha(path) for path in calibration_paths},
        "mapping_sha256": sha(output / "calibration-mapping.json"), "implementation_sha256": sha(output / "implementation.json"),
        "parent_commitment_sha256": sha(parent / "calibration-commit.json"), "reused_without_sends": True})
    runner.score(output, "calibration")
    sources = {}
    for opaque in read(output / "selection-mapping.json"):
        directory = parent / "attempts" / f"selection-{opaque}"
        prior = read(directory / "result.json")
        packet = {name: prior[name] for name in
                  ("plan", "searches", "sources", "retrieval_ledger", "domain", "fact_check_exposures")}
        cache_path = output / "selection" / f"{opaque}-evidence.json"
        save(cache_path, packet)
        prefix, elapsed = retrieval_prefix(directory)
        sources[opaque] = {"initial_path": str(directory / "initial.json"), "initial_sha256": sha(directory / "initial.json"),
            "cache_path": str(cache_path), "cache_sha256": sha(cache_path),
            "inherited_policy_accounting": prefix, "inherited_elapsed_seconds": elapsed,
            "parent_result_sha256": sha(directory / "result.json")}
    save(output / "selection-reuse.json", sources)
    return {"prepared": True, "reused_calibration": 30, "selection_reassessment": len(sources),
            "protected_final": len(split["final_ids"]), "exploratory": True}


def cached_execution(job, inputs, provider, journal, commit_initial):
    from kaji_langgraph.incremental.method import reassess
    from kaji_langgraph.study import ClosedBookAssessment
    source = job["development_reuse"]
    initial_path, cache_path = Path(source["initial_path"]), Path(source["cache_path"])
    if sha(initial_path) != source["initial_sha256"] or sha(cache_path) != source["cache_sha256"]:
        raise ValueError("Inherited initial/evidence commitment changed")
    initial = ClosedBookAssessment.model_validate(read(initial_path)["prediction"]).model_dump()
    commit_initial(initial)
    journal.counts.update(source["inherited_policy_accounting"]["calls"])
    return reassess(inputs, initial, read(cache_path), provider, job["config"])


def choose(parent, output):
    from kaji_langgraph.incremental.analysis import compare
    from kaji_langgraph.incremental.runner import scored_rows
    routing = read(output / "calibration-report.json")["routing_rule"]
    original = compare(scored_rows(parent, "selection"), routing)
    revised = compare(scored_rows(output, "selection"), routing)
    if original != read(parent / "selection-report.json") or revised != read(output / "selection-report.json"):
        raise ValueError("Version comparison does not reproduce")
    entries = [(version, name, report["candidates"][name]) for version, report in
               (("original", original), ("material", revised)) for name in ("A", "B")]
    def rank(entry):
        version, name, candidate = entry
        calls = candidate["policy_resources"]["calls"]
        return (candidate["metrics"]["accuracy"], candidate["metrics"]["macro_f1"],
                -calls.get("ollama", 0), -calls.get("fetch", 0), -calls.get("search", 0),
                name == "B", version == "original")
    version, candidate, stats = max(entries, key=rank)
    improved = stats["metrics"]["accuracy"] > original["model_only"]["accuracy"]
    receipt = {"at": now(), "selected_version": version, "best_research_candidate": candidate,
        "final_research_rule": "all" if candidate == "A" else routing,
        "promoted": improved, "deployment": candidate + "/" + version if improved else "model_only",
        "baseline_accuracy": original["model_only"]["accuracy"], "chosen_accuracy": stats["metrics"]["accuracy"],
        "chosen_macro_f1": stats["metrics"]["macro_f1"], "exploratory_repeated_selection": True,
        "parent_selection_report": str(parent / "selection-report.json"),
        "parent_selection_report_sha256": sha(parent / "selection-report.json"),
        "revision_selection_report_sha256": sha(output / "selection-report.json"),
        "selection_comparison": {"original": original, "material": revised},
        "no_more_method_revisions": True}
    save(output / "final-method-choice.json", receipt)
    return {key: value for key, value in receipt.items() if key != "selection_comparison"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "choose"))
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent, output = args.parent.resolve(), args.output.resolve()
    result = prepare_revision(Path.cwd(), parent, output) if args.command == "prepare" else choose(parent, output)
    print(result)


if __name__ == "__main__":
    main()

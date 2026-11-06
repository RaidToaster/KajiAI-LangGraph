"""Regenerate historical empirical table rows and verify their manuscript values."""
import argparse
import json
from pathlib import Path
from statistics import mean, median


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def gemma(root):
    directory = root / "evaluation/results/study-20261009-v3"
    saved = read(directory / "study-metrics.json")["metrics"]
    rows = {}
    for condition in ("full", "closed_book"):
        with (directory / condition / "results.jsonl").open(encoding="utf8") as stream:
            rows[condition] = [json.loads(line) for line in stream]
        assert len({row["claim_id"] for row in rows[condition]}) == len(rows[condition]) == 500
    for name, key, observed in (
        ("Always Refuted", "majority_baseline", sum(r["gold_label"] == "Refuted" for r in rows["full"])),
        ("Model only", "closed_book_predictions", sum(r["predicted_label"] == r["gold_label"] for r in rows["closed_book"])),
        (r"First round$^{\dagger}$", "first_round_prediction", None),
        ("Final workflow", "full_predictions", sum(r["predicted_label"] == r["gold_label"] for r in rows["full"])),
    ):
        m = saved[key]
        assert observed is None or m["accuracy"] == observed / 500
        lower, upper = (100 * x for x in m["accuracy_ci95"])
        yield f"{name} & {m['accuracy']*100:.1f} & {lower:.1f}--{upper:.1f} & {m['macro_f1']:.3f}"

    for name, key in (("Structural only", "structural_only"), ("Structural + Jev", "full_policy")):
        m = saved[key]
        accepted, correct = round(m["coverage"]*500), round(m["accuracy"]*500)
        if key == "full_policy":
            actual = [r for r in rows["full"] if r["accepted_label"] != "ABSTAIN"]
            assert len(actual) == accepted and sum(r["accepted_label"] == r["gold_label"] for r in actual) == correct
        yield f"{name} & {accepted} & {m['coverage']*100:.1f} & {correct}/{accepted} ({correct/accepted*100:.1f}" + r"\pct)"

    def costs(records):
        results = [record["result"] for record in records]
        seconds = sorted(r["elapsed_seconds"] for r in results)
        return (
            str(len(results)),
            str(sum(r["verification_status"] == "execution_error" for r in results)),
            f"{mean(seconds):.1f}", f"{median(seconds):.1f}", f"{seconds[449]:.1f}",
            f"{sum(r['budget']['search_calls'] for r in results):,}",
            f"{sum(r['budget']['scrapes'] for r in results):,}",
            f"{sum(r['budget']['tokens_used'] for r in results):,}",
        )

    full, control = (costs(rows[key]) for key in ("full", "closed_book"))
    for label, a, b in zip((
        "Attempted tasks", "Fatal execution errors", "Mean elapsed time (s)", "Median elapsed time (s)",
        "90th percentile time (s)", "Logical search calls", "Page-fetch attempts", "Observed model tokens",
    ), full, control):
        yield f"{label} & {a} & {b}"


def flash(root):
    directory = root / "artifacts/flash-workflow-20261103"
    for revision, candidate in (("revision-3", "Compact"), ("revision-8", "Candidate")):
        data = read(directory / revision / "development-analysis.json")
        for model, name in (("glm", "GLM"), ("deepseek", "DeepSeek")):
            for arm, label in (("baseline", "Current"), ("candidate", candidate)):
                m = data["models"][model]["paired"][arm]
                n = m["raw"]["n"]
                correct = round(m["raw"]["accuracy"] * n)
                yield (f"{name} & {label} & {correct}/{n} & {m['raw']['macro_f1']:.3f} & "
                       f"{m['counts'].get('accepted', 0)}/{n} & {m['counts']['failed']}/{n}")


def stopping(root):
    saved = read(root / "artifacts/aris/run_20261103_exhaustion_9c7e12bf/live-analysis.json")
    for name, tag in (
        ("Gemma 4 31B", "gemma4:31b-cloud"),
        ("GLM 5.3 Flash", "glm-5.3-flash:cloud"),
        ("DeepSeek V4.1 Flash", "deepseek-v4.1-flash:cloud"),
    ):
        m = saved["by_model"][tag]
        yield (f"{name} & {m['correct_proposals_baseline']} / {m['correct_proposals_candidate']} & "
               f"{m['accepted_baseline']} / {m['accepted_candidate']} & {m['skipped_policy_sends_in_complete_pairs']} & "
               f"{m['skipped_policy_tokens_in_complete_pairs']:,}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("historical_root", type=Path)
    parser.add_argument("paper", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = [row + r"\\" for render in (gemma, stopping, flash) for row in render(args.historical_root)]
    source = args.paper.read_text(encoding="utf8")
    for row in rows:
        assert row in source, row
    args.output.write_text("\n".join(rows) + "\n", encoding="utf8")
    print(f"{len(rows)} historical rows regenerated and matched the manuscript")


if __name__ == "__main__":
    main()

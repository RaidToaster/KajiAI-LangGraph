"""Render the DeepSeek manuscript's result table from the offline score summary."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("summary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    names = {"selected_50": "Selected 50", "other_450": "Other 450", "pooled_500": "Pooled 500"}
    lines = []
    for key, name in names.items():
        target = int(name.split()[-1])
        for arm, metrics in summary["strata"][key]["arms"].items():
            n = metrics["attempted"]
            correct = f"{metrics['correct_proposals']}/{n}" if n else "--"
            lines.append(
                f"{name} & {arm.title()} & {n}/{target} & {metrics['failed']} & {correct} & "
                f"{metrics['correct_acceptances']}/{metrics['incorrect_acceptances']} " + r"\\"
            )
    args.output.write_text(r"\newcommand{\DeepSeekRows}{%"+"\n"+"\n".join(lines)+"\n}\n", encoding="utf-8")


if __name__ == "__main__":
    main()


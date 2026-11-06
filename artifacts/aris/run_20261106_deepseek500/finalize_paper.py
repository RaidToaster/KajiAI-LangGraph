"""Render the finished DeepSeek comparison and regenerate its table offline."""
import argparse
import json
from pathlib import Path


def replace_between(text, start, end, replacement):
    begin = text.index(start)
    return text[:begin] + replacement + text[text.index(end, begin):]


def result_table(summary):
    labels = {"selected_50": "Selected 50", "other_450": "Other 450", "pooled_500": "Pooled 500"}
    lines = [r"\newcommand{\DeepSeekRows}{%"]
    for key, name in labels.items():
        for arm, value in summary["strata"][key]["arms"].items():
            n = value["attempted"]
            agreement = f"{value['correct_proposals']}/{n}" if n else "--"
            coverage = f"{value['coverage']:.1%}".replace("%", r"\%") if n else "--"
            lines.append(
                f"{name} & {arm.title()} & {n} & {value['completed']} & {value['failed']} & {value['timeout']} & "
                f"{agreement} & {value['correct_acceptances']}/{value['incorrect_acceptances']} & {coverage} " + r"\\"
            )
    return "\n".join([*lines, "}", ""])


def difference(group):
    lower, upper = (100 * x for x in group["paired_bootstrap_95"]["accuracy"])
    delta = 100 * group["paired_agreement_delta"]
    return f"{delta:+.1f} points (95" + r"\pct{}" + f" paired bootstrap interval {lower:+.1f} to {upper:+.1f})"


def plural(number, singular):
    return singular if number == 1 else singular + "s"


def resource_text(summary):
    lines = []
    for label, cohort in summary["resources_by_source"].items():
        sends = cohort["send_resources"]

        def tokens(service, kind):
            return f"{sends[service][kind + '_tokens']['observed_total']:,}"

        active = cohort["resources"]["active_seconds"]["observed_total"]
        lines.append(
            f"The {label} cells recorded {tokens('ollama', 'input')} Ollama input and {tokens('ollama', 'output')} output tokens, "
            f"{tokens('jev', 'input')} Jev input and {tokens('jev', 'output')} output tokens, "
            f"{sends['tinyfish_search']['count']:,} Search reservations, {sends['tinyfish_fetch']['count']:,} Fetch URL reservations "
            f"and {active/3600:.2f} worker hours."
        )
    tariff = summary["tariffs"]
    lines.append(
        f"Of the fresh cells, {tariff['fresh_builder_attempts']} used Builder and "
        f"{tariff['fresh_hobby_attempts']} used zero-rate Hobby. "
        r"The Builder retrieval ledger reserved \$" + tariff["rate_derived_reserved_usd"] +
        " at the recorded rates. Token totals include observed usage. The ledger retains separate reservations "
        "for unknown outcomes. Estimates use the frozen conservative tariffs. Provider invoices were unavailable."
    )
    return " ".join(lines) + "\n\n"


def manuscript(paper, summary):
    assert summary["complete"] and summary["accounted"] == 1000
    pooled = summary["strata"]["pooled_500"]
    baseline, candidate = (pooled["arms"][arm] for arm in ("baseline", "candidate"))
    other = summary["strata"]["other_450"]
    paper = paper.replace("% DeepSeek results are interim. The completed Gemma study is historical.",
                          "% The frozen DeepSeek evaluation is complete. The Gemma study is historical.")
    abstract = (
        r"\begin{abstract}" + "\n"
        "KajiAI is a LangGraph workflow that separates proposed factual labels from evidence acceptance and retains retrieved text for audit. "
        "We evaluated its standard workflow and an evidence-adjudicated candidate on 500 AVeriTeC development claims with DeepSeek V4.1 Flash "
        "and a fixed Jev verifier. The paired comparison includes all 1,000 scheduled cells, with 47 retained from a resource pilot. "
        f"The standard workflow and candidate produced {baseline['correct_proposals']} and {candidate['correct_proposals']} correct proposals, "
        f"{baseline['failed']} and {candidate['failed']} execution failures, and {baseline['correct_acceptances']} and "
        f"{candidate['correct_acceptances']} correct acceptances, respectively. "
        f"Candidate-minus-baseline proposal agreement was {difference(pooled)}. "
        f"On the 450 cases outside the pilot sample, the difference was {difference(other)}. "
        "The study measures failure-inclusive label agreement under live retrieval. Human assessment of citation support remains open.\n"
    )
    paper = replace_between(paper, r"\begin{abstract}", r"\end{abstract}", abstract)
    paper = paper.replace("Hobby reinstates pilot pacing", "Hobby waits only after a provider rate rejection")
    paper = paper.replace(
        "After Builder, the Hobby phase reinstated the original zero-rate quota guard and counted all earlier retrieval in its rolling windows.",
        "After Builder, the wallet again reported zero-rate Hobby Search and Fetch. A between-cell checkpoint initially applied the earlier local "
        "quota windows, including prior retrieval. The next amendment removed those windows and full-cell quota reservations. "
        "The single worker then dispatched the next untouched cell after each terminal record, subject to the original spending ceilings "
        "and any wait triggered by an observed provider rate rejection. Read-only retrieval history could reconcile service outcomes "
        "without changing a failed workflow record. Unknown outcomes retained their reservations."
    )
    results = (
        r"\subsection{Frozen DeepSeek Results}" + "\n"
        r"Table~\ref{tab:deepseek-results} includes both arms of all 500 cases. "
        "Every execution failure contributes a disagreement and an abstention. Correct acceptances indicate agreement with the local label after the automated gate. "
        f"The candidate-minus-baseline proposal agreement difference was {difference(pooled)}.\n\n"
    )
    for key, label in (("selected_50", "selected 50-case stratum"), ("other_450", "remaining 450 cases")):
        group = summary["strata"][key]
        b, c = (group["arms"][arm] for arm in ("baseline", "candidate"))
        results += (
            f"For the {label}, the baseline recorded {b['correct_proposals']}/{b['attempted']} correct proposals and "
            f"{b['failed']} {plural(b['failed'], 'failure')}, while the candidate recorded "
            f"{c['correct_proposals']}/{c['attempted']} correct proposals and {c['failed']} {plural(c['failed'], 'failure')}. "
            f"The paired difference was {difference(group)}. "
        )
    paper = replace_between(paper, r"\subsection{Interim DeepSeek Comparison}", r"\begin{table*}", results + "\n\n")
    paper = paper.replace(
        r"\caption{Interim DeepSeek outcomes. Accepted counts show correct/incorrect labels. Untouched cells contribute to the planned counts only.}",
        r"\caption{Frozen DeepSeek outcomes. Failed cells include worker timeouts. Accepted counts show correct/incorrect local labels.}"
    ).replace(
        r"\begin{tabular}{@{}llrrrr@{}}" + "\n" + r"\toprule" + "\n"
        + r"Stratum & Arm & Terminal/planned & Failed & Correct proposals & Accepted\\",
        r"\begin{tabular}{@{}llrrrrrrr@{}}" + "\n" + r"\toprule" + "\n"
        + r"Stratum & Arm & Attempted & Completed & Failed & Timeout & Correct proposals & Accepted & Coverage\\"
    )
    paper = replace_between(paper, "The reused cohort recorded", r"\subsection{Historical Gemma Paired Label Prediction}",
                            resource_text(summary))
    paper = paper.replace(
        "The DeepSeek results estimate a combined intervention under live retrieval.",
        "The DeepSeek comparison estimates the outcome of the combined intervention under live retrieval. The arms differ in "
        "assessment structure, reasoning options, evidence checks and output limits. The Builder-to-Hobby transition occurred in schedule order. "
        "Provider availability and tariff phase therefore vary with time and case position."
    )
    paper = paper.replace(
        r"\textit{Service availability:} Quota and concurrent-slot interruptions required resumption across time. A post hoc sensitivity",
        r"\textit{Service availability:} The DeepSeek schedule crossed retrieval tiers and kept failures after provider or transport interruptions. "
        "Historical Gemma quota and concurrent-slot interruptions also required resumption. A post hoc sensitivity"
    )
    conclusion = (
        r"\section{Conclusion}" + "\n"
        "The frozen DeepSeek comparison accounted for all 1,000 scheduled cells. The evidence gate separates label proposals from accepted decisions, "
        "and the journal preserves failures and reservations alongside completed workflows. "
        f"On the 450 cases outside the selected sample, the candidate-minus-baseline proposal agreement difference was {difference(other)}. "
        "These results describe the tested DeepSeek configurations under live retrieval. Independent human evidence adjudication remains open.\n\n"
    )
    return replace_between(paper, r"\section{Conclusion}", r"\section*{Acknowledgment}", conclusion)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("table", type=Path)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--manuscript", type=Path)
    args = parser.parse_args()
    if bool(args.template) != bool(args.manuscript):
        parser.error("--template and --manuscript must be provided together")
    summary = json.loads(args.summary.read_text(encoding="utf8"))
    args.table.write_text(result_table(summary), encoding="utf8")
    if args.template:
        text = manuscript(args.template.read_text(encoding="utf8"), summary)
        args.manuscript.write_text(text, encoding="utf8")


if __name__ == "__main__":
    main()

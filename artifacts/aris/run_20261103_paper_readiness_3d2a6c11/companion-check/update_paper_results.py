"""Generate the historical completed-study draft without overwriting revised prose."""
import argparse
from pathlib import Path
import json
import re


def generate(destination: Path) -> None:
    ROOT = Path(__file__).resolve().parent
    data = json.loads((ROOT / "results/study-20261009-v3/study-metrics.json").read_text(encoding="utf-8"))
    assert data["complete"] and data["n"] == 500
    m, d, p = data["metrics"], data["diagnostics"], data["paired_accuracy_comparisons"]
    text = (ROOT / "paper-partial.tex").read_text(encoding="utf-8")

    def paragraph(prefix, replacement):
        nonlocal text
        text, count = re.subn(re.escape(prefix) + r".*?(?=\n\n)", lambda _: replacement,
                             text, count=1, flags=re.S)
        assert count == 1, prefix

    def region(start, end, replacement):
        nonlocal text
        a, b = text.index(start), text.index(end)
        assert a < b
        text = text[:a] + replacement + "\n\n" + text[b:]

    def pct(v):
        return f"{100*v:.1f}"

    def ci(v):
        return f"{100*v[0]:.1f}--{100*v[1]:.1f}"

    def tex_p(v):
        if v < 0.0001:
            mantissa, exponent = f"{v:.2e}".split("e")
            return mantissa + r"\times 10^{" + str(int(exponent)) + "}"
        return f"{v:.3g}"

    raw, control, first = m["full_predictions"], m["closed_book_predictions"], m["first_round_prediction"]
    gate, structural = m["full_policy"], m["structural_only"]
    accepted, correct = round(500*gate["coverage"]), round(500*gate["accuracy"])
    sn, sc = round(500*structural["coverage"]), round(500*structural["accuracy"])
    diff, extra, nf = p["full_minus_closed_book"], p["full_minus_first_round"], p["nonfatal_full_minus_first_round"]
    changes, pairs = d["extra_research"], d["paired_correctness"]
    fe, ce = len(data["execution_errors"]["full"]), len(data["execution_errors"]["model_only"])
    removed, citations, audit = data["semantic_gate_removed"], data["citations"], data["human_audit_sample"]
    op, cb = data["full_execution"], data["closed_book_execution"]
    lat, clat = d["full_latency"], d["control_latency"]
    fetch_failures = sum(n for category, n in d["recorded_error_categories"].items()
                         if category.startswith("Page fetch failed"))
    accepted_description = ", ".join(f"{n} {label}" for label, n in data["accepted_label_distribution"].items())

    region(r"\begin{abstract}", r"\begin{IEEEkeywords}", rf"""\begin{{abstract}}
A correct factual prediction does not necessarily provide verifiable evidence, and additional web research can change a previously correct answer. This paper presents KajiAI, a LangGraph workflow that separates a language model's proposed verdict from an evidence-based acceptance decision. It records versioned retrieved text, checks literal quotation provenance, applies structural evidence requirements and model-based citation review, and repeats research within explicit resource budgets. A completed evaluation assessed all 500 AVeriTeC development claims using both the workflow and a model-only control, retaining {fe+ce} execution failures. The workflow achieved {pct(raw['accuracy'])}\pct\ label accuracy and {raw['macro_f1']:.3f} macro F1, compared with {pct(control['accuracy'])}\pct\ and {control['macro_f1']:.3f} for the control. The paired accuracy difference was {100*diff['delta_b_minus_a']:.1f} percentage points, with a 95\pct\ bootstrap interval of {ci(diff['ci95'])} points. The complete gate accepted {accepted} verdicts, of which {correct} matched the dataset labels; coverage was {pct(gate['coverage'])}\pct. Additional rounds corrected {changes['wrong_to_correct']} predictions and changed {changes['correct_to_wrong']} correct predictions into incorrect outcomes. These results show why prediction quality, acceptance coverage, evidence support and research cost require separate measurement. Contemporary web access, development-set reuse and the absence of independent human citation validation limit the conclusions.
\end{{abstract}}""")
    text = text.replace("% All numerical results refer to the partial study-20261009-v3.", "% Results refer to the complete 500-by-two study-20261009-v3.")
    text = text.replace(r"\scriptsize", r"\footnotesize")
    text = text.replace(r"left, font=\footnotesize, rotate=90", r"left, xshift=-2mm, font=\footnotesize, rotate=90")
    text = text.replace(r"\usepackage{booktabs}", "\\usepackage{booktabs}\n\\usepackage{balance}")
    text = text.replace("% Native IEEEtran last-page column balancing; no margin or body-font changes.\n\\IEEEtriggeratref{2}", "% Balance final columns without changing margins or body fonts.\n\\balance")
    text = text.replace("and preliminary measurements exposing", "and measurements exposing")
    text = text.replace("The intended study assesses all 500", "The completed study assesses all 500")
    text = text.replace("Observed-token ceiling", "Budgeted reported tokens")
    text = text.replace(
        "Time limits are checked before scheduling work; an in-flight request can finish after the soft deadline.",
        "Time and token limits govern scheduling; an in-flight request can finish after the soft deadline or exceed the reported-token threshold. Missing usage prevents a guaranteed spend cap.")
    text = text.replace(
        r"\subsection{Retrieval and Citation Evaluation}",
        r"The 2025 AVeriTeC shared task instead specifies open-weight models, a precompiled evidence store, a single-GPU resource constraint and a one-minute processing limit \cite{sharedtask2025}. Our cloud-assisted, contemporary-web protocol does not reproduce those conditions."
        + "\n\n" + r"\subsection{Retrieval and Citation Evaluation}")
    text = text.replace(
        "ALCE evaluates generated answers",
        r"FIRE integrates retrieval and verification iteratively, choosing a final judgment or another search query using confidence \cite{fire}. EMULATE distributes search-result ranking and webpage-content assessment across agents \cite{emulate}. Iterative research and role separation therefore precede KajiAI. Our empirical focus is preserving source versions, separating provisional prediction from rule-based acceptance, and measuring iteration effects in frozen traces; we do not claim these mechanisms are first proposed here."
        + "\n\n" + "ALCE evaluates generated answers")
    text = text.replace(r"\bibitem{selfrag}", r"""\bibitem{sharedtask2025}
M. Akhtar et al., \lq\lq The 2nd Automated Verification of Textual Claims (AVeriTeC) shared task: Open-weights, reproducible and efficient systems,'' in \emph{Proc. Eighth Fact Extraction and VERification Workshop}, 2025, pp. 201--223, doi: 10.18653/v1/2025.fever-1.15.

\bibitem{selfrag}""")
    text = text.replace(r"\bibitem{selective}", r"""\bibitem{fire}
Z. Xie et al., \lq\lq FIRE: Fact-checking with iterative retrieval and verification,'' in \emph{Findings of the Association for Computational Linguistics: NAACL 2025}, 2025, pp. 2901--2914, doi: 10.18653/v1/2025.findings-naacl.158.

\bibitem{emulate}
S. Hong, M. Luo, and X. Wan, \lq\lq EMULATE: A multi-agent framework for determining the veracity of atomic claims by emulating human actions,'' in \emph{Proc. Eighth Fact Extraction and VERification Workshop}, 2025, pp. 179--183, doi: 10.18653/v1/2025.fever-1.13.

\bibitem{selective}""")
    paragraph("Ollama's monthly usage limit interrupted execution", rf"The study completed 500 full-workflow and 500 model-only attempts on the same claims. Ollama's monthly usage limit interrupted execution after 302 workflow and 283 control attempts. Execution resumed after additional credits were supplied, with the original model, source, dataset and settings. The seven earlier quota failures remain recorded rather than being retried or replaced. In total, {fe} workflow and {ce} control attempts ended in fatal execution errors. All 1,000 planned claim-condition attempts are retained in scoring.")
    text = text.replace("The seven earlier quota failures remain recorded rather than being retried or replaced.", "The seven earlier quota failures remain recorded rather than being retried or replaced. Later concurrent-slot timeouts halted scheduling; restarting the local Ollama daemon interrupted two pending control requests. These failures also remain recorded, and only unattempted tasks were resumed.")
    failure = ("Raw and failure-inclusive accuracies coincide." if raw["accuracy"] == m["full_failure_inclusive"]["accuracy"]
               else rf"Raw accuracy is {pct(raw['accuracy'])}\pct, while failure-inclusive accuracy is {pct(m['full_failure_inclusive']['accuracy'])}\pct.")
    paragraph("Fatal errors remain in the denominator.", rf"Fatal errors remain in the denominator. Failure-inclusive scoring treats them as abstentions; raw scoring can preserve an earlier prediction if a later service fails. {failure} We report 95\pct\ Wilson intervals for proportions, a paired accuracy bootstrap with 2,000 claim-level resamples and seed 20261009, and an exact two-sided McNemar test. These intervals treat claims as sampling units; they do not capture correlated topics, shared-source effects, model drift, service availability or web changes.")
    paragraph("Citation measurements count finding--URL occurrences", rf"Citation measurements count finding--URL occurrences in final assessments, including repeated URLs across findings. A blinded human-audit worksheet contains {audit['citation_rows']} citation rows from {audit['accepted_claims']} accepted and {audit['rejected_claims']} sampled rejected claims; labels and acceptance status are stored separately. Human annotation fields remain blank. Automated Jev judgments are measurements rather than independent human ground truth.")

    prediction_rows = "\n".join(rf"{label} & {pct(m[name]['accuracy'])} & {ci(m[name]['accuracy_ci95'])} & {m[name]['macro_f1']:.3f}\\"
        for label, name in [("Always Refuted", "majority_baseline"), ("Model only", "closed_book_predictions"),
                            (r"First round$^{\dagger}$", "first_round_prediction"), ("Final workflow", "full_predictions")])
    conflicting_calls = sum(r["Conflicting Evidence/Cherrypicking"] for r in raw["confusion_matrix"].values())
    quote_gaps = d["structural_gap_claim_counts"].get("Each citation needs an exact quote from its retrieved text.", 0)
    independence_gaps = sum(n for msg, n in d["structural_gap_claim_counts"].items() if msg.startswith("Establish source independence;"))
    rounds = ", ".join(f"{n} use {r} round{'s' if r != '1' else ''}" for r, n in sorted(d["round_count_distribution"].items(), reverse=True))
    cost_rows = "\n".join([
        r"Attempted tasks & 500 & 500\\",
        rf"Fatal execution errors & {fe} & {ce}\\",
        rf"Mean elapsed time (s) & {lat['mean_seconds']:.1f} & {clat['mean_seconds']:.1f}\\",
        rf"Median elapsed time (s) & {lat['median_seconds']:.1f} & {clat['median_seconds']:.1f}\\",
        rf"90th percentile time (s) & {lat['p90_seconds']:.1f} & {clat['p90_seconds']:.1f}\\",
        rf"Logical search calls & {op['total_searches']:,} & 0\\",
        rf"Page-fetch attempts & {op['total_page_fetches']:,} & 0\\",
        rf"Observed model tokens & {op['total_observed_tokens']:,} & {cb['total_observed_tokens']:,}\\"])

    results = rf"""\section{{Results}}
\subsection{{Paired Label Prediction}}
Both conditions assess the same 500 claims: 122 Supported, 305 Refuted, 35 \NEI\ and 38 Conflicting labels. Table~\ref{{tab:prediction}} reports the paired label results, including failed attempts.

\begin{{table}}[t]
\caption{{Prediction Results on All 500 Claims}}
\label{{tab:prediction}}
\centering
\footnotesize
\begin{{tabular}}{{@{{}}lrrr@{{}}}}
\toprule
Condition & Accuracy (\pct) & 95\pct\ \CI & Macro F1\\
\midrule
{prediction_rows}
\bottomrule
\end{{tabular}}
\par\smallskip
\parbox{{\columnwidth}}{{\scriptsize $^{{\dagger}}$Saved-trajectory truncation, not a separate live one-round condition. Wilson intervals; local label metrics, not official AVeriTeC evidence scores.}}
\end{{table}}

Full predictions are correct on {round(500*raw['accuracy'])} claims, compared with {round(500*control['accuracy'])} for the control. The workflow is correct on {pairs.get('full_correct__control_wrong',0)} claims missed by the control, while the control is correct on {pairs.get('full_wrong__control_correct',0)} missed by the workflow; both are correct on {pairs.get('full_correct__control_correct',0)} and both are wrong on {pairs.get('full_wrong__control_wrong',0)}. The paired accuracy difference is {100*diff['delta_b_minus_a']:.2f} percentage points (bootstrap 95\pct\ \CI: {100*diff['ci95'][0]:.2f}--{100*diff['ci95'][1]:.2f}); exact McNemar \(p={tex_p(d['accuracy_mcnemar_exact_two_sided_p'])}\).

The majority baseline achieves {pct(m['majority_baseline']['accuracy'])}\pct\ accuracy because Refuted dominates the split, but its macro F1 is only {m['majority_baseline']['macro_f1']:.3f}. The workflow improves accuracy and macro F1 over the model-only control. It predicts the conflicting class {conflicting_calls} times, compared with 38 gold conflicting labels. Its \NEI\ recall is {pct(raw['per_class']['Not Enough Evidence']['recall'])}\pct, compared with {pct(control['per_class']['Not Enough Evidence']['recall'])}\pct\ for the control. Improvement is therefore not uniform across classes.

\subsection{{Selective Acceptance}}
Table~\ref{{tab:acceptance}} compares acceptance rules on all 500 saved final assessments. Raw prediction accuracy and accepted-label accuracy represent different outcomes.

\begin{{table}}[t]
\caption{{Acceptance Replay on 500 Final Assessments}}
\label{{tab:acceptance}}
\centering
\footnotesize
\begin{{tabular}}{{@{{}}lrrr@{{}}}}
\toprule
Policy & Accepted & Coverage (\pct) & Correct / accepted\\
\midrule
Structural only & {sn} & {pct(structural['coverage'])} & {sc}/{sn} ({pct(structural['selective_accuracy'])}\pct)\\
Structural + Jev & {accepted} & {pct(gate['coverage'])} & {correct}/{accepted} ({pct(gate['selective_accuracy'])}\pct)\\
\bottomrule
\end{{tabular}}
\par\smallskip
\parbox{{\columnwidth}}{{\scriptsize Conditional accuracy 95\pct\ \CI: {ci(structural['selective_accuracy_ci95'])}\pct\ for structural-only replay; {ci(gate['selective_accuracy_ci95'])}\pct\ for the full gate.}}
\end{{table}}

The full gate withholds {removed['total']} outputs accepted by structural-only replay: {removed['wrong_labels']} wrong labels and {removed['correct_labels']} correct labels. It accepts {accepted_description}; \NEI\ is excluded by design. Its coverage interval is {ci(gate['coverage_ci95'])}\pct; end-to-end accepted-label accuracy is {pct(gate['accuracy'])}\pct. The gate rejects {d['rejected_predictions'].get('raw_correct',0)} correct raw predictions and {d['rejected_predictions'].get('raw_wrong',0)} wrong ones. Its observed {pct(gate['selective_accuracy'])}\pct\ conditional accuracy describes a small selected subset and does not guarantee correct accepted verdicts.

Both accepted errors have gold conflicting-evidence labels but receive Refuted predictions. Passing quotation-support and structural checks therefore does not ensure the correct claim-level label.

Figure~\ref{{fig:threshold}} shows descriptive threshold replay. Stricter thresholds reduce coverage, while lower thresholds can admit additional outputs. Selecting a threshold from this development analysis would require separate validation.

\begin{{figure}}[t]
\centering
\includegraphics[width=\columnwidth]{{acceptance-thresholds.pdf}}
\caption{{Semantic-threshold replay on all 500 final assessments. Evidence and structural rules are fixed; the curve does not establish an optimal threshold.}}
\label{{fig:threshold}}
\end{{figure}}

\subsection{{Effect of Additional Research}}
First-round accuracy is {pct(first['accuracy'])}\pct, compared with {pct(raw['accuracy'])}\pct\ for final predictions. Additional rounds change {changes['predictions_changed']} predictions: {changes['wrong_to_correct']} wrong-to-correct, {changes['correct_to_wrong']} correct-to-wrong and {changes['predictions_changed']-changes['wrong_to_correct']-changes['correct_to_wrong']} between incorrect labels. The final-minus-first difference is \({100*extra['delta_b_minus_a']:.2f}\) percentage points (bootstrap 95\pct\ \CI: \({100*extra['ci95'][0]:.2f}\) to \({100*extra['ci95'][1]:.2f}\)). Excluding {fe} fatal attempts yields \({100*nf['delta_b_minus_a']:.2f}\) points on {nf['n']} nonfatal attempts, with an interval of \({100*nf['ci95'][0]:.2f}\) to \({100*nf['ci95'][1]:.2f}\).

These saved trajectories quantify the observed effect of later research, while a separately deployed one-round system can behave differently because timing and search responses can change. Of the attempted workflows, {rounds}. The prevalence of the round limit warrants evaluating stopping behavior.

The paired intervals include zero, so the negative point estimate does not establish a negative average iteration effect. Individual harmful changes and additional resource use still warrant examining stopping policies.

\subsection{{Citation Diagnostics and Resource Use}}
Final assessments contain {citations['total']:,} citation occurrences. Of these, {citations['exact_quote']:,} have literal quotes present in canonical text and {citations['reviewed']:,} have Jev reviews. {citations.get('exact_quote_but_jev_does_not_support',0)} reviewed quotes receive a relation other than \lq\lq supports,'' and {citations.get('exact_quote_but_jev_uncertain',0)} receive supporting confidence below 0.8. The remaining {citations['total']-citations['exact_quote']:,} occurrences fail literal provenance matching. They are not automatically counted as hallucinations: a quotation can refer to a snippet differing from the preferred full-page text, or exhibit another provenance mismatch.

Final structural gaps include missing exact quotations on {quote_gaps} claims and insufficient independence flags on {independence_gaps}; these categories overlap. A host-exposure audit unwraps Wayback Machine URLs before comparison. On {data['same_host_as_gold_fact_check_cited']} of 500 claims, a cited host matches the host of the dataset's fact-check article. Host equality does not prove exact-article exposure, and an unmatched host does not exclude other exposure routes.

In the post hoc host-match group, workflow and control accuracies are {pct(data['descriptive_exposure_groups']['host_match']['full']['accuracy'])}\pct\ and {pct(data['descriptive_exposure_groups']['host_match']['model_only']['accuracy'])}\pct\ ({data['descriptive_exposure_groups']['host_match']['n']} claims); in the unmatched group they are {pct(data['descriptive_exposure_groups']['no_host_match']['full']['accuracy'])}\pct\ and {pct(data['descriptive_exposure_groups']['no_host_match']['model_only']['accuracy'])}\pct\ ({data['descriptive_exposure_groups']['no_host_match']['n']} claims). Groups depend on workflow citations and differ in class composition. This is a descriptive exposure audit, not a causal comparison or contamination-free score.

\begin{{table}}[t]
\caption{{Operational Measurements on 500 Tasks per Condition}}
\label{{tab:cost}}
\centering
\footnotesize
\begin{{tabular}}{{@{{}}lrr@{{}}}}
\toprule
Measurement & Full workflow & Model only\\
\midrule
{cost_rows}
\bottomrule
\end{{tabular}}
\par\smallskip
\parbox{{\columnwidth}}{{\scriptsize Same 500 claim inputs; tokens aggregate providers and accounting is incomplete. Concurrent task durations are not study wall-clock time.}}
\end{{table}}

Table~\ref{{tab:cost}} reports operational totals. There are {fetch_failures} recorded fetch failures and {d['recorded_error_categories'].get('Jev search ranking failed',0)} Jev ranking failures, distinct from fatal execution errors. The {changes['extra_rounds']} rounds after the first consume {changes['searches_after_first_round']:,} searches, {changes['fetches_after_first_round']:,} fetch attempts and {changes['observed_tokens_after_first_round']:,} observed tokens; {changes['extra_rounds_without_new_sources']} add no new ledger records. Incomplete provider-level accounting prevents an exact monetary-cost estimate. Iteration cost and the saved accuracy changes support investigating evidence novelty and stopping rules."""
    region(r"\section{Preliminary Results}", r"\section{Discussion and Limitations}", results)
    text = text.replace(r"\scriptsize", r"\footnotesize")
    text = text.replace("The paired comparison offers preliminary evidence", "The paired comparison offers evidence")
    paragraph(r"\textit{Interrupted execution:}", rf"\textit{{Service availability:}} All planned claim-condition attempts are complete, including {fe+ce} recorded fatal failures. The quota interruption required resumption across time; remote responses and current web results can drift. Retaining failures exposes operational performance, while rerunning failed claims and silently replacing them would change the experiment.")
    clean = p["nonfatal_full_minus_closed_book"]
    text = text.replace("The quota interruption required resumption across time;", rf"Quota and concurrent-slot interruptions required resumption across time. A post hoc sensitivity analysis on {clean['n']} pairs without fatal errors gives a workflow-minus-control difference of {100*clean['delta_b_minus_a']:.2f} points (bootstrap 95\pct\ \CI: {100*clean['ci95'][0]:.2f}--{100*clean['ci95'][1]:.2f});")
    paragraph("The next computational step is to resume", "Independent human review should assess citation support and source credibility. A separate study can compare one-round and iterative workflows under controlled retrieval and test stopping rules based on usable-evidence novelty rather than ledger growth. A held-out, temporally constrained evaluation and independently executed retrieval-only and Jev-disabled conditions would better isolate the contribution of each mechanism. Such changes must be versioned and evaluated separately to avoid mixing post hoc improvements into this condition.")
    paragraph("KajiAI makes proposed verdicts,", "KajiAI makes proposed verdicts, evidence acceptance and research history independently inspectable. In a completed 500-claim AVeriTeC development evaluation, the workflow improves paired label accuracy over a model-only control, while a strict gate accepts few claims and later research can worsen saved predictions. The measured tradeoff concerns coverage, conditional correctness and cost. Independent citation validation, held-out evaluation and controlled studies of revised stopping policies remain necessary.")
    assert r"\section{Results}" in text and "177-claim" not in text and "remaining 415 tasks" not in text
    destination.write_text(text, encoding="utf-8")
    print(f"Generated historical completed-study draft: {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("paper-regenerated.tex"),
                        help="Destination for the historical draft (default: paper-regenerated.tex).")
    args = parser.parse_args()
    generate(args.output)


if __name__ == "__main__":
    main()

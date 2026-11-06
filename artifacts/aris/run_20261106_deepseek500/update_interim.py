"""Reconcile the canonical and later review manuscript into an interim DeepSeek draft."""
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
historical = (RUN / "manuscript-before/paper.tex").read_text(encoding="utf-8")
review = (ROOT / "artifacts/flash-workflow-20261103/manuscript/paper.tex").read_text(encoding="utf-8")
paper = historical.replace(
    "% Results refer to the complete 500-by-two study-20261009-v3.",
    "% DeepSeek results are interim. The completed Gemma study is historical."
)
paper = paper.replace(
    r"\title{KajiAI: Auditable Claim Verification with Bounded Research and Selective Evidence Gates}",
    r"\title{Evidence Gates and Failure-Inclusive Evaluation for Claim Verification with KajiAI}"
)

start = paper.index(r"\begin{abstract}")
end = paper.index(r"\end{abstract}", start)
paper = paper[:start] + r"""\begin{abstract}
KajiAI is a LangGraph workflow that separates proposed factual labels from evidence acceptance and retains retrieved text versions for audit. We froze a comparison of the current workflow and an evidence-adjudicated candidate on 500 AVeriTeC development claims with DeepSeek and a fixed Jev verifier. This interim analysis accounts for 47 of 1,000 scheduled cells, all carried forward from a resource pilot. The baseline proposed 6 correct labels in 24 cells and accepted one. The candidate proposed 3 correct labels in 23 cells, had 15 execution failures and accepted zero. Across 23 terminal pairs, the candidate-minus-baseline proposal agreement difference was $-8.7$ percentage points (95\pct\ paired bootstrap interval $-30.4$ to $+13.0$). The other 450 claims remain untouched in this comparison. The separate historical Gemma study measured a 13.6-point gain over a model-only control, and a controlled stopping challenge forfeited two correct acceptances when it skipped reassessment. These studies use different configurations and answer different questions. Pilot-based model selection, live retrieval, incomplete coverage and outstanding human citation adjudication limit inference.
""" + paper[end:]

start = paper.index(r"We examine three questions.")
end = paper.index(r"\section{Related Work}", start)
paper = paper[:start] + r"""The frozen DeepSeek comparison asks how an evidence-adjudicated candidate changes proposal agreement, acceptance coverage, execution failures and resource use relative to the standard workflow. We report the exposed pilot stratum separately from the other 450 cases. Historical studies give two different comparisons: Gemma with and without the workflow, and three cloud models under scripted fixed-evidence stopping.

The evaluation treats operational failure as a result. It preserves each started cell and the service reservations associated with it. Source versions and saved assessments support inspection of disagreements among label agreement, evidence checks and resource use.

""" + paper[end:]

paper = paper.replace("Individual claims follow a sequential graph; the study runner processes up to three claims concurrently.",
    "Individual claims follow a sequential graph. The frozen DeepSeek comparison uses one worker. The historical Gemma runner used up to three.")
paper = paper.replace(
    r"The evaluated model is \modelname, accessed through a local Ollama endpoint. The cloud model and TinyFish and TypeSafe services make this a network-dependent implementation. Successfully fetched pages are reused within a claim. The study runner resumes at completed claim boundaries; the graph has no persistent checkpoint store.",
    r"The DeepSeek comparison uses the exact Ollama tag \texttt{deepseek-v4.1-flash:cloud} through a loopback service and checks the returned model ID. TinyFish Search and Fetch and TypeSafe Jev supply the other network services. Within one attempt the retriever reuses fetched pages. Each arm starts a fresh workflow state. The coordinator saves checkpoints at attempt boundaries. The graph itself has no persistent checkpoint store.")
paper = paper.replace(
    "Decomposition is a deterministic conjunction heuristic, limited to six fragments; the original claim is always retained. Fragments are coverage obligations within one assessment, rather than independently executed agents or a weighted verdict ensemble.",
    "The baseline uses a deterministic conjunction heuristic limited to six fragments. Fragments act as coverage obligations within the assessment. The candidate adds neutral research questions as guidance while retaining the heuristic coverage obligations and the original claim."
)
paper = paper.replace(
    "At round $t$, retrieval constructs an ordered list",
    "At round $t$, the standard workflow constructs an ordered list"
)
paper = paper.replace(
    "Candidate construction therefore combines model suggestions with hardcoded templates.",
    "The standard workflow combines model suggestions with hardcoded templates. The candidate places verification questions after prior follow-up queries, prepends primary-source queries when a provenance gap is active, and can move an eligible source-reference query into the second slot."
)
paper = paper.replace(
    r"\section{Evaluation Protocol}"+"\n"+r"\subsection{Dataset and Frozen Conditions}",
    r"""\subsection{Evidence-Adjudicated Candidate}
The candidate first selects literal passages by ID and proposes a factual class. It evaluates passage stance and checks source paths separately, using source-bound anchors from a predecision review. The origin-review head adjudicates the acceptance materiality of each lead. A material or unresolved class-undermining issue blocks acceptance. The compiler resolves selected IDs to their original retained text and rejects invalid bindings. An additional independent-provenance review is required before acceptance. Source references found during research can supply a follow-up query within the existing round budget.

The executable path is the archived \path{flash_study.py} worker and \path{graph.py} runtime. The candidate uses \path{evidence_adjudicated.py}, \path{source_paths.py} and \path{passage_decision.py}. The current command-line defaults in \path{config/default.yaml} use standard assessment and Gemma. Query-exhaustion stopping is opt-in and disabled in both DeepSeek arms. The current tree's unfinished \path{semantic_evidence.py} integration is outside the frozen archive. The companion code audit maps these paths to the archived versions and fixture tests.

\section{Evaluation Protocol}
\subsection{Frozen DeepSeek Comparison}
The shared manifest contains 500 distinct AVeriTeC development claims. We preserved the earlier seeded 50-case pilot order and each case's relative DeepSeek arm order. The other 450 follow manifest order and alternate the first arm. Both arms receive only claim text and date. The analysis joins labels offline. The retained early pilot records were bound to the frozen source, configuration and raw journal hashes. A started cell remains in the ledger even if its workflow fails.

\begin{table}[t]
\caption{Frozen settings for the two DeepSeek arms}
\label{tab:deepseek-settings}
\centering
\footnotesize
\begin{tabular}{@{}p{.31\columnwidth}p{.61\columnwidth}@{}}
\toprule
Setting & Value\\
\midrule
Shared & DeepSeek V4.1 Flash cloud at temperature zero; Jev 1.13; three rounds; one worker; 270 s graph budget and 300 s worker limit\\
Standard arm & Standard assessment; 4,096 requested output tokens; original reasoning behavior\\
Candidate arm & Evidence adjudication, bound anchors, separate materiality judgment and provenance review; requests up to 6,144 assessment or 2,048 planning output tokens; reasoning disabled on both request types\\
Transport & Per cell, at most 8 Ollama, 40 Jev, 6 Search and 12 Fetch URLs; zero external retries\\
Retrieval pacing & 27 searches/min and 450/hour; 135 Fetch URLs/min and 900/rolling 24 h\\
\bottomrule
\end{tabular}
\end{table}

Table~\ref{tab:deepseek-settings} lists the combined intervention. Generic classification can retain original reasoning behavior in the candidate and uses its 6,144-token ceiling. The archived native GLM trial of the candidate failed its source-fidelity check on an unsupported scope and materiality concern. The native check closed before the planned eight-case development and twelve-case confirmation screens were released. The DeepSeek comparison waived qualification for entry while retaining the acceptance checks. Early outcomes influenced the choice of DeepSeek. On 23 paired cases shared with the pilot's GLM arm, baseline proposals agreed with gold on 5 cases for DeepSeek and 3 for GLM, and candidate proposals agreed on 3 and 2. Execution failures were 0 and 2 for the baseline and 15 and 18 for the candidate, in the same model order. The earlier Gemma run used different conditions.

We count execution failures as disagreement and withhold acceptance on failures. We report the proportions over observed terminal cells, plus candidate-minus-baseline differences from terminal pairs with a case-level percentile bootstrap. Correct acceptance refers to label agreement after the automated gate. Independent human evidence annotation remains outstanding. The official AVeriTeC evidence score is outside this protocol.

\subsection{Historical Gemma Dataset and Conditions}"""
)

paper = paper.replace(
    r"\section{Results}"+"\n"+r"\subsection{Paired Label Prediction}",
    r"""\section{Results}
\subsection{Interim DeepSeek Comparison}
The interim snapshot retains 47 of the 1,000 scheduled cells. The fresh run is checkpointed before its first new cell because the earlier pilot left fewer than the 12 Fetch URL slots reserved for a new cell. The other 450 claims contribute zero terminal cells. Table~\ref{tab:deepseek-results} uses observed cells as denominators for agreement and reports terminal counts against the target. All 24 baseline cells completed. Eight candidate cells completed and 15 failed. Neither arm timed out. Baseline acceptance coverage was 1/24, with one correct acceptance on the unpaired baseline cell. Candidate coverage was 0/23. Across the 23 terminal pairs, baseline and candidate correctly proposed 5 and 3 labels. The paired difference was $-8.7$ percentage points (95\pct\ paired bootstrap interval $-30.4$ to $+13.0$). No correct or incorrect acceptance occurred on the matched pairs.

\begin{table*}[t]
\caption{Interim DeepSeek outcomes. Accepted counts show correct/incorrect labels. Untouched cells contribute to the planned counts only.}
\label{tab:deepseek-results}
\centering
\footnotesize
\begin{tabular}{@{}llrrrr@{}}
\toprule
Stratum & Arm & Terminal/planned & Failed & Correct proposals & Accepted\\
\midrule
\DeepSeekRows
\bottomrule
\end{tabular}
\end{table*}

The reused cells generated 1,536,161 input and 395,590 output tokens on Ollama and 1,496,816 input and 185,349 output tokens on Jev. They reserved 185 searches and 366 Fetch URLs. Worker time including startup was about 70.4 minutes. At peak uncached list rates these tokens imply estimated costs of \$0.936 for Ollama and \$0.063 for Jev. Provider charges and cache or reasoning counts remain unavailable where the response does not report them. The journal separates worker time from quota waits and calendar time. Fresh usage is zero at this checkpoint.

\subsection{Historical Gemma Paired Label Prediction}"""
)

# Keep the substantive negative Flash development evidence and its tables from the newer draft.
flash_start = review.index(r"\subsection{Flash Workflow Development}")
flash_end = review.index(r"\section{Discussion and Limitations}", flash_start)
flash = review[flash_start:flash_end].replace(
    "Both candidate runs and both matched control runs on that split remained unstarted.",
    "The earlier four-arm release remained unstarted at that development checkpoint. The later resource pilot and one-model study have separate entry protocols."
)
paper = paper.replace(r"\section{Discussion and Limitations}", flash + r"\section{Discussion and Limitations}")
paper = paper.replace(
    "The paired comparison shows higher label accuracy for this combined workflow than for its control.",
    "The historical Gemma comparison shows higher label accuracy for its combined workflow than for its model-only control. The interim DeepSeek pairs have lower candidate proposal agreement and more candidate failures. The adaptive sample, wide interval and incomplete coverage limit that comparison."
)
paper = paper.replace(
    "Both sets of reported results can be checked from saved records without calling live services.",
    "The DeepSeek companion includes the case and configuration freeze, journal hashes and records, a separate attempt and service ledger, and the offline scorer and table commands. Historical records and their provenance remain separate. The artifact permits a recount without service calls. Provider revisions and live web state may differ in a new execution."
)

start = paper.index(r"\section{Conclusion}")
end = paper.index(r"\section*{Acknowledgment}", start)
paper = paper[:start] + r"""\section{Conclusion}
KajiAI preserves proposed verdicts, evidence decisions and research traces as separate records. The historical Gemma comparison measured higher proposal agreement than its model-only control, and the controlled stopping challenge lost correct acceptances when it skipped reassessment. The interim DeepSeek comparison retains the candidate's failures and sparse acceptance without establishing a qualified improvement. A quota checkpoint leaves 953 cells untouched. Completion requires accounting for those cells under the same freeze and auditing the resulting evidence and costs.

""" + paper[end:]
paper = paper.replace("OpenAI Codex assisted with drafting Sections I--VII,", "OpenAI Codex assisted with drafting and revision,")
paper = paper.replace(r"\begin{document}",r"\input{deepseek-results.tex}"+"\n"+r"\begin{document}",1)
(ROOT / "evaluation/paper.tex").write_text(paper, encoding="utf-8")


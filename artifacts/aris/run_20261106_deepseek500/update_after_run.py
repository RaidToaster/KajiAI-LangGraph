"""Refresh the DeepSeek paper text at a terminal or between-attempt boundary."""
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
s = json.loads((RUN/"summary.json").read_text(encoding="utf8"))
billing = json.loads((RUN/"builder-summary.json").read_text(encoding="utf8"))
p = ROOT/"evaluation/paper.tex"
paper = p.read_text(encoding="utf8")
pooled = s["strata"]["pooled_500"]
b, c = (pooled["arms"][a] for a in ("baseline","candidate"))
paired = pooled["paired_n"]
stage = "completed" if s["complete"] else "interim"
assert s["accounted"] > 47

def replace_between(text, start, end, content):
    i = text.index(start)
    return text[:i] + content + text[text.index(end,i):]

def comparison(group):
    low, high = group["paired_bootstrap_95"]["accuracy"]
    delta = group["paired_agreement_delta"]*100
    return f"{delta:+.1f} percentage points (95"+r"\pct{}"+f" paired bootstrap {low*100:+.1f} to {high*100:+.1f})"

abstract = (
    r"\begin{abstract}"+"\n"
    "KajiAI is a LangGraph workflow that separates proposed factual labels from evidence acceptance and retains retrieved text versions for audit. "
    "We froze a comparison of the current workflow and an evidence-adjudicated candidate on 500 AVeriTeC development claims with DeepSeek and a fixed Jev verifier. "
    f"This {stage} analysis accounts for {s['accounted']:,} of 1,000 cells, including 47 from a resource pilot. "
    f"The baseline proposed {b['correct_proposals']} correct labels in {b['attempted']} cells and the candidate proposed {c['correct_proposals']} in {c['attempted']}. "
    f"The arms recorded {b['failed']} and {c['failed']} execution failures and {b['correct_acceptances']} and {c['correct_acceptances']} correct acceptances, respectively. "
    f"Across {paired} terminal pairs, candidate-minus-baseline proposal agreement was {comparison(pooled)}. "
    "Pilot-based model selection, live retrieval and outstanding human citation adjudication limit inference.\n"
)
paper = replace_between(paper,r"\begin{abstract}",r"\end{abstract}",abstract)
results = (
    r"\subsection{" + ("DeepSeek Comparison" if s["complete"] else "Interim DeepSeek Comparison") + "}\n"
    + f"The analysis includes {s['accounted']} terminal cells and {paired} terminal pairs. "
    + r"Table~\ref{tab:deepseek-results} uses observed cells as denominators for proposal agreement. "
    + f"The candidate-minus-baseline difference was {comparison(pooled)}. "
    + "The workflow and transport failure records remain in the analysis. The companion records quota waits and any stop condition.\n\n"
)
status = s["status"]
if status["status"] == "quota_checkpoint":
    results += f"At the recorded Hobby quota checkpoint, {1000-s['accounted']} scheduled cells were untouched. "
    results += "Earlier Builder retrieval was counted in the rolling Fetch window. "
elif not s["complete"]:
    results += f"At this snapshot, {1000-s['accounted']} scheduled cells were untouched. "
results += "\n\n"
for key, name in (("selected_50","selected pilot stratum"),("other_450","other 450 claims")):
    group = s["strata"][key]
    if not any(m["attempted"] for m in group["arms"].values()):
        results += f"The {name} have no terminal cells. "
        continue
    results += f"For the {name}, "
    results += " and ".join(f"the {a} recorded {m['correct_proposals']}/{m['attempted']} correct proposals and "
                           f"{m['failed']} failure"+("s" if m["failed"] != 1 else "") for a,m in group["arms"].items() if m["attempted"])+". "
    if group["paired_n"]:
        results += f"The {group['paired_n']} terminal pairs gave a difference of {comparison(group)}. "
results += "\n\n"
section = r"\subsection{Interim DeepSeek Comparison}" if r"\subsection{Interim DeepSeek Comparison}" in paper else r"\subsection{DeepSeek Comparison}"
paper = replace_between(paper,section,r"\begin{table*}",results)
def total(resource, field, places=0):
    entry = resource.get(field,{})
    return f"{entry.get('observed_total',0):,.{places}f}"
body = ""
for cohort in ("reused","fresh"):
    resource = s["resources_by_source"][cohort]["resources"]
    body += (
        f"The {cohort} cohort recorded {total(resource,'ollama_input_tokens')} Ollama input and "
        f"{total(resource,'ollama_output_tokens')} output tokens, and {total(resource,'jev_input_tokens')} Jev input and "
        f"{total(resource,'jev_output_tokens')} output tokens. Its journal contains "
        f"{total(resource,'tinyfish_search_sends')} searches and {total(resource,'fetch_urls')} Fetch URL reservations. "
        f"Observed worker time was {total(resource,'active_seconds',1)} seconds. "
    )
body += ("The fresh retrieval ledger reserved "+r"\$"+str(billing["rate_derived_reserved_usd"])+
         " from the "+r"\$12"+" authorized Builder wallet. Rate-derived reservations are tracked separately from provider charges. "
         f"The fresh cohort contains {billing['fresh_builder_attempts']} Builder and {billing['fresh_hobby_attempts']} Hobby cells. "
         "The companion distinguishes measured and missing usage and separates round, startup, quota and service timing.\n\n")
resources = "The reused cells generated" if "The reused cells generated" in paper else "The reused cohort recorded"
paper = replace_between(paper,resources,r"\subsection{Historical Gemma Paired Label Prediction}",body)
policy = " After Builder, the Hobby phase reinstated the original zero-rate quota guard and counted all earlier retrieval in its rolling windows."
if policy not in paper:
    anchor = "Per-cell tariff receipts separate free and paid sends."
    assert anchor in paper
    paper = paper.replace(anchor, "Per-cell tariff receipts distinguish zero-rate and full-rate reservations."+policy, 1)
    paper = paper.replace("Builder paid phase: 150 searches/min and 250 Fetch URLs/min",
                          "Builder paid phase: 150 searches/min and 250 Fetch URLs/min. Hobby reinstates pilot pacing",1)
conclusion = (
    r"\section{Conclusion}"+"\n"
    "KajiAI preserves proposed verdicts, evidence decisions and research traces as separate records. "
    "The historical Gemma comparison measured higher proposal agreement than its model-only control, and the controlled stopping challenge lost correct acceptances when it skipped reassessment. "
    f"The frozen DeepSeek comparison accounts for {s['accounted']} of 1,000 scheduled cells at the recorded boundary. "
    "The evidence gate and retained failures define the reported acceptance and label agreement. Human evidence adjudication remains open.\n\n"
)
paper = replace_between(paper,r"\section{Conclusion}",r"\section*{Acknowledgment}",conclusion)
p.write_text(paper,encoding="utf8")



"""Rebuild the study report and paper table from the frozen journals offline."""
import csv
from datetime import datetime
from pathlib import Path
import statistics

import launch
from analyze_flash_study import extract_citations, paired_bootstrap, summarize
from kaji_langgraph.evaluation import ABSTAIN

RUN = launch.RUN
read, save, digest = launch.read, launch.save, launch.digest
ARMS = ("baseline", "candidate")
SERVICES = ("ollama", "jev", "tinyfish_search", "tinyfish_fetch")


def stats(values):
    known = sorted(v for v in values if v is not None)
    quantiles = statistics.quantiles(known, n=100, method="inclusive") if len(known) > 1 else known * 99
    return dict(observed=len(known), missing=len(values)-len(known), observed_total=sum(known),
                mean=statistics.mean(known) if known else None,
                median=statistics.median(known) if known else None,
                p90=quantiles[89] if known else None, p95=quantiles[94] if known else None)


def sum_known(values):
    return sum(values) if all(v is not None for v in values) else None


def load_rows(protocol, references):
    gold = read(RUN / "gold.json")
    selected = set(read(RUN / "selection.json")["pilot_order"])
    rows, ledger, audits = [], [], []
    for position, task in enumerate(protocol["schedule"], 1):
        identity = launch.fs.task_id(task)
        ref = references.get(identity)
        directory = launch.ROOT / ref["path"] if ref else RUN / "attempts" / identity
        if not directory.exists():
            continue
        attempt = read(directory / "attempt.json")
        assert all(attempt[k] == v for k, v in task.items())
        job_path = directory / "job.json"
        job = read(job_path) if job_path.exists() else {}
        record_path = directory / "result.json"
        record = read(record_path) if record_path.exists() else {}
        if record:
            assert record["requested_model"] == launch.MODEL and not record["gold_label"]
            assert all(record[k] == v for k, v in task.items())
        result = record.get("result", {})
        failed = (not result or not job or job["exit_code"] != 0 or
                  result["verification_status"] in ("execution_error", "invalid_input"))
        citations = extract_citations(result, 0.8) if result else []
        prediction = (record.get("predicted_label") or ABSTAIN) if not failed else ABSTAIN
        accepted = (record.get("accepted_label") or ABSTAIN) if not failed else ABSTAIN
        timing_path = directory / "worker-timing.json"
        workflow = read(timing_path).get("workflow_seconds") if timing_path.exists() else None
        active = job.get("elapsed_seconds")
        cumulative = [r["elapsed_seconds"] for r in result.get("research_history", []) if "elapsed_seconds" in r]
        elapsed = [b-a for a, b in zip([0]+cumulative, cumulative)]
        row = dict(attempt=identity, schedule_position=position, **task, source="reused" if ref else "fresh",
                   stratum="selected_50" if task["case"] in selected else "other_450",
                   terminal=bool(job), started_at=attempt["started_at"], finished_at=job.get("finished_at"),
                   completed=not failed, failed=failed and bool(job), timeout=job.get("timeout"),
                   operational_stop=job.get("operational_stop"), prediction=prediction, accepted=accepted,
                   gold_label=gold[task["case"]], citations=citations, active_seconds=active,
                   workflow_seconds=workflow, worker_overhead_seconds=max(0, active-workflow)
                   if workflow is not None and active is not None else None,
                   round_seconds=elapsed, stop_reason=result.get("stop_reason") or job.get("stop_reason"),
                   workflow_errors=result.get("errors", []), operational_problems=job.get("problems", []),
                   journal_path=directory.relative_to(launch.ROOT).as_posix())
        usage = launch.pilot.usage(directory, launch.MODEL)
        for send in usage:
            ledger.append({**send, "attempt": identity, "arm": task["arm"], "source": row["source"],
                           "journal_path": row["journal_path"]})
        for service in SERVICES:
            sends = [r for r in usage if r["service"] == service]
            row[f"{service}_sends"] = len(sends)
            row[f"{service}_seconds"] = sum_known([s.get("elapsed_seconds") for s in sends])
            if service in ("ollama", "jev"):
                for metric in ("input_tokens", "output_tokens", "estimated_usd"):
                    row[f"{service}_{metric}"] = sum_known([s.get(metric) if s.get("usage_known") else None for s in sends])
        row["fetch_urls"] = sum(s["url_attempts"] for s in usage if s["service"] == "tinyfish_fetch")
        row["unknown_sends"] = sum(not s.get("usage_known") for s in usage)
        row["unknown_model_reservations_usd"] = sum(
            s.get("reservation_usd") or 0 for s in usage if not s.get("usage_known"))
        rows.append(row)
        if accepted != ABSTAIN:
            audits.append(dict(attempt=identity, case=task["case"], citations=citations, human_adjudication=None))
    return rows, ledger, audits


def metrics(rows, ledger):
    terminal = [r for r in rows if r["terminal"]]
    n = len(terminal)
    scored = summarize(terminal) if n else None
    good = sum(r["prediction"] == r["gold_label"] for r in terminal)
    correct = sum(r["accepted"] == r["gold_label"] for r in terminal)
    wrong = sum(r["accepted"] not in (ABSTAIN, r["gold_label"]) for r in terminal)
    resource_fields = [k for k in rows[0] if k.endswith(
        ("_seconds", "_sends", "_urls", "_tokens", "_usd")) and k != "round_seconds"] if rows else []
    ids = {r["attempt"] for r in rows}
    return dict(started=len(rows), attempted=n, completed=sum(r["completed"] for r in terminal),
                failed=sum(r["failed"] for r in terminal), timeout=sum(r["timeout"] for r in terminal),
                correct_proposals=good, agreement=good/n if n else None, correct_acceptances=correct,
                incorrect_acceptances=wrong, coverage=(correct+wrong)/n if n else None, frozen_scores=scored,
                resources={k: stats([r[k] for r in rows]) for k in resource_fields},
                unknown_sends=sum(r["unknown_sends"] for r in rows),
                per_send_seconds={s: stats([r.get("elapsed_seconds") for r in ledger
                                           if r["service"] == s and r["attempt"] in ids]) for s in SERVICES},
                round_seconds=stats([t for r in rows for t in r["round_seconds"]]))


def group(rows, ledger):
    arms = {a: [r for r in rows if r["arm"] == a] for a in ARMS}
    pairs = [{r["case"]: r for r in arms[a] if r["terminal"]} for a in ARMS]
    matched = sorted(pairs[0].keys() & pairs[1].keys())
    b, c = ([p[k] for k in matched] for p in pairs)
    return dict(arms={a: metrics(arms[a], ledger) for a in ARMS}, paired_n=len(matched),
                paired_agreement_delta=(sum(r["prediction"] == r["gold_label"] for r in c) -
                                        sum(r["prediction"] == r["gold_label"] for r in b))/len(b) if b else None,
                paired_bootstrap_95=paired_bootstrap(b, c) if b else None)


def report(summary):
    target = RUN / "REPORT.md"
    next_cell = summary["next_untouched"] or "none"
    lines = ["# Frozen DeepSeek comparison", "",
             f"**{summary['accounted']:,}/1,000 cells accounted.** "
             f"{summary['reused']} reused and {summary['fresh_terminal']} fresh terminal cells. "
             f"Next untouched cell is `{next_cell}`.", "",
             summary["status_text"], "",
             "The 50-case stratum includes the early cases used to select DeepSeek. The remaining 450 follow the original manifest order. "
             "The candidate was unqualified at entry. The original evidence gates remained active. "
             "Proposal agreement is local label agreement. The official AVeriTeC evidence score was outside the scoring protocol.", "",
             "| Stratum | Arm | Target | Terminal | Completed | Failed | Timeout | Correct proposals | Correct acceptances | Incorrect acceptances | Coverage |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    tex = []
    for stratum, count in (("selected_50", 50), ("other_450", 450), ("pooled_500", 500)):
        for arm, m in summary["strata"][stratum]["arms"].items():
            n = m["attempted"]
            coverage = f"{m['coverage']:.1%}" if n else "—"
            a, w = m["correct_acceptances"], m["incorrect_acceptances"]
            lines.append(f"| {stratum} | {arm} | {count} | {n} | {m['completed']} | {m['failed']} | {m['timeout']} | {m['correct_proposals']} | {a} | {w} | {coverage} |")
            if stratum == "selected_50":
                tex.append(f"{arm.title()} & {n}/50 & {m['failed']} & {m['correct_proposals']}/{n} & {a} & {w} " + chr(92)*2)
        g = summary["strata"][stratum]
        if g["paired_n"]:
            low, high = g["paired_bootstrap_95"]["accuracy"]
            if stratum == "selected_50":
                tex.append(r"\def\DeepSeekPaired{" + f"{g['paired_n']}" + "}")
            lines.extend([])
    lines += ["", "## Paired agreement", ""]
    for stratum, g in summary["strata"].items():
        if g["paired_n"]:
            low, high = g["paired_bootstrap_95"]["accuracy"]
            lines.append(f"- {stratum} has {g['paired_n']} terminal pairs. Candidate minus baseline "
                         f"is {g['paired_agreement_delta']*100:+.1f} percentage points "
                         f"(95% paired bootstrap {low*100:+.1f} to {high*100:+.1f}).")
        else:
            lines.append(f"- {stratum} has no terminal pairs.")
    lines += ["", "## Measured resources", "",
              "| Source | Ollama input / output | Jev input / output | Search / Fetch URLs | Worker s | Ollama / Jev estimated USD |",
              "|---|---|---|---|---:|---|"]
    for source, m in summary["resources_by_source"].items():
        def number(metric, places=0):
            data = m["resources"].get(metric, {})
            value = data.get("observed_total", 0)
            return f"{value:,.{places}f}" + (" observed" if data.get("missing") else "")
        lines.append(f"| {source} | {number('ollama_input_tokens')} / {number('ollama_output_tokens')} | "
                     f"{number('jev_input_tokens')} / {number('jev_output_tokens')} | "
                     f"{number('tinyfish_search_sends')} / {number('fetch_urls')} | {number('active_seconds',1)} | "
                     f"{number('ollama_estimated_usd',4)} / {number('jev_estimated_usd',4)} |")
    lines += ["", "Per-arm means, medians, P90/P95, per-send and round times, paired intervals, and cohort timing are in `summary.json`.",
              "The ledger retains recorded cache and reasoning fields when the provider supplied them. Actual charges are unavailable. "
              "The estimate uses peak uncached Ollama rates of $0.30 input and $1.20 output per million tokens and "
              "Jev's $0.042 per million input tokens. TinyFish Search and Fetch are free within the authorized limits.", "",
              "Historical GLM outcomes and the separate Gemma study are outside these tables. "
              "Any accepted cases in `acceptance-audit.json` await independent human adjudication.", ""]
    target.write_text("\n".join(lines), encoding="utf-8")
    # Keep only tabular rows in the include file.
    (RUN / "deepseek-rows.tex").write_text("\n".join(row for row in tex if not row.startswith(chr(92)))+"\n", encoding="utf-8")


def main():
    protocol, refs = launch.verify(), launch.prior_check()
    rows, ledger, audits = load_rows(protocol, refs)
    flat = [{k: v for k, v in row.items() if k != "citations"} for row in rows]
    with (RUN / "attempts.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    save(RUN / "service-ledger.json", ledger)
    save(RUN / "acceptance-audit.json", audits)
    started = {r["attempt"] for r in rows}
    accounted = sum(r["terminal"] for r in rows)
    status_path = RUN / "status.json"
    status = read(status_path) if status_path.exists() else {"status": "preflight"}
    next_cell = next((launch.fs.task_id(t) for t in protocol["schedule"] if launch.fs.task_id(t) not in started), None)
    text = {
        "preflight": "Preflight only. No fresh cell has started.",
        "quota_checkpoint": f"Between-attempt quota checkpoint. Earliest quota eligibility was recorded as {status.get('resume_at')}.",
        "operational_stop": f"Operational stop at {status.get('attempt')}. Reconcile the recorded condition before dispatch.",
        "complete": "All scheduled cells have terminal records.",
    }.get(status["status"], f"Snapshot status is {status['status']}.")
    summary = dict(accounted=accounted, reused=len(refs), fresh_terminal=accounted-len(refs),
                   next_untouched=next_cell, status=status, status_text=text,
                   complete=accounted == 1000, protocol_sha256=digest(RUN / "protocol.json"),
                   strata={k: group([r for r in rows if r["stratum"] == k], ledger) for k in ("selected_50", "other_450")},
                   resources_by_source={k: metrics([r for r in rows if r["source"] == k], ledger) for k in ("reused", "fresh")},
                   cohort_timing={}, provider_billing_usd=None)
    summary["strata"]["pooled_500"] = group(rows, ledger)
    for source in ("reused", "fresh"):
        cohort = [r for r in rows if r["source"] == source and r["finished_at"]]
        if cohort:
            first = min(datetime.fromisoformat(r["started_at"]) for r in cohort)
            last = max(datetime.fromisoformat(r["finished_at"]) for r in cohort)
            summary["cohort_timing"][source] = dict(calendar_seconds=(last-first).total_seconds(),
                worker_seconds=sum(r["active_seconds"] for r in cohort),
                other_elapsed_seconds=(last-first).total_seconds()-sum(r["active_seconds"] for r in cohort))
    summary["quota_boundaries"] = [read(p) for p in sorted((RUN / "quota-boundaries").glob("*.json"))]
    save(RUN / "summary.json", summary)
    report(summary)
    print(f"{accounted}/1000; next untouched: {next_cell}; {text}")


if __name__ == "__main__":
    main()


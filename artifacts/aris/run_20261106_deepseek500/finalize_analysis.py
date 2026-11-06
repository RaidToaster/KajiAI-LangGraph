"""Recount frozen study records, including reactive stop and tariff receipts."""
from collections import Counter
from datetime import datetime
from decimal import Decimal

import analyze
import analyze_paid
import hobby_reactive
import launch
import report_builder

RUN = launch.RUN
read, save = launch.read, launch.save
original_metrics = analyze.metrics


def usage(directory, model):
    rows = analyze_paid.usage(directory, model)
    record = hobby_reactive.overlay(directory)
    if record:
        for row in rows:
            outcome = record["outcomes"].get(row["request_id"])
            if outcome:
                row.update(outcome)
                row["reconciliation_receipt"] = f"reactive-outcomes/{directory.name}.json"
    return rows


def metrics(rows, ledger):
    result = original_metrics(rows, ledger)
    ids = {row["attempt"] for row in rows}
    sends = [send for send in ledger if send["attempt"] in ids]
    result["send_resources"] = {}
    for service in analyze.SERVICES:
        records = [send for send in sends if send["service"] == service]
        resource = {
            "count": len(records),
            "outcomes": dict(Counter(send.get("provider_outcome") or
                                      ("CAPTURED" if send["usage_known"] else "UNKNOWN")
                                      for send in records)),
        }
        if service in {"ollama", "jev"}:
            for name in ("input_tokens", "output_tokens", "estimated_usd"):
                resource[name] = analyze.stats([r.get(name) if r["usage_known"] else None for r in records])
            resource["unknown_reserved_usd"] = sum(
                (r.get("reservation_usd") or 0) for r in records if not r["usage_known"]
            )
        result["send_resources"][service] = resource
    return result


def failure_category(row, sends):
    if row["timeout"]:
        return "worker_timeout"
    if any(send.get("provider_outcome") == "RATE_REJECTED" for send in sends):
        return "provider_rate_rejection"
    problems = row["operational_problems"]
    if "transport failure; no retry" in problems or any(
        not send["usage_known"] or send["status"] != 200 for send in sends
    ):
        return "service_or_capture_failure"
    if any(problem.endswith(" request cap") for problem in problems):
        return "per_cell_request_cap"
    if "spend reservation ceiling" in problems:
        return "spend_cap"
    return "workflow_failure"


def validate_rows(protocol, refs, rows, ledger):
    schedule = [launch.fs.task_id(task) for task in protocol["schedule"]]
    assert len(schedule) == len(set(schedule)) == 1000
    cases = {task["case"] for task in protocol["schedule"]}
    assert len(cases) == 500
    assert Counter(task["arm"] for task in protocol["schedule"]) == {"baseline": 500, "candidate": 500}
    assert Counter(task["case"] for task in protocol["schedule"]) == dict.fromkeys(cases, 2)
    assert len(refs) == 47
    fresh = [cell for cell in schedule if cell not in refs]
    assert [row["attempt"] for row in rows if row["source"] == "fresh"] == fresh[:len(rows)-len(refs)]
    assert all(row["terminal"] and row["completed"] != row["failed"] for row in rows)
    assert len({(send["attempt"], send["request_id"]) for send in ledger}) == len(ledger)
    by_attempt = {row["attempt"]: [] for row in rows}
    for send in ledger:
        by_attempt[send["attempt"]].append(send)
        service = send["service"]
        if service in {"ollama", "jev"}:
            expected = launch.MODEL if service == "ollama" else "jev-1.13.0"
            assert send["requested_model"] == expected
            if send["usage_known"]:
                assert send["model_verified"]
    for row in rows:
        directory = launch.ROOT / row["journal_path"]
        sends = by_attempt[row["attempt"]]
        counts = Counter(send["service"] for send in sends)
        state = read(directory / "live-state.json")
        assert counts == +Counter(state["counts"]), row["attempt"]
        assert all(count <= protocol["caps"][service] for service, count in counts.items())
        assert row["fetch_urls"] <= protocol["caps"]["tinyfish_fetch"]
    return by_attempt


def timing(rows):
    fresh = [row for row in rows if row["source"] == "fresh"]
    if not fresh:
        return {}
    parse = datetime.fromisoformat
    start, end = parse(fresh[0]["started_at"]), parse(fresh[-1]["finished_at"])
    worker = sum(row["active_seconds"] for row in fresh)
    active_workflow = sum(row["workflow_seconds"] or 0 for row in fresh)
    launches = [read(path) for path in sorted(RUN.glob("launch-*.json"))]
    startup = sum((parse(r["coordinator_ready_at"]) - parse(r["started_at"])).total_seconds() for r in launches)
    provider_wait = 0.0
    for row, following in zip(fresh, fresh[1:]):
        overlay = hobby_reactive.overlay(launch.ROOT / row["journal_path"])
        if overlay and overlay["resume_at"]:
            begin = parse(row["finished_at"])
            stop = min(parse(overlay["resume_at"]), parse(following["started_at"]))
            provider_wait += max(0, (stop - begin).total_seconds())
    return dict(first_start=start.isoformat(), last_finish=end.isoformat(),
                calendar_seconds=(end-start).total_seconds(), worker_seconds=worker,
                observed_workflow_seconds=active_workflow,
                workers_missing_workflow_time=sum(row["workflow_seconds"] is None for row in fresh),
                recorded_startup_seconds=startup, provider_rejection_wait_upper_bound_seconds=provider_wait,
                calendar_minus_worker_seconds=(end-start).total_seconds()-worker)


def main():
    protocol, refs = launch.verify(), launch.prior_check()
    hobby_reactive.policy(protocol)
    launch.pilot.usage = usage
    analyze.metrics = metrics
    original = analyze.load_rows
    rows, ledger, audits = original(protocol, refs)
    by_attempt = validate_rows(protocol, refs, rows, ledger)
    analyze.load_rows = lambda _protocol, _refs: (rows, ledger, audits)
    analyze.main()
    report_builder.main()
    billing = read(RUN / "builder-summary.json")
    summary = read(RUN / "summary.json")
    summary["fresh_timing"] = timing(rows)
    assert summary["accounted"] == len(rows)
    if summary["complete"]:
        assert summary["status"]["status"] == "complete" and summary["next_untouched"] is None
        assert all(group["paired_n"] == int(key.split("_")[-1]) for key, group in summary["strata"].items())
    caps = protocol["scheduling_cost_caps_usd"]
    for service, limit in caps.items():
        resource = summary["resources_by_source"]["fresh"]["send_resources"][service]
        known = Decimal(str(resource["estimated_usd"]["observed_total"]))
        unknown = Decimal(str(resource["unknown_reserved_usd"]))
        assert known + unknown <= Decimal(str(limit)), (service, known, unknown, limit)
    for name, group in summary["strata"].items():
        for arm, arm_summary in group["arms"].items():
            failed = [r for r in rows if r["failed"] and r["arm"] == arm
                      and (name == "pooled_500" or r["stratum"] == name)]
            arm_summary["failure_categories"] = dict(Counter(
                failure_category(r, by_attempt[r["attempt"]]) for r in failed
            ))
    summary["tariffs"] = {k: v for k, v in billing.items() if k != "attempts"}
    save(RUN / "summary.json", summary)

    report = RUN / "REPORT.md"
    content = report.read_text(encoding="utf8")
    start = content.index("## Measured resources")
    end = content.index("Historical GLM outcomes", start)
    lines = ["## Measured resources", "",
             "| Cohort | Ollama input / output | Jev input / output | Search / Fetch URLs | Worker s | Ollama / Jev estimated USD |",
             "|---|---|---|---|---:|---|"]
    for cohort, result in summary["resources_by_source"].items():
        resources = result["send_resources"]
        def total(service, field, places=0):
            measure = resources[service][field]
            return f"{measure['observed_total']:,.{places}f}"
        lines.append(
            f"| {cohort} | {total('ollama', 'input_tokens')} / {total('ollama', 'output_tokens')} | "
            f"{total('jev', 'input_tokens')} / {total('jev', 'output_tokens')} | "
            f"{resources['tinyfish_search']['count']} / {resources['tinyfish_fetch']['count']} | "
            f"{result['resources']['active_seconds']['observed_total']:,.1f} | "
            f"{total('ollama', 'estimated_usd', 4)} / {total('jev', 'estimated_usd', 4)} |"
        )
    lines += ["", "Token and cost totals sum known sends. The JSON summary retains missing counts, per-send and per-cell means, "
              "medians and P90/P95, round durations, and conservative reservations for unobserved model usage. "
              "Peak uncached rates are USD 0.30 per million Ollama input tokens and USD 1.20 per million output tokens. "
              "Jev costs USD 0.042 per million input tokens. Provider invoices were unavailable.", ""]
    content = content[:start] + "\n".join(lines) + "\n" + content[end:]
    content += ("\n## Retrieval tariff and execution changes\n\n"
                f"Builder applied to {billing['fresh_builder_attempts']} fresh cells. "
                f"At USD 0.005 per Search and USD 0.001 per Fetch URL it reserved USD {billing['rate_derived_reserved_usd']} "
                f"of the USD {billing['wallet_ceiling_usd']} cap. The verified zero-rate Hobby tier applied to "
                f"{billing['fresh_hobby_attempts']} fresh cells. After the Hobby checkpoint, the resumed dispatcher removed local "
                "minute, hourly, rolling-day and full-cell quota checks. It waited after a recorded provider rejection. "
                "The original caps, frozen workflow and single worker remained in force. "
                "Read-only reconciliation records and unresolved reservations appear in the service ledger. "
                "Neither a reconciliation nor a provider wait replaces a failed cell.\n")
    content += "\n## Failure categories\n\n"
    for arm, result in summary["strata"]["pooled_500"]["arms"].items():
        items = ", ".join(f"{name}={count}" for name, count in sorted(result["failure_categories"].items()))
        content += f"- {arm}: {items or 'none'}.\n"
    content += ("\n## Timing boundaries\n\n"
                "The JSON summary separates recorded worker and workflow time, Ollama startup receipts, and calendar elapsed. "
                "The provider wait measure is bounded by the rejected cell's finish and the next start. "
                "Historical quota checkpoints preserve intended wake times. Calendar time outside the worker also includes "
                "operator actions, read-only history, coordination and interruptions. Those components cannot all be "
                "disaggregated from the recorded timestamps.\n")
    report.write_text(content, encoding="utf8")


if __name__ == "__main__":
    main()

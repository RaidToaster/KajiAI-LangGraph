"""Keep raw transport failure metrics and attach proven provider outcomes in the report."""
import analyze
import launch
import recover_fetch
import report_builder

original_usage = launch.pilot.usage


def usage(directory, model):
    rows = original_usage(directory, model)
    receipts = {"tinyfish_fetch": {**recover_fetch.carried_fetch(directory), **recover_fetch.confirmed(directory)},
                "tinyfish_search": recover_fetch.carried_search(directory)}
    dns = recover_fetch.carried_dns(directory)
    for row in rows:
        service = receipts.get(row["service"], {})
        identity = row["request_id"]
        outcome = service.get(identity) or dns.get((row["service"],identity))
        if outcome:
            row["provider_outcome"], row["reconciliation_receipt"] = outcome
    return rows


if __name__ == "__main__":
    launch.pilot.usage = usage
    analyze.main()
    report_builder.main()
    run = launch.RUN
    report = run/"REPORT.md"
    content = report.read_text(encoding="utf8")
    content = content.replace(
        "TinyFish Search and Fetch are free within the authorized limits.",
        "TinyFish's pilot retrieval was free. The Builder phase reserves the verified rate for every paid-phase send."
    )
    billing = launch.read(run/"builder-summary.json")
    summary = launch.read(run/"summary.json")
    content += (
        "\n## Builder retrieval and continuation\n\n"
        f"Fresh retrieval reserved USD {billing['rate_derived_reserved_usd']} of the USD {billing['wallet_ceiling_usd']} cap. "
        "The full-rate reservation counts all sends, including unsuccessful sends. "
        "The worker timeout column counts 300-second worker expirations. Individual transport timeouts remain in the service ledger.\n\n"
    )
    carry_path = run/"carry-unknown-search.json"
    if carry_path.exists():
        record = launch.read(carry_path)
        content += (
            f"Request {record['request_id']} on {record['attempt']} was carried forward as UNKNOWN after three read-only history checks. "
            f"Its USD {record['reserved_usd']} Search reservation and original workflow failure remain in the ledgers. The cell was never replayed.\n\n"
        )
    stop_path = run/"STOP.json"
    if stop_path.exists():
        stop = launch.read(stop_path)
        reasons = ", ".join(stop["problems"])
        content += f"The latest operational stop was {stop['attempt']} ({reasons}).\n\n"
    if (run/"hobby-amendment.json").exists():
        content += (
            "The resumed Hobby phase uses zero-rated Search and Fetch and the original rolling quotas, including prior Builder activity. "
            f"Terminal fresh cells by phase: {billing['fresh_builder_attempts']} Builder and {billing['fresh_hobby_attempts']} Hobby.\n\n"
        )
    status = summary["status"]
    if status.get("reason"):
        content += f"Recorded boundary reason: {status['reason']}.\n\n"
    report.write_text(content,encoding="utf8")

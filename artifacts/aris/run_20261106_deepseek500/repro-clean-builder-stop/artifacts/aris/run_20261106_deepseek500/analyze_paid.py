"""Keep raw transport failure metrics and attach proven provider outcomes in the report."""
import analyze
import launch
import recover_fetch
import report_builder

original_usage = launch.pilot.usage


def usage(directory, model):
    rows = original_usage(directory, model)
    resolved = recover_fetch.confirmed(directory)
    for row in rows:
        if row["service"] == "tinyfish_fetch" and row["request_id"] in resolved:
            row["provider_outcome"], row["reconciliation_receipt"] = resolved[row["request_id"]]
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
    wallet = launch.read(run/"builder-wallet-stop.json")
    content += (
        "\n## Builder billing and stop\n\n"
        f"Fresh retrieval reserved ${billing['rate_derived_reserved_usd']} of the ${billing['wallet_ceiling_usd']} cap. "
        f"The wallet showed ${wallet['available_balance']} at the stop, compared with $12.000 at the transition. "
        "The account-level balance change does not attribute charges to individual sends. "
        "The full-rate reservation counts all sends, including unsuccessful sends.\n\n"
        "The coordinator stopped at TinySearch request 007 for dev-427-deepseek-candidate. "
        "The remote connection closed before an HTTP response. Read-only provider history matched a neighboring search "
        "and returned no terminal record for the reset request. The request stays UNKNOWN and its reservation is retained. "
        "The next untouched cell is dev-373-deepseek-baseline. Resume requires a terminal provider outcome or a documented reconciliation rule. "
        "The worker timeout column counts 300-second worker expirations. Individual transport timeouts remain in the service ledger.\n"
    )
    report.write_text(content,encoding="utf8")


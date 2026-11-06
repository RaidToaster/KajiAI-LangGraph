"""Add Builder amendment and fresh journals to the credential-scanned archive."""
import package

RUN = package.RUN
prior = package.inputs


def inputs():
    files = set(prior())
    for name in ("builder.py", "builder-amendment.json", "run-builder.ps1", "BUILDER_AMENDMENT.md",
                  "builder-wallet-current.json", "builder-spend.json", "builder-summary.json", "report_builder.py",
                 "builder_paid.py", "run-builder-paid.ps1", "builder-paid-amendment.json", "builder-paid-wallet-current.json",
                 "analyze_paid.py", "recover_fetch.py", "reconcile_fetch.py", "keep-builder.ps1",
                 "archive_recovered_stop.py", "supervisor-hashes.json",
                 "reconcile_search.py", "builder-wallet-stop.json"):
        files.add(RUN / name)
    for pattern in ("attempts/*/*", "launch-*.json", "quota-boundaries/*.json", "fetch-reconciliation-*.json", "search-reconciliation-*.json", "stop-dev-*.json", "status-dev-*.json"):
        files.update(path for path in RUN.glob(pattern) if path.is_file())
    if (RUN / "carry-unknown-search.json").exists():
        files.add(RUN / "carry-unknown-search.json")
        files.update((RUN / "builder-paid-before-search-resume").glob("*"))
    for pattern in ("builder-paid-before-*/*", "unknown-fetch-carried/*.json", "dns-reservation-carried/*.json",
                    "dns-resolved-*.json", "unknown-fetch-policy.json", "dns-carry-policy.json",
                    "hobby*.py", "hobby-amendment.json", "hobby-wallet-current.json",
                    "keep-hobby.ps1", "run-hobby.ps1", "stop-before-hobby.json", "pause-before-hobby.json",
                    "status-before-tier-pause.json"):
        files.update(path for path in RUN.glob(pattern) if path.is_file())
    if (RUN / "STOP.json").exists():
        files.add(RUN / "STOP.json")
    return sorted(files)


if __name__ == "__main__":
    package.inputs = inputs
    package.main()


"""Build the indexed reproduction archive using an explicit credential-free allowlist."""
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def inputs():
    protocol = read(RUN/"protocol.json")
    paths = {RUN/name for name in protocol["freeze_files"]}
    for ref in read(RUN/"reused.json").values():
        paths.update(ROOT/ref["path"]/name for name in ref["files"])
    paths.update(ROOT/name for name in protocol["historical_hashes"])
    paths.update(RUN/name for name in (
        "protocol.json", "approval.json", "account-confirmation.json", "status.json",
        "REPORT.md", "FORECAST.md", "CODE_AUDIT.md", "summary.json", "attempts.csv", "service-ledger.json",
        "acceptance-audit.json", "offline-check.json", "forecast.py", "forecast.json", "render_table.py",
        "REPRODUCE.md", "INVOCATION_REVIEW.md", "PAPER_CLAIM_AUDIT.md", "PAPER_CLAIM_AUDIT.json",
    ))
    paths.update((RUN/"quota-boundaries").glob("*.json"))
    paths.update((RUN/"predispatch-v1").glob("*"))
    paths.add(RUN.with_name("run_20261106_pilot50")/"environment.json")
    paths.update(ROOT/"evaluation"/name for name in ("paper.tex", "deepseek-results.tex"))
    paths.update((ROOT/"evaluation/paper-figures").glob("*"))
    return sorted(paths)


def secret_values():
    values = []
    for line in (ROOT/".env").read_text(encoding="utf8").splitlines():
        key, _, value = line.partition("=")
        if re.search(r"(?i)(key|token|secret|password)", key) and not key.lstrip().startswith("#"):
            secret = value.strip().strip("\x22\x27").encode()
            if len(secret) >= 12:
                values.append(secret)
    return values


def assert_clean(data, name, secrets):
    assert not any(value in data for value in secrets), f"Credential match in {name}"
    if name.endswith(".zip"):
        with ZipFile(BytesIO(data)) as nested:
            for item in nested.infolist():
                assert Path(item.filename).name not in {".env", "id_ed25519", "id_rsa"}
                assert_clean(nested.read(item), f"{name}/{item.filename}", secrets)


def main():
    secrets = secret_values()
    output = RUN/"deepseek500-reproducibility.zip"
    temporary = output.with_suffix(".zip.tmp")
    paths = inputs()
    with ZipFile(temporary,"w",ZIP_DEFLATED) as archive:
        for path in paths:
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            assert_clean(data, name, secrets)
            archive.writestr(name, data)
    temporary.replace(output)
    print(f"{len(paths)} files passed credential exclusion and were packaged")


if __name__ == "__main__":
    main()


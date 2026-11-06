"""Package an audited paper source and reproducibility archive from allowlisted inputs."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import extend_package
import package

RUN, ROOT = package.RUN, package.ROOT
EVALUATION = ROOT / "evaluation"
SOURCE = EVALUATION / "paper-source.zip"
FLASH = ROOT / "artifacts/flash-workflow-20261103"


def write_archive(output, paths, index=False):
    secrets = package.secret_values()
    temporary = output.with_suffix(".zip.tmp")
    hashes = {}
    with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
        for name, path in sorted(paths.items()):
            data = path.read_bytes()
            package.assert_clean(data, name, secrets)
            archive.writestr(name, data)
            if index:
                hashes[name] = hashlib.sha256(data).hexdigest()
        if index:
            archive.writestr("REPRO-MANIFEST.json", json.dumps(hashes, indent=2) + "\n")
    temporary.replace(output)
    print(f"{len(paths)} credential-scanned files in {output}")


def paper_source():
    files = {name: EVALUATION / name for name in ("paper.tex", "deepseek-results.tex")}
    files["README.md"] = RUN / "BUILD-PAPER.md"
    for path in (EVALUATION / "paper-figures").glob("*"):
        if path.is_file():
            files[path.relative_to(EVALUATION).as_posix()] = path
    write_archive(SOURCE, files)


def reproduction():
    paths = set(extend_package.inputs())
    paths.add(FLASH / "flash-study-negative-development-20261104-verified.zip")
    paths.update(RUN / name for name in (
        "hobby_reactive.py", "reconcile_reactive.py", "run-hobby-reactive.ps1", "hobby-reactive-amendment.json",
        "hobby_reactive_v2.py", "reconcile_reactive_v2.py", "run-hobby-reactive-v2.ps1",
        "hobby-reactive-amendment-v2.json", "hobby-reactive-wallet-v2.json", "REACTIVE_AMENDMENT.md",
        "hobby-reactive-wallet.json", "finalize_analysis.py", "finalize_paper.py", "pack_final.py",
        "verify_paper_build.py", "historical_tables.py", "verify_extraction.py",
        "VERIFICATION.md", "verification.json", "BUILD-PAPER.md", "REPRODUCE-FINAL.md",
    ))
    for pattern in ("reactive-outcomes/*", "reactive-v1/*", "hobby-reactive-wallet-*.json",
                    "wallet-refresh-error.json"):
        paths.update(path for path in RUN.glob(pattern) if path.is_file())
    paths.update((EVALUATION / "paper.pdf", SOURCE, EVALUATION / "generate_paper_figures.py"))
    write_archive(RUN / "deepseek500-reproducibility.zip", {p.relative_to(ROOT).as_posix(): p for p in paths}, index=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", choices=("source", "reproduction"))
    args = parser.parse_args()
    (paper_source if args.artifact == "source" else reproduction)()

"""Verify an extracted companion and regenerate its DeepSeek outputs offline."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

STUDY = Path("artifacts/aris/run_20261106_deepseek500")
DERIVED = (
    *(STUDY / name for name in ("summary.json", "REPORT.md", "attempts.csv", "service-ledger.json",
                               "builder-summary.json", "acceptance-audit.json")),
    Path("evaluation/deepseek-results.tex"),
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("extraction", type=Path)
    parser.add_argument("--index-only", action="store_true")
    args = parser.parse_args()
    root = args.extraction.resolve()
    index = json.loads((root / "REPRO-MANIFEST.json").read_text(encoding="utf8"))
    for name, sha in index.items():
        path = (root / name).resolve()
        assert path.is_relative_to(root) and digest(path) == sha, name
    if not args.index_only:
        for command in (
            [STUDY / "finalize_analysis.py"],
            [STUDY / "finalize_paper.py", STUDY / "summary.json", DERIVED[-1]],
        ):
            subprocess.run([sys.executable, *map(str, command)], cwd=root, check=True)
        for path in DERIVED:
            assert digest(root / path) == index[path.as_posix()], path
    print(json.dumps({"indexed_files_verified": len(index),
                      "regenerated_and_matched": [] if args.index_only else [p.as_posix() for p in DERIVED]}))


if __name__ == "__main__":
    main()

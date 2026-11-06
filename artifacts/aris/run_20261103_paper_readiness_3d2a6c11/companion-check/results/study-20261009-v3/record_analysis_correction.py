"""Prove that the completed study's inference remains identical to its archive."""
import hashlib
import json
from pathlib import Path
import zipfile

from kaji_langgraph.evaluation import code_digest

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
status = json.loads((ROOT / "status.json").read_text())
assert status["complete"] and not status["halted"]
manifest = json.loads((ROOT / "manifest.json").read_text())
metrics = json.loads((ROOT / "study-metrics.json").read_text())
changes = []
with zipfile.ZipFile(ROOT / "source-snapshot.zip") as archive:
    for name in archive.namelist():
        old = archive.read(name)
        new = (REPO / name).read_bytes()
        if old != new:
            changes.append({"path": name, "old_sha256": hashlib.sha256(old).hexdigest(),
                            "new_sha256": hashlib.sha256(new).hexdigest()})
assert [change["path"] for change in changes] == ["src/kaji_langgraph/study_analysis.py"]
for condition, key in [("full", "full_results_sha256"), ("closed_book", "model_only_results_sha256")]:
    assert hashlib.sha256((ROOT / condition / "results.jsonl").read_bytes()).hexdigest() == metrics["analysis_provenance"][key]
payload = {"scope": "Post-study correction of archive-wrapped hostname exposure audit only",
           "live_study_complete_before_source_edit": True, "changed_archived_files": changes,
           "frozen_source_sha256": manifest["code_sha256"], "current_source_sha256": code_digest(),
           "inference_files_byte_identical": True, "raw_results_unchanged": True,
           "tests": "Archived-host regression reproduced before fix; 9 study tests passed after fix.",
           "note": "Frozen source archive remains authoritative for the evaluated run. Use a new output directory for future live evaluations with edited analysis source."}
(ROOT / "analysis-correction.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(json.dumps(payload, indent=2))

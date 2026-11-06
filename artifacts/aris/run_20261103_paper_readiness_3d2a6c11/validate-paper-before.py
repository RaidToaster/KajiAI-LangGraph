"""Validate and package the revised IEEE manuscript without changing inference."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import zipfile

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--visual-review-complete", action="store_true")
parser.add_argument("--build-directory", type=Path, default=ROOT / "paper-build",
                    help="Build containing paper.pdf and compilation.json for this revision.")
parser.add_argument("--audit-directory", type=Path,
                    help="Include the current offline audit's reports and reproducibility scripts.")
args = parser.parse_args()
build = args.build_directory.resolve()
diagnostic = json.loads((build / "compilation.json").read_text(encoding="utf-8-sig"))
assert diagnostic["exitCode"] == 0 and diagnostic["pdfExists"]
log = "\n".join(attempt.get("log", "") for attempt in diagnostic["attempts"])
(build / "compiler-output.log").write_text(log, encoding="utf-8")
assert "Overfull" not in log
reader = PdfReader(build / "paper.pdf")
assert len(reader.pages) > 0
text = "\n".join(page.extract_text() for page in reader.pages)
assert "[?]" not in text
for evidence in ["500", "624a8d2fa125", "499793726b4a", "OpenAI Codex"]:
    assert evidence in text, evidence
source = (ROOT / "paper.tex").read_text(encoding="utf-8")
cited = {key for group in re.findall(r"\\cite\{([^}]+)\}", source) for key in group.split(",")}
bibliography = set(re.findall(r"\\bibitem\{([^}]+)\}", source))
assert cited == bibliography and len(bibliography) == 11
assert source.count(r"\begin{table}") == 4 and source.count(r"\begin{figure}") == 2
metrics_path = ROOT / "results/study-20261009-v3/study-metrics.json"
metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
assert metrics["complete"] is True and metrics["n"] == 500
for name in ["majority_baseline", "closed_book_predictions", "first_round_prediction", "full_predictions"]:
    value = metrics["metrics"][name]
    assert f"{100*value['accuracy']:.1f}" in text
    assert f"{value['macro_f1']:.3f}" in text
assert f"{100*metrics['metrics']['full_policy']['coverage']:.1f}" in text
assert "remaining 415 tasks" not in source and "177-claim subset" not in source
provenance = json.loads((ROOT / "paper-figures/provenance.json").read_text(encoding="utf-8"))
assert provenance["complete"] is True and provenance["matched_n"] == 500
assert provenance["source_metrics_sha256"] == hashlib.sha256(metrics_path.read_bytes()).hexdigest()
fonts = {}
visited = set()
def inspect_resources(resources):
    resources = resources.get_object()
    for value in resources.get("/Font", {}).values():
        font = value.get_object()
        if "/DescendantFonts" in font:
            font = font["/DescendantFonts"][0].get_object()
        descriptor = font.get("/FontDescriptor")
        if descriptor:
            descriptor = descriptor.get_object()
        fonts[str(font.get("/BaseFont"))] = bool(descriptor and any(
            field in descriptor for field in ["/FontFile", "/FontFile2", "/FontFile3"]))
    for value in resources.get("/XObject", {}).values():
        obj = value.get_object()
        if id(obj) not in visited and "/Resources" in obj:
            visited.add(id(obj))
            inspect_resources(obj["/Resources"])
for page in reader.pages:
    inspect_resources(page["/Resources"])
assert all(fonts.values())
shutil.copyfile(build / "paper.pdf", ROOT / "paper.pdf")
files = [
    ROOT / "paper.tex",
    ROOT / "paper-partial.tex",
    ROOT / "paper-notes.md",
    ROOT / "generate_paper_figures.py",
    ROOT / "update_paper_results.py",
    ROOT / "validate_paper.py",
    ROOT / "write_paper_notes.py",
    ROOT / "paper-figures/acceptance-thresholds.pdf",
    ROOT / "paper-figures/acceptance-thresholds.svg",
    ROOT / "paper-figures/acceptance-thresholds.png",
    ROOT / "paper-figures/provenance.json",
    metrics_path,
    ROOT / "results/study-20261009-v3/RESULTS.md",
    ROOT / "results/study-20261009-v3/manifest.json",
    ROOT / "results/study-20261009-v3/final_analysis.py",
    ROOT / "results/study-20261009-v3/diagnostics.json",
    ROOT / "results/study-20261009-v3/runtime-incidents.json",
    ROOT / "results/study-20261009-v3/per-claim-results.csv",
    ROOT / "results/study-20261009-v3/human-audit-instructions.md",
    ROOT / "results/study-20261009-v3/analysis-correction.json",
    ROOT / "results/study-20261009-v3/record_analysis_correction.py",
]
if args.audit_directory:
    files.extend(path for path in args.audit_directory.resolve().iterdir()
                 if path.is_file() and path.suffix in {".md", ".json", ".csv", ".py", ".txt", ".diff"})
with zipfile.ZipFile(ROOT / "paper-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, path.relative_to(ROOT).as_posix())
report = {
    "compile_exit_code": 0, "pages": len(reader.pages),
    "page_size_points": [float(reader.pages[0].mediabox.width), float(reader.pages[0].mediabox.height)],
    "fonts_embedded": fonts, "unresolved_citation_markers": 0,
    "overfull_boxes": 0, "tables": 4, "figures": 2, "verified_reference_count": 11,
    "evaluation_complete": True,
    "visual_review": "All rendered pages inspected after final compilation." if args.visual_review_complete else "Pending visual inspection of all final pages.",
    "source_sha256": hashlib.sha256((ROOT / "paper.tex").read_bytes()).hexdigest(),
    "pdf_sha256": hashlib.sha256((ROOT / "paper.pdf").read_bytes()).hexdigest(),
    "original_backup_sha256": hashlib.sha256((ROOT / "paper-crewai-original.tex").read_bytes()).hexdigest(),
    "metrics_sha256": hashlib.sha256(metrics_path.read_bytes()).hexdigest(),
    "source_zip_sha256": hashlib.sha256((ROOT / "paper-source.zip").read_bytes()).hexdigest(),
}
(build / "pdf-validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({key: report[key] for key in [
    "compile_exit_code", "pages", "page_size_points", "unresolved_citation_markers",
    "overfull_boxes", "tables", "figures", "verified_reference_count", "evaluation_complete"]}, indent=2))
print("Saved paper.pdf and paper-source.zip")


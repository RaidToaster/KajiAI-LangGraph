# Reproduce the 2026-11-04 negative development snapshot

This package contains retained data and source. It is not a final 500-per-model evaluation. All commands below are offline; do not invoke live runner CLIs as reproduction commands. Run from the extracted repository root with a Python environment matching pyproject.toml and uv.lock. The author's unchanged .venv was used; no new packages were installed. Put extracted src first on PYTHONPATH when reusing an existing environment.

```powershell
$env:PYTHONUTF8 = '1'
$env:OMP_NUM_THREADS = '2'
$env:MKL_NUM_THREADS = '2'
$env:OPENBLAS_NUM_THREADS = '2'
$env:NUMEXPR_NUM_THREADS = '2'
$env:VECLIB_MAXIMUM_THREADS = '2'
$env:PYTHONPATH = (Resolve-Path ./src).Path
python evaluation/verify_flash_snapshot.py artifacts/flash-workflow-20261103
python evaluation/flash_method_windows.py artifacts/flash-workflow-20261103
python evaluation/analyze_flash_study.py artifacts/flash-workflow-20261103/revision-8 development --adjudications artifacts/flash-workflow-20261103/revision-8/development-adjudications.json
```

The snapshot verifier reconstructs every revision-specific analysis, resolves reused cells through frozen manifests, compares normalized usage against raw transport bodies, recounts historical headline metrics from both 500-row JSONL files, verifies the final shared 500-case order, checks split disjointness and verifies zero advanced-phase attempts. Historical service failures with missing usage remain explicit; no token count is invented. It verifies both packet sends and both untouched DeepSeek cells separately. All 64 unique workflow attempts are counted once for service totals; standalone diagnostics are not pooled with them. The selector output should reproduce byte-identically.

Do not overwrite the close reason by interpreting an incomplete eight-case analysis as a completed screen. The ordinary scorer produces the same failed model criteria; revision-8/development-decision.json also retains the early mathematical-futility explanation. All nine unrun cells remain untouched.

To reconstruct the historical stopping summary without service calls:

```powershell
python artifacts/aris/run_20261103_exhaustion_9c7e12bf/analyze_live.py --help
```

Rebuild the recorded batch1 schedule/adjudication with its positional output argument:

```powershell
python artifacts/aris/run_20261103_exhaustion_9c7e12bf/analyze_live.py stopping-reproduction.json batch1
``` Historical Gemma scripts and their raw full/closed_book records are in evaluation/results/study-20261009-v3. The historical analysis uses 10,000 bootstrap draws and may take longer; the snapshot verifier independently recounts the headline point estimates directly. Numeric intervals and auxiliary historical diagnostics retain their original analysis/provenance and unchanged source tables.

The editable manuscript is artifacts/flash-workflow-20261103/manuscript/paper.tex with adjacent paper-figures. Compile using installed Tectonic (no shell escape or package installation). The successful compilation JSON and built PDF are retained. Use evaluation/verify_flash_pdf.py with a pypdf-capable environment after independently rendering and reviewing the pages; do not claim a new visual review merely by running the flag. The author's verified checks and PDF/source hashes are in manuscript/verification.json.

PACKAGE_MANIFEST.json in the archive records SHA-256 for every packaged file except itself. The package builder is evaluation/package_flash_snapshot.py. The extraction verification record beside the delivered archive records integrity, clean-source imports, reproduced metrics/windows, historical stopping reanalysis and matching PDF/source digests. No credentials, environment secrets, model weights or Git metadata are packaged.

Primary outcomes and unfinished deliverables: STUDY_STATUS_20261104.md. Claim mapping: CLAIM_RECORD_MAP.md. Review: feasibility-review-20261104/response.md and round2.md (same-family/provisional). Independent human annotation remains pending.

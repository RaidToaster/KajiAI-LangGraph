# Reproduce the interim DeepSeek checkpoint

Extract this archive into an empty directory and keep its paths intact. The companion includes the frozen runner and isolated runtime, frozen case manifests, 47 raw DeepSeek attempt directories and their hash references, the scorer, and the report and service ledger. It excludes the project .env and provider credentials.

From the extraction root, use Python 3.12 with the same dependency versions recorded in the pilot environment. The frozen runtime's `pyproject.toml` and `uv.lock` identify the dependencies. The commands below only read saved inference records and write analysis files.

```powershell
$study = 'artifacts/aris/run_20261106_deepseek500'
python "$study/analyze.py"
python "$study/forecast.py"
python "$study/render_table.py" "$study/summary.json" evaluation/deepseek-results.tex
```

The first command rehashes the frozen inputs and all reused journals, checks the archived import paths, joins gold offline and regenerates the report, CSV, ledger and summary. The frozen Flash scorer supplies citation checks and paired-case intervals. The second command recomputes arm-specific cost and usage forecasts from observed pilot resources. The third command regenerates the DeepSeek table.

Build the manuscript from `evaluation/` with the commands in the separate paper source archive. The bibliography is embedded in `paper.tex`. The historical figure and provenance accompany the editable source.

## Historical evidence index

- The complete Gemma comparison is in the repository at `evaluation/results/study-20261009-v3`, with the frozen runtime, dataset, raw result files, `final_analysis.py`, and per-claim tables.
- The fixed-evidence stopping experiment is in `artifacts/aris/run_20261103_exhaustion_9c7e12bf`, with raw paired records and `analyze_live.py`.
- The compact-passage and revision-8 results have separate raw journals and scorers under `artifacts/flash-workflow-20261103`. The historical Flash reproducibility archives in that directory retain those records.
- The failed native fidelity result remains in `artifacts/owned-evidence-native-20261106/readiness-decision.json`.

## Execution boundary

The archive is an offline snapshot. The original workspace maintains the operational checkpoints and raw records. The preserved `status.json` records the earliest quota expiry and exact next untouched cell. Run the launcher only in that workspace, under the current authorized caps, with a verified current account and one worker. The 47 referenced cells are already started and must never be repeated.


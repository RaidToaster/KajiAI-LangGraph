# KajiAI manuscript companion

The companion supports local review of the IEEE draft. The manuscript uses development-set label agreement, saved-policy replay, and a separate controlled continuation challenge. Each result has its own denominator.

| Evidence | Main records | Interpretation |
| --- | --- | --- |
| Historical 500 paired claims | `results/study-20261009-v3/study-metrics.json`, `per-claim-results.csv`, `manifest.json`, `analysis-correction.json` | Historical workflow and same-model control, with 13 retained fatal attempts |
| Historical no-search screen | `stopping-study/historical-guard.json` and `historical_guard.py` | Possible eligibility envelope for the previously selected 252 trajectories |
| Controlled stopping study | `stopping-study/PROTOCOL.md`, `cases.json`, `offline/`, `batch1/`, `live-analysis.json`, `LIVE_DECISION.md` | Scripted reachability and four fixed-evidence live pairs per model. Batch two stayed unrun under the frozen quality guard |

The historical raw JSONL, archived inference source, dataset snapshot and original stopping replay CSV remain in the project tree. See `evaluation/results/study-20261009-v3/` and `evaluation/aris/20261102_120247/stopping-replay.csv`. The source ZIP includes the derived historical tables and manifests and the full synthetic challenge records. The earlier two-claim pilot remains separate at `artifacts/aris/run_20261102_222304_bdd31bb4/`. The original controlled run is at `artifacts/aris/run_20261103_exhaustion_9c7e12bf/`.

## Offline reproduction

Use the project Python environment or an environment with the dependencies recorded in `stopping-study/runtime-environment.json`. From an extracted copy of the source ZIP, run the following in PowerShell with that interpreter active. Set `PYTHONPATH` to the bundled runtime source on other shells as well.

```powershell
$env:PYTHONPATH = (Resolve-Path stopping-study/runtime-src).Path
python stopping-study/analyze_live.py live-recount.json batch1
```

The output should match `stopping-study/live-analysis.json`. The script reads the saved pair results, adjudication, durable request records and final response messages. A candidate that continued reused its baseline's result after checking input equality. The network total is 15 sends. The attributed continuation counts are 15 for baseline and 8 for candidate. A skipped cost is the observed cost of a baseline continuation bypassed by the paired candidate.

To replay the scripted reachability challenge, copy `challenge.py` and `cases.json` to a fresh directory and run `python path/to/challenge.py offline` with the same `PYTHONPATH`. Compare per-case decisions, trace checks and retained evidence against `stopping-study/offline/`. Execution IDs and timing vary. Both commands are offline. The original job receipts document the executed invocations and environment limits.

For the historical eligibility screen, run `historical_guard.py` from a fresh run directory under the original repository's `artifacts/aris/` with its existing environment. It reads the preserved no-search replay CSV and full-workflow JSONL. Historical source-review state is incomplete, so the screen cannot determine exact stopping eligibility.

## Review boundaries

The draft uses venue-neutral IEEE conference formatting. Choose a venue before applying its page, author, anonymity and artifact requirements. Review redistribution terms before sharing historical retrieved text or benchmark material. The synthetic fixtures and archived responses support the controlled acceptance counterexample. Human citation annotation of the historical study remains separate and pending.

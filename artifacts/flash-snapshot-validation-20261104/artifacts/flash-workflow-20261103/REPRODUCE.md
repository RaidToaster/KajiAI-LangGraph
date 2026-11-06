# Reproduce the Flash development analyses

Run commands from the repository root with the existing Python environment. They use saved files and issue no service requests.

```powershell
$env:PYTHONUTF8 = '1'
$env:OMP_NUM_THREADS = '2'
$env:MKL_NUM_THREADS = '2'
$env:OPENBLAS_NUM_THREADS = '2'
.venv/Scripts/python.exe evaluation/audit_flash_prior.py
.venv/Scripts/python.exe evaluation/analyze_flash_study.py artifacts/flash-workflow-20261103 development
.venv/Scripts/python.exe evaluation/analyze_flash_study.py artifacts/flash-workflow-20261103/revision-2 development
.venv/Scripts/python.exe evaluation/analyze_flash_study.py artifacts/flash-workflow-20261103/revision-3 development
.venv/Scripts/python.exe evaluation/analyze_flash_study.py artifacts/flash-workflow-20261103/revision-6 development --adjudications artifacts/flash-workflow-20261103/revision-6/citation-adjudications.json
.venv/Scripts/python.exe evaluation/recount_flash_transport.py artifacts/flash-workflow-20261103
```

The analyzers rebuild each phase's `development-analysis.json` from its attempt, usage, job and result records. Revision 2 and revision 3 reference the same two original baseline attempts via the frozen schedule. Their actual usage is the new traffic only. Do not pool revisions or count reused baseline attempts as fresh sends.

`PROTOCOL.md` records the evaluation criteria and operating bounds. The compact candidate presents up to twelve ranked sources with up to two contiguous 72-word windows per source. The request uses JSON mode with `think: false`; the existing tolerant parser extracts a valid object. Model-supplied source and passage IDs resolve back to exact text in the analyzed versions. Unresolvable IDs remain structurally ineligible. The assessment passes through the original gate and Jev citation review.

For each attempt, `request-NNN.json` is a reservation and records the body, service, path or destination and timestamp. Authorization headers are omitted. `response-NNN.body` is the raw response, which may be compressed or streamed as newline-delimited JSON. `response-NNN.json` records the transport status. `usage.json` contains normalized token accounting and the returned IDs. `result.json` contains the full graph trace, including source text versions and citation keys. Inspect `job.json` for a failed attempt or transport stop before scoring. A started attempt is retained even if no result was produced.

`train-slice.json` is the bounded AVeriTeC training data slice. Each case manifest extracts only the claim, label and date. The runner withholds labels and all gold evidence from inference. `final-case-manifest.json` binds the common 500-case set to the historical dataset snapshot by SHA-256. The earlier use of this AVeriTeC development split is disclosed in the protocol. The historical Gemma and query-exhaustion records remain in their original directories.

Source archives bind each iteration's code to its protocol. The development allowance receipts are phase-specific. Live dispatch requires an unchanged manifest, recorded headroom and a matching receipt. A confirmation or final dispatch also requires a passing preceding quality screen.

In the current runner, confirmation and final release re-score the retained preceding attempts and verify the adjudication digest. The phase must use the same frozen workflow settings, exact models, and scorer. Each case must be scheduled once per arm and model. Final release also requires the shared 500-case manifest, disjoint case text, and frozen retrieval pacing. Historical source snapshots remain available for replaying earlier runs.

The current archive contains the original revision 3 evidence plus later frozen source archives and live attempt records. For an extracted-archive recount, extract only the src directory from revision-6/source-v6.zip into the archive root and place that directory on PYTHONPATH. Use the top-level evaluation scripts from the current archive. Their post-close tally fix accounts for the incomplete Ollama reservation. Extracting the frozen evaluation scripts over those tools would restore the pre-fix tally behavior. The original launcher remains available in the revision 6 source archive.

The transport recount covers cell-level usage journals with attempt metadata. Some earlier fixed-evidence diagnostics store usage inside result files. Their usage remains separate. The ledger replay preserves the exact two requests, raw replies, frozen verdict runner, and decision. Reproduce its outcome by inspecting the raw answers with parse_reply from evaluation/flash_ledger_replay.py. Its live CLI requires an allowance and is outside the offline reproduction commands.

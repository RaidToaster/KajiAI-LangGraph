# Incremental DeepSeek study

This is an opt-in study entry point. It preserves a single saved initial
DeepSeek prediction and evaluates the incremental effect of research. The
initial prompt and schema are shared with `study.closed_book`; the old graph
and study retain their default behavior.

`method.py` has no dataset or scoring access. Its sole claim input is
`{"claim": ..., "reference_date": ...}`. The controller creates opaque worker
identifiers and separate allowlisted files. All labels, annotations, dataset IDs,
historical outcomes and annotated URLs remain outside inference. The worker has
no agent/file/search tools beyond the bounded provider adapter. Source content
is treated as untrusted data. This is an application boundary, not an OS sandbox
against hostile Python code.

## Method

The initial prediction is durably committed before research. A and B share it.
A researches every valid initial; B researches Low only or Low+Medium.
Calibration uses 30 initials and the predeclared Medium-accuracy threshold 0.80.
Selection uses a separate 30 claims; B reuses A's exact research records on its
routed claims. Candidates rank by accuracy, macro F1, then lower policy call
cost. A losing candidate is not promoted. The best research challenger still
receives a frozen final comparison against the shared initial, with the negative
development outcome clearly recorded.

Research makes two neutral queries, one testing an alternative/falsifier, and
fetches up to four unique pages. Jev classifies the domain, ranks search results,
screens pages and reviews citations. The evidence assessor is blind to the
initial. The adjudicator sees both predictions and must justify any change with
material, exact retrieved evidence. A deterministic update check prevents
unsupported changes. No second research round or voting is used in v1.

Acceptance reuses the existing structural evidence gate, source screening and
Jev citation threshold 0.8. It is separate from the final label. Retrieval
failure, limited independence or rejected citations do not force factual NEI.
A valid saved initial survives inconclusive/failed research; unavailable initials
remain failures in the denominator. A completed adjudication also survives a
subsequent citation-review failure as an unaccepted prediction.

## Controller commands

Run from the project root using `.venv/Scripts/python.exe`. The following
commands describe a future **eligible, released** run, not a release to start
the currently blocked v1 split:

```powershell
.venv/Scripts/python.exe -m kaji_langgraph.incremental prepare --output evaluation/results/NEW-VERSION --dataset evaluation/data/averitec_dev.json
.venv/Scripts/python.exe -m kaji_langgraph.incremental preflight --output evaluation/results/NEW-VERSION
.venv/Scripts/python.exe -m kaji_langgraph.incremental snapshot --output evaluation/results/NEW-VERSION
.venv/Scripts/python.exe -m kaji_langgraph.incremental run --output evaluation/results/NEW-VERSION --phase calibration --limit 30
.venv/Scripts/python.exe -m kaji_langgraph.incremental score --output evaluation/results/NEW-VERSION --phase calibration
.venv/Scripts/python.exe -m kaji_langgraph.incremental run --output evaluation/results/NEW-VERSION --phase selection --limit 30
.venv/Scripts/python.exe -m kaji_langgraph.incremental score --output evaluation/results/NEW-VERSION --phase selection
.venv/Scripts/python.exe -m kaji_langgraph.incremental freeze --output evaluation/results/NEW-VERSION
.venv/Scripts/python.exe -m kaji_langgraph.incremental run --output evaluation/results/NEW-VERSION --phase final --limit 100
.venv/Scripts/python.exe -m kaji_langgraph.incremental score --output evaluation/results/NEW-VERSION --phase final
```

Copy and declare `PROTOCOL.md` in a new output directory **before** `prepare`.
Preparation refuses to overwrite a split. It never materializes final texts.
`snapshot` archives code, explicit prompts, config, dependencies and environment;
`freeze` additionally binds the reproduced calibration/selection decision before
final input materialization. All phases require unchanged code and environment.
Only complete, hashed prediction commitments permit scoring; final freeze and
result hashes are checked again before final scoring. No interim final accuracy
is produced. Repeat scoring is deterministic and makes no provider calls.

## Resource receipt

The user's request authorizes existing resources, without buying credits or
changing accounts. A run-specific `resource-release.json` records the inspected
headroom; it is not a request for new purchases. Required fields are:

```json
{
  "split_sha256": "SHA256_OF_THIS_SPLIT",
  "existing_credits_only": true,
  "zero_rated_retrieval_verified": true,
  "billing_changes": false,
  "remaining_existing_credit_usd": {"ollama": 10, "jev": 1},
  "caps_usd": {"ollama": 10, "jev": 1, "search": 0, "fetch": 0},
  "valid_until": "CURRENT_TIMEZONE_AWARE_EXPIRY",
  "basis": "References to current account evidence and original user authorization"
}
```

Numbers above illustrate a bounded allocation, not observed account balances.
Caps must fit verified existing credit. Do not fill an evidence field from an
assumption or copy an old experiment's allocation. The hard per-send reservation
uses peak public rates and a conservative input allowance; observed counters
replace reservations when known. Unknown usage remains reserved. The saved
resource estimate distinguishes a no-repair planning estimate from the much
larger all-repair/per-request-bound ceiling. A lower allocation may stop before
the evaluation finishes; preserve the partial run instead of exceeding it.

One worker and at most two numerical threads. Each claim has a 300-second hard
supervisor limit. Every send is fsynced before dispatch, with raw responses and
actual model IDs recorded. Physical ceilings: 8 Ollama, 12 Jev, 2 Search and 4
Fetch URLs per researched claim. Repairs count; SDK/network retries are disabled.
The original requested model ID and the provider's accepted base alias are
verified separately. Reasoning is omitted, preserving the native default; actual
request bodies show that setting. Output request is 8192 tokens.

## Stopping and resuming

All historical coordinator locks must be idle. Their shared locks are held
throughout new dispatch; the exposure audit repeats under those locks to close
the preflight race. A held/inaccessible lock blocks execution. Any newly exposed
selected identity blocks the run. Never replace identities after development.

The runner reuses committed results; it never reopens a started worker or sends
an uncertain request again. A started attempt without a result needs manual
provider/journal reconciliation. Preserve `provider-stop.json`, request/response
files and spend reservations; do not delete them to force progress. This version
deliberately provides no automatic stop-clearing or uncertain-send replay command.
If a provider stop requires a code/method change, preserve this run and begin a
new development cycle rather than mutate the freeze.

## Scoring and artifacts

Reports contain failure-inclusive accuracy and Wilson intervals, four-class
macro/per-class F1 and confusion matrices, seeded 10,000-resample paired bootstrap,
exact McNemar, both correctness transitions, routing/category results, update
reasons, acceptance coverage/accuracy, execution failures, physical accounting
and deployed-policy accounting. Operational fallback predictions are available
labels; research failures remain visible separately. Missing predictions count
as incorrect. An accepted citation or valid schema is never called correctness.

Artifacts: protocol; initial/latest exposure audits; split manifest/hashes;
implementation archive/prompts/environment; opaque mappings and allowlisted
inputs; request reservations/raw response journals; immutable initials; final
predictions and complete commitments; calibration/selection/final reports;
method freeze; preflight and resource accounting. No final presentation is
generated before a complete verified final evaluation.

Offline verification uses only synthetic fixtures:

```powershell
.venv/Scripts/python.exe -m pytest --basetemp tmp/NEW-UNUSED-TEST-DIRECTORY
```

Use a fresh test directory: pytest can clear an existing `--basetemp`.

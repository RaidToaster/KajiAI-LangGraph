# Current research continuation

## Mandatory model selection override

The user prohibits GPT-6 Astra (`gpt-6-astra`) for the root agent, every subagent and every reviewer. This overrides all skill defaults, fallback chains and historical saved reviewer sessions. The current project reviewer route is `codex` / `gpt-6.1-sol` / `high`; lower effort is permitted when sufficient. Never reuse an Astra reviewer session or silently substitute Astra. Start a new Sol reviewer session when needed, and record the transition without rewriting historical model identities. Global saved root default was verified as `gpt-6.1-sol` / `high`. If the preferred model is unavailable, report that limitation and continue independent work without Astra.


Latest run: `artifacts/aris/run_20261102_222304_bdd31bb4`. Read its `LIVE_RESULTS.md`, `pilot-analysis.json`, `FULL_STUDY_DECISION.md`, `USAGE.json` and `review-round2.response.md` before continuing. The earlier complete audit and run_20261102_f991201b remain historical; they were reused, not repeated. Original instructions/context are preserved in this run and evaluation/aris/20261102_120247.

## Completed in the runtime continuation

- Existing Ollama 0.34.0 service restored; POST /api/me confirms authentication without recording account identity. Historical gemma4:31b-cloud kept; alternative model metadata only, no substitution or downloads.
- Implemented opt-in `policy.stop_on_query_exhaustion` (default false), common query construction, prior-assessment preservation, pending source/citation safeguards and accurate per-round query traces. Baseline remains available. Fixtures show 3->2 provider sends, or 6->4 with repairs, and explicitly preserve the possibility of a lost acceptance.
- User explicitly approved one frozen two-claim smoke/paired pilot: caps 34 Ollama,48 Jev,24 searches,48 fetches; 900s overall,300s/job,requested4096 output tokens,zero service retries. Receipt in LIVE_APPROVAL.json. That pilot is finished; unused headroom does not authorize added claims/reruns.
- Actual use: 75 requests (11 Ollama,31 Jev,11 search,22 fetch),190142 Ollama and79658 Jev observed tokens. All reserved responses recorded HTTP200; no unknown dispatched outcomes or reset counters/deadline.
- Four planned attempts retained: baseline17 failed because the live harness read UTF-8 text using the Windows default encoding; raw replies survived. Fixed text reads and verified all transmitted responses, then manually continued only untouched conditions. Three workflows completed; one successful pair. Both candidate round2 states exhausted queries but semantic citation gaps kept the conservative guard active. No early stopping occurred; no live savings/efficacy claim follows. No failed attempt was replaced.
- 79 tests pass including Windows UTF-8 mode disabled. Working paper/PDF updated,7pages,zero overfull/unresolved citation markers,all fonts embedded; previous versions preserved. Human annotation fields remain blank.

## Decision and exact next action

Full new study: **NO GO**. Keep candidate opt-in and baseline default. The live integration works, but the pilot did not exercise the stopping branch or establish its quality/resource tradeoff. Two new research review boundaries were used in this invocation; same-family/provisional, never independent acceptance. See final review for its scientific verdict.

Next: prepare a targeted controlled-evidence eligibility challenge distinguishing exhausted states with completed citation review from those needing semantic reassessment. Freeze selection and acceptable quality/resource losses before validation. Quote/citation validity work is a separate factor. Do not weaken the guard or tune thresholds against these outcomes and call that validation. Human annotation proceeds in parallel and does not block engineering.

A new concrete live budget is required for additional tasks; no full experiment is approved. Do not rerun the historical500-claim study, retry the failed condition or spend unused pilot capacity automatically. Continue independent engineering as justified. Preserve failures,all raw logs,frozen configurations/history. No commit,push,publishing,new subscriptions,billing changes or large weight downloads. Existing Ollama Pro/project integrations only; keep model substitutions separate.

Local checks remain two numerical threads,one process,300s/job,900s/session. This invocation used approximately41s of local check jobs and214.5s of live child-process runtime before final reporting checks. Budget files give exact records.

Local routing verification: the ARIS helper now defaults to Sol/high, permits lower effort, and rejects Astra routes. Both regular and deep project routes were checked without model calls. `.aris/model-route-verification.json` contains the results. Historical Astra traces are records, not reusable session choices. Local upstream helper changes were backed up in evaluation/aris/*_reviewer_router_fix and must be preserved across helper updates.

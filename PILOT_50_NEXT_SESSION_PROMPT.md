/goal Run a frozen 50-case AVeriTeC resource pilot in D:\Projects\!skripsi\KajiAI-LangGraph, then stop and report the measured token usage, time, retrieval usage and cost forecast before I decide whether to continue to all 500 cases.

Read AGENTS.md, this prompt, PILOT_50_HANDOFF.md, and the latest authoritative checkpoint first. This is my NEW scope instruction: stop method development and qualification loops. I authorize a resource/comparison pilot of an UNQUALIFIED frozen candidate. The earlier requirement to pass 8-case development and 12-case confirmation is waived AS AN ENTRY CONDITION FOR THIS PILOT ONLY. Do not forge passing decisions, rescore historical failures as passes, or claim a qualified improvement. All evidence-acceptance checks remain unchanged. The remaining 450 cases/full 2,000-attempt study are NOT released.

1. Exact models and counts

Use only glm-5.3-flash:cloud and deepseek-v4.1-flash:cloud through Ollama. These are the models at https://ollama.com/library/glm-5.3-flash and https://ollama.com/library/deepseek-v4.1-flash. Check actual requested and returned IDs on every response. The corresponding base names without :cloud are normal returned IDs; reject other models or silent fallbacks. Never use GPT-6 Astra. Jev remains jev-1.13.0.

Use the SAME 50 cases for candidate and CURRENT-WORKFLOW baseline on BOTH models: 50 x 2 arms x 2 models = 200 fresh attempts. A future complete comparison would be 500 x 2 x 2 = 2,000 attempts. Do not interpret 50 as 50 per model without baseline or 50 total attempts. No historical baseline attempts are reused in the resource pilot.

2. Freeze a tested snapshot; do not finish the partial prototype

Use artifacts/owned-evidence-native-20261106/source.zip, SHA256 f9c7598dcd0c8f89be4e9f969c3819b17fd5609c8e0dfb09151cea57d93bf9c8, as the candidate source. Its associated protocol.json describes the tested settings. This snapshot compiled in its native GLM test but FAILED semantic fidelity on an unsupported scope/materiality objection. DeepSeek has not run this exact candidate. Keep those facts disclosed. This pilot measures what it actually does, including abstentions/errors; it does not require another qualification pass.

The dirty working tree contains later UNFINISHED/UNTESTED semantic_evidence.py and Jev.adjudicate_selected_evidence work. Do not use it, finish it, or silently substitute it for the tested snapshot. Preserve the dirty tree and every historical archive, trace, failure and usage record.

Extract the tested archive into a new isolated directory inside this workspace; never overwrite the working tree. Reuse the existing environment/dependencies without upgrades. Explicitly verify Python imports resolve to the isolated archived src, not the editable install pointing at the dirty workspace. Keep secrets out of snapshots/log output. The archive is not a standalone complete experiment package: add and hash the necessary scorer, case manifests and minimal pilot runner.

Candidate: archived evidence_adjudicated mode, predecision_source_path_review=true, bound_source_anchors=true, single_materiality_owner=true, questions_as_guidance, 6144 assessment output tokens, GLM reasoning high, DeepSeek reasoning false, required independent-provenance review and source-reference research. Baseline: archived standard CURRENT workflow and its original frozen configuration/output/reasoning settings. Recover exact settings from the archived runtime, associated native protocol and original study protocols; do not accidentally use default Gemma. Disclose the settings as part of the combined intervention rather than pretending every parameter is identical.

Only implement the minimal pilot execution/accounting layer and necessary launch fixes. Do not disable qualification globally in the historical runner: use a separately identified prospective pilot protocol with its own entry authorization. Preserve existing acceptance/scoring logic. An offline import/configuration/transport check is appropriate; no more live positive-anchor or redesign loops. Freeze source, runner, scorer, settings and schedule before the first pilot call.

3. Select and protect the cases

Use the existing final-cases.json, SHA256 4687c951515657657d418d6439bf7b180c5a912465f79c32fdd58a52a4cc0c60, and final-case-manifest.json, SHA256 b3f4016c0de144b27bc02d2167093eda3da938a1f694605aa8148db3920bccf2, under artifacts/flash-workflow-20261103.

Draw a reproducible sample of 50 IDs without replacement from that 500-case manifest using seed 20261106 and manifest IDs only, before inspecting labels, outputs or outcomes. Save the selection code/version, seed, ordered IDs and hashes. Use the same selected IDs in all four model/arm combinations. Keep the remaining 450 claims/labels out of development and tuning. Never send gold labels to inference or retrieval. Record the execution order prospectively and alternate arm/model order across cases to reduce order effects. No cross-arm cache sharing or unrecorded prefetching; preserve frozen within-attempt caching.

4. Resources and execution

Verify the old chat and every experiment worker are stopped. One experiment worker, at most two numerical threads, 300 seconds per attempt. Preserve original per-attempt ceilings of 8 Ollama calls, 40 Jev calls, 6 Search calls and 12 TinyFetch URL attempts, three rounds and the original token limit. Do not add external retries or rerun/replace a started attempt. Preserve any frozen within-attempt behavior and log every send.

KEEP TINYFETCH; do not switch to public HTTP. Use existing prepaid/included credits only. Pilot scheduling spend ceilings are $10 Ollama and $1 Jev; reserve conservatively using verified rates and stop before exceeding them. These are scheduling limits, not a claim of provider-enforced billing caps. No paid TinyFish retrieval is authorized by this prompt. No upgrades, topups, subscriptions, billing changes or automatic Builder switch.

Before launch, produce a concrete preflight budget and check account quota/headroom against existing authorization and current recorded usage. Known last user-reported balances were about $60 Ollama/$4.77 Jev; TinyFish screenshot showed $12 wallet/auto-reload off. Do not present those as freshly verified balances. Before any paid retrieval, actual account daily quota, rates, wallet and a separate concrete spend cap must be verified/authorized. Enforce the recorded conservative free pacing: Search 27/minute and 450/hour; Fetch 135 URL attempts/minute and 900/rolling 24 hours, including existing recorded usage. If quotas require waiting, report the quota-limited calendar estimate; do not bypass limits. Ask only a genuinely necessary concrete budget/account question, not routine permission for already authorized counts.

Complete all 200 scheduled attempts failure-inclusively unless an operational/model-identity/accounting/quota/spend condition requires stopping. Incorrect predictions, known parser/execution failures and abstentions are results, not reasons to tune or cherry-pick replacements. Unknown send outcomes stay UNKNOWN, not zero, and require reconciliation before further potentially duplicate calls. Resume only untouched schedule entries. No changes to prompts, method, thresholds, caps or case selection after seeing pilot outcomes.

5. What to measure and deliver

Retain raw requests/responses, source versions/hashes, actual model IDs, configuration, failure reasons and usage for every attempt. Report separately for each model/arm: attempted/completed/failed counts; Ollama input/output tokens and provider-reported cache/reasoning usage where available; Jev input/output tokens; calls per service; Search/Fetch attempts; and time per attempt/round/service where observable. Missing counters remain unknown. Distinguish workflow API tokens from unobservable Codex/reviewer overhead.

Measure active processing time separately from quota waits, startup, operator/audit time and total calendar elapsed time. Give totals, mean, median, P90/P95 and timeouts; include failed attempts in resource denominators. Separate measured billing from rate-derived estimates, and show the rates/cache assumptions used. Do not call label agreement official AVeriTeC evidence scoring or treat this adaptive pilot as pristine held-out proof of improvement.

Produce an attempt-level CSV, reconciled service ledger, frozen pilot protocol/manifest/source package, readable PILOT_50_REPORT.md and machine-readable FORECAST_500.json. Estimate each model/arm separately, then sum: full 500-case resource use is approximately 10x its 50-case measurement; the additional 450 cases approximately 9x. Give uncertainty/sensitivity ranges, account for paired-case variability, failures and quota-limited calendar time; do not promise linear scaling or count already completed pilot attempts twice.

If I later approve continuation with exactly the same freeze/protocol, these 200 attempts may form the first part of the planned 2,000 and only 1,800 remain. If the method changes, preserve this pilot separately and disclose exposure; do not silently pool incompatible runs. STOP after this pilot and report. Do not launch the remaining 450 cases, continue method optimization, or claim the full paper/study complete without my subsequent instruction.

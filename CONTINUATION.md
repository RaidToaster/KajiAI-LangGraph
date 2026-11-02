# Current research continuation — read first

User direction: finish the research as soon as possible, including justified runtime changes and actual bounded live experiments. The project is NOT restricted to offline work. This direction supersedes the previous handoff's recommendation to stop after offline analysis or wait for human annotation before engineering.

## What is already done

The completed study in evaluation/results/study-20261009-v3 has 500 workflow and 500 model-only attempts. Provenance and central results reproduce; 63 tests passed. Previous changes fixed paper/notes generation, packaging and offline analysis utilities. The inference graph, prompts, gates, runtime model and stopping policy were NOT changed; no new live inference ran. Research reviews scored 5/10 not ready; writing/layout scored 9/10. These are separate same-family/provisional judgments.

Historical evidence and original instructions: evaluation/aris/20261102_120247/USER_BRIEF.txt. Read the compact claim map, decision log and model-integration notes there as needed; do not repeat the entire completed audit.

## Immediate execution sequence

1. Inspect Git state and create a NEW timestamped research run. Preserve existing edits, raw records, frozen source, drafts and prior review traces. The completed run_20261102_f991201b must not be reopened or rewritten as though runtime/pilot work was completed.
2. Restore the existing Ollama integration: inspect installed service/process/configuration, start the existing local service if necessary, and verify localhost:11434 metadata, authenticated model identifiers and capabilities. The earlier refusal is a diagnostic observation, not a permanent blocker. Routine local repairs and read-only discovery can proceed; do not change global permissions, credentials or billing.
3. Reproduce a concrete runtime issue with focused fixtures. First candidate: explicit stopping when no unused query remains. Existing frozen traces show 252 third rounds with unchanged usable-source versions and no new searches, consuming 4,154,865 observed tokens. Later assessment produced two label gains, one loss and two extra acceptances. Stopping is a quality/resource hypothesis, not a proven improvement. Check pending source/citation review and reassessment behavior before deciding the minimum implementation.
4. Implement and test the smallest justified candidate. Verify actual provider-call counts, retained prior assessment, acceptance/failure semantics, explicit stop reason and trace consistency. Keep the unchanged baseline available as a separate condition. Use the historical manifest's configuration when defining the baseline; current defaults must not silently replace it.
5. Before asking for live approval, prepare concrete reviewable code and a small protocol: selected claims/seed, conditions, prompts/settings, failure rules, validity/quality/coverage/citation/resource metrics, actual request caps including repairs/retries and all services, timeouts, output caps where supported, logging/recovery, and go/no-go criteria. Ask ONE concise bounded approval request, then execute that scope after approval without asking for each call. Continue independent authorized work while waiting. Do not mark 'not authorized' and terminate without presenting the request.
6. Run the approved integration smoke and smallest informative paired pilot. Preserve every attempt and failure. Compare the baseline with ONE candidate factor; keep model substitution separate from stopping-policy changes. Report gains, losses, uncertainty and observed usage. No threshold tuning on reused development results presented as validation.
7. Revise the working manuscript from actual results and make a full-study readiness decision. Larger inference requires a justified frozen protocol, resource estimates and explicit approval. Never rerun the historical study merely to finish this task.

## Models and authorization

Use existing Ollama Pro and existing project integrations only. The historical model is gemma4:31b-cloud. Consider deepseek-v4.1-flash:cloud and glm-5.3-flash:cloud when scientifically useful; do not test all models just because available. Verify identifiers, structured-output/repair support, thinking controls and available response metadata at the actual endpoint. Do not silently substitute models, download large weights, add DeepSeek/Z.ai subscriptions or enable billing. No numerical live-service budget is approved yet; urgency does not define one.

Human citation annotation is a parallel scientific dependency, NOT a prerequisite for restoring services, fixing code or testing a runtime hypothesis. Keep all human fields blank until actual human work. Automated citation judgments are not human validation. Do not contact annotators without explicit messaging instructions.

## Limits and completion

Conserve tokens: targeted reads, reuse verified artifacts, focused tests, compact reviewer responses, and reviews only at meaningful new boundaries. At most two NEW research review-and-fix rounds and at most two final writing rounds if needed. Local CPU checks: two numerical threads, one experiment process, 300 seconds per job, 900 seconds total in the new session. Live request/runtime budgets require separate explicit approval; distinguish scheduling deadlines from cancellation of in-flight requests.

Maintain state, decisions, tracker, claim evidence, changes, reviews and observed usage in the new run. Deliver runtime diff/tests, actual authorized live outputs, analysis, updated paper/PDF and exact resume action. If genuinely blocked, show the specific failure and the concrete action/approval needed; finish unaffected work. Do not declare the whole project complete because the paper compiles or an AI reviewer likes its writing. No commit, push, publication or submission without explicit instruction.

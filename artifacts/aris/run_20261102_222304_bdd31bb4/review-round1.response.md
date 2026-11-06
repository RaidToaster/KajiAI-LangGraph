# Runtime continuation review — round 1

Score: **8/10 for bounded-pilot engineering readiness**. Verdict: **ready** for the explicitly approved frozen smoke/pilot after the fixes inspected below. Full-study readiness remains **NO GO**; no empirical quality gain is established.

Review independence: **same-family**; acceptance status: **provisional**. Requested reviewer: GPT-6-Astra, xhigh. Actual model/effort are not independently exposed to this reviewer and are recorded as **unknown**, rather than inferred from the request.

## Scope coverage

Inspected AGENTS.md, CONTINUATION.md, local ARIS desktop guidance, graph/state/default configuration, both targeted test files, pilot executor, frozen Markdown/JSON protocol, supplied test logs, authenticated Ollama metadata, and installed LangChain Ollama, HTTPX/HTTPX2 and TypeSafe client/retry/transport sources. Historical study audit was not repeated. The parent reported explicit approval during review; this reviewer did not launch inference, tests, experiments, or client processes.

The documented project-venv command is plausible by inspection: `.venv/pyvenv.cfg` identifies Python 3.12.4; its editable `.pth` points to this repository's `src`; required installed client sources are present. The child command reuses `sys.executable` and inherits the project working directory. This is an invocation inspection, **not an independently executed fresh-environment check**.

The opt-in stop shares retrieval's unused-query inventory, preserves prior assessment/prediction, records `query_exhausted` on the last actual round, and retains baseline behavior when disabled. Acceptance, fatal-error, stagnation and budget precedence remain intact. Pending source reviews and citation semantic gaps prevent the new stop. Fixtures count adapter invoke boundaries, including repair calls, check trace serialization, and explicitly demonstrate that skipped reassessment can lose acceptance. These are fixture results, not remote provider measurements.

The frozen two-claim protocol holds model, prompts and thresholds fixed across conditions and discloses shared limits differing from historical execution. It separates development findings from confirmatory claims. Request reservations precede sends; failed attempts and repairs consume the shared caps. Inspected SDK retry settings disable retries; redirects are disabled. The parent enforces 300-second children within the 900-second scheduling deadline. Remote cancellation and server enforcement of requested output tokens are correctly treated as unknown until observed. Durable request records preserve unknown outcomes and prevent automatic restart.

## Findings and minimum fixes

Two concrete defects were reported to the parent before launch:

1. TinyFish delegated to unbounded `json.load(response)`, bypassing the promised 2 MB capture bound and losing original HTTP failure bodies/status. The inspected fix now reads at most 2,000,001 bytes, retains bounded raw bytes and actual status, stops on overflow/failure, and preserves the existing no-redirect/no-retry policy.
2. Stream failure metadata was overwritten by the subsequent partial-response record. The inspected fix merges metadata, retaining both the error and partial-body/status evidence.

No remaining must-fix defect was confirmed for this narrowly bounded pilot. Logs report 73 regression passes, 10 stopping-fixture passes, five transport/guard passes, and 16 focused passes after fixes. I inspected these records; I did not rerun them. The transport mocks exercise already-consumed responses; the actual streaming and TinyFish branches were inspected, not independently executed. Live output-cap support, integration validity and trace completeness remain smoke/pilot acceptance gates.

## Memory update

This is the first new-run review; historical 5/10 is not superseded as a study-quality judgment. Two pilot transport defects were found and fixed during this round. Engineering is ready for the approved small pilot; larger inference remains unauthorized by this review. Retain every failure/incomplete pair. No triggering exhaustion pair means inconclusive. Human annotation stays parallel, and automated judgments remain explicitly nonhuman.

# Experiment tracker

| Work | Status | Evidence |
|---|---|---|
| Reuse historical audit | Done, not rerun | historical-review-state.json |
| Restore authenticated Ollama | Done | ollama-auth-discovery.json |
| Runtime fixture reproduction/change | Done | source-before,source-final,focused-tests*.log |
| Regression | 79 pass | final-tests.stdout.log |
| Concrete pilot approval | Granted and scope executed | LIVE_APPROVAL.json,pilot-protocol.json |
| Live smoke | Passed | smoke.json,request-001.json,response-001.body |
| Baseline17 | Failed local UTF-8 logging, retained | 17-baseline.result.json |
| Candidate17 | Completed; guard retained reassessment | 17-query_exhaustion.result.json |
| Candidate246 / baseline246 | Both complete; no early stop | 246-*.result.json |
| Full-study efficacy/readiness | NO GO / unsupported | FULL_STUDY_DECISION.md,pilot-analysis.json |
| Human citation annotation | Parallel,pending; no fabricated labels | historical blank worksheet retained |
| Paper/PDF | Updated and verified | paper-runtime-final.pdf,paper-build-verified/pdf-validation.json |

# Interim manuscript claim audit

**Verdict: PASS for the reported interim scope.** A fresh GPT-6.1 Sol high reviewer audited the paper from the primary records. This same-family review is provisional. Human citation and source-credibility adjudication remains outstanding.

| Claim group | Primary evidence | Outcome |
|---|---|---|
| Frozen schedule and reuse | Study protocol and schedule, parent protocol, manifest, 4,106 frozen file hashes for 47 reused journals | 1,000 cells and 500 unique IDs, 100 pilot-ordered cells followed by 900 alternated cells. The next untouched cell is the DeepSeek candidate for dev-296. |
| DeepSeek outcomes | Parent DeepSeek job and result files with offline gold labels | 24 baseline and 23 candidate terminal cells. 6 and 3 correct proposals, 0 and 15 failures. One correct acceptance on an unpaired baseline. |
| Paired and adaptive context | Parent job and result records across both exact models | 23 paired DeepSeek IDs. Candidate-minus-baseline proposal agreement −8.7 points (paired interval −30.4 to +13.0). The GLM and DeepSeek pilot model-selection counts reconcile. |
| Observed resources and settings | Raw request and response records, protocol, account usage receipt | Observed token and retrieval totals and 70.4 worker minutes reconcile. Baseline omitted explicit reasoning and candidate planning and assessment set it false. |
| Earlier Gemma results | Historical Gemma raw paired records, frozen dataset and saved trajectories | Correct proposals, failure counts, acceptance replay, citation diagnostics and temporal comparisons reconcile. |
| Historical fixed-evidence and Flash results | Raw controlled stopping pairs and service records, and Flash revision journals | Controlled paired results, compact-passage and revision-8 table values, retained failures, and service counts reconcile. |

The manuscript now distinguishes the requested generation limits, 270-second graph budget and 300-second worker timeout. It also describes the standard and candidate query ordering, the exact candidate's failed native GLM check and unreleased screens, and the insufficient whole-cell quota headroom.


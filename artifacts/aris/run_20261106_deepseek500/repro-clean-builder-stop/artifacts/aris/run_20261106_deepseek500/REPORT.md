# Frozen DeepSeek comparison

**80/1,000 cells accounted.** 47 reused and 33 fresh terminal cells. Next untouched cell is `dev-373-deepseek-baseline`.

Operational stop at dev-427-deepseek-candidate. Reconcile the recorded condition before dispatch.

The 50-case stratum includes the early cases used to select DeepSeek. The remaining 450 follow the original manifest order. The candidate was unqualified at entry. The original evidence gates remained active. Proposal agreement is local label agreement. The official AVeriTeC evidence score was outside the scoring protocol.

| Stratum | Arm | Target | Terminal | Completed | Failed | Timeout | Correct proposals | Correct acceptances | Incorrect acceptances | Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| selected_50 | baseline | 50 | 40 | 39 | 1 | 0 | 7 | 1 | 0 | 2.5% |
| selected_50 | candidate | 50 | 40 | 11 | 29 | 0 | 4 | 0 | 0 | 0.0% |
| other_450 | baseline | 450 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| other_450 | candidate | 450 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| pooled_500 | baseline | 500 | 40 | 39 | 1 | 0 | 7 | 1 | 0 | 2.5% |
| pooled_500 | candidate | 500 | 40 | 11 | 29 | 0 | 4 | 0 | 0 | 0.0% |

## Paired agreement

- selected_50 has 40 terminal pairs. Candidate minus baseline is -7.5 percentage points (95% paired bootstrap -22.5 to +7.5).
- other_450 has no terminal pairs.
- pooled_500 has 40 terminal pairs. Candidate minus baseline is -7.5 percentage points (95% paired bootstrap -22.5 to +7.5).

## Measured resources

| Source | Ollama input / output | Jev input / output | Search / Fetch URLs | Worker s | Ollama / Jev estimated USD |
|---|---|---|---|---:|---|
| reused | 1,536,161 / 395,590 | 1,496,816 / 185,349 | 185 / 366 | 4,224.6 | 0.9356 / 0.0629 |
| fresh | 930,605 / 243,427 | 910,894 / 109,857 | 118 / 225 | 2,757.9 | 0.5713 / 0.0383 |

Per-arm means, medians, P90/P95, per-send and round times, paired intervals, and cohort timing are in `summary.json`.
The ledger retains recorded cache and reasoning fields when the provider supplied them. Actual charges are unavailable. The estimate uses peak uncached Ollama rates of $0.30 input and $1.20 output per million tokens and Jev's $0.042 per million input tokens. TinyFish's pilot retrieval was free. The Builder phase reserves the verified rate for every paid-phase send.

Historical GLM outcomes and the separate Gemma study are outside these tables. Any accepted cases in `acceptance-audit.json` await independent human adjudication.

## Builder billing and stop

Fresh retrieval reserved $0.600 of the $12 cap. The wallet showed $11.922 at the stop, compared with $12.000 at the transition. The account-level balance change does not attribute charges to individual sends. The full-rate reservation counts all sends, including unsuccessful sends.

The coordinator stopped at TinySearch request 007 for dev-427-deepseek-candidate. The remote connection closed before an HTTP response. Read-only provider history matched a neighboring search and returned no terminal record for the reset request. The request stays UNKNOWN and its reservation is retained. The next untouched cell is dev-373-deepseek-baseline. Resume requires a terminal provider outcome or a documented reconciliation rule. The worker timeout column counts 300-second worker expirations. Individual transport timeouts remain in the service ledger.

# Frozen DeepSeek comparison

**107/1,000 cells accounted.** 47 reused and 60 fresh terminal cells. Next untouched cell is `dev-007-deepseek-baseline`.

Between-attempt quota checkpoint. Earliest quota eligibility was recorded as 2026-11-06T23:46:56.811815+00:00.

The 50-case stratum includes the early cases used to select DeepSeek. The remaining 450 follow the original manifest order. The candidate was unqualified at entry. The original evidence gates remained active. Proposal agreement is local label agreement. The official AVeriTeC evidence score was outside the scoring protocol.

| Stratum | Arm | Target | Terminal | Completed | Failed | Timeout | Correct proposals | Correct acceptances | Incorrect acceptances | Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| selected_50 | baseline | 50 | 50 | 40 | 10 | 0 | 8 | 1 | 0 | 2.0% |
| selected_50 | candidate | 50 | 50 | 12 | 38 | 0 | 4 | 0 | 0 | 0.0% |
| other_450 | baseline | 450 | 3 | 2 | 1 | 0 | 0 | 0 | 0 | 0.0% |
| other_450 | candidate | 450 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 0.0% |
| pooled_500 | baseline | 500 | 53 | 42 | 11 | 0 | 8 | 1 | 0 | 1.9% |
| pooled_500 | candidate | 500 | 54 | 12 | 42 | 0 | 4 | 0 | 0 | 0.0% |

## Paired agreement

- selected_50 has 50 terminal pairs. Candidate minus baseline is -8.0 percentage points (95% paired bootstrap -20.0 to +4.0).
- other_450 has 3 terminal pairs. Candidate minus baseline is +0.0 percentage points (95% paired bootstrap +0.0 to +0.0).
- pooled_500 has 53 terminal pairs. Candidate minus baseline is -7.5 percentage points (95% paired bootstrap -18.9 to +3.8).

## Measured resources

| Source | Ollama input / output | Jev input / output | Search / Fetch URLs | Worker s | Ollama / Jev estimated USD |
|---|---|---|---|---:|---|
| reused | 1,536,161 / 395,590 | 1,496,816 / 185,349 | 185 / 366 | 4,224.6 | 0.9356 / 0.0629 |
| fresh | 1,167,189 / 318,823 | 1,241,278 / 147,319 | 183 / 337 | 4,648.8 | 0.7327 / 0.0521 |

Per-arm means, medians, P90/P95, per-send and round times, paired intervals, and cohort timing are in `summary.json`.
The ledger retains recorded cache and reasoning fields when the provider supplied them. Actual charges are unavailable. The estimate uses peak uncached Ollama rates of $0.30 input and $1.20 output per million tokens and Jev's $0.042 per million input tokens. TinyFish's pilot retrieval was free. The Builder phase reserves the verified rate for every paid-phase send.

Historical GLM outcomes and the separate Gemma study are outside these tables. Any accepted cases in `acceptance-audit.json` await independent human adjudication.

## Builder retrieval and continuation

Fresh retrieval reserved USD 1.037 of the USD 12 cap. The full-rate reservation counts all sends, including unsuccessful sends. The worker timeout column counts 300-second worker expirations. Individual transport timeouts remain in the service ledger.

Request 007 on dev-427-deepseek-candidate was carried forward as UNKNOWN after three read-only history checks. Its USD 0.005 Search reservation and original workflow failure remain in the ledgers. The cell was never replayed.

The resumed Hobby phase uses zero-rated Search and Fetch and the original rolling quotas, including prior Builder activity. Terminal fresh cells by phase: 60 Builder and 0 Hobby.


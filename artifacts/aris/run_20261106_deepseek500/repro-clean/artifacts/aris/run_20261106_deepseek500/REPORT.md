# Frozen DeepSeek comparison

**47/1,000 cells accounted.** 47 reused and 0 fresh terminal cells. Next untouched cell is `dev-296-deepseek-candidate`.

Between-attempt quota checkpoint. Earliest quota eligibility was recorded as 2026-11-06T10:04:49.100000+00:00.

The 50-case stratum includes the early cases used to select DeepSeek. The remaining 450 follow the original manifest order. The candidate was unqualified at entry. The original evidence gates remained active. Proposal agreement is local label agreement. The official AVeriTeC evidence score was outside the scoring protocol.

| Stratum | Arm | Target | Terminal | Completed | Failed | Timeout | Correct proposals | Correct acceptances | Incorrect acceptances | Coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| selected_50 | baseline | 50 | 24 | 24 | 0 | 0 | 6 | 1 | 0 | 4.2% |
| selected_50 | candidate | 50 | 23 | 8 | 15 | 0 | 3 | 0 | 0 | 0.0% |
| other_450 | baseline | 450 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| other_450 | candidate | 450 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| pooled_500 | baseline | 500 | 24 | 24 | 0 | 0 | 6 | 1 | 0 | 4.2% |
| pooled_500 | candidate | 500 | 23 | 8 | 15 | 0 | 3 | 0 | 0 | 0.0% |

## Paired agreement

- selected_50 has 23 terminal pairs. Candidate minus baseline is -8.7 percentage points (95% paired bootstrap -30.4 to +13.0).
- other_450 has no terminal pairs.
- pooled_500 has 23 terminal pairs. Candidate minus baseline is -8.7 percentage points (95% paired bootstrap -30.4 to +13.0).

## Measured resources

| Source | Ollama input / output | Jev input / output | Search / Fetch URLs | Worker s | Ollama / Jev estimated USD |
|---|---|---|---|---:|---|
| reused | 1,536,161 / 395,590 | 1,496,816 / 185,349 | 185 / 366 | 4,224.6 | 0.9356 / 0.0629 |
| fresh | 0 / 0 | 0 / 0 | 0 / 0 | 0.0 | 0.0000 / 0.0000 |

Per-arm means, medians, P90/P95, per-send and round times, paired intervals, and cohort timing are in `summary.json`.
The ledger retains recorded cache and reasoning fields when the provider supplied them. Actual charges are unavailable. The estimate uses peak uncached Ollama rates of $0.30 input and $1.20 output per million tokens and Jev's $0.042 per million input tokens. TinyFish Search and Fetch are free within the authorized limits.

Historical GLM outcomes and the separate Gemma study are outside these tables. Any accepted cases in `acceptance-audit.json` await independent human adjudication.

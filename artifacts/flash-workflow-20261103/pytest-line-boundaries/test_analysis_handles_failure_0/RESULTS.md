# Completed LangGraph computational evaluation

Claims per live condition: 2.

Development-set, contemporary open-web results; local label metrics, not the official AVeriTeC evidence score.

| Condition | Accuracy | Macro F1 | Coverage | Accuracy among covered outputs |
|---|---:|---:|---:|---:|
| full_predictions | 50.0% | 0.250 | 50.0% | 100.0% |
| full_failure_inclusive | 50.0% | 0.250 | 50.0% | 100.0% |
| closed_book_predictions | 50.0% | 0.250 | 50.0% | 100.0% |
| structural_only | 50.0% | 0.250 | 50.0% | 100.0% |
| full_policy | 50.0% | 0.250 | 50.0% | 100.0% |
| first_round_prediction | 50.0% | 0.250 | 50.0% | 100.0% |
| first_round_verified | 50.0% | 0.250 | 50.0% | 100.0% |
| semantic_threshold_0.50 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.60 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.70 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.80 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.90 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.95 | 0.0% | 0.000 | 0.0% | N/A |
| without_high_confidence | 50.0% | 0.250 | 50.0% | 100.0% |
| without_exact_quotes | 50.0% | 0.250 | 50.0% | 100.0% |
| without_host_diversity | 50.0% | 0.250 | 50.0% | 100.0% |
| without_duplicate_check | 50.0% | 0.250 | 50.0% | 100.0% |
| without_independence_flag | 50.0% | 0.250 | 50.0% | 100.0% |
| without_assertion_coverage | 50.0% | 0.250 | 50.0% | 100.0% |
| without_counterevidence_flag | 50.0% | 0.250 | 50.0% | 100.0% |
| without_peer_review_flag | 50.0% | 0.250 | 50.0% | 100.0% |
| majority_baseline | 50.0% | 0.167 | 100.0% | 50.0% |

## Interpretation boundaries

- Model-only control has no verification gate; use its prediction metrics.
- Structural-only, rule-removal and threshold results replay the SAME final assessments and evidence. They measure acceptance policy, not complete alternative workflows.
- First-round results truncate the same saved live trace. They isolate additional research on that trace rather than rerunning changing web searches.
- NEI remains a factual prediction but is outside decisive acceptance; accepted NEI recall is zero by design.
- Full predictions preserve model assessments even if a later service fails. Failure-inclusive metrics count those operational failures as abstentions.
- Threshold curves are descriptive development analyses, not independently validated optimal thresholds.
- Confidence intervals and paired accuracy bootstrap use claims as units. API/model/search drift is not captured by these intervals.
- Jev citation judgments are automated measurements, not human ground truth. Human audit fields remain blank.
- Published fact checks and later documents can be retrieved; no historical cutoff was enforced.

## Citation checks

Final-assessment citations: 2; exact quotations: 2; Jev-reviewed: 0.
Exact quotations whose Jev review did not support the finding: 0; uncertain support: 0.
Claims citing the same host as their dataset fact-check article: 0/2 (proxy only).

## Paired accuracy differences

```json
{
  "full_minus_closed_book": {
    "n": 2,
    "delta_b_minus_a": 0.0,
    "ci95": [
      0.0,
      0.0
    ]
  },
  "full_minus_first_round": {
    "n": 2,
    "delta_b_minus_a": 0.0,
    "ci95": [
      0.0,
      0.0
    ]
  }
}
```

## Artifacts

- study-metrics.json: metrics, Wilson intervals, paired bootstrap, execution and citation diagnostics.
- policy-replay.csv: per-claim policy decisions.
- human-citation-audit.csv: blinded worksheet, with unfilled human judgments.
- human-audit-key.json: keep separate from human reviewers.
- source-snapshot.zip and manifest.json: frozen source and run settings.

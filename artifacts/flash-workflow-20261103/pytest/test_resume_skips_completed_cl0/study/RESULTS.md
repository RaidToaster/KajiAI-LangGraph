# Completed LangGraph computational evaluation

Claims per live condition: 1.

Development-set, contemporary open-web results; local label metrics, not the official AVeriTeC evidence score.

| Condition | Accuracy | Macro F1 | Coverage | Accuracy among covered outputs |
|---|---:|---:|---:|---:|
| full_predictions | 0.0% | 0.000 | 0.0% | N/A |
| full_failure_inclusive | 0.0% | 0.000 | 0.0% | N/A |
| closed_book_predictions | 0.0% | 0.000 | 0.0% | N/A |
| structural_only | 0.0% | 0.000 | 0.0% | N/A |
| full_policy | 0.0% | 0.000 | 0.0% | N/A |
| first_round_prediction | 0.0% | 0.000 | 0.0% | N/A |
| first_round_verified | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.50 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.60 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.70 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.80 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.90 | 0.0% | 0.000 | 0.0% | N/A |
| semantic_threshold_0.95 | 0.0% | 0.000 | 0.0% | N/A |
| without_high_confidence | 0.0% | 0.000 | 0.0% | N/A |
| without_exact_quotes | 0.0% | 0.000 | 0.0% | N/A |
| without_host_diversity | 0.0% | 0.000 | 0.0% | N/A |
| without_duplicate_check | 0.0% | 0.000 | 0.0% | N/A |
| without_independence_flag | 0.0% | 0.000 | 0.0% | N/A |
| without_assertion_coverage | 0.0% | 0.000 | 0.0% | N/A |
| without_counterevidence_flag | 0.0% | 0.000 | 0.0% | N/A |
| without_peer_review_flag | 0.0% | 0.000 | 0.0% | N/A |
| majority_baseline | 100.0% | 0.250 | 100.0% | 100.0% |

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

Final-assessment citations: 0; exact quotations: 0; Jev-reviewed: 0.
Exact quotations whose Jev review did not support the finding: 0; uncertain support: 0.
Claims citing the same host as their dataset fact-check article: 0/1 (proxy only).

## Paired accuracy differences

```json
{
  "full_minus_closed_book": {
    "n": 1,
    "delta_b_minus_a": 0.0,
    "ci95": [
      0.0,
      0.0
    ]
  },
  "full_minus_first_round": {
    "n": 1,
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

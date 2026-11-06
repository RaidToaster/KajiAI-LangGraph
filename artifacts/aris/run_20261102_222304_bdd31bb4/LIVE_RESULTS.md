# Actual bounded live pilot

Actual service requests: 75. Planned workflow denominator: 4.

| Claim | Condition | Status | Prediction | Accepted | Stop | Ollama sends |
|---|---|---|---|---|---|---:|
| 17 | baseline | execution_error | ABSTAIN | ABSTAIN | execution_error | 1 |
| 17 | query_exhaustion | insufficient_evidence | Refuted | ABSTAIN | max_rounds | 3 |
| 246 | baseline | insufficient_evidence | Refuted | ABSTAIN | max_rounds | 3 |
| 246 | query_exhaustion | insufficient_evidence | Refuted | ABSTAIN | max_rounds | 3 |

Full study: **NO GO**. Raw attempts and failures remain separate from the completed historical study.

Both candidate trajectories exhausted queries after round 2, but uncertain or contradicting citation reviews kept the conservative semantic-review guard active. Both therefore retained round 3; this pilot demonstrates no stopping savings.

Human citation validation was not performed. No automated review is represented as human evidence.

One early attempt failed because of local UTF-8 logging; retain in denominator.
Only untouched conditions continued after all dispatched outcomes were verified; original counters/deadline retained.
Independent web and model responses can drift across conditions.
Requested output cap and disabled retries differ from historical execution for both arms.
Missing/failed conditions prevent paired efficacy conclusions; do not impute outcomes.
Observed transport usage can exceed graph usage after a local exception; neither is a monetary estimate.

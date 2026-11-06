# KajiAI AVeriTeC evaluation

Completed 1 of 1 selected claims.

Local label-only metrics, NOT the official AVeriTeC evidence score.

| Output | Accuracy | Macro F1 (4 classes) | Coverage | Accuracy on covered claims |
|---|---:|---:|---:|---:|
| predictions | 1.000 | 0.250 | 1.000 | 1.000 |
| failure_inclusive_predictions | 1.000 | 0.250 | 1.000 | 1.000 |
| verified | 1.000 | 0.250 | 1.000 | 1.000 |

Abstentions count as incorrect in overall accuracy. Raw predictions preserve an available model assessment even if a later service fails; failure-inclusive predictions count execution failures as abstentions. Selective accuracy excludes abstentions and must be reported alongside coverage. Missing selected claims are not yet scored; partial runs are not full benchmark results.

## Prediction performance by class

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Supported | 1.000 | 1.000 | 1.000 | 1 |
| Refuted | 0.000 | 0.000 | 0.000 | 0 |
| Not Enough Evidence | 0.000 | 0.000 | 0.000 | 0 |
| Conflicting Evidence/Cherrypicking | 0.000 | 0.000 | 0.000 | 0 |

## Execution

- Error rate: 0.000
- Mean elapsed seconds: 0.1
- Searches / page fetches: 1 / 0
- Observed tokens: 0
- Complete token accounting: True

## Stop reasons

- evidence_sufficient: 1

## Most frequent verification gaps


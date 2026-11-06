# Flash evaluation release decision

The tested Flash revisions did not qualify for confirmation. The shared final case manifest is frozen at 500 AVeriTeC development claims, previously studied with Gemma. Both final Flash runs are at **0/500 attempted**, and both planned matched current-workflow runs are unstarted. The twelve confirmation claims remain untouched.

| Model | Current correct / attempted | Compact correct / attempted | Correct acceptances, current / compact | Failures, current / compact |
| --- | ---: | ---: | ---: | ---: |
| GLM 5.3 Flash | 1/6 | 0/6 | 0 / 0 | 2 / 6 |
| DeepSeek V4.1 Flash | 1/6 | 2/6 | 0 / 0 | 1 / 0 |

Coverage and incorrect acceptances were zero in every arm. Accuracy among accepted verdicts was undefined. Macro F1 was 0.100 versus 0.000 for GLM and 0.167 versus 0.350 for DeepSeek. DeepSeek's compact arm returned 34 exact citations of 34 final-assessment citation references, with 29 passing automated semantic review. The current arm returned six exact citations of eight references, all six passing automated semantic review. These citations did not yield accepted verdicts. Independent human annotation has not been performed.

The GLM compact failure count made the eight-case guard unreachable at five pairs. Even three more baseline failures would have left fewer baseline failures than the five already observed in the candidate. The scheduled batch closed at six matched pairs per model and the remaining two case blocks were left untouched. The six GLM compact failures included three schema failures and three free page-fetch transport failures. All attempted cases remain in the denominator.

The short contract replay used the same saved evidence, tags and output cap. It recovered valid evidence-bearing responses in two of three GLM replays and preserved DeepSeek's Supported proposal. The third GLM replay reached 4,096 generated tokens without a parseable assessment, so the all-four diagnostic guard failed. The early, fixed-evidence gains do not establish end-to-end accuracy or acceptance. These are bounded failures for the evaluated designs and cap.

Actual use across Flash phases and diagnostics was 125 Ollama requests, 232 Jev requests, 111 searches and 217 fetch reservations. Four free Fetch outcomes remained unknown after read timeouts and were counted once. All Ollama and Jev outcomes and model IDs were reconciled. The uncached list-price estimates were $0.343 Ollama and $0.023 Jev. No account, payment, or quota error prevented evaluation. The blocker was the scientific release guard combined with unresolved generation reliability under the tested settings.

The current workflow is the default. Query-exhaustion remains opt-in. The revised manuscript preserves the completed Gemma, failed pilot and query-exhaustion findings, and labels the Flash evidence as development only.

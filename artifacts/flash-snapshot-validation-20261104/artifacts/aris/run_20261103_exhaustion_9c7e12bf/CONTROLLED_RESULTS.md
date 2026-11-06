# Query-exhaustion decision

**Keep the baseline as default. Keep query exhaustion opt-in.** The controlled evidence rejects a zero-loss guarantee for the policy. The live effect is unresolved. The historical pilot's two candidate runs reached exhausted queries with unresolved citation review. Neither used query-exhaustion stopping.

| Frozen offline stratum | Paired cases | Early stops | Baseline and candidate assessments per pair | Correct acceptance lost | Incorrect baseline acceptance avoided |
| --- | ---: | ---: | --- | ---: | ---: |
| Completed review | 4 | 4 | 3 and 2 | 2 | 1 |
| Unresolved review | 4 | 0 | 3 and 3 | 0 | 0 |

Eight of eight traces passed. All early stops preserved the exact round-two proposal and both literal citations. Neither policy searched in round three. In e01 and e04, reassessment changed Medium to High on unchanged evidence and the baseline accepted the correct verdict, while stopping preserved a correct proposal with abstention. In e03 it changed a correct proposal to an incorrect accepted verdict, which stopping avoided. In u03 both policies accepted the same wrong verdict under the permissive scripted round-three reviewer. These are designed reachability outcomes with zero inference sends, not observed rates of model rescue or regression.

The follow-up eligibility screen reused the existing 252-row no-search audit instead of rerunning it. The semantic guard rules out 77 of those rows, including both recovered correct acceptances. In the 175 with no recorded blocker, reassessment changed two wrong labels to correct and one correct label to wrong, and added no acceptances. Round-two source-review completeness is missing, so these 175 are only possibly eligible. Within the saved subset, truncation could change correct predictions by −2 to +1, depending on eligibility. The corresponding third rounds recorded 2,877,298 observed tokens. These are retrospective bounds and counts for the saved trajectories, with incomplete accounting. They are not deployed savings or rates.

The wire fixtures exercised real LangChain/Ollama client serialization using mocked responses for the three tags. All passed and sent no service inference. The 79 repository tests passed. The completed pilot and original 500-claim study remain separate and retain their original attempt denominators and artifacts.

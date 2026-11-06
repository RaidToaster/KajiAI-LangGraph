# Live decision

**No-go for default query-exhaustion stopping under the frozen zero-loss guard.** Finish after batch one. The second frozen batch remains unrun by the predeclared rule.

| Exact requested cloud tag | Runtime response ID | Completed pairs | Candidate early stops | Correct proposals baseline / candidate | Correct acceptances baseline / candidate | Actual sends | Continuation sends skipped | Continuation tokens skipped |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gemma4:31b-cloud` | `gemma4:31b` | 4 | 2 | 4 / 4 | 3 / 1 | 4 | 2 | 4,446 |
| `glm-5.3-flash:cloud` | `glm-5.3-flash` | 4 | 2 | 1 / 2 | 0 / 0 | 7 | 3 | 9,086 |
| `deepseek-v4.1-flash:cloud` | `deepseek-v4.1-flash` | 4 | 2 | 4 / 4 | 0 / 0 | 4 | 2 | 7,461 |

All 12 pairs passed the trace guard, with no workflow failures or replacements. All six completed-review candidates preserved the exact round-two assessment and both citations. All six unresolved-review pairs continued and matched under coupled continuation. The GLM baseline retained zero literal quotes across its four cases, while its candidate retained four. Gemma and DeepSeek each retained eight literal quotes under either policy.

Gemma e01 and e02 lost a correct acceptance while preserving the right proposal and two literal quotes. In e01 the firsthand account and committee record directly support the Thursday fair. In e02 the public opening record identifies August 2 and the diary corroborates an August opening ceremony. The diary does not establish the exact day or settle a hypothetical distinction between public opening and earlier access. The authored fixture refers to one opening, and e01 alone meets the stop rule. The separate audit and fresh provisional reviewer corroborated these findings. No independent human citation annotation was performed.

Actual use was 15 terminal HTTP 200 Ollama replies with complete usage, 23,181 input plus 19,266 output tokens. Three GLM sends were schema repairs, with no transport retries. Four GLM and one DeepSeek replies reached the 2,048 requested generation cap. Measured wall time was 110.109 seconds for the whole batch, with zero TinyFish or Jev sends. The candidate's 8 attributed continuation sends and 21,454 tokens come from replaying identical unresolved-case inputs. There were only 15 physical sends. The 7 skipped sends and 20,993 skipped tokens quantify the observed baseline continuations that the candidate bypasses on this designed sample. They do not estimate live-web savings or latency.

Eligible loss counts were 2/2 for Gemma and 0/2 for each Flash model. Exact fixed-n 95% binomial references are 15.8–100% and 0–84.2%, respectively. The same designed cases across models, scripted correct prefixes, coupled continuations and sequential stop preclude a representative population estimate. The Flash models' zero baseline acceptance gives no evidence of preserving useful acceptance. Model results are conditional on this prompt, evidence and output cap.

The existing Pro account showed $59.97 in included credits with auto-reload off. The first launch was rejected by automatic approval review because it required a concrete allowance. No request was dispatched in that attempt. The user then explicitly approved the requested two-batch allowance, and the first batch ran on included credits. Based on the public regular rates and observed uncached tokens, estimated use is under $0.02, separate from the dashboard debit. Billing was not changed.

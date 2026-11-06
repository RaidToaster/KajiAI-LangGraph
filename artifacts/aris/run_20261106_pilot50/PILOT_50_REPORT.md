# Frozen50-case resource pilot

Status: 46/200fresh attempts accounted. Remaining450cases are NOT authorized.

The candidate is UNQUALIFIED. Its frozen GLMnative test failed scope/materiality fidelity; DeepSeek had not run this exact snapshot. No method tuning or historical pass rewriting.

|Model/arm|Attempted|Completed|Failed|Ollama input/output|Jev input/output|Search/FetchURLs|Active seconds|Estimated model/Jev USD|
|---|---:|---:|---:|---|---|---|---:|---|
|glm/baseline|12|10|2|458680/162473|184737/22200|49/98|1494.7|0.150038/0.007759|
|glm/candidate|11|1|10|306908/141924|512159/59159|37/74|1331.0|0.116998/0.021511|
|deepseek/baseline|11|11|0|490260/144619|194955/22359|48/93|1314.0|0.320621/0.008188|
|deepseek/candidate|12|2|10|202902/27515|413299/51963|36/72|709.6|0.093889/0.017359|

Active processing: 4849.249s. Recorded quota waits: 0.000s. First-attempt to last-finish calendar: 23083.179s. Other between-attempt startup/audit: 18233.930s. Preflight/startup before the first attempt is separate (timestamps in protocol/PREFLIGHT/launch records).

Per-arm mean/median/P90/P95, timeouts, service-time distributions and failure reasons are in summary.json and attempts.csv. Missing cache/reasoning/billing counters remain unknown. Raw requests/responses and per-send timing reside under attempts/. Round traces are retained in completed result.json; no round duration is invented for failed/missing traces.

Candidate: archivedevidence_adjudicated, bound anchors, predecision source-path review, single materiality owner, questions_as_guidance, provenance review, source-reference research,6144assessmentoutput, GLMhigh/DeepSeekfalse. Baseline: original standard workflow,4096output and original default reasoning behavior. This compares a combined intervention.

Estimates use peak uncached [Ollama rates](https://ollama.com/pricing): GLM$0.15input/$0.50output and DeepSeek$0.30/$1.20 per million. [Jev1.13](https://docs.typesafe.ai/models):$0.042/millioninput, outputfree. [TinyFishSearch/Fetch](https://www.tinyfish.ai/pricing) free within limits. No provider billing total was available; these are rate-derived estimates.

Forecasts: FORECAST_500.json provides10xfull500and9xadditional450byarm, paired bootstrap intervals and quota-aware schedule replay when all200finish. Failed attempts remain in denominators. Cache/offpeak sensitivity and all-timeout bounds are disclosed. No remaining cases were launched.

Historical approximate balances ($60Ollama/$4.77Jev) were reconciled conservatively against recorded usage in PREFLIGHT.json; they were not freshly verified account balances. Historical unknown usage remains separate.

This adaptive resource pilot is not pristine held-out evidence of improvement. Label agreement is descriptive and is not official AVeriTeC evidence scoring. Inference receives only claim and claim date, never gold labels.

Pilot incomplete: inspect STOP.json/status.json. Do not replace started attempts or treat partial totals as50case estimates.

The interrupted attempt retained 8.157 seconds of observed runtime as a lower bound. Its exact stop time and one TinyFetch outcome remain unknown. The reservation counts as one Fetch URL. The activity gap during the interruption is separate from quota waiting. The usage lookup receipts and `interruption_accounting` in `FORECAST_500.json` document this gap.

The 500-case and additional 450-case estimates remain pending until the 50-case sample is accounted.

TinyFetch usage history confirmed terminal provider outcomes for locally truncated responses. Each affected workflow remains a recorded execution failure. See the service ledger for the receipts.

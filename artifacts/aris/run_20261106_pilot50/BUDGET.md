# Concrete preflight budget — frozen pilot only

Authorized: 50 shared cases × 2 arms × 2 exact models = 200 fresh attempts. No remaining450 release.

Scheduling ceilings: $10 Ollama and $1 Jev from user-confirmed existing credits; $0 paid retrieval. Published peak uncached rates per million tokens: GLM input$0.15/output$0.50; DeepSeek$0.30/$1.20; Jev1.13 input$0.042/outputfree. DeepSeek offpeak and cache discounts are excluded from reservations.

Before each Ollama send reserve 1,048,576input plus1,048,576output tokens: GLM$0.6815744 or DeepSeek$1.572864. This deliberately exceeds one shared1Mcontext; it covers requested-output limits being ignored. Jev reserve65,536input=$0.002752512. Release only on complete known matching-model usage. Therefore dispatch may stop below the nominal ceiling if its remaining headroom cannot cover the next conservative reservation. These are scheduling limits, not provider-enforced billing caps.

Maximum request counts:1600Ollama,8000Jev,1200Search,2400FetchURLs. These cannot all be guaranteed to fit the monetary caps; stop-before-spend rules take precedence. At most one worker, two numerical threads,300seconds/attempt; maximum child processing16.667hours. Previous64mixed-development attempts averaged87.393seconds/attempt and7.6875FetchURLs; applying that observation solely for planning gives4.855processinghours and1537.5FetchURLs. It is not a prediction or replacement pilot measurement.

Preflight recorded retrieval headroom:0Search in the last hour and143FetchURLs in rolling24h. Conservative pacing remains27Search/minute,450/hour,135FetchURLs/minute,900/rolling24h. Reserve full next-cell6Search/12FetchURLs. Historical fetch throughput suggests waiting across at least one daily window; the2400URLworst case may require two waits. Expect roughly one to three calendar days depending on failures, latency, old quota expiry and actual retrieval use. Waits are measured separately, never bypassed.

Current user reply: 'Confirmed: credits available, free Hobby tier, no other worker'. This confirms >=$10Ollama/>=$1Jev, current freeHobby retrieval and no competing worker. It is not a freshly viewed exact balance. Dated approximate$60/$4.77 less conservative all-recorded known costs and a separate$1historicalUNKNOWN model reserve leaves modeled$57.52/$4.69; external activity is unknown. Historical UNKNOWN usage remains UNKNOWN.

Rates verified2026-11-06Asia/Jakarta at https://ollama.com/pricing and https://docs.typesafe.ai/models.1Mcontext bounds at both exact Ollama model library pages; Jev64kcontext at model docs. Free retrieval limits at https://www.tinyfish.ai/pricing; retained user accountHobby/free confirmation takes precedence over any hypothetical paid switch. No purchases, topups, subscriptions, automaticBuilder switch or billing changes.

Stop on operational/model identity/accounting/quota/spend failures; no unknown-outcome replay. Known parser/execution errors, wrong predictions and abstentions remain results; never rerun/replace started cells. Source/scorer/settings/schedule froze before first inference; minimal launcher hash is recorded separately at launch.

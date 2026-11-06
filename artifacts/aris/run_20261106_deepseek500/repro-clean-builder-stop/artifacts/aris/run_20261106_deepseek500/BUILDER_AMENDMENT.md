# Builder retrieval amendment

The user resumed the study and authorized up to $12 in existing TinyFish wallet funds for the remaining scheduled cells. The $30 Ollama and $2.50 Jev ceilings and all 1,000 frozen cell identities and their ordering still apply. The amendment is operational and records a change in retrieval account terms. It leaves case inputs, service endpoints, prompts, workflow, model IDs, evidence checks, analysis and attempt budgets frozen.

The Builder dashboard reports 150 Search requests and 250 Fetch URLs per minute, and a pricing transition at 11:00 WIB on November 6, 2026. The wallet lookup at 10:44 WIB verified $12 available, auto-reload unconfigured and currently zero rates. The Builder daily Fetch limit was not displayed. The dispatcher therefore retains the published standard ceilings of 500 Search requests per hour and 1,000 Fetch URLs in rolling 24 hours. It uses the local reservations plus a separate provider history expiry check.

The Builder wrapper checks wallet rates at startup. A cell starts only when its entire retrieval budget fits the authorized cap and available wallet. All retrieval sends, including errors and unknown outcomes, reserve their full rate at the recorded tariff. Tariff receipts are recorded per cell. An in-flight cell will not straddle the pricing transition. The first cell after the transition requires effective rates from the wallet. The runner then continues through untouched scheduled cells and handles quota waits between attempts. A rejected request or spend boundary is recorded without replaying any started cell.

At the earlier advertised rates of $0.005 per Search and $0.001 per Fetch URL, the retained pilot's fresh usage forecast implies roughly $26.14 for all 953 remaining cells. The $12 ceiling may bind before study completion. Rates and traffic are measured separately from this planning estimate.


## Effective paid phase

The post-transition wallet read verified $0.005/Search and $0.001/Fetch URL.
The paid amendment uses the 150 Search/minute and 250 Fetch URL/minute Builder
limits. TinyFish documents its daily free allowances as billing thresholds
that admit additional requests with a positive wallet, so the paid phase no
longer has the earlier temporary rolling day and hourly limits. It reserves
the full verified wallet rate for all Search and Fetch sends.

References: https://docs.tinyfish.ai/fetch-api/reference#billing and
https://docs.tinyfish.ai/search-api/reference#billing.

The first paid baseline cell dev-001 timed out on Fetch request 004. The
provider usage history uniquely matched a terminal failed timeout, so the
cell remains an execution failure and its request remains reserved. Raw
stop and response metadata were preserved. Only the next untouched cell
was released. The recovery overlay verifies receipt SHA-256, URL, format
and time against the original raw request before permitting a continuation.

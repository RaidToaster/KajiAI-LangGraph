# Provider-triggered retrieval pacing

The raw journals verified 107 terminal cells before the resumed dispatch. These
were 47 reused pilot records and 60 fresh Builder records. The next untouched
cell was dev-007-deepseek-baseline. The resumed wallet check recorded zero USD
per Search and Fetch URL, with automatic reload unconfigured.

The schedule, model identities, arm settings, evidence checks, 300-second
worker limit, serial execution, and per-cell transport limits retain the
original hashes. The dispatcher uses the existing Ollama USD 30 and Jev USD
2.50 ceilings and accounts for earlier retrieval under the USD 12 Builder
ceiling. Each fresh Hobby cell has a verified zero-rate tariff receipt.
The dispatcher bypasses the previous minute, hour, rolling-day and full-cell
retrieval quota checks.

The worker journals provider retry/reset headers independently of the body.
A known quota rejection leaves the cell terminal and delays the next untouched
cell to the latest applicable provider time. The documented TinyFish
FREE_ALLOWANCE_EXHAUSTED rejection resets at midnight UTC. Headerless HTTP 429
responses use conservative reactive backoff. Read-only usage history can
reconcile a unique matching retrieval record. Ambiguous or unavailable
outcomes retain the original send and its reservation. The preserved records
show the local workflow failure even when provider history shows completion.

The first launcher revision was checked against the running journals by a
fresh GPT-6.1 Sol reviewer. The audit is same-family and provisional. Offline
checks exercised the numeric and date retry fields, a rejection whose body
was unavailable, the documented daily reset, and a generic access denial.
The provider behavior reference is the [TinyFish error documentation](https://docs.tinyfish.ai/error-codes).

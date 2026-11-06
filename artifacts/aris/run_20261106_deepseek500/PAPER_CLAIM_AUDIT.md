# Interim Builder-phase paper claim audit

**Verdict: PASS for the 80-cell interim snapshot.** A fresh GPT-6.1 Sol high reviewer audited the DeepSeek manuscript against the frozen schedule, raw request/response and workflow records, Builder terms, and stop receipts. The earlier 47-cell audit retains the historical Gemma, controlled stopping and Flash development checks. Both reviews are same-family and provisional. Independent human citation and source-credibility adjudication remains outstanding.

| Claim group | Independent raw recount |
|---|---|
| Coverage and schedule | 47 reused and 33 fresh terminal cells form the first 80 scheduled cells. All reused-file hashes matched. The last cell was dev-427-deepseek-candidate and the next untouched cell is dev-373-deepseek-baseline. |
| Outcomes | 40 cells per arm. Baseline/candidate correct proposals 7/4, failures 1/29, correct acceptances 1/0, wrong acceptances 0/0, worker timeouts 0/0. All observed pairs belong to the pilot stratum. |
| Paired effect | Six losses, three gains and 31 ties. Candidate-minus-baseline difference −7.5 points and the 10,000-draw paired bootstrap interval −22.5 to +7.5. |
| Resource records | All eight model-token counts, 185/118 Search reservations, 366/225 Fetch URL reservations and 4,224.606/2,757.858 worker seconds match for reused/fresh cohorts. There were three fresh Fetch transport read timeouts. |
| Billing | Eight zero-rate fresh cells recorded 31 searches and 60 Fetch URLs. The remaining 25 fresh cells recorded 87 full-rate Search reservations and 165 full-rate Fetch URL reservations. The amount reserved is $0.600. The wallet delta is account-level and per-send charges are unavailable. |
| Stop | TinyFish Search request 007 on dev-427-deepseek-candidate had a connection reset before an HTTP response. Three bounded history reads matched the neighboring control and found no matching record. The $0.005 Search reservation remains included in the $0.600 total. |

The manuscript distinguishes the initial Builder pacing and subsequent paid minute limits, the observed sample and planned denominator, worker versus transport timeouts, and provider billing versus conservative reservations.


"""Scale retained failure-inclusive pilot observations by each arm's fresh quota."""
import csv
import json
from pathlib import Path
import random
import statistics

RUN = Path(__file__).resolve().parent
keys = ("tinyfish_search_sends", "fetch_urls", "active_seconds", "ollama_estimated_usd", "jev_estimated_usd")
with (RUN/"attempts.csv").open(encoding="utf8", newline="") as stream:
    rows = [r for r in csv.DictReader(stream) if r["source"] == "reused"]
remaining = {"baseline":476, "candidate":477}
estimates = {}
rng = random.Random(20261106)
for arm, count in remaining.items():
    arm_rows = [r for r in rows if r["arm"] == arm]
    draws = {key:[] for key in keys}
    for _ in range(4000):
        sample = rng.choices(arm_rows,k=len(arm_rows))
        for key in keys:
            draws[key].append(statistics.mean(float(r[key]) for r in sample)*count)
    estimates[arm] = {key: dict(point=statistics.mean(float(r[key]) for r in arm_rows)*count,
                                bootstrap_95=[sorted(draws[key])[99],sorted(draws[key])[3899]])
                      for key in keys}
total = {key:sum(arm[key]["point"] for arm in estimates.values()) for key in keys}
out = dict(untouched_by_arm=remaining,arm_estimates=estimates,total_point_estimates=total,
           worker_hours=total["active_seconds"]/3600,fetch_cap_per_rolling_24h=900,
           nominal_fetch_quota_days=total["fetch_urls"]/900,
           cost_assumption="Peak uncached DeepSeek and Jev list rates. Observed counters, not provider charges.",
           limitation="Adaptive early sample. Within-arm percentile intervals describe observed case variability only; they omit quota history, drift and outages.")
(RUN/"forecast.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf8")
print(json.dumps(out["total_point_estimates"]))


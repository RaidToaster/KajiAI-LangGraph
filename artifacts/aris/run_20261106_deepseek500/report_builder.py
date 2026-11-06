"""Recount retrieval charges reserved from actual sends and per-cell tariff receipts."""
from collections import Counter, defaultdict
from decimal import Decimal
import json

import builder
import launch

RUN = launch.RUN
read, save = launch.read, launch.save


def main():
    allocation = builder.amendment()
    attempts = {}
    totals = defaultdict(Decimal)
    calls = Counter()
    phases = Counter()
    for path in sorted((RUN/"attempts").glob("*/attempt.json")):
        attempt = path.parent.name
        tariff = read(path.parent/"builder-tariff.json")
        rates = {k: Decimal(v) for k, v in tariff["rates"].items()}
        usage = launch.pilot.usage(path.parent, launch.MODEL)
        retrieval = {service:sum(r.get("url_attempts", 1) for r in usage if r["service"] == service)
                     for service in builder.RATE_KEYS}
        cost = builder.reserved_cost(usage, rates)
        phase = tariff.get("phase", "builder")
        assert phase in {"builder","hobby"}
        if phase == "hobby":
            assert not cost and not any(rates.values())
        phases[phase] += 1
        assert cost <= Decimal(tariff["reserved_max_usd"])
        attempts[attempt] = {"phase":phase,"searches": retrieval["tinyfish_search"], "fetch_urls": retrieval["tinyfish_fetch"],
                             "rate_usd": tariff["rates"], "reserved_usd": str(cost),
                             "rate_checked_at": tariff["checked_at"], "rate_as_of": tariff["rates_as_of"]}
        totals["reserved"] += cost
        calls.update(retrieval)
    cap = Decimal(allocation["wallet_ceiling_usd"])
    assert totals["reserved"] <= cap
    out = {"fresh_builder_attempts":phases["builder"],"fresh_hobby_attempts":phases["hobby"], "wallet_ceiling_usd":str(cap),
           "rate_derived_reserved_usd":str(totals["reserved"]),
           "remaining_authorized_usd":str(cap-totals["reserved"]),
           "search_calls":calls["tinyfish_search"],"fetch_urls":calls["tinyfish_fetch"],
           "actual_provider_billing_usd":None,"attempts":attempts}
    save(RUN/"builder-summary.json",out)
    print(json.dumps({k:v for k,v in out.items() if k != "attempts"}))


if __name__ == "__main__":
    main()


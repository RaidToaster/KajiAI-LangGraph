from decimal import Decimal

from kaji_langgraph.evidence_ledger import PassageLink
from kaji_langgraph.quantity_ledger import ReportedQuantity,compare_reported_quantities


def quantity(id,amount,population="bottom38_households",**changes):
    data=dict(id=id,amount=Decimal(str(amount)),unit="USD_billion",measure="net_wealth",
              population=population,period="2020-02",passage=PassageLink(
                  source_url="https://example.test/record",source_hash="version1",
                  quote=f"Reported quantity: {amount}"))
    data.update(changes)
    return ReportedQuantity(**data)


def compare(left,rights,population="bottom38_households"):
    return compare_reported_quantities(left,rights,target_population=population,target_period="2020-02")


def test_two_positive_totals_do_not_reverse_a_conditional_inequality():
    result=compare(quantity("person",64.2,"person"),[quantity("estimateA",6),quantity("estimateB",11.4)])
    assert result["conditional_order"]=="greater_for_all_reported"
    assert not result["semantic_binding_verified"] and not result["independence_verified"]
    assert "confidence" not in result and "accepted" not in result


def test_threshold_crossing_scenarios_remain_unresolved():
    result=compare(quantity("person",12,"person"),[quantity("estimateA",11),quantity("estimateB",14)])
    assert result["conditional_order"]=="differs_across_reported_scenarios"


def test_negative_bottom37_cannot_be_transferred_to_positive_bottom38():
    result=compare(quantity("person",64.2,"person"),[quantity("bottom37",-44,"bottom37_households"),quantity("bottom38",6)])
    assert result["conditional_order"]=="not_comparable"
    assert any("bottom37" in q and "population" in q for q in result["scope_blockers"])


def test_household_average_proxy_does_not_establish_poorest_individuals():
    result=compare(quantity("person",64.2,"person"),[quantity("converted",11.4,"poorest125m_individuals",population_is_proxy=True)],"poorest125m_individuals")
    assert result["conditional_order"]=="not_comparable"
    assert any("proxy" in q for q in result["scope_blockers"])


def test_dates_units_measurement_and_explicit_uncertainty_are_not_discarded():
    result=compare(quantity("person",64.2,"person"),[quantity("other",6,period="2025-02",unit="USD_million",measure="gross_assets",unresolved_assumptions=["origin unclear"])])
    assert result["conditional_order"]=="not_comparable"
    assert len(result["scope_blockers"])==4

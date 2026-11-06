"""Conditional arithmetic on scope-keyed, unverified reported quantities.

No output from this module certifies evidence, assigns confidence, clears a
research gap, or changes the factual acceptance gate.
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel,Field

from kaji_langgraph.evidence_ledger import PassageLink


class ReportedQuantity(BaseModel):
    """A proposed reading of a passage, still requiring semantic verification."""
    id: str
    amount: Decimal
    unit: str
    measure: str
    population: str
    period: str
    passage: PassageLink
    population_is_proxy: bool=False
    unresolved_assumptions: list[str]=Field(default_factory=list)


def compare_reported_quantities(left: ReportedQuantity,rights: list[ReportedQuantity],*,
                                target_population: str,target_period: str) -> dict:
    """Compare explicit scenarios while retaining every incompatible scope.

    Quantity values and semantic keys are proposed inputs, not extracted or
    verified facts. Distinct reported estimates are not a statistical interval.
    """
    blockers=[]
    if not rights:blockers.append("No right-hand reported quantity.")
    if left.period!=target_period:blockers.append("Left-hand period differs from the target period.")
    if left.population_is_proxy:blockers.append("Left-hand population uses a proxy.")
    blockers.extend(left.unresolved_assumptions)
    for right in rights:
        if right.population!=target_population:blockers.append(f"{right.id}: population differs from the target population.")
        if right.period!=target_period:blockers.append(f"{right.id}: period differs from the target period.")
        if right.unit!=left.unit:blockers.append(f"{right.id}: units differ; no conversion is inferred.")
        if right.measure!=left.measure:blockers.append(f"{right.id}: measurement definitions differ.")
        if right.population_is_proxy:blockers.append(f"{right.id}: population uses a proxy.")
        blockers.extend(f"{right.id}: {q}" for q in right.unresolved_assumptions)
    order="not_comparable"
    if rights and not blockers:
        relations=["greater" if left.amount>r.amount else "less" if left.amount<r.amount else "equal" for r in rights]
        order=relations[0]+"_for_all_reported" if len(set(relations))==1 else "differs_across_reported_scenarios"
    return {"conditional_order":order,"scope_blockers":list(dict.fromkeys(blockers)),
            "left_id":left.id,"right_ids":[r.id for r in rights],
            "semantic_binding_verified":False,"independence_verified":False,
            "scope":"Conditional arithmetic only. Inputs remain unverified; reported alternatives do not define an uncertainty interval. No acceptance or confidence decision is made."}

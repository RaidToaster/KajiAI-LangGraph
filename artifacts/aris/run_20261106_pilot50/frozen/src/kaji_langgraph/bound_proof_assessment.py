"""Issue dependencies without a second, unanchored factual recital.

The model retains all judgments. Factual premises live in source-bound findings;
questions and dependency links remain subject to semantic audit.
"""
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kaji_langgraph.proof_assessment import ProofDecision, ProofIssue, compile_proof, proof_prompt


class BoundIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    component: str
    source: str | None = None
    question: str = Field(min_length=1)
    classification: Literal["material", "nonblocking"]
    dependency: Literal["support_missing", "authenticity_unresolved", "independence_unresolved",
        "scope_unaligned", "opposing_evidence", "outside_target", "class_consistent", "response_missing", "other_uncertainty"]
    basis_findings: list[str]


class BoundProofDecision(ProofDecision):
    issues: list[BoundIssue]


def bound_proof_prompt(context, selection, ranges):
    original = proof_prompt(context, selection, ranges)
    prefix = original.rsplit("\nReturn ONLY JSON matching:\n", 1)[0]
    prefix = prefix.replace("with an accurate reason.", "with an accurate dependency category and linked factual premises.")
    prefix = prefix.replace("explain that distinction honestly.", "Represent that distinction through the issue dependency and linked findings.")
    schema = BoundProofDecision.model_json_schema()
    defs = schema["$defs"]
    bound = json.loads(original.rsplit("\nReturn ONLY JSON matching:\n", 1)[1])["$defs"]
    for name in ("ProofComponent", "ProofOrigin", "CatalogueFinding"):
        defs[name] = bound[name]
    defs["BoundIssue"]["properties"]["component"]["enum"] = list(context["required_components"])
    defs["BoundIssue"]["properties"]["source"]["enum"] = [None, *[r["id"] for r in context["records"]]]
    return prefix + """

ISSUE DEPENDENCY CONTRACT: There is no free-form reason field. Express each
remaining issue as a neutral question without asserting a factual premise.
Choose its dependency category and material/nonblocking classification yourself.
Link basis_findings to your finding IDs when factual premises are needed. Each
such premise must be a narrow finding supported by its ONE cited passage; never
transfer a method or fact between outlets. Empty basis is allowed for missing
evidence. Dependency categories describe your reasoning, not certified facts.
other_uncertainty permits any issue that does not fit another category; preserve
it as a neutral question. There is no category-based client materiality filter.
Every material entry blocks, whatever its category or basis. No category clears
another issue. A factual or loaded question still fails fidelity audit. Keep
every real uncertainty, including issues with no available supporting passage.
The client renders the category and linked IDs verbatim; it infers no factual
premise or resolution from them. Do not add a factual reason to another field.
""" + "\nReturn ONLY JSON matching:\n" + json.dumps(schema, separators=(",", ":"))


def compile_bound_proof(selection, decision, components, records):
    issues = [ProofIssue(id=i.id, component=i.component, source=i.source,
        question=i.question, classification=i.classification,
        reason=f"Model dependency: {i.dependency}; basis finding IDs: {', '.join(i.basis_findings) or '(none)' }.")
        for i in decision.issues]
    translated = ProofDecision.model_validate({**decision.model_dump(exclude={"issues"}),
        "issues": [i.model_dump() for i in issues]})
    result = compile_proof(selection, translated, components, records)
    known = {f.id for f in decision.findings}
    for issue in decision.issues:
        unknown = set(issue.basis_findings) - known
        if unknown:
            result.gaps.append(f"Unknown issue basis finding IDs for {issue.id}: {sorted(unknown)}")
        if len(set(issue.basis_findings)) != len(issue.basis_findings):
            result.gaps.append(f"Duplicate issue basis finding IDs for {issue.id}")
    result.indexed_input.update(bound_proof_response=decision.model_dump(mode="json"),
        bound_issue_registry=[i.model_dump(mode="json") for i in decision.issues],
        assessment_mode="bound_proof")
    return result

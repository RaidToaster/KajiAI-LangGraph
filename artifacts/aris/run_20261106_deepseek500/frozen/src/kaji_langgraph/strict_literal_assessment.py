"""Conditional issue output: typed concerns or an explicit other question."""
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kaji_langgraph.literal_proof_assessment import LiteralProofDecision, compile_literal_proof, literal_proof_prompt


class TypedLiteralIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    component: str
    source: str | None = None
    classification: Literal["material", "nonblocking"]
    dependency: Literal["support_missing", "authenticity_unresolved", "independence_unresolved",
        "scope_unaligned", "opposing_evidence", "outside_target", "class_consistent", "response_missing"]
    basis_findings: list[str]


class OtherLiteralIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    component: str
    source: str | None = None
    classification: Literal["material", "nonblocking"]
    dependency: Literal["other_uncertainty"]
    basis_findings: list[str]
    custom_question: str = Field(min_length=1)


class StrictLiteralDecision(LiteralProofDecision):
    issues: list[TypedLiteralIssue | OtherLiteralIssue]


def strict_literal_prompt(context, selection, ranges):
    original = literal_proof_prompt(context, selection, ranges)
    prefix = original.split("For every remaining issue choose dependency,", 1)[0]
    schema = StrictLiteralDecision.model_json_schema()
    defs = schema["$defs"]
    inherited = json.loads(original.rsplit("\nReturn ONLY JSON matching:\n", 1)[1])["$defs"]
    for name in ("ProofComponent", "ProofOrigin", "LiteralFinding"):
        defs[name] = inherited[name]
    for name in ("TypedLiteralIssue", "OtherLiteralIssue"):
        defs[name]["properties"]["component"]["enum"] = list(context["required_components"])
        defs[name]["properties"]["source"]["enum"] = [None, *[r["id"] for r in context["records"]]]
    return prefix + """
CONDITIONAL ISSUE CONTRACT: For every remaining issue choose its exact component,
source, material/nonblocking classification and basis finding IDs. Common typed
dependencies have no free-text question/reason field: the client renders a
neutral question for that dependency. response_missing asks whether missing a
response leaves uncertainty; a missing response is not a denial. No category
chooses materiality or overrides any other issue. Every material entry blocks.

For ANY remaining uncertainty that typed dependencies cannot adequately express,
use other_uncertainty with a required custom_question. This escape is unrestricted
in topic: never omit a real issue or hide material uncertainty to fit categories.
custom_question must be a neutral question, without declarative factual premises;
needed factual premises use separate literal findings. Empty basis is allowed
for genuine missing evidence. No factual narrative is requested in another field.
Unknown/extra fields fail rather than being dropped. All raw issue declarations
survive. Actual confidence, stance, classes and independence remain your judgments;
whole-claim/context/provenance/uncertainty fidelity still require substantive audit.
""" + "\nReturn ONLY JSON matching:\n" + json.dumps(schema, separators=(",", ":"))


def compile_strict_literal(selection, decision, components, records):
    translated = LiteralProofDecision.model_validate(decision.model_dump(mode="json"))
    result = compile_literal_proof(selection, translated, components, records)
    result.indexed_input.update(strict_literal_response=decision.model_dump(mode="json"),
        strict_issue_registry=[i.model_dump(mode="json") for i in decision.issues],
        assessment_mode="strict_literal")
    return result

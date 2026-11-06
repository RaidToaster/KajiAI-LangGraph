"""Auditable component-to-passage links for diagnostic use.

The ledger records model judgments without certifying them. Exact references
are checked locally; semantic support and independence remain gate decisions.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from kaji_langgraph.models import SourceRecord


class PassageLink(BaseModel):
    source_url: str
    source_hash: str
    quote: str = Field(min_length=1)
    event_date: str = ""
    data_date: str = ""
    origin: str = ""
    relation: Literal["supports", "refutes", "context", "unresolved"] = "unresolved"


class ComponentLedger(BaseModel):
    component: str = Field(min_length=1)
    questions: list[str] = Field(default_factory=list)
    passages: list[PassageLink] = Field(default_factory=list)
    unresolved_material_questions: list[str] = Field(default_factory=list)


def audit_ledger(rows: list[ComponentLedger], sources: list[SourceRecord],
                 required_components: list[str]) -> dict:
    """Audit identity and literal anchoring; never infer a semantic pass.

    Empty/missing rows, unanchored dates/origins and unresolved questions are
    retained. A duplicate URL's latest version cannot validate an older quote.
    """
    versions = {(source.url, source.content_hash): source for source in sources}
    components = [row.component for row in rows]
    issues = []
    for required in required_components:
        if required not in components:
            issues.append({"component": required, "issue": "missing_component"})
    if len(components) != len(set(components)):
        issues.append({"issue": "duplicate_components"})
    checked = []
    for row in rows:
        links = []
        for link in row.passages:
            source = versions.get((link.source_url, link.source_hash))
            text = source.retrieved_text if source else ""
            offset = text.find(link.quote) if source else -1
            fields = {name: not value or value in text
                      for name in ("event_date", "data_date", "origin")
                      if (value := getattr(link, name)) is not None}
            valid = offset >= 0 and all(fields.values())
            links.append({**link.model_dump(), "exact_quote": offset >= 0,
                          "quote_start": offset if offset >= 0 else None,
                          "quote_end": offset + len(link.quote) if offset >= 0 else None,
                          "literal_metadata_checks": fields,
                          "reference_valid": valid})
            if not valid:
                issues.append({"component": row.component, "issue": "unanchored_reference",
                               "source_url": link.source_url})
        checked.append({**row.model_dump(), "passages": links})
    return {"components": checked, "issues": issues,
            "literal_references_valid": not issues,
            "semantic_support_verified": False,
            "independence_verified": False,
            "scope": "Literal-reference audit only; questions and ledger judgments are not evidence."}

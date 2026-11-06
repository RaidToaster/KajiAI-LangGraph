"""A compact line protocol for benchmark assessment responses."""
from __future__ import annotations

import re

from kaji_langgraph.models import BenchmarkAssessment


LINE_CITATIONS = """Use short findings and cite one source ID and passage ID per
finding. Cite each assertion with the relevant source IDs. Choose only passages
that directly establish the finding. Check dates, quantities and qualifications.
Evaluate independence among cited sources. Keep the summary to one sentence."""


LINE_CONTRACT = """

Return only the assessment block below. Replace example values using the evidence.
Write one item per line, with no Markdown. Use these verdicts: TRUE, FALSE,
CONFLICTING, NOT_ENOUGH_EVIDENCE. Confidence: High, Medium, Low.
Finding stance: supports, refutes, context. Booleans: true or false.
For FLAGS, the three booleans mean counterevidence searched, independent sources,
and peer-reviewed sources, in that order. Use one FINDING line per cited passage.
Copy each required assertion verbatim and list its source IDs separated by commas.
Include GAP, CONTRADICTION and QUERY lines only when needed.

BEGIN_ASSESSMENT
VERDICT|FALSE
CONFIDENCE|High
SUMMARY|One sentence
FINDING|refutes|S1|P1|One fact directly established by the passage
ASSERTION|true|S1|Exact required assertion
FLAGS|true|true|false
GAP|A material issue affecting the verdict
CONTRADICTION|Unresolved conflicting evidence
QUERY|A search for evidence to resolve a gap
END_ASSESSMENT
"""


def _boolean(value: str) -> bool:
    if value not in {"true", "false"}:
        raise ValueError(f"Invalid assessment boolean: {value}")
    return value == "true"


def parse_assessment_lines(
    text: str, *, stopped_normally: bool = False, retain_unresolved_proposal: bool = False,
) -> BenchmarkAssessment:
    lines = [line.strip() for line in text.splitlines()]
    starts = [
        index for index, line in enumerate(lines)
        if line == "BEGIN_ASSESSMENT" or (
            re.search(r"(?<!\w)BEGIN_ASSESSMENT$", line)
            and index + 1 < len(lines) and lines[index + 1].startswith("VERDICT|")
        )
    ]
    ends = [index for index, line in enumerate(lines) if line == "END_ASSESSMENT"]
    omitted_markers = False
    if len(starts) == len(ends) == 1 and starts[0] < ends[0]:
        body = lines[starts[0] + 1:ends[0]]
    elif stopped_normally and not (starts or ends) and text.count("</think>") == 1:
        # A normal GLM reply can omit the outer markers. Preserve a complete
        # proposal after its explicit thinking delimiter but withhold acceptance.
        body = [line.strip() for line in text.split("</think>", 1)[1].strip().splitlines()]
        if not body or not body[0].startswith("VERDICT|"):
            raise ValueError("Expected assessment immediately after thinking delimiter")
        omitted_markers = True
    else:
        raise ValueError("Expected one complete assessment block")

    fields: dict = {"evidence": [], "assertions": [], "gaps": [],
                    "contradictions": [], "next_queries": []}
    seen = set()
    for line in body:
        if not line:
            continue
        kind, separator, value = line.partition("|")
        if not separator or not value.strip():
            raise ValueError("Malformed assessment line")
        value = value.strip()
        if kind in {"VERDICT", "CONFIDENCE", "SUMMARY", "FLAGS"}:
            if kind in seen:
                raise ValueError(f"Duplicate assessment field: {kind}")
            seen.add(kind)
        if kind == "VERDICT":
            fields["proposed_verdict"] = value
        elif kind in {"CONFIDENCE", "SUMMARY"}:
            fields[kind.lower()] = value
        elif kind == "FLAGS":
            searched, independent, peer_reviewed = map(_boolean, value.split("|"))
            fields.update(counterevidence_searched=searched, sources_independent=independent,
                          peer_reviewed_sources=peer_reviewed)
        elif kind == "FINDING":
            stance, source, passage, finding = value.split("|", 3)
            fields["evidence"].append({"stance": stance, "source_urls": [source],
                                       "quotes": {source: passage}, "finding": finding})
        elif kind == "ASSERTION":
            if (stopped_normally and retain_unresolved_proposal and value.startswith("false|")
                    and value.count("|") == 1 and value[6:].strip()):
                fields["gaps"].append("An unresolved assertion omitted its text.")
                continue
            resolved, sources, assertion = value.split("|", 2)
            fields["assertions"].append({"resolved": _boolean(resolved), "assertion": assertion,
                                         "source_urls": [s.strip() for s in sources.split(",") if s.strip()]})
        elif kind in {"GAP", "CONTRADICTION", "QUERY"}:
            name = {"GAP": "gaps", "CONTRADICTION": "contradictions", "QUERY": "next_queries"}[kind]
            fields[name].append(value)
        else:
            raise ValueError(f"Unexpected assessment line: {kind}")
    if seen != {"VERDICT", "CONFIDENCE", "SUMMARY", "FLAGS"}:
        raise ValueError("Missing required assessment fields")
    if omitted_markers:
        fields["gaps"].append("The assessment omitted its required boundaries.")
    return BenchmarkAssessment.model_validate(fields)

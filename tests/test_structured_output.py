from __future__ import annotations

import json
from types import SimpleNamespace

from kaji_langgraph.assessment_lines import parse_assessment_lines
from kaji_langgraph.gate import evidence_gaps
from kaji_langgraph.llm import OllamaBackend
from kaji_langgraph.models import BenchmarkAssessment, Classification, EvidenceAssessment, SourceRecord
import pytest
from pydantic import ValidationError


class Runnable:
    def __init__(self, value):
        self.value = value

    def invoke(self, prompt):
        assert prompt
        return self.value


class RepairingModel:
    def with_structured_output(self, schema, *, method, include_raw):
        assert schema is Classification
        assert method == "json_mode"
        assert include_raw is True
        raw = SimpleNamespace(content="### Classification\nThis is general.", usage_metadata={"total_tokens": 9})
        return Runnable({"parsed": None, "raw": raw, "parsing_error": ValueError("not JSON")})

    def bind(self, *, format):
        assert format["title"] == "Classification"
        content = json.dumps(
            {
                "domain": "general",
                "confidence": 0.8,
                "reasoning": "General factual claim.",
                "risk_level": "low",
            }
        )
        return Runnable(SimpleNamespace(content=content, usage_metadata={"total_tokens": 7}))


def test_structured_output_repairs_markdown_response():
    backend = OllamaBackend.__new__(OllamaBackend)
    backend._model = RepairingModel()
    parsed, tokens = backend._structured(Classification, "Classify this claim")
    assert parsed.domain == "general"
    assert tokens == 16


def test_json_extractor_accepts_fenced_json():
    text = '```json\n{"domain":"political","confidence":0.7,"reasoning":"x","risk_level":"medium"}\n```'
    assert OllamaBackend._parse_json(Classification, text).domain == "political"


def test_analysis_prompt_includes_domain_specific_guidance():
    backend = OllamaBackend.__new__(OllamaBackend)
    captured = {}

    def capture(schema, prompt):
        captured["schema"] = schema
        captured["prompt"] = prompt
        return EvidenceAssessment(), 0

    backend._structured = capture
    guidance = {
        "research": "Prioritize registered clinical trials.",
        "analysis": "Distinguish trials from anecdotes.",
        "verification_standard": "Apply a strict medical evidence standard.",
    }
    backend.analyze(
        "A medical claim",
        "health_medical",
        ["A medical claim"],
        [],
        [],
        "2026-09-21",
        guidance,
    )
    assert captured["schema"] is EvidenceAssessment
    assert guidance["research"] in captured["prompt"]
    assert guidance["analysis"] in captured["prompt"]
    assert guidance["verification_standard"] in captured["prompt"]


def test_benchmark_analysis_uses_four_class_schema():
    backend = OllamaBackend.__new__(OllamaBackend)
    backend.verdict_mode = "averitec"

    def capture(schema, prompt):
        assert schema is BenchmarkAssessment
        assert "permitted factual labels are exactly" in prompt
        return schema(proposed_verdict="NOT_ENOUGH_EVIDENCE"), 0

    backend._structured = capture
    assessment, _ = backend.analyze("A claim", "general", ["A claim"], [], [], "2020-10-31", {})
    assert assessment.proposed_verdict == "NOT_ENOUGH_EVIDENCE"
    for verdict in ("MISLEADING", "UNVERIFIED"):
        with pytest.raises(ValidationError):
            BenchmarkAssessment(proposed_verdict=verdict)


def test_canonical_prompt_uses_the_same_text_the_quote_gate_checks():
    backend = OllamaBackend.__new__(OllamaBackend)
    backend.canonical_evidence_prompt = True
    prompts = []
    backend._structured = lambda schema, prompt: (prompts.append(prompt), 0)
    full = SourceRecord(
        url="https://example.org/full", retrieved_at="", query="", provider="mock",
        content_hash="full", snippet="obsolete snippet", page_text="canonical document",
        retrieval_kind="full_page",
    )
    snippet = SourceRecord(
        url="https://example.org/snippet", retrieved_at="", query="", provider="mock",
        content_hash="snippet", snippet="canonical fallback",
    )
    backend.analyze("A claim", "general", [], [full, snippet], [], "", {})
    assert '"retrieved_text": "canonical document"' in prompts[0]
    assert '"retrieved_text": "canonical fallback"' in prompts[0]
    assert "obsolete snippet" not in prompts[0]
    backend.canonical_evidence_prompt = False
    backend.analyze("A claim", "general", [], [full, snippet], [], "", {})
    assert '"snippet": "obsolete snippet"' in prompts[1]


def test_recovery_from_empty_truncation_keeps_the_original_evidence():
    original = "Evidence packet for a factual claim"
    backend = OllamaBackend.__new__(OllamaBackend)
    backend.recover_empty_assessment = True

    class TruncatedModel:
        def with_structured_output(self, schema, **kwargs):
            raw = SimpleNamespace(
                content="", usage_metadata={"total_tokens": 15},
                response_metadata={"done_reason": "length"},
            )
            return Runnable({"parsed": None, "raw": raw})

        def bind(self, *, format, reasoning):
            assert format["title"] == "BenchmarkAssessment"
            assert reasoning is False
            return self

        def invoke(self, prompt):
            assert original in prompt
            assert "Draft:" not in prompt
            return SimpleNamespace(content='{"proposed_verdict":"FALSE"}',
                                   usage_metadata={"total_tokens": 8})

    backend._model = TruncatedModel()
    result, tokens = backend._structured(BenchmarkAssessment, original)
    assert result.proposed_verdict == "FALSE"
    assert tokens == 23


def test_compact_passage_resolution_preserves_exact_text_and_rejects_unknown_ids():
    backend = OllamaBackend.__new__(OllamaBackend)
    backend.compact_evidence_prompt = True
    text = "The charter passed.\nThe vote was unanimous."
    source = SourceRecord(url="https://example.org/charter", snippet=text, query="",
                          retrieved_at="", provider="mock", content_hash="charter")

    def respond(schema, prompt):
        assert '"P1": ' + json.dumps(text) in prompt
        return schema.model_validate({
            "proposed_verdict": "TRUE",
            "evidence": [{
                "finding": "The charter passed unanimously",
                "source_urls": ["S1", "S8"],
                "quotes": {"S1": "P1", "S8": "P1"},
            }],
            "assertions": [{"assertion": "The vote was unanimous", "source_urls": ["S1"]}],
        }), 0

    backend._structured = respond
    result, _ = backend.analyze("The vote was unanimous", "general", [], [source], [], "", {})
    assert result.evidence[0].quotes == {source.url: text}
    assert result.evidence[0].source_urls == [source.url, "unresolved:S8"]
    assert result.assertions[0].source_urls == [source.url]


def test_incomplete_unresolved_assertion_preserves_proposal_with_blocking_gap():
    answer = (
        "BEGIN_ASSESSMENT\nVERDICT|FALSE\nCONFIDENCE|High\nSUMMARY|A source contradicts the claim.\n"
        "ASSERTION|false|S1\nFLAGS|true|true|false\nEND_ASSESSMENT"
    )
    with pytest.raises(ValueError):
        parse_assessment_lines(answer, stopped_normally=True)
    assessment = parse_assessment_lines(answer, stopped_normally=True, retain_unresolved_proposal=True)
    assert assessment.proposed_verdict == "FALSE"
    assert assessment.assertions == []
    assert "An unresolved assertion omitted its text." in evidence_gaps(assessment, ["claim"], [], {})
    with pytest.raises(ValueError):
        parse_assessment_lines(
            answer.replace("ASSERTION|false", "ASSERTION|true"),
            stopped_normally=True, retain_unresolved_proposal=True,
        )

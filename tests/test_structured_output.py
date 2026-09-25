from __future__ import annotations

import json
from types import SimpleNamespace

from kaji_langgraph.llm import OllamaBackend
from kaji_langgraph.models import Classification, EvidenceAssessment


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

from __future__ import annotations

from kaji_langgraph.graph import run_claim
from kaji_langgraph.retrieval import StaticRetriever


class FailingModel:
    def classify(self, claim):
        raise ConnectionError("Ollama unavailable")

    def decompose(self, claim):
        raise ConnectionError("Ollama unavailable")

    def analyze(self, claim, domain, assertions, sources, prior_gaps, reference_date, domain_guidance):
        raise ConnectionError("Ollama unavailable")


def test_model_failure_never_switches_provider_or_accepts(config, two_source_retriever):
    result = run_claim(
        "A vaccine claim requiring analysis",
        model=FailingModel(),
        retriever=two_source_retriever,
        config=config,
    )
    assert result.domain == "health_medical"
    assert result.verdict == "UNVERIFIED"
    assert result.stop_reason == "execution_error"
    assert any("Analysis failed: ConnectionError" in error for error in result.errors)

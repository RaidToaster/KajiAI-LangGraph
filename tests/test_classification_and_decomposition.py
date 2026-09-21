from kaji_langgraph.llm import heuristic_decomposition, keyword_classification


def test_domain_classification_health_indonesian():
    result = keyword_classification("Vaksin dan obat ini menyembuhkan penyakit")
    assert result.domain == "health_medical"


def test_claim_decomposition_preserves_full_claim_and_parts():
    claim = "The agency published the report and the minister signed the order"
    parts = heuristic_decomposition(claim)
    assert parts == ["The agency published the report", "the minister signed the order"]


def test_short_clause_is_not_detached_from_context():
    claim = "The report exists and is false"
    assert heuristic_decomposition(claim) == [claim]


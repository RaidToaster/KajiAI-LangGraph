from copy import deepcopy

from kaji_langgraph.gate import evidence_gaps
from kaji_langgraph.graph import run_claim
from kaji_langgraph.llm import DeterministicBackend
from kaji_langgraph.models import EvidenceAssessment
from kaji_langgraph.retrieval import StaticRetriever
from kaji_langgraph.report import format_report
from test_gate import source, valid_assessment


def test_later_snippet_cannot_hide_previously_fetched_quote():
    full = source("https://a.example/record", "Search summary")
    full.page_text = "The original document establishes the event date."
    full.retrieval_kind = "full_page"
    other = source("https://b.example/record", "Independent confirmation from another archive.")
    assessment = valid_assessment("Event occurred", [full, other])
    assessment.evidence[0].quotes[full.url] = full.page_text
    later_snippet = source(full.url, "Short search summary omitting the event date.")
    assert evidence_gaps(assessment, ["Event occurred"], [full, other, later_snippet], {}) == []


class NeedMoreBackend(DeterministicBackend):
    def analyze(self, claim, *args):
        return EvidenceAssessment(next_queries=[claim + " evidence"], gaps=["Find original records."]), 0


class FetchingRetriever(StaticRetriever):
    def __init__(self):
        super().__init__([
            {"url": "https://a.example/record", "snippet": "Search summary A"},
            {"url": "https://b.example/record", "snippet": "Search summary B"},
        ])
        self.fetched = []

    def fetch(self, url, **kwargs):
        self.fetched.append(url)
        return "Original page text from " + url, 200, None


def test_repeated_results_reuse_pages_and_continue_searches(config):
    config["policy"].update(full_page_retrieval=True, page_fetches_per_search=2)
    retriever = FetchingRetriever()
    result = run_claim("Documented event", max_rounds=3, model=NeedMoreBackend(), retriever=retriever, config=config)
    assert retriever.fetched == ["https://a.example/record", "https://b.example/record"]
    assert len(result.retrieval_ledger) == 2
    assert len(result.search_queries) == 3
    assert len(set(result.search_queries)) == 3


def test_rejected_prediction_remains_available_for_evaluation(config, two_source_retriever):
    class MediumBackend(DeterministicBackend):
        def analyze(self, *args):
            assessment, tokens = super().analyze(*args)
            assessment.confidence = "Medium"
            return assessment, tokens

    result = run_claim("A test claim", max_rounds=1, model=MediumBackend(), retriever=two_source_retriever, config=config)
    assert result.verdict == "UNVERIFIED"
    assert result.predicted_verdict == "TRUE"
    assert result.prediction_confidence == "Medium"
    assert result.prediction_summary
    assert result.verification_status == "insufficient_evidence"
    report = format_report(result)
    assert "Prediction: TRUE" in report
    assert "Model assessment (not accepted by the verification gate)" in report
    assert "## Accepted evidence" not in report


def test_duplicate_lineage_only_considers_cited_records():
    records = [source("https://a.example/record", "Original document confirms this event."),
               source("https://b.example/record", "A separate archive independently establishes the date.")]
    uncited_copy = deepcopy(records[0])
    uncited_copy.url = "https://mirror.example/record"
    assessment = valid_assessment("Event occurred", records)
    assert evidence_gaps(assessment, ["Event occurred"], [*records, uncited_copy], {}) == []


def test_existing_snippet_can_be_upgraded_on_later_search(config):
    config["policy"].update(full_page_retrieval=True, page_fetches_per_search=1)
    retriever = FetchingRetriever()
    result = run_claim("Documented event", max_rounds=3, model=NeedMoreBackend(), retriever=retriever, config=config)
    assert retriever.fetched == ["https://a.example/record", "https://b.example/record"]
    assert len([r for r in result.retrieval_ledger if r.page_text]) == 2


def test_cited_copies_still_fail_provenance_gate():
    records = [source("https://a.example/record", "Original document confirms this event."),
               source("https://b.example/record", "Original document confirms this event.")]
    assessment = valid_assessment("Event occurred", records)
    assert any("similar text" in gap for gap in evidence_gaps(assessment, ["Event occurred"], records, {}))


def test_conflicting_verdict_requires_both_sides():
    records = [source("https://a.example/record", "Primary record supports the event."),
               source("https://b.example/record", "Independent record disputes the date.")]
    assessment = valid_assessment("Event occurred", records)
    assessment.proposed_verdict = "CONFLICTING"
    assert any("both sides" in gap for gap in evidence_gaps(assessment, ["Event occurred"], records, {}))
    assessment.evidence = [
        assessment.evidence[0].model_copy(update={"source_urls": [records[0].url], "stance": "supports"}),
        assessment.evidence[0].model_copy(update={"source_urls": [records[1].url], "stance": "refutes"}),
    ]
    assert evidence_gaps(assessment, ["Event occurred"], records, {}) == []

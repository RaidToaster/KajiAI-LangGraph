import hashlib
import json
from types import SimpleNamespace

import pytest

from kaji_langgraph.evaluation import ABSTAIN, prediction_label, summarize
from kaji_langgraph.graph import _citation_key, run_claim
from kaji_langgraph.models import BudgetState, FinalResult
from kaji_langgraph import study
from kaji_langgraph.study_analysis import analyze, paired_accuracy, replay_labels, semantic_pass, source_host, wilson


@pytest.mark.parametrize("gold_url,cited_url,expected", [
    ("https://www.factcheck.example/article", "https://factcheck.example/other", True),
    ("https://web.archive.org/web/20201130144023id_/https://www.factcheck.example/article",
     "https://factcheck.example/article", True),
    ("https://web.archive.org/web/20201130144023/https://factcheck.example/article",
     "https://unrelated.example/article", False),
])
def test_source_host_matches_original_factcheck_behind_archive(gold_url, cited_url, expected):
    assert (source_host(gold_url) == source_host(cited_url)) is expected


def row_for(result, index=0, gold="Supported"):
    return {"claim_id": index, "gold_label": gold,
            "predicted_label": prediction_label(result.predicted_verdict),
            "accepted_label": prediction_label(result.verdict), "result": result.model_dump()}


def test_execute_allowlists_input_and_preserves_unexpected_failure(tmp_path, monkeypatch, config):
    dataset_row = {"claim": "Example", "claim_date": "01-02-2020", "label": "Refuted",
                   "justification": "GOLD SECRET", "fact_checking_article": "https://secret.example"}
    calls = []
    def fails(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("Service failed")
    monkeypatch.setattr(study, "closed_book", fails)
    row = study.execute("closed_book", 0, dataset_row, config, tmp_path, 3)
    assert set(calls[0]) == {"claim", "reference_date", "config"}
    assert calls[0]["reference_date"] == "2020-02-01"
    assert row["gold_label"] == "Refuted"
    assert row["predicted_label"] == ABSTAIN
    assert row["result"]["verification_status"] == "execution_error"


def test_failure_inclusive_score_differs_when_reviewer_fails():
    result = FinalResult(claim="Example", domain="general", budget=BudgetState(),
                         predicted_verdict="TRUE", verification_status="execution_error")
    metrics = summarize([row_for(result)])
    assert metrics["predictions"]["accuracy"] == 1
    assert metrics["failure_inclusive_predictions"]["accuracy"] == 0


def test_semantic_replay_requires_matching_source_and_finding(config, backend, two_source_retriever):
    result = run_claim("Example", model=backend, retriever=two_source_retriever, config=config).model_dump()
    trace = result["research_history"][-1]
    records = {(s["url"], s["content_hash"]): s for s in result["retrieval_ledger"]}
    sources = {key[0]: records[tuple(key)] for key in trace["usable_source_keys"]}
    reviews = []
    for item in trace["assessment"]["evidence"]:
        for url in item["source_urls"]:
            reviews.append({"round": trace["round_number"], "relation": "supports", "confidence": 0.85,
                            "key": _citation_key(item["finding"], url, item["quotes"][url], sources[url]["content_hash"])})
    result["jev_audit"]["citations"] = reviews
    assert semantic_pass(result, trace, 0.8)
    assert not semantic_pass(result, trace, 0.9)
    reviews[0]["key"] = "wrong-finding"
    assert not semantic_pass(result, trace, 0.8)


def test_analysis_handles_failure_before_first_round(tmp_path, config, backend, two_source_retriever):
    verified = run_claim("Example", model=backend, retriever=two_source_retriever, config=config)
    failed = FinalResult(claim="Failure", domain="auto", budget=BudgetState(),
                         verification_status="execution_error", stop_reason="execution_error")
    full = [row_for(verified), row_for(failed, 1, "Refuted")]
    closed = [row_for(verified), row_for(failed, 1, "Refuted")]
    data = [{"claim": "Example", "label": "Supported"}, {"claim": "Failure", "label": "Refuted"}]
    snapshot = tmp_path / "dataset-snapshot.json"
    snapshot.write_text(json.dumps(data), encoding="utf-8")
    manifest = {"claim_ids": [0, 1], "config": config, "scope": "test",
                "dataset_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest()}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for condition, rows in [("full", full), ("closed_book", closed)]:
        folder = tmp_path / condition
        folder.mkdir()
        (folder / "results.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    metrics = analyze(tmp_path)
    assert metrics["complete"] and metrics["n"] == 2
    assert metrics["metrics"]["full_policy"]["coverage"] == 0.5
    assert metrics["full_execution"]["execution_error_rate"] == 0.5
    assert not metrics["human_audit_performed"]
    assert (tmp_path / "human-citation-audit.csv").exists()
    snapshot.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="Archived dataset"):
        analyze(tmp_path)


def test_resume_skips_completed_claims_and_rejects_changed_code(tmp_path, monkeypatch, config):
    data = [{"claim": "Example", "label": "Supported"}]
    dataset = tmp_path / "data.json"
    dataset.write_text(json.dumps(data), encoding="utf-8")
    output = tmp_path / "study"
    calls = []
    def fake_execute(condition, index, row, *_):
        calls.append((condition, index))
        return row_for(FinalResult(claim=row["claim"], domain="auto", budget=BudgetState(),
                                  verification_status="execution_error", stop_reason="execution_error"))
    monkeypatch.setattr(study, "execute", fake_execute)
    monkeypatch.setattr(study, "load_config", lambda: config)
    monkeypatch.setenv("TINYFISH_API_KEY", "test")
    monkeypatch.setenv("TYPESAFE_API_KEY", "test")
    args = SimpleNamespace(dataset=dataset, output=output, limit=1, seed=1,
                           workers=1, max_rounds=3, max_seconds=30, resume=False)
    study.run(args)
    assert len(calls) == 2
    args.resume = True
    study.run(args)
    assert len(calls) == 2
    monkeypatch.setattr(study, "code_digest", lambda: "changed")
    with pytest.raises(ValueError, match="identical code"):
        study.run(args)


def test_intervals_distinguish_no_accepted_results_from_perfect_accuracy():
    assert wilson(0, 0) is None
    assert 0 < wilson(1, 1)[0] < 1
    comparison = paired_accuracy(["Supported"]*4, [ABSTAIN]*4, ["Supported"]*4)
    assert comparison["delta_b_minus_a"] == 1
    assert comparison["ci95"] == [1, 1]

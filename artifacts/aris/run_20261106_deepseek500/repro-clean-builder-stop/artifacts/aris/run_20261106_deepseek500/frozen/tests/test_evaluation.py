import argparse
import json

import pytest

from kaji_langgraph.evaluation import (
    ABSTAIN, LABELS, classification_metrics, dataset_report, model_input,
    prediction_label, read_completed, run_evaluation,
)
from kaji_langgraph.graph import run_claim
from kaji_langgraph.study_analysis import read_rows


def test_abstention_is_not_not_enough_evidence():
    assert prediction_label("UNVERIFIED") == ABSTAIN
    assert prediction_label("MISLEADING") == ABSTAIN
    assert prediction_label("NOT_ENOUGH_EVIDENCE") == "Not Enough Evidence"
    assert prediction_label("CONFLICTING") == LABELS[3]


def test_metrics_keep_failures_in_denominator_and_count_missed_classes():
    metrics = classification_metrics(list(LABELS), [LABELS[0], ABSTAIN, LABELS[2], LABELS[0]])
    assert metrics["accuracy"] == 0.5
    assert metrics["coverage"] == 0.75
    assert metrics["selective_accuracy"] == pytest.approx(2 / 3)
    assert metrics["macro_f1"] == pytest.approx((2 / 3 + 1) / 4)
    assert metrics["confusion_matrix"]["Refuted"][ABSTAIN] == 1
    assert classification_metrics([LABELS[0]], [ABSTAIN])["selective_accuracy"] is None


def test_live_input_excludes_all_gold_annotations():
    row = {"claim": "Event happened", "claim_date": "31-10-2020", "label": "Refuted",
           "questions": [{"answer": "Secret answer"}], "justification": "Secret rationale",
           "fact_checking_article": "https://example.com/secret"}
    assert model_input(row) == {"claim": "Event happened", "reference_date": "2020-10-31"}


def test_reference_date_reaches_analysis(config, backend, two_source_retriever):
    result = run_claim("A claim", reference_date="2020-10-31", config=config, model=backend, retriever=two_source_retriever)
    assert result.reference_date == "2020-10-31"
    with pytest.raises(ValueError):
        run_claim("A claim", reference_date="not-a-date", config=config, model=backend)


def test_end_to_end_evaluation_and_resume(tmp_path, monkeypatch, config, backend, two_source_retriever):
    dataset = [{"claim": "A claim", "label": "Supported", "claim_date": "31-10-2020"}]
    path = tmp_path / "dev.json"
    path.write_text(json.dumps(dataset))
    calls = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        return run_claim(**{**kwargs, "config": config}, model=backend, retriever=two_source_retriever)

    monkeypatch.setattr("kaji_langgraph.evaluation.run_claim", fake_run)
    args = argparse.Namespace(dataset=path, config=None, max_seconds=30, no_jev=True,
                              snippets_only=True, ids=None, seed=42, limit=1, max_rounds=1,
                              output=tmp_path / "run", resume=False, continue_on_error=False)
    run_evaluation(args, dataset)
    metrics = json.loads((args.output / "metrics.json").read_text())
    assert metrics["predictions"]["accuracy"] == 1
    assert metrics["complete"] is True
    assert (args.output / "report.md").exists()
    assert len(calls) == 1
    assert "label" not in calls[0]
    args.resume = True
    run_evaluation(args, dataset)
    assert len(calls) == 1
    args.max_rounds = 2
    with pytest.raises(ValueError, match="Resume requires"):
        run_evaluation(args, dataset)
    rows = (args.output / "results.jsonl").read_text()
    (args.output / "results.jsonl").write_text(rows + rows)
    with pytest.raises(ValueError, match="duplicate"):
        read_completed(args.output / "results.jsonl", dataset, [0])


def test_dataset_baseline_is_explicitly_descriptive():
    report = dataset_report([{"label": "Refuted"}] * 3 + [{"label": "Supported"}])
    assert report["majority_baseline"]["accuracy"] == 0.75
    assert "not trained model performance" in report["note"]


def test_execution_failure_has_no_factual_nei_label(config, backend):
    class BrokenRetriever:
        def search(self, *args, **kwargs):
            raise ConnectionError("Service offline")

    result = run_claim("A claim", config=config, model=backend, retriever=BrokenRetriever())
    assert result.verification_status == "execution_error"
    assert prediction_label(result.predicted_verdict) == ABSTAIN


def test_jsonl_unicode_separators_are_source_data_not_record_boundaries(tmp_path):
    row = {"claim_id": 0, "gold_label": "Supported", "predicted_label": "Supported",
           "accepted_label": ABSTAIN, "result": {"claim": "Example", "predicted_verdict": "TRUE",
           "verdict": "UNVERIFIED", "source_text": "First\u2028second\u2029third\u0085fourth"}}
    path = tmp_path / "results.jsonl"
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    assert read_rows(path) == [row]
    assert read_completed(path, [{"claim": "Example", "label": "Supported"}], [0]) == [row]

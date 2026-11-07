"""Synthetic-only tests of research retention, isolation and resumability."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from kaji_langgraph.config import load_config
from kaji_langgraph.incremental.analysis import calibration, compare, paired
from kaji_langgraph.incremental.boundary import prepare, read, save, sha
from kaji_langgraph.incremental.method import (
    Assessment, Decision, Plan, accept, assess_prompt, execute, route, update,
)
from kaji_langgraph.incremental.providers import Journal, ProviderBoundary, Providers, accounting
from kaji_langgraph.incremental.runner import complete_or_refuse, scored_rows
from kaji_langgraph.models import SourceRecord
from kaji_langgraph.study import ClosedBookAssessment, closed_book_prompt


INITIAL = {"proposed_verdict": "TRUE", "confidence": "Medium", "summary": "Provisional synthetic answer"}
INPUT = {"claim": "The fictional Luma bridge opened in 2000.", "reference_date": "2020-01-01"}


def source(url="https://records.example.test/opening"):
    return SourceRecord(url=url, page_text="The fictional Luma bridge opened in 2001.",
        retrieved_at="2026-01-01T00:00:00Z", content_hash="synthetic", query="Luma bridge opening record", provider="fixture")


def assessment(**changes):
    s = source()
    values = {"proposed_verdict": "FALSE", "confidence": "High", "summary": "Opening was a year later.",
        "evidence": [{"finding": s.page_text, "source_urls": [s.url], "quotes": {s.url: s.page_text}, "stance": "refutes"}],
        "assertions": [{"assertion": INPUT["claim"], "resolved": True, "source_urls": [s.url]}],
        "can_resolve": True, "material_evidence_reason": "The original dated record gives 2001, contradicting 2000.",
        "unresolved_issues": [], "provenance": ["Fictional original opening register"],
        "counterevidence_searched": True, "sources_independent": True}
    return Assessment.model_validate({**values, **changes})


def decision(**changes):
    s = source()
    return Decision.model_validate({"action": "change", "label": "FALSE", "reason": "The original record contradicts the year.",
        "decisive_quotes": {s.url: s.page_text}, **changes})


@pytest.mark.parametrize("rule,confidence,expected", [
    ("all", "High", True), ("low", "Low", True), ("low", "Medium", False),
    ("low_medium", "Medium", True), ("low_medium", "High", False), ("none", "Low", False)])
def test_routing_uses_only_initial_confidence(rule, confidence, expected):
    assert route({**INITIAL, "confidence": confidence}, rule) is expected
    assert not route(None, rule)


@pytest.mark.parametrize("changes", [
    {"can_resolve": False}, {"unresolved_issues": ["Date could refer to construction"]},
    {"material_evidence_reason": ""}, {"evidence": []},
    {"proposed_verdict": "NOT_ENOUGH_EVIDENCE", "substantive_nei_reason": ""}])
def test_inconclusive_or_ungrounded_research_retains_initial(changes):
    a = assessment(**changes)
    d = decision(label=a.proposed_verdict)
    assert update(INITIAL, a, d, [source()])[0] == "TRUE"


def test_decisive_contrary_evidence_changes_without_gate_acceptance():
    a = assessment()
    assert update(INITIAL, a, decision(), [source()])[0] == "FALSE"
    passed, gaps = accept(a, [source()], INPUT["claim"], {}, [{"relation": "supports", "confidence": 0.99}], True)
    assert not passed  # Only one host: acceptance and label are separate.
    assert any("two source hosts" in x for x in gaps)


def test_invalid_or_snippet_only_quote_cannot_change():
    assert update(INITIAL, assessment(), decision(decisive_quotes={source().url: "fabricated"}), [source()])[0] == "TRUE"
    snippet = source().model_copy(update={"page_text": "", "snippet": source().page_text})
    assert update(INITIAL, assessment(), decision(), [snippet])[0] == "TRUE"


class FakeJev:
    def classify(self, *args, **kwargs):
        return SimpleNamespace(domain="general"), 1

    def rank_results(self, claim, query, results, **kwargs):
        return [1] * len(results), 1

    def review_sources(self, claim, sources, **kwargs):
        return [{"injection": 0, "relevant": 1, "evidence": 1, "counterevidence": 1} for _ in sources], 1

    def check_citations(self, citations, **kwargs):
        return [{"relation": "supports", "confidence": 0.99} for _ in citations], 1


class FakeProvider:
    def __init__(self, fail=None):
        self.jev, self.fail, self.prompts = FakeJev(), fail, []

    def remaining(self, maximum):
        return maximum

    def structured(self, schema, prompt, stage):
        self.prompts.append((stage, prompt))
        if stage == self.fail:
            raise TimeoutError("synthetic provider failure")
        if stage == "initial":
            return ClosedBookAssessment(**INITIAL)
        if stage == "plan":
            return Plan(questions=["When did the fictional bridge open?"],
                        neutral_query="Luma bridge original opening register", falsifying_query="Luma bridge construction completion versus public opening")
        if stage == "assessment":
            assert "Provisional synthetic answer" not in prompt
            return assessment()
        return decision()

    def search(self, query):
        if self.fail == "search":
            raise ConnectionError("synthetic retrieval failure")
        return [{"url": source().url, "title": "Fictional opening register", "snippet": "A dated opening register"}]

    def fetch(self, url):
        return source().page_text, 200, None


def test_shared_initial_committed_before_research_and_not_mutated():
    provider, committed = FakeProvider(), []
    result = execute(INPUT, provider, load_config(), "all", lambda x: committed.append(deepcopy(x)))
    assert committed == [INITIAL]
    assert result["initial"] == INITIAL
    assert result["final_label"] == "FALSE"
    assert result["transitions"] == ["TRUE", "FALSE", "FALSE"]
    assert not result["evidence_accepted"]


@pytest.mark.parametrize("stage", ["plan", "assessment", "adjudicator", "search"])
def test_provider_failure_keeps_valid_initial(stage):
    result = execute(INPUT, FakeProvider(stage), load_config(), "all", lambda x: None)
    assert result["final_label"] == "TRUE"
    assert result["initial"] == INITIAL
    assert result["research_status"] == "operational_fallback"
    assert not result["evidence_accepted"]


def test_no_initial_is_failure_not_nei():
    result = execute(INPUT, FakeProvider("initial"), load_config(), "all", lambda x: pytest.fail("must not commit"))
    assert result["final_label"] is None
    assert result["research_status"] == "initial_failure"


def test_skip_has_explicit_unverified_status():
    result = execute(INPUT, FakeProvider(), load_config(), "low", lambda x: None)
    assert result["research_status"] == "skipped"
    assert not result["research_attempted"]
    assert not result["evidence_accepted"]


def test_gold_fields_rejected_at_inference_boundary():
    with pytest.raises(ValueError, match="only claim"):
        execute({**INPUT, "gold_label": "Refuted"}, FakeProvider(), load_config(), "all", lambda x: None)


def test_assessor_prompt_has_no_initial_or_annotation_argument():
    plan = Plan(questions=["When?"], neutral_query="original", falsifying_query="alternative")
    text = assess_prompt(INPUT["claim"], INPUT["reference_date"], plan, [source()], [])
    assert INITIAL["summary"] not in text
    assert "UNTRUSTED_EVIDENCE_JSON" in text


def test_prompt_preserves_restored_control_wording():
    assert closed_book_prompt("Synthetic claim", None) == """Assess the factual claim using your existing knowledge only.
Claim: Synthetic claim
Claim reference date: not supplied
Use TRUE for supported claims, FALSE for refuted claims, CONFLICTING for genuine
conflicting evidence/cherry-picking, and NOT_ENOUGH_EVIDENCE when you cannot
resolve the claim. Missing knowledge is not FALSE. Give your best assessment
and honest Low, Medium, or High confidence. Do not invent citations."""


def test_sampling_identity_only_and_attempt_exclusion(tmp_path):
    data = [{"claim": f"Synthetic claim {i}", "label": "never accessed"} for i in range(170)]
    dataset = tmp_path / "data.json"
    save(dataset, data)
    attempt = tmp_path / "evaluation/results/deepseek-old/attempts/000-full/attempt.json"
    save(attempt, {"claim_id": 0})
    out = tmp_path / "new"
    protocol = out / "PROTOCOL.md"
    protocol.parent.mkdir(exist_ok=True)
    protocol.write_text("Synthetic protocol")
    counts = prepare(tmp_path, dataset, out, protocol)
    split = read(out / "split.json")
    assert counts == {"eligible": 169, "final": 100, "calibration": 30, "selection": 30, "shortfall": 0}
    assert 0 not in split["eligible_ids"]
    all_ids = split["final_ids"] + split["calibration_ids"] + split["selection_ids"]
    assert len(set(all_ids)) == 160
    assert not (out / "final").exists()
    with pytest.raises(ValueError, match="immutable"):
        prepare(tmp_path, dataset, out, protocol)


def test_sampling_shortfall_does_not_substitute(tmp_path):
    dataset = tmp_path / "data.json"
    save(dataset, [{"claim": f"Synthetic {i}"} for i in range(120)])
    out = tmp_path / "new"
    out.mkdir()
    protocol = out / "PROTOCOL.md"
    protocol.write_text("Synthetic protocol")
    result = prepare(tmp_path, dataset, out, protocol)
    assert result["shortfall"] == 40
    assert result["final"] == 100
    assert result["calibration"] == result["selection"] == 0


def test_user_approved_22_selection_split_is_disjoint_and_exact(tmp_path):
    dataset = tmp_path / "data.json"
    save(dataset, [{"claim": f"Fictional amendment record {i}"} for i in range(152)])
    out = tmp_path / "new"
    out.mkdir()
    protocol = out / "PROTOCOL.md"
    protocol.write_text("Synthetic approved protocol")
    with pytest.raises(ValueError, match="explicit user-approved"):
        prepare(tmp_path, dataset, out, protocol, selection_size=22)
    amendment = out / "protocol-amendment.json"
    save(amendment, {"approved_split": {"final": 100, "calibration": 30, "selection": 22},
                     "user_approval": "Synthetic explicit approval"})
    result = prepare(tmp_path, dataset, out, protocol, selection_size=22, amendment=amendment)
    assert result == {"eligible": 152, "final": 100, "calibration": 30, "selection": 22, "shortfall": 0}
    split = read(out / "split.json")
    assert split["required"]["selection"] == 22
    assert len(set(split["final_ids"] + split["calibration_ids"] + split["selection_ids"])) == 152
    assert split["amendment_sha256"] == sha(amendment)


def test_exposure_audit_recognizes_opaque_prior_attempt(tmp_path):
    from kaji_langgraph.incremental.boundary import audit
    dataset = tmp_path / "data.json"
    save(dataset, [{"claim": f"Fictional opaque history {i}"} for i in range(160)])
    old = tmp_path / "evaluation/results/deepseek-incremental-old"
    save(old / "split.json", {})
    save(old / "calibration-mapping.json", {"opaque": 4})
    save(old / "attempts/calibration-opaque/job.json", {"opaque_id": "opaque"})
    result = audit(tmp_path, dataset)
    assert result["excluded_ids"] == [4]
    assert len(result["eligible_ids"]) == 159


def test_exposure_audit_recognizes_nested_revision_final_attempt(tmp_path):
    from kaji_langgraph.incremental.boundary import audit
    dataset = tmp_path / "data.json"
    save(dataset, [{"claim": f"Fictional nested exposure {i}"} for i in range(160)])
    nested = tmp_path / "evaluation/results/deepseek-incremental-parent/revision-1"
    save(nested / "split.json", {})
    save(nested / "final-mapping.json", {"opaque-final": 9})
    save(nested / "attempts/final-opaque-final/job.json", {"opaque_id": "opaque-final"})
    assert audit(tmp_path, dataset)["excluded_ids"] == [9]
    assert audit(tmp_path, dataset, own_run=nested)["excluded_ids"] == []


def test_uncertain_send_cannot_automatically_resume(tmp_path):
    out = tmp_path / "run"
    directory = out / "attempts/calibration-opaque"
    directory.mkdir(parents=True)
    save(out / "resource-release.json", {"caps_usd": {"ollama": 10}, "valid_until": "2099-01-01T00:00:00+00:00"})
    import time
    journal = Journal(directory, out, time.monotonic() + 300)
    journal.reserve("ollama", {"model": "deepseek-v4.1-flash:cloud"}, "http://localhost:11434/api/chat")
    assert accounting(directory)["uncertain_sends"] == ["request-001.json"]
    with pytest.raises(ValueError, match="reconcile"):
        complete_or_refuse(directory)
    replacement = Journal(directory, out, time.monotonic() + 300)
    with pytest.raises(ProviderBoundary, match="halted"):
        replacement.reserve("ollama", {"model": "deepseek-v4.1-flash:cloud"}, "http://localhost:11434/api/chat")
    assert len(list(directory.glob("request-*.json"))) == 1


def test_completed_attempt_reused_without_duplicate_send(tmp_path):
    directory = tmp_path / "attempt"
    save(directory / "result.json", {"initial": INITIAL, "final_label": "TRUE"})
    assert complete_or_refuse(directory)["final_label"] == "TRUE"
    assert not list(directory.glob("request-*"))


def test_scoring_cannot_read_labels_before_full_commit(tmp_path):
    with pytest.raises(FileNotFoundError):
        scored_rows(tmp_path, "final")


def test_scoring_rejects_mutated_predictions_before_loading_dataset(tmp_path):
    save(tmp_path / "method-freeze.json", {})
    save(tmp_path / "final-mapping.json", {"opaque": 0})
    save(tmp_path / "implementation.json", {})
    result = tmp_path / "attempts/final-opaque/result.json"
    save(result, {"final_label": "TRUE"})
    save(tmp_path / "final-commit.json", {"mapping_sha256": sha(tmp_path / "final-mapping.json"),
        "method_freeze_sha256": sha(tmp_path / "method-freeze.json"),
        "implementation_sha256": sha(tmp_path / "implementation.json"),
        "prediction_hashes": {"attempts/final-opaque/result.json": sha(result)}})
    save(result, {"final_label": "FALSE"})
    with pytest.raises(ValueError, match="predictions changed"):
        scored_rows(tmp_path, "final")


def test_calibration_and_selection_keep_failures_in_denominator():
    account = {"calls": {"ollama": 1}, "observed_tokens": {"ollama": 10}, "token_usage_complete": True}
    rows = [{"initial": INITIAL, "final_label": "FALSE", "gold_label": "Refuted", "opaque_id": "a",
             "research_status": "resolved", "decision_reason": "evidence", "accounting": account,
             "initial_accounting": account, "evidence_accepted": False},
            {"initial": None, "final_label": None, "gold_label": "Supported", "opaque_id": "b",
             "research_status": "initial_failure", "decision_reason": "failure", "accounting": account,
             "initial_accounting": account, "evidence_accepted": False}]
    assert calibration(rows)["routing_rule"] == "low_medium"
    report = compare(rows, "low_medium")
    assert report["model_only"]["accuracy"] == 0
    assert report["candidates"]["A"]["metrics"]["accuracy"] == 0.5
    assert report["candidates"]["A"]["execution_failures"] == 1
    assert report["physical_resources"]["calls"]["ollama"] == 2


def test_exact_mcnemar_and_bootstrap():
    result = paired(["Supported"] * 5, ["Refuted"] * 5, ["Supported"] * 5)
    assert result["initial_wrong_final_correct"] == 5
    assert result["exact_mcnemar_two_sided_p"] == 0.0625
    assert result["bootstrap_ci95"] == [1, 1]
    assert result == paired(["Supported"] * 5, ["Refuted"] * 5, ["Supported"] * 5)


def test_normal_cli_prepare_with_synthetic_dataset(tmp_path):
    save(tmp_path / "data.json", [{"claim": f"Fictional record {i}"} for i in range(170)])
    output = tmp_path / "experiment"
    output.mkdir()
    (output / "PROTOCOL.md").write_text("Synthetic offline CLI check")
    completed = subprocess.run([sys.executable, "-m", "kaji_langgraph.incremental", "prepare",
        "--root", str(tmp_path), "--dataset", str(tmp_path / "data.json"), "--output", str(output)],
        capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["selection"] == 30
    assert not (output / "attempts").exists()


def mock_providers(tmp_path, monkeypatch, replies):
    import httpx
    import time
    out = tmp_path / "run"
    directory = out / "attempts/opaque"
    directory.mkdir(parents=True)
    save(out / "resource-release.json", {"caps_usd": {"ollama": 10, "jev": 1, "search": 0, "fetch": 0}, "valid_until": "2099-01-01T00:00:00+00:00"})
    client_type = httpx.Client
    sent = []
    def respond(request):
        sent.append(json.loads(request.content))
        reply = replies[len(sent) - 1]
        if isinstance(reply, Exception):
            raise reply
        return httpx.Response(200, json=reply)
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client_type(transport=transport, **kwargs))
    journal = Journal(directory, out, time.monotonic() + 300)
    return Providers(journal, "http://localhost:11434"), directory, sent


def reply(content, model="deepseek-v4.1-flash", **changes):
    return {"model": model, "done": True, "message": {"role": "assistant", "content": content},
            "prompt_eval_count": 100, "eval_count": 50, **changes}


def test_physical_repair_is_counted_and_raw_responses_preserved(tmp_path, monkeypatch):
    provider, directory, sent = mock_providers(tmp_path, monkeypatch, [reply("not JSON"), reply(json.dumps(INITIAL))])
    result = provider.structured(ClosedBookAssessment, closed_book_prompt(**INPUT), "initial")
    assert result.model_dump() == INITIAL
    assert len(sent) == 2
    assert sent[0]["model"] == "deepseek-v4.1-flash:cloud"
    assert sent[0]["options"] == {"temperature": 0, "num_predict": 8192}
    assert "think" not in sent[0]
    assert accounting(directory)["calls"] == {"ollama": 2}
    assert accounting(directory)["observed_tokens"] == {"ollama": 300}
    assert not accounting(directory)["uncertain_sends"]
    assert (directory / "response-001.body").exists()
    assert (directory / "response-002.body").exists()


def test_unexpected_returned_model_halts_without_retry(tmp_path, monkeypatch):
    provider, directory, sent = mock_providers(tmp_path, monkeypatch, [reply(json.dumps(INITIAL), model="wrong-model")])
    with pytest.raises(ProviderBoundary, match="returned model"):
        provider.structured(ClosedBookAssessment, "Synthetic prompt", "initial")
    assert len(sent) == 1
    assert read(directory / "provider-stop.json")["reason"] == "unexpected returned model ID"


def test_uncertain_http_send_is_journaled_and_never_retried(tmp_path, monkeypatch):
    import httpx
    provider, directory, sent = mock_providers(tmp_path, monkeypatch, [httpx.ReadTimeout("synthetic timeout")])
    with pytest.raises(ProviderBoundary, match="uncertain"):
        provider.structured(ClosedBookAssessment, "Synthetic prompt", "initial")
    assert len(sent) == 1
    assert accounting(directory)["uncertain_sends"] == ["request-001.json"]
    with pytest.raises(ProviderBoundary):
        provider.structured(ClosedBookAssessment, "Synthetic prompt", "initial")
    assert len(sent) == 1


def test_known_missing_token_usage_is_not_fabricated(tmp_path, monkeypatch):
    provider, directory, _ = mock_providers(tmp_path, monkeypatch, [reply(json.dumps(INITIAL), prompt_eval_count=None, eval_count=None)])
    provider.structured(ClosedBookAssessment, "Synthetic prompt", "initial")
    assert not accounting(directory)["token_usage_complete"]
    assert accounting(directory)["observed_tokens"] == {}


def test_jev_sdk_transport_counts_physical_send_and_actual_model(tmp_path, monkeypatch):
    import httpx2
    import time
    from kaji_langgraph.incremental.providers import JournalJev
    out = tmp_path / "run"
    directory = out / "attempts/opaque"
    directory.mkdir(parents=True)
    save(out / "resource-release.json", {"caps_usd": {"jev": 1}, "valid_until": "2099-01-01T00:00:00+00:00"})
    sent = []
    def handler(request):
        sent.append(json.loads(request.content))
        return httpx2.Response(200, json={"model": "jev-1.13.0", "answers": {"domain": {
            "type": "choice", "choice": "general", "confidence": 0.95,
            "probabilities": {"general": 0.95, "scientific": 0, "political": 0.05, "health_medical": 0}}},
            "usage": {"input_tokens": 5, "output_tokens": 2}})
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-test-key")
    monkeypatch.setattr(httpx2, "HTTPTransport", lambda **kwargs: httpx2.MockTransport(handler))
    client = JournalJev(Journal(directory, out, time.monotonic() + 300))
    result, tokens = client.classify("Fictional bridge opening", timeout=3)
    assert result.domain == "general"
    assert tokens == 7
    assert len(sent) == 1
    assert accounting(directory)["calls"] == {"jev": 1}
    assert read(directory / "response-001.json")["returned_model"] == "jev-1.13.0"
    assert "synthetic-test-key" not in (directory / "request-001.json").read_text()


def test_worker_receives_only_allowlisted_input_and_refuses_replay(tmp_path, monkeypatch):
    from kaji_langgraph.incremental import providers, runner
    directory = tmp_path / "attempts/selection-opaque"
    directory.mkdir(parents=True)
    inputs = tmp_path / "opaque-input.json"
    save(inputs, INPUT)
    job_path = directory / "job.json"
    save(job_path, {"nonce": "fixture-nonce", "opaque_id": "opaque", "input_path": str(inputs),
        "output": str(tmp_path), "remaining_seconds": 300, "rule": "all", "config": load_config()})
    # A poison annotation exists nearby but never enters worker I/O or prompts.
    save(tmp_path / "dataset.json", {"gold_label": "POISON", "fact_check_url": "POISON"})
    captured = []
    original_read = runner.read
    def checked_read(path):
        captured.append(Path(path).name)
        assert Path(path).name not in {"dataset.json", "split.json", "selection-mapping.json"}
        return original_read(path)
    monkeypatch.setattr(runner, "read", checked_read)
    fake = FakeProvider()
    monkeypatch.setattr(providers, "Providers", lambda journal, base_url: fake)
    monkeypatch.setenv("KAJI_INCREMENTAL_NONCE", "fixture-nonce")
    runner.worker(job_path)
    result = read(directory / "result.json")
    assert result["initial"] == INITIAL
    assert result["final_label"] == "FALSE"
    assert "dataset.json" not in captured
    assert all("POISON" not in text for _, text in fake.prompts)
    n = len(fake.prompts)
    monkeypatch.setenv("KAJI_INCREMENTAL_NONCE", "fixture-nonce")
    with pytest.raises(ValueError, match="replayed"):
        runner.worker(job_path)
    assert len(fake.prompts) == n

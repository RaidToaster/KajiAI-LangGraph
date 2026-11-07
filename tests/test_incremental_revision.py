"""Synthetic verification of the single material-resolution revision."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from kaji_langgraph.config import load_config
from kaji_langgraph.incremental.boundary import assert_unexposed, read, save, sha
from kaji_langgraph.incremental.method import (
    MaterialAssessment, Plan, accept, reassess, update,
)
from kaji_langgraph.incremental.revision import combine_accounts, retrieval_prefix
from test_incremental_study import INITIAL, INPUT, FakeProvider, assessment, decision, source


def material(blocking=None):
    return MaterialAssessment.model_validate({**assessment(
        unresolved_issues=["The archive does not identify the photographer."]).model_dump(),
        "label_blocking_issues": blocking or []})


def test_residual_detail_does_not_veto_grounded_material_change():
    revised = material()
    assert update(INITIAL, revised, decision(), [source()])[0] == "FALSE"
    legacy = assessment(unresolved_issues=revised.unresolved_issues)
    assert update(INITIAL, legacy, decision(), [source()])[0] == "TRUE"


def test_genuine_label_blocking_issue_retains_initial():
    revised = material(["The opening date may refer to a different bridge with the same name."])
    assert update(INITIAL, revised, decision(), [source()])[0] == "TRUE"


def test_material_revision_still_needs_literal_retrieved_quotes():
    assert update(INITIAL, material(), decision(decisive_quotes={source().url: "invented"}), [source()])[0] == "TRUE"


def test_acceptance_gate_is_unchanged_by_material_field():
    legacy = assessment(unresolved_issues=material().unresolved_issues)
    reviews = [{"relation": "supports", "confidence": 0.99}]
    original = accept(legacy, [source()], INPUT["claim"], {}, reviews, True)
    revised = accept(material(), [source()], INPUT["claim"], {}, reviews, True)
    assert original == revised
    assert not revised[0]
    assert any("two source hosts" in gap for gap in revised[1])


class CachedProvider(FakeProvider):
    def structured(self, schema, prompt, stage):
        if stage == "assessment":
            self.prompts.append((stage, prompt))
            assert INITIAL["summary"] not in prompt
            assert schema is MaterialAssessment
            return material()
        assert stage == "adjudicator"
        return super().structured(schema, prompt, stage)

    def search(self, *args):
        pytest.fail("Fixed-evidence revision must not repeat a search")

    def fetch(self, *args):
        pytest.fail("Fixed-evidence revision must not repeat a fetch")


def packet():
    s = source().model_copy(update={"jev_scores": {"injection": 0, "relevant": 1, "evidence": 1, "counterevidence": 1}})
    plan = Plan(questions=["When did the fictional bridge open?"], neutral_query="original record", falsifying_query="alternative date")
    return {"plan": plan.model_dump(), "searches": [{"kind": "falsifying"}],
            "sources": [s.model_dump()], "retrieval_ledger": [s.model_dump()],
            "domain": "general", "fact_check_exposures": []}


def test_fixed_evidence_revision_uses_exact_initial_and_only_two_judgment_calls():
    config = load_config()
    config["incremental"] = {"material_resolution": True}
    provider = CachedProvider()
    result = reassess(INPUT, INITIAL, packet(), provider, config)
    assert result["initial"] == INITIAL
    assert result["final_label"] == "FALSE"
    assert [stage for stage, _ in provider.prompts] == ["assessment", "adjudicator"]
    assert not result["evidence_accepted"]


@pytest.mark.parametrize("extra", ["gold_label", "assessments", "adjudication", "final_label"])
def test_cached_inference_rejects_parent_answers_and_annotations(extra):
    cached = {**packet(), extra: "POISON"}
    with pytest.raises(ValueError, match="allowlist"):
        reassess(INPUT, INITIAL, cached, CachedProvider(), load_config())


def test_retrieval_policy_accounting_excludes_unused_parent_judgments(tmp_path):
    from kaji_langgraph.incremental.method import PLAN_PROMPT, ASSESS_PROMPT, ADJUDICATE_PROMPT
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    prompts = ["Assess the factual claim using your existing knowledge only.", PLAN_PROMPT, ASSESS_PROMPT, ADJUDICATE_PROMPT]
    for n, prompt in enumerate(prompts, 1):
        save(tmp_path / f"request-{n:03}.json", {"service": "ollama", "units": 1,
            "at": (start + timedelta(seconds=n*10)).isoformat(), "reserved_usd": 0.02,
            "body": {"messages": [{"content": prompt}]}})
        save(tmp_path / f"response-{n:03}.json", {"outcome": "completed", "input_tokens": 100,
            "output_tokens": 50, "estimated_usd": 0.001})
    save(tmp_path / "initial.json", {"prediction": INITIAL, "elapsed_seconds": 5})
    account, elapsed = retrieval_prefix(tmp_path)
    assert account["calls"] == {"ollama": 2}
    assert account["observed_tokens"] == {"ollama": 300}
    assert account["estimated_or_reserved_usd"]["ollama"] == 0.002
    assert elapsed == 15
    total = combine_accounts(account, {"calls": {"ollama": 2}, "token_usage_complete": True})
    assert total["calls"]["ollama"] == 4


def test_declared_development_reuse_never_waives_final_exposure(tmp_path):
    dataset = tmp_path / "dataset.json"
    save(dataset, [{"claim": f"Fictional protected identity {i}"} for i in range(160)])
    parent = tmp_path / "evaluation/results/deepseek-parent"
    save(parent / "split.json", {})
    save(parent / "calibration-mapping.json", {"old-cal": 100})
    save(parent / "attempts/calibration-old-cal/job.json", {"opaque_id": "old-cal"})
    output = parent / "revision-1"
    receipt = {"parent_run": str(parent), "parent_relative": "evaluation/results/deepseek-parent",
        "parent_commitments": {"split.json": sha(parent / "split.json")},
        "calibration_ids": list(range(100, 130)), "selection_ids": list(range(130, 160))}
    save(output / "development-reuse.json", receipt)
    save(output / "split.json", {"dataset_path": str(dataset), "dataset_sha256": sha(dataset),
        "final_ids": list(range(100)), "calibration_ids": receipt["calibration_ids"],
        "selection_ids": receipt["selection_ids"], "development_reuse_sha256": sha(output / "development-reuse.json")})
    assert_unexposed(tmp_path, output)
    save(parent / "final-mapping.json", {"old-final": 0})
    save(parent / "attempts/final-old-final/job.json", {"opaque_id": "old-final"})
    with pytest.raises(ValueError, match="1 selected identities exposed"):
        assert_unexposed(tmp_path, output)

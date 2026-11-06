"""Freeze the authorized DeepSeek schedule and bind each reused journal."""
from collections import Counter
from pathlib import Path
import random
import shutil
import sys
import zipfile

RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
PARENT = RUN.with_name("run_20261106_pilot50")
sys.path.insert(0, str(PARENT))
import pilot50 as pilot

read, save, digest = pilot.read, pilot.save, pilot.digest
MODEL = pilot.fs.MODELS["deepseek"]
INPUTS = {
    "artifacts/aris/run_20261106_pilot50/protocol.json": "24437f4f7f8fd24443ec7f01ebf1753897c3f6752464fcd87b216a37f231cb3d",
    "artifacts/aris/run_20261106_pilot50/source-package.zip": "0c5875ec70e3b96bacea3d7b52fb6738e526a675e7529d805d15e27cd574a4bc",
    "artifacts/owned-evidence-native-20261106/source.zip": "f9c7598dcd0c8f89be4e9f969c3819b17fd5609c8e0dfb09151cea57d93bf9c8",
    "artifacts/flash-workflow-20261103/final-case-manifest.json": "b3f4016c0de144b27bc02d2167093eda3da938a1f694605aa8148db3920bccf2",
    "artifacts/flash-workflow-20261103/final-cases.json": "4687c951515657657d418d6439bf7b180c5a912465f79c32fdd58a52a4cc0c60",
}
SCORER = "d9a372fb4891c6f93f22c57347b2d9bb12f1f5c8a0549174347f688db75b2e9b"


def main():
    assert not (RUN / "protocol.json").exists(), "Existing freeze"
    for rel, sha in INPUTS.items():
        assert digest(ROOT / rel) == sha, rel
    parent = pilot.verify()
    assert digest(PARENT / "frozen/evaluation/analyze_flash_study.py") == SCORER
    assert parent["caps"] == {"ollama": 8, "jev": 40, "tinyfish_search": 6, "tinyfish_fetch": 12}
    assert parent["num_predict"] == 4096 and parent["brief_assessment_tokens"] == 6144
    assert parent["candidate_reasoning_effort"]["deepseek"] is False
    assert parent["require_independent_provenance_review"] and parent["search_source_references"]
    candidate = read(PARENT / "candidate-config.json")
    assert all(candidate["model"][k] is True for k in (
        "predecision_source_path_review", "bound_source_anchors", "single_materiality_owner"))
    assert candidate["model"]["assessment_mode"] == "evidence_adjudicated"
    assert candidate["model"]["decomposition_method"] == "questions_as_guidance"
    assert read(PARENT / "baseline-config.json")["jev"] == candidate["jev"]
    case_dir = ROOT / "artifacts/flash-workflow-20261103"
    manifest, cases = (read(case_dir / name) for name in ("final-case-manifest.json", "final-cases.json"))
    ids = manifest["ids"]
    assert len(ids) == len(set(ids)) == 500 and list(cases) == ids
    selected = read(PARENT / "selection.json")["ordered_ids"]
    assert selected == random.Random(20261106).sample(ids, 50)
    inference = {case: {k: cases[case][k] for k in ("claim", "claim_date") if k in cases[case]} for case in ids}
    gold = {case: cases[case]["label"] for case in ids}
    assert {case: inference[case] for case in selected} == read(PARENT / "selected-inference.json")
    assert {case: gold[case] for case in selected} == read(PARENT / "selected-gold.json")
    assert read(PARENT / "STOP.json")["next_attempt_started"] is False
    historical = [PARENT / "attempts" / pilot.fs.task_id(t) for t in parent["schedule"]]
    assert {d.name for d in historical[:94]} == {d.name for d in (PARENT / "attempts").iterdir()}
    prior = read(PARENT / "prior-retrieval-ledger.json")
    reused = {}
    for task, directory in zip(parent["schedule"][:94], historical[:94]):
        attempt = read(directory / "attempt.json")
        job = read(directory / "job.json")
        assert all(attempt[k] == v for k, v in task.items())
        assert attempt["protocol_sha256"] == INPUTS["artifacts/aris/run_20261106_pilot50/protocol.json"]
        sends = pilot.usage(directory, parent["models"][task["model"]])
        assert Counter(r["service"] for r in sends) == +Counter(read(directory / "live-state.json")["counts"])
        prior.extend({**r, "source": directory.relative_to(ROOT).as_posix()} for r in sends
                     if r["service"].startswith("tinyfish"))
        if task["model"] != "deepseek":
            continue
        assert not job["operational_stop"] and not job["timeout"]
        for row in sends:
            assert row["usage_known"], (directory.name, row)
            if row["service"] in ("ollama", "jev"):
                assert row["model_verified"]
                assert row["requested_model"] == (MODEL if row["service"] == "ollama" else "jev-1.13.0")
            req = read(directory / f"request-{row['request_id']}.json")
            assert req["task"] == directory.name
            if row["service"] == "ollama":
                body = req["request"]["body"]
                assert body["options"]["num_predict"] <= (6144 if task["arm"] == "candidate" else 4096)
                if task["arm"] == "baseline":
                    assert body.get("think") in (None, False)
        reused[directory.name] = {
            "path": directory.relative_to(ROOT).as_posix(),
            "files": {p.name: digest(p) for p in sorted(directory.iterdir()) if p.is_file()},
        }
    schedule = [task for task in parent["schedule"] if task["model"] == "deepseek"]
    for i, case in enumerate(case for case in ids if case not in selected):
        arms = ("baseline", "candidate") if i % 2 == 0 else ("candidate", "baseline")
        schedule.extend(dict(case=case, model="deepseek", arm=arm) for arm in arms)
    assert len({pilot.fs.task_id(t) for t in schedule}) == len(schedule) == 1000
    assert Counter(t["arm"] for t in schedule if pilot.fs.task_id(t) not in reused) == {"baseline": 476, "candidate": 477}
    assert len({r["request_sha256"] for r in prior}) == len(prior)
    with zipfile.ZipFile(PARENT / "source-package.zip") as archive:
        for name in archive.namelist():
            path = Path(name)
            assert not path.is_absolute() and ".." not in path.parts
            if name.startswith("frozen/") or name in parent["configurations"].values() or name == "pilot50.py":
                archive.extract(name, RUN)
    for name in ("final-case-manifest.json", "final-cases.json"):
        shutil.copyfile(case_dir / name, RUN / name)
    save(RUN / "selected-inference.json", inference)
    save(RUN / "gold.json", gold)
    save(RUN / "selection.json", {"pilot_order": selected, "additional_order": [c for c in ids if c not in selected]})
    save(RUN / "schedule.json", schedule)
    save(RUN / "reused.json", reused)
    save(RUN / "prior-retrieval-ledger.json", prior)
    shutil.copyfile(ROOT / "DEEPSEEK_500_NEXT_SESSION_PROMPT.md", RUN / "AUTHORIZATION.md")
    # Only files that already exist at freeze time can be loaded by the launcher.
    files = {p.relative_to(RUN).as_posix(): digest(p) for p in sorted(RUN.rglob("*")) if p.is_file()}
    protocol = {**parent, "phase": "deepseek500", "created_at": pilot.now(),
                "models": {"deepseek": MODEL}, "candidate_reasoning_effort": {"deepseek": False},
                "schedule": schedule, "entry_authorization": "AUTHORIZATION.md",
                "scheduling_cost_caps_usd": {"ollama": 30, "jev": 2.5},
                "freeze_files": files, "historical_hashes": INPUTS, "reuse_attempts": True,
                "remaining450_released": True, "fresh_attempt_limit": 953}
    save(RUN / "protocol.json", protocol)
    save(RUN / "approval.json", {"protocol_sha256": digest(RUN / "protocol.json"), "user_authorized_fresh": 953})
    print("Frozen 1,000 cells, 47 journal references, 953 untouched cells")


if __name__ == '__main__':
    main()

from __future__ import annotations

import json
import sys

from kaji_langgraph.cli import main
from kaji_langgraph.config import load_config
from kaji_langgraph.graph import run_claim


def test_stream_reports_work_before_final_result(backend, two_source_retriever, config):
    events: list[str] = []
    result = run_claim(
        "The documented fixture event occurred",
        max_rounds=1,
        model=backend,
        retriever=two_source_retriever,
        config=config,
        progress=events.append,
    )

    assert result.verdict == "TRUE"
    assert any(event.startswith("Search ") for event in events)
    assert any(event.startswith("Evidence check:") for event in events)
    assert events[-1].startswith("Finished: TRUE")


def test_cli_keeps_json_on_stdout_and_progress_on_stderr(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv", ["kaji-langgraph", "Fixture claim", "--mock", "--format", "json", "--max-rounds", "1"]
    )
    main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)["claim"] == "Fixture claim"
    assert "Search " in captured.err
    assert "Finished:" in captured.err


def test_cli_can_disable_progress(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv", ["kaji-langgraph", "Fixture claim", "--mock", "--format", "json", "--no-progress"]
    )
    main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)["claim"] == "Fixture claim"
    assert captured.err == ""


def test_default_budgets_are_generous_for_every_domain():
    config = load_config()
    policy = config["policy"]
    assert policy["max_search_calls"] == 20
    assert policy["max_scrapes"] == 20
    assert policy["max_execution_time_seconds"] == 1800
    assert policy["max_token_limit"] == 250000
    assert all(
        key not in overrides
        for overrides in config["domains"].values()
        for key in ("max_search_calls", "max_scrapes", "max_execution_time_seconds")
    )

"""Command-line interface for the standalone LangGraph workflow."""

from __future__ import annotations

import argparse
from copy import deepcopy
import sys

from kaji_langgraph.config import load_config
from kaji_langgraph.graph import run_claim
from kaji_langgraph.llm import DeterministicBackend
from kaji_langgraph.report import format_report
from kaji_langgraph.retrieval import StaticRetriever


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KajiSF-DJ evidence-driven claim analysis")
    parser.add_argument("claim", help="Claim to investigate")
    parser.add_argument(
        "--domain",
        default="auto",
        choices=["auto", "general", "scientific", "political", "health_medical"],
    )
    parser.add_argument("--max-rounds", type=int, default=3, choices=range(1, 11))
    parser.add_argument("--format", choices=["report", "brief", "json"], default="report")
    parser.add_argument("--mock", action="store_true", help="Run an offline deterministic smoke workflow")
    return parser


def _mock_dependencies():
    phrase_a = "Independent archival record confirms the fixture claim for deterministic testing."
    phrase_b = "A separate official record confirms the fixture claim and its stated date."
    return DeterministicBackend(), StaticRetriever(
        [
            {"title": "Archive A", "href": "https://archive-a.example/record", "body": phrase_a},
            {"title": "Archive B", "href": "https://archive-b.example/source", "body": phrase_b},
        ]
    )


def main() -> None:
    args = build_parser().parse_args()
    model = retriever = None
    config = load_config()
    if args.mock:
        model, retriever = _mock_dependencies()
        config = deepcopy(config)
        config["policy"]["full_page_retrieval"] = False
        config["jev"]["enabled"] = False
    try:
        result = run_claim(
            args.claim,
            domain=args.domain,
            max_rounds=args.max_rounds,
            model=model,
            retriever=retriever,
            config=config,
        )
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.format == "json":
        print(result.model_dump_json(indent=2))
    elif args.format == "brief":
        print(f"Verdict: {result.verdict}")
        print(f"Confidence: {result.confidence}")
        print(result.summary)
    else:
        print(format_report(result))

    connection_markers = (
        "connectionerror",
        "connecterror",
        "connection refused",
        "failed to connect",
        "ollama unavailable",
    )
    if any(any(marker in error.lower() for marker in connection_markers) for error in result.errors):
        print(
            "\nOllama setup required: keep Ollama running at the configured "
            "KAJI_OLLAMA_BASE_URL and ensure KAJI_MODEL is available.",
            file=sys.stderr,
        )
    elif any("json schema validation failed" in error.lower() for error in result.errors):
        print(
            "\nOllama is reachable, but the model did not produce valid structured JSON "
            "after one repair attempt.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

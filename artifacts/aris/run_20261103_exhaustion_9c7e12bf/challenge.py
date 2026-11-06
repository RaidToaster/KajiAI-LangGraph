"""Paired controlled evidence challenge using the production workflow."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
import traceback

from langchain_ollama import ChatOllama

from kaji_langgraph.config import load_config
from kaji_langgraph.graph import run_claim
from kaji_langgraph.llm import OllamaBackend
from kaji_langgraph.models import EvidenceAssessment


RUN = Path(__file__).resolve().parent
DATE = "2026-11-03"
MODELS = {
    "gemma4:31b-cloud": "gemma4:31b",
    "glm-5.3-flash:cloud": "glm-5.3-flash",
    "deepseek-v4.1-flash:cloud": "deepseek-v4.1-flash",
}
URLS = ["https://ledger.example/entry", "https://witness.example/entry"]


def save(path, value):
    with path.open("x", encoding="utf-8") as file:
        json.dump(value, file, indent=2, ensure_ascii=False, default=str)


def assessment(case):
    return EvidenceAssessment(
        proposed_verdict=case["label"], confidence="Medium", summary=case["finding"],
        evidence=[dict(finding=case["finding"], source_urls=URLS,
                       quotes=dict(zip(URLS, case["quotes"])),
                       stance="supports" if case["label"] == "TRUE" else "refutes")],
        assertions=[dict(assertion=case["claim"], resolved=True, source_urls=URLS)],
        sources_independent=True, counterevidence_searched=True,
    )


class Corpus:
    provider = "frozen-controlled-corpus"

    def __init__(self, case):
        self.queries = []
        self.records = [
            dict(url=url, snippet=quote, retrieved_at=f"{DATE}T00:00:00Z")
            for url, quote in zip([*URLS, "https://unrelated.example/entry"],
                                  [*case["quotes"], "The neighbouring orchard advertises apple cider."])
        ]

    def search(self, query, *, max_results):
        self.queries.append(query)
        return [self.records[len(self.queries) - 1]]


class ControlledReview:
    def __init__(self, case):
        self.case = case
        self.citation_rounds = 0

    def review_sources(self, claim, records, *, timeout):
        return [
            dict(relevant=1.0, evidence=1.0, injection=0.0) if r.url in URLS else
            dict(relevant=0.0, evidence=0.0, counterevidence=0.0, injection=0.0)
            for r in records
        ], 0

    def check_citations(self, batch, *, timeout):
        self.citation_rounds += 1
        confidence = 0.5 if self.citation_rounds <= 2 and self.case["stratum"] == "unresolved" else 1.0
        return [dict(confidence=confidence, relation="supports") for _ in batch], 0


class ScriptedPrefix:
    def __init__(self, case, tail):
        self.case = case
        self.tail = tail
        self.calls = 0

    def decompose(self, claim):
        return [claim], 0

    def analyze(self, *args):
        self.calls += 1
        return (assessment(self.case), 0) if self.calls <= 2 else self.tail(*args)


class Transport:
    """Save the exact cloud dispatches and responses, including repairs and failures."""

    def __init__(self, directory, tag):
        self.directory = directory
        self.tag = tag
        self.rows = []
        self.failed = False

    def request(self, request):
        payload = json.loads(request.content)
        if (self.failed or len(self.rows) >= 2 or payload.get("model") != self.tag
                or request.url.path != "/api/chat" or payload.get("options", {}).get("num_predict") != 2048):
            raise RuntimeError("Unexpected inference dispatch")
        self.rows.append({"started": time.monotonic()})
        save(self.directory / f"request-{len(self.rows)}.json", payload)

    def response(self, response):
        index = len(self.rows)
        row = self.rows[-1]
        row["status"] = response.status_code
        raw = response.read()
        with (self.directory / f"response-{index}.body").open("xb") as file:
            file.write(raw)
        row["seconds"] = time.monotonic() - row.pop("started")
        if response.is_error:
            self.failed = True
            return
        terminal = json.loads(raw.splitlines()[-1])
        row.update({key: terminal.get(key) for key in
                    ("model", "done", "done_reason", "prompt_eval_count", "eval_count")})
        if row["model"] not in {self.tag, MODELS[self.tag]} or not row["done"]:
            self.failed = True
            raise RuntimeError("Response did not establish requested model identity and completion")

    def backend(self):
        adapter = OllamaBackend(model=self.tag, base_url="http://127.0.0.1:11434", verdict_mode="averitec")
        adapter._model = ChatOllama(
            model=self.tag, base_url=adapter.base_url, temperature=0, num_predict=2048,
            client_kwargs=dict(trust_env=False, timeout=40.0,
                               event_hooks={"request": [self.request], "response": [self.response]}),
        )
        return adapter


def execute(case, enabled, tail):
    cfg = load_config()
    cfg["policy"].update(full_page_retrieval=False, stop_on_query_exhaustion=enabled,
                         retry_on_failure=False, max_execution_time_seconds=100)
    # One citation batch per assessment even if the live output contains extra findings.
    cfg["jev"]["citation_batch_size"] = 10000
    corpus = Corpus(case)
    model = ScriptedPrefix(case, tail)
    result = run_claim(case["claim"], domain="general", max_rounds=3, model=model,
                       retriever=corpus, jev=ControlledReview(case), config=cfg, reference_date=DATE)
    return result, model.calls, corpus.queries


def substantive(result):
    return result.model_dump(include={"verdict", "predicted_verdict", "prediction_summary",
                                      "prediction_confidence", "evidence", "gaps", "stop_reason"})


def evaluate(case, baseline, candidate, baseline_calls, candidate_calls, baseline_queries, candidate_queries):
    before = baseline.research_history[1]
    eligible = case["stratum"] == "completed"
    literal_pairs = lambda r: {(url, quote) for e in r.evidence for url, quote in e.quotes.items()}
    expected_pairs = set(zip(URLS, case["quotes"]))
    trace = (
        len(baseline_queries) == 3 and baseline_queries == candidate_queries
        and len(baseline.research_history) == baseline_calls == 3
        and baseline.research_history[-1].queries == []
        and baseline.research_history[-1].new_sources == 0
        and bool(before.semantic_gaps) == (not eligible)
        and bool(before.structural_gaps)
        and not any(not source.jev_scores for source in baseline.retrieval_ledger)
        and len(candidate.research_history) == candidate_calls == (2 if eligible else 3)
        and candidate.research_history[1].assessment == before.assessment
        and candidate.research_history[1].decision == ("query_exhausted" if eligible else "research_more")
        and all(r.research_history[-1].decision == r.stop_reason for r in (baseline, candidate))
        and (candidate.research_history[-1].assessment == before.assessment
             and candidate.predicted_verdict == before.proposed_verdict
             and candidate.prediction_summary == before.assessment.summary
             and candidate.prediction_confidence == before.confidence
             and literal_pairs(candidate) == expected_pairs
             and {s.url for s in candidate.sources} == set(URLS) if eligible
             else substantive(baseline) == substantive(candidate))
    )
    return {
        "case": case["id"], "stratum": case["stratum"], "gold": case["label"], "trace_pass": trace,
        "baseline_prediction": baseline.predicted_verdict, "candidate_prediction": candidate.predicted_verdict,
        "baseline_accepted": baseline.verdict, "candidate_accepted": candidate.verdict,
        "baseline_stop": baseline.stop_reason, "candidate_stop": candidate.stop_reason,
        "baseline_assessments": baseline_calls, "candidate_assessments": candidate_calls,
        "baseline_seconds": baseline.elapsed_seconds, "candidate_seconds_replay": candidate.elapsed_seconds,
        "baseline_literal_quotes": len(literal_pairs(baseline)),
        "candidate_literal_quotes": len(literal_pairs(candidate)),
        "baseline_exact_source_quote_coverage": len(literal_pairs(baseline) & expected_pairs),
        "candidate_exact_source_quote_coverage": len(literal_pairs(candidate) & expected_pairs),
        "potential_correct_acceptance_loss": baseline.verdict == case["label"] != candidate.verdict,
        "incorrect_baseline_acceptance": baseline.verdict not in {"UNVERIFIED", case["label"]},
        "incorrect_candidate_acceptance": candidate.verdict not in {"UNVERIFIED", case["label"]},
        "errors": [*baseline.errors, *candidate.errors],
    }


def pair(case, tag, directory):
    transport = Transport(directory, tag) if tag else None
    cached = {}

    def obtain(*args):
        cached["inputs"] = deepcopy(args)
        if transport:
            cached["tail"] = transport.backend().analyze(*args)
        else:
            value = assessment(case)
            if case["offline"] in {"rescue", "harm"}:
                value.confidence = "High"
            if case["offline"] == "harm":
                value.proposed_verdict = "FALSE" if case["label"] == "TRUE" else "TRUE"
            cached["tail"] = value, 0
        return deepcopy(cached["tail"])

    def replay(*args):
        if args != cached.get("inputs"):
            raise AssertionError("Continuation inputs differ")
        return deepcopy(cached["tail"])

    try:
        baseline, baseline_calls, baseline_queries = execute(case, False, obtain)
        save(directory / "baseline.json", baseline.model_dump(mode="json"))
        candidate, candidate_calls, candidate_queries = execute(case, True, replay)
        save(directory / "candidate.json", candidate.model_dump(mode="json"))
        row = evaluate(case, baseline, candidate, baseline_calls, candidate_calls, baseline_queries, candidate_queries)
        if transport:
            tokens = [item["prompt_eval_count"] + item["eval_count"] for item in transport.rows
                      if isinstance(item.get("prompt_eval_count"), int) and isinstance(item.get("eval_count"), int)]
            row.update(model=tag, actual_requests=len(transport.rows), observed_tokens=sum(tokens),
                       requests_with_token_counts=len(tokens),
                       baseline_policy_sends=len(transport.rows),
                       candidate_policy_sends=len(transport.rows) if candidate_calls == 3 else 0)
        return row
    finally:
        if transport:
            save(directory / "usage.json", transport.rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["offline", "batch1", "batch2"])
    parser.add_argument("--models", nargs="+", choices=MODELS)
    opts = parser.parse_args()
    cases = json.loads((RUN / "cases.json").read_text(encoding="utf-8"))
    models = [None] if opts.mode == "offline" else opts.models
    if not models:
        parser.error("Live mode requires quota-verified model tags")
    work = RUN / opts.mode
    work.mkdir()
    cells = [(case, model) for case in cases if opts.mode == "offline" or case["batch"] == int(opts.mode[-1])
             for model in models]
    save(work / "schedule.json", [{"case": case["id"], "model": model} for case, model in cells])
    rows = []
    for case, model in cells:
        cell = work / f"{case['id']}-{model.replace(':', '_') if model else 'scripted'}"
        cell.mkdir()
        try:
            row = pair(case, model, cell)
        except Exception:
            row = {"case": case["id"], "model": model, "errors": [traceback.format_exc()], "trace_pass": False}
        rows.append(row)
        save(cell / "metrics.json", row)
        print(json.dumps(row), flush=True)
        if row["errors"] or not row["trace_pass"]:
            break
    save(work / "summary.json", rows)
    return 0 if len(rows) == len(cells) and all(r["trace_pass"] and not r["errors"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())

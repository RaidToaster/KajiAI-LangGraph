"""Exercise the live harness's transport and pairing locally, without an Ollama send."""

import json
from pathlib import Path
from unittest.mock import patch

import httpx

import challenge


def main():
    cases = json.loads((challenge.RUN / "cases.json").read_text(encoding="utf-8"))
    folder = challenge.RUN / "wire-fixture"
    folder.mkdir()
    for case, tag in zip(cases, challenge.MODELS):
        dispatches = []

        def mock_response(request):
            payload = json.loads(request.content)
            dispatches.append(payload)
            value = challenge.assessment(case).model_copy(update={"confidence": "High"})
            reply = {"model": challenge.MODELS[tag], "created_at": "2026-11-03T00:00:00Z",
                     "message": {"role": "assistant", "content": value.model_dump_json()},
                     "done": True, "done_reason": "stop", "prompt_eval_count": 100, "eval_count": 20}
            return httpx.Response(200, content=json.dumps(reply).encode() + b"\n")

        def local_chat(**kwargs):
            kwargs["client_kwargs"]["transport"] = httpx.MockTransport(mock_response)
            return real_chat(**kwargs)

        directory = folder / case["id"]
        directory.mkdir()
        real_chat = challenge.ChatOllama
        with patch.object(challenge, "ChatOllama", local_chat):
            row = challenge.pair(case, tag, directory)
        assert len(dispatches) == row["actual_requests"] == 1
        assert row["observed_tokens"] == 120 and row["trace_pass"] and not row["errors"]
        assert row["candidate_policy_sends"] == (case["stratum"] == "unresolved")
        challenge.save(directory / "fixture-metrics.json", row)
    print("Three offline wire fixtures passed, including coupled continuation and raw usage.")


if __name__ == "__main__":
    main()

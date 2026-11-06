import importlib.util
import json
from pathlib import Path
import time

import pytest

spec=importlib.util.spec_from_file_location("runtime_pilot",Path(__file__).resolve().parents[1]/"evaluation/runtime_pilot.py")
pilot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def test_ledger_reserves_failed_attempts_and_enforces_caps(tmp_path):
    protocol={"caps":{"ollama":2},"num_predict":4}
    pilot.write(tmp_path/"live-state.json",{"counts":{"ollama":0},"deadline":time.time()+10,"stop":None})
    ledger=pilot.Ledger(tmp_path,protocol)
    assert ledger.before("ollama",{"prompt":"A retrieved quotation ends here\u201d"}) == 1
    assert ledger.before("ollama",{"prompt":"repair"}) == 2
    with pytest.raises(pilot.LimitReached):ledger.before("ollama",{})
    assert json.loads((tmp_path/"live-state.json").read_text())["counts"]["ollama"] == 2
    assert len(list(tmp_path.glob("request-*.json"))) == 2


@pytest.mark.parametrize("status,body",[(429,b'{}'),(200,b'{"eval_count":5}')])
def test_quota_and_observed_output_overrun_stop_further_calls(tmp_path,status,body):
    protocol={"caps":{"ollama":2},"num_predict":4}
    pilot.write(tmp_path/"live-state.json",{"counts":{"ollama":0},"deadline":time.time()+10,"stop":None})
    ledger=pilot.Ledger(tmp_path,protocol)
    number=ledger.before("ollama",{})
    ledger.response(number,status,body)
    with pytest.raises(pilot.LimitReached):ledger.before("ollama",{})
    assert (tmp_path/"response-001.body").read_bytes() == body


@pytest.mark.parametrize("module_name",["httpx","httpx2"])
def test_transport_counts_sends_and_preserves_response_stream(tmp_path,monkeypatch,module_name):
    import importlib
    module=importlib.import_module(module_name)
    monkeypatch.setattr(module,"HTTPTransport",lambda **kwargs: module.MockTransport(
        lambda request: module.Response(200,json={"eval_count":2})))
    protocol={"caps":{"ollama":2},"num_predict":4}
    pilot.write(tmp_path/"live-state.json",{"counts":{"ollama":0},"deadline":time.time()+10,"stop":None})
    ledger=pilot.Ledger(tmp_path,protocol)
    with module.Client(transport=pilot.transport(module,ledger,"ollama")) as client:
        assert client.post("http://fixture.test/api/chat",json={"model":"fixture"}).json() == {"eval_count":2}
    assert json.loads((tmp_path/"live-state.json").read_text())["counts"]["ollama"] == 1
    assert json.loads((tmp_path/"response-001.body").read_bytes()) == {"eval_count":2}


def test_partial_body_record_keeps_transport_error(tmp_path):
    protocol={"caps":{"ollama":2},"num_predict":4}
    pilot.write(tmp_path/"live-state.json",{"counts":{"ollama":0},"deadline":time.time()+10,"stop":None})
    ledger=pilot.Ledger(tmp_path,protocol)
    number=ledger.before("ollama",{})
    ledger.failed(number,TimeoutError("partial stream"))
    ledger.response(number,200,b'partial')
    meta=json.loads((tmp_path/"response-001.json").read_text())
    assert meta["status"] == 200
    assert meta["error"] == "TimeoutError: partial stream"

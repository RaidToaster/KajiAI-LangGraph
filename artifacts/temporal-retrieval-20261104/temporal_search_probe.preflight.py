"""Four matched-ceiling searches for historically scoped survey evidence."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import os
from pathlib import Path
import subprocess
import sys
import time

from flash_study import read,save,digest,THREADS,recorded_retrieval_sends,retrieval_pause_until
from runtime_pilot import Ledger,load_keys,transport


def prepare(root):
    root.mkdir(exist_ok=False)
    source=Path("artifacts/flash-workflow-20261103/development-cases.json")
    case=read(source)["train-1219"]
    queries=[("baseline-1",case["claim"]+" evidence"),("temporal-1","hunters background checks all gun buyers survey poll exact question wording 2019 2020 before February 26 2020"),
             ("temporal-2","2016 Trump voters background checks private gun sales gun shows 2019 poll exact question before February 26 2020"),
             ("baseline-2",case["claim"]+" counterevidence")]
    save(root/"protocol.json",{"case_id":"train-1219","claim":case["claim"],"case_metadata":{k:v for k,v in case.items() if k not in {"claim","label"}},
        "source_sha256":digest(source),"runner_sha256":digest(Path(__file__)),
        "hypothesis":"Queries that retain the claim's distinct populations and historical reference period may find better-scoped evidence than long present-tense claim queries. No generated plan or retrieval gain is assumed.",
        "schedule":[{"id":id,"query":q} for id,q in queries],
        "caps":{"tinyfish_search":1},"total_search_cap":4,"results_per_query":5,
        "retrieval_budget":"Two queries/arm, at most two Fetch slots/query later, identical ceilings. Fetch is not launched by this stage. Reuse identical returned URLs if a later frozen Fetch diagnostic follows; report actual versus logical slots.",
        "prior_evidence":"Earlier first-query probe used claim/decomposed statements plus original-survey language, without historical reference-year constraints. Retained Marist lead is2019; hunter lead is2013 with exceptions. No current/historical sufficiency follows from those snippets.",
        "controls":["Sufficient: source documents both populations, pre-reference field dates, actual support proportions and applicable purchase/exception wording.",
            "Insufficient: a current or undated source, different population (all gun owners versus hunters), or only an attributed politician's statement.",
            "Conflicting: poll questions/conditions or dates disagree; retain both rather than selecting favorable figures.",
            "Shared lineage: several articles citing one poll remain one evidentiary origin."],
        "screen":"Compare raw returned leads under the same top5 and2-query ceilings. A promising lead needs explicit population/date/question wording, not label agreement or a fact-check headline. Inspect before any later Fetch. No correct-acceptance/discovery-of-verified-evidence claim, no workflow release, no model calls.",
        "operations":"One worker,two numerical threads,300s/job;15s request timeout;zero retries;preserve every started reservation. Existing free/included Search quota only; stop on authentication/quota/transport problems."})
    save(root/"receipt.json",{"protocol_sha256":digest(root/"protocol.json"),"scope":"Four free/included Search sends only;zero Flash,Jev or Fetch calls. A separate bounded Fetch receipt is required after inspecting leads. Continuing user low-risk authorization;68 workflow attempts remain unreleased."})


def worker(root,p,task):
    import httpx
    load_keys();d=root/task["id"]
    class QueryLedger(Ledger):
        def before(self,service,request):return super().before(service,{**request,"query":task["query"]})
    ledger=QueryLedger(d,p);ledger.task=task["id"]
    with httpx.Client(transport=transport(httpx,ledger,"tinyfish_search"),timeout=15,trust_env=False,follow_redirects=False) as client:
        response=client.get("https://api.search.tinyfish.ai",params={"query":task["query"]},headers={"X-API-Key":os.environ["TINYFISH_API_KEY"]})
        response.raise_for_status();value=response.json()
    assert isinstance(value.get("results"),list)
    save(d/"result.json",{"query":task["query"],"results":value["results"][:5],"errors":value.get("errors",[]),"verified_evidence":False})


def main():
    parser=argparse.ArgumentParser();parser.add_argument("directory",type=Path);parser.add_argument("--prepare",action="store_true");parser.add_argument("--worker");parser.add_argument("--limit",type=int,default=1)
    args=parser.parse_args();root=args.directory
    if args.prepare:prepare(root);return
    p=read(root/"protocol.json")
    assert p["runner_sha256"]==digest(Path(__file__))
    assert read(root/"receipt.json")["protocol_sha256"]==digest(root/"protocol.json")
    if args.worker:worker(root,p,next(t for t in p["schedule"] if t["id"]==args.worker));return
    assert args.limit in {1,2}
    if (root/"decision.json").exists():raise SystemExit("Phase already closed")
    history=recorded_retrieval_sends(Path("artifacts/flash-workflow-20261103"))+recorded_retrieval_sends(root)
    if retrieval_pause_until(history,{"tinyfish_search":[[60,27],[3600,450]]},time.time())>time.time():raise SystemExit("Shared Search window lacks headroom")
    count=0
    for task in p["schedule"]:
        d=root/task["id"]
        if d.exists():
            assert (d/"job.json").exists() and not read(d/"job.json")["hard_stop"],"Unresolved retained failure;do not retry"
            continue
        if count>=args.limit:break
        d.mkdir();save(d/"attempt.json",{"id":task["id"],"query":task["query"],"started_at":datetime.now(timezone.utc).isoformat(),"protocol_sha256":digest(root/"protocol.json")})
        save(d/"live-state.json",{"counts":{"tinyfish_search":0},"deadline":time.time()+270,"stop":None})
        start=time.monotonic()
        with (d/"stdout.log").open("wb") as stdout,(d/"stderr.log").open("wb") as stderr:
            try:
                proc=subprocess.run([sys.executable,__file__,str(root),"--worker",task["id"]],timeout=300,stdout=stdout,stderr=stderr,env={**os.environ,**THREADS,"PYTHONUTF8":"1"});code=proc.returncode
            except subprocess.TimeoutExpired:code=None
        state=read(d/"live-state.json");hard=bool(code!=0 or state["stop"] or state["counts"]["tinyfish_search"]!=1)
        save(d/"job.json",{"exit_code":code,"elapsed_seconds":time.monotonic()-start,"hard_stop":hard})
        print(task["id"],"STOP" if hard else "DONE",flush=True);count+=1
        if hard:raise SystemExit("Inspect retained failure;no retries")


if __name__=="__main__":main()

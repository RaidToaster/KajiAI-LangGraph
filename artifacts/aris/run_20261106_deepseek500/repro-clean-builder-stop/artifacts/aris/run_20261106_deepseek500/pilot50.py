"""Frozen accounting/execution layer; archived workflow and acceptance remain intact."""
from pathlib import Path
import argparse, gzip, hashlib, importlib.metadata, json, os, subprocess, sys, time
from copy import deepcopy
from collections import Counter
from datetime import datetime, timezone

RUN=Path(__file__).resolve().parent
FROZEN=RUN/'frozen'
sys.path[:0]=[str(FROZEN/'src'),str(FROZEN/'evaluation')]
import flash_study as fs
from runtime_pilot import LimitReached
from kaji_langgraph.evaluation import code_digest
from kaji_langgraph import graph, llm, jev
read,save,digest=fs.read,fs.save,fs.digest
def now(): return datetime.now(timezone.utc).isoformat()

def verify():
    p=read(RUN/'protocol.json')
    assert read(RUN/'approval.json')['protocol_sha256']==digest(RUN/'protocol.json')
    assert len(p['schedule'])==200 and len({fs.task_id(t) for t in p['schedule']})==200
    assert p['models']==fs.MODELS and p['caps']==fs.CAPS
    assert code_digest()==p['candidate_source_sha256']
    for module in (graph,llm,jev): assert Path(module.__file__).resolve().is_relative_to(FROZEN/'src')
    for name,sha in p['freeze_files'].items(): assert digest(RUN/name)==sha, f'Changed freeze: {name}'
    return p

def parse_response(directory, number):
    meta=read(directory/f'response-{number:03}.json')
    data=(directory/f'response-{number:03}.body').read_bytes()
    if data.startswith(b'\x1f\x8b'): data=gzip.decompress(data)
    service=read(directory/f'request-{number:03}.json')['service']
    value=json.loads(data.splitlines()[-1] if service=='ollama' else data)
    return meta,value

def usage(directory,model):
    # Archived fs.scan indexes status directly; retain error-only/partial metadata safely here.
    rows=[]
    for path in sorted(directory.glob('request-*.json')):
        req=read(path);suffix=path.stem.split('-')[1]
        mp=directory/f'response-{suffix}.json';bp=directory/f'response-{suffix}.body'
        meta=read(mp) if mp.exists() else {}
        row=dict(service=req['service'],request_id=suffix,sent_at=req['timestamp'],status=meta.get('status'),transport_error=meta.get('error'))
        if not mp.exists() or not bp.exists() or meta.get('status') is None:row['incomplete']=True
        elif meta.get('status')==200 and req['service'] in ('ollama','jev'):
            try:
                _,value=parse_response(directory,int(suffix))
                if req['service']=='ollama':
                    row.update(returned_model=value['model'],done=value['done'],done_reason=value.get('done_reason'),
                        input_tokens=value['prompt_eval_count'],output_tokens=value['eval_count'],
                        model_verified=value['model'] in (model,model.removesuffix(':cloud')),incomplete=not value['done'])
                else:row.update(returned_model=value['model'],model_verified=value['model']=='jev-1.13.0',**value['usage'])
            except (ValueError,OSError,KeyError,IndexError) as exc:row['accounting_error']=str(exc)
        rows.append(row)
    for row in rows:
        n=int(row['request_id']);request=read(directory/f'request-{n:03}.json')
        row['requested_model']=(request['request'].get('body') or {}).get('model')
        meta_path=directory/f'response-{n:03}.json'
        meta=read(meta_path) if meta_path.exists() else {}
        row.update(elapsed_seconds=meta.get('elapsed_seconds'),finished_at=meta.get('finished_at'),
                   reservation_usd=request.get('reservation_usd'),input_upper_bound=request.get('input_upper_bound'),
                   request_sha256=digest(directory/f'request-{n:03}.json'))
        if row['service']=='tinyfish_fetch':
            row['url_attempts']=len((request['request'].get('body') or {}).get('urls',[None]))
        if row.get('status')==200 and row['service'] in ('ollama','jev') and not row.get('accounting_error') and not row.get('incomplete') and not row.get('transport_error'):
            try:
                _,value=parse_response(directory,n)
                row['provider_usage']=value.get('usage')
                row['provider_timing']={k:value[k] for k in ('total_duration','load_duration','prompt_eval_duration','eval_duration') if k in value}
                row['provider_cache_reasoning']={k:v for k,v in value.items() if 'cache' in k or 'reasoning' in k}
                row['cache_tokens']=None;row['reasoning_tokens']=None
                if row['service']=='ollama':
                    rates=read(RUN/'protocol.json')['rates_per_million'][next(k for k,v in fs.MODELS.items() if v==model)]
                else: rates=[.042,0]
                row['estimated_usd']=(row['input_tokens']*rates[0]+row['output_tokens']*rates[1])/1e6
                row['usage_known']=True
            except (OSError,ValueError,KeyError): row['usage_known']=False
        elif row['service'].startswith('tinyfish'):
            row.update(estimated_usd=0,usage_known=bool(row.get('status') is not None and not row.get('incomplete') and not row.get('transport_error')))
        else: row['usage_known']=False
    return rows

class PilotLedger(fs.FlashLedger):
    def before(self,service,request):
        body=request.get('body') or {}
        if service=='ollama' and body.get('model')!=self.model: raise LimitReached('Requested model mismatch')
        if service=='jev' and body.get('model')!='jev-1.13.0': raise LimitReached('Requested Jev mismatch')
        p=read(RUN/'protocol.json')
        # Stop any further dispatch after an unresolved model response, including SDK-caught errors.
        prior=usage(self.directory,self.model)
        if any(not r.get('usage_known') or (r['service'] in ('ollama','jev') and r.get('model_verified') is not True) for r in prior):
            raise LimitReached('Unresolved service send; no further dispatch')
        financial=read(self.directory/'budget-at-entry.json')
        reserve=0;upper=None
        if service in ('ollama','jev'):
            upper=p['provider_reservation_token_bounds'][service+'_input']
            if service=='ollama':
                tag=next(k for k,v in fs.MODELS.items() if v==self.model)
                rates=p['rates_per_million'][tag]
                requested=body.get('options',{}).get('num_predict',self.protocol['num_predict'])
                if not isinstance(requested,int) or requested<1 or requested>self.protocol['num_predict']: raise LimitReached('Unexpected output setting')
                out=p['provider_reservation_token_bounds']['ollama_output']
            else: rates=[.042,0];out=0
            reserve=(upper*rates[0]+out*rates[1])/1e6
            spent=financial[service]+sum(r.get('estimated_usd',r.get('reservation_usd') or 0) for r in prior if r['service']==service)
            if spent+reserve>p['scheduling_cost_caps_usd'][service]:
                state=read(self.directory/'live-state.json');state['stop']='spend reservation ceiling';save(self.directory/'live-state.json',state)
                raise LimitReached('Spend reservation ceiling before send')
        number=super().before(service,request)
        path=self.directory/f'request-{number:03}.json';r=read(path)
        r.update(reservation_usd=reserve,input_upper_bound=upper,monotonic_started=time.monotonic())
        save(path,r)
        return number
    def response(self,number,status,body):
        super().response(number,status,body)
        path=self.directory/f'response-{number:03}.json';meta=read(path)
        req=read(self.directory/f'request-{number:03}.json')
        meta.update(finished_at=now(),elapsed_seconds=time.monotonic()-req['monotonic_started'])
        save(path,meta)
        if req['service']=='jev' and status==200:
            _,value=parse_response(self.directory,number)
            if value.get('model')!='jev-1.13.0':
                self.failed(number,LimitReached('Returned Jev model mismatch'));raise LimitReached('Returned Jev model mismatch')

def worker(identity):
    p=verify();task=next(t for t in p['schedule'] if fs.task_id(t)==identity)
    d=RUN/'attempts'/identity
    assert (d/'attempt.json').exists() and not list(d.glob('request-*.json'))
    cp=deepcopy(p);cp['config']=read(RUN/p['configurations'][task['arm']])
    if task['arm']=='candidate': cp['num_predict']=6144
    else:
        cp.update(compiled_ledger_candidate=False,require_independent_provenance_review=False,search_source_references=False)
    fs.FlashLedger=PilotLedger
    case=read(RUN/'selected-inference.json')[task['case']]
    original_claim=graph.run_claim
    def timed_claim(**kwargs):
        start=time.monotonic();save(d/'worker-timing.json',dict(workflow_started_at=now(),workflow_started_epoch=time.time()))
        try:return original_claim(**kwargs)
        finally:
            timing=read(d/'worker-timing.json');timing.update(workflow_finished_at=now(),workflow_seconds=time.monotonic()-start)
            save(d/'worker-timing.json',timing)
    graph.run_claim=timed_claim
    # Historical run_cell requires a label only for saving, after inference; never load gold here.
    fs.run_cell(d,cp,task,{**case,'label':''})

def retrieval_sends():
    rows=read(RUN/'prior-retrieval-ledger.json')
    for d in (RUN/'attempts').glob('*'):
        if d.is_dir(): rows.extend(r for r in usage(d,fs.MODELS[read(d/'attempt.json')['model']]) if r['service'].startswith('tinyfish'))
    return rows

def quota_until(rows,p):
    stamp=time.time();until=stamp
    for service,windows in p['quota_windows'].items():
        times=[]
        for r in rows:
            if r['service']==service:
                times.extend([datetime.fromisoformat(r['sent_at']).timestamp()]*r.get('url_attempts',1))
        for seconds,maximum in windows:
            recent=sorted(t for t in times if t>stamp-seconds)
            excess=len(recent)+p['caps'][service]-maximum
            if excess>0: until=max(until,recent[excess-1]+seconds+.1)
    return until

def reconcile():
    rows=[];costs={'ollama':0.,'jev':0.};problems=[]
    for d in sorted((RUN/'attempts').glob('*')):
        if not d.is_dir(): continue
        task=read(d/'attempt.json');u=usage(d,fs.MODELS[task['model']]);save(d/'usage.json',u)
        for r in u:
            rows.append(dict(attempt=d.name,**task,**r))
            if r['service'] in costs: costs[r['service']]+=r.get('estimated_usd',r.get('reservation_usd') or 0)
            if not r.get('usage_known') or (r['service'] in costs and r.get('model_verified') is not True): problems.append(d.name+': unresolved service outcome/usage/identity')
        if not (d/'job.json').exists(): problems.append(d.name+': started without terminal job')
    save(RUN/'service-ledger.json',dict(updated_at=now(),rows=rows,cost_estimates_usd=costs,problems=problems))
    return rows,costs,problems

def preflight():
    p=verify()
    from importlib.metadata import distributions
    save(RUN/'environment.json',dict(python=sys.version,executable=sys.executable,
        packages={d.metadata['Name']:d.version for d in distributions()},
        imports={m.__name__:m.__file__ for m in (graph,llm,jev,fs)},threads=fs.THREADS,
        warm_reuse=True,dependencies_changed=False,source_digest=code_digest()))
    # A conservative accounting check, not a fresh account-balance claim.
    historical=read(Path('artifacts/question-ledger-20261104/prior-development-usage.json'))['totals']
    recent=read(Path('artifacts/owned-evidence-native-20261106/continuation-accounting.json'))['totals']
    model_upper=((historical['ollama_input_tokens']+recent['ollama_input_tokens'])*.30+
                 (historical['ollama_output_tokens']+recent['ollama_output_tokens'])*1.20)/1e6
    jev_upper=(historical['jev_input_tokens']+recent['jev_input_tokens'])*.042/1e6
    rows=retrieval_sends();stamp=time.time()
    recent_quota={s:sum(r.get('url_attempts',1) for r in rows if r['service']==s and datetime.fromisoformat(r['sent_at']).timestamp()>stamp-window) for s,window in [('tinyfish_search',3600),('tinyfish_fetch',86400)]}
    account=read(RUN/'account-confirmation.json') if (RUN/'account-confirmation.json').exists() else {}
    account_ok=(account.get('existing_ollama_credits_at_least_usd',0)>=10 and account.get('existing_jev_credits_at_least_usd',0)>=1
                and account.get('tinyfish_free_hobby') is True and account.get('no_other_experiment_or_quota_worker') is True)
    save(RUN/'PREFLIGHT.json',dict(timestamp=now(),authorized_attempts=200,
        maximum_sends={s:n*200 for s,n in p['caps'].items()},maximum_processing_hours=200*300/3600,
        retrieval_free_only=True,quota_usage=recent_quota,quota_resume_at=datetime.fromtimestamp(quota_until(rows,p),timezone.utc).isoformat(),
        historical_reported_balances={'ollama':60,'jev':4.77},fresh_account_balances_verified=False,
        conservative_all_recorded_model_cost_usd=model_upper,conservative_all_recorded_jev_cost_usd=jev_upper,
        extra_unknown_history_reservation_usd=1,model_headroom_after_all_recorded_and_extra_reserve=60-model_upper-1,
        jev_headroom_after_all_recorded=4.77-jev_upper,
        warning='Reported balances are approximate and dated; external account activity unknown. No fresh balance claim. Stop on account/quota errors; no purchases.',
        scheduling_caps_usd=p['scheduling_cost_caps_usd'],rates_sources=p['rates_sources'],
        preflight_compute='local CPU orchestration only; exact models served in Ollama cloud; no GPU allocation',
        account_confirmation_present=bool(account),first_attempt_can_launch=account_ok))
    print(json.dumps(read(RUN/'PREFLIGHT.json'),indent=2))

def launch():
    p=verify();assert read(RUN/'PREFLIGHT.json')['first_attempt_can_launch'] is True, 'Current account headroom/tier confirmation required'
    stage=RUN/'attempts';stage.mkdir(exist_ok=True)
    lock=RUN/'running.lock'
    with lock.open('x') as h: h.write(str(os.getpid()))
    try:
        rows,costs,problems=reconcile()
        if problems: raise RuntimeError(problems)
        for task in p['schedule']:
            identity=fs.task_id(task);d=stage/identity
            if d.exists(): continue
            if (RUN/'STOP.json').exists(): break
            until=quota_until(retrieval_sends(),p)
            waitstart=time.time()
            if until>waitstart:
                save(RUN/'status.json',dict(status='quota_wait',next_attempt=identity,resume_at=datetime.fromtimestamp(until,timezone.utc).isoformat(),updated_at=now()))
                print('QUOTA_WAIT',identity,datetime.fromtimestamp(until,timezone.utc).isoformat(),flush=True)
                while time.time()<until:
                    if (RUN/'STOP.json').exists(): return
                    time.sleep(min(30,until-time.time()))
                with (RUN/'quota-waits.jsonl').open('a') as h: h.write(json.dumps(dict(started_at=waitstart,ended_at=time.time(),seconds=time.time()-waitstart,next_attempt=identity))+'\n')
            d.mkdir();save(d/'attempt.json',dict(**task,started_at=now(),protocol_sha256=digest(RUN/'protocol.json')))
            save(d/'budget-at-entry.json',costs)
            save(d/'live-state.json',dict(counts=dict.fromkeys(p['caps'],0),deadline=time.time()+285,stop=None))
            start=time.monotonic()
            save(RUN/'status.json',dict(status='running',current_attempt=identity,started_at=now(),completed_attempts=len(list(stage.glob('*/job.json')))))
            with (d/'stdout.log').open('wb') as out,(d/'stderr.log').open('wb') as err:
                try:
                    child=subprocess.run([sys.executable,str(Path(__file__)),'--worker',identity],stdout=out,stderr=err,timeout=300,
                        env={**os.environ,**fs.THREADS,'PYTHONUTF8':'1','PYTHONPATH':str(FROZEN/'src')+os.pathsep+str(FROZEN/'evaluation')})
                    code=child.returncode
                except subprocess.TimeoutExpired: code=None
            u=usage(d,fs.MODELS[task['model']]);state=read(d/'live-state.json')
            counts=Counter(r['service'] for r in u)
            unknown=any(not r.get('usage_known') or (r['service'] in ('ollama','jev') and r.get('model_verified') is not True) for r in u)
            operational=bool(state['stop'] or unknown or any(r.get('status') in (401,402,403,429) or (r.get('status') or 0)>=500 or r.get('transport_error') for r in u))
            if any(counts[s]!=n for s,n in state['counts'].items()): operational=True
            failure=(d/'stderr.log').read_text(encoding='utf-8',errors='replace')
            save(d/'usage.json',u)
            save(d/'job.json',dict(exit_code=code,elapsed_seconds=time.monotonic()-start,finished_at=now(),
                workflow_completed=(d/'result.json').exists(),failure_reason=failure[-6000:] if code!=0 else None,
                timeout=code is None,operational_stop=operational,stop_reason=state['stop']))
            rows,costs,problems=reconcile()
            print(identity,'COMPLETE' if (d/'result.json').exists() else 'FAILED',costs,flush=True)
            if operational or problems:
                save(RUN/'STOP.json',dict(reason='Operational/accounting condition',attempt=identity,problems=problems,stop_reason=state['stop'],timestamp=now()))
                break
        done=len(list(stage.glob('*/job.json')))
        save(RUN/'status.json',dict(status='complete' if done==200 else 'stopped',attempted=done,updated_at=now(),remaining450_released=False))
    finally: lock.unlink(missing_ok=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--worker');a.add_argument('--preflight',action='store_true');a.add_argument('--verify',action='store_true');args=a.parse_args()
    if args.worker: worker(args.worker)
    elif args.preflight: preflight()
    elif args.verify: verify();print('Frozen hashes and isolated imports verified; zero live inference')
    else: launch()

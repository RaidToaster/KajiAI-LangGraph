"""Resource accounting and paired-case forecast; no inference and no method decisions."""
from pathlib import Path
import csv, json, math, random, statistics, sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
import pilot50 as pilot
RUN=Path(__file__).resolve().parent
read,save=pilot.read,pilot.save

def quantile(xs,q):
    if not xs:return None
    xs=sorted(xs);x=(len(xs)-1)*q;l=math.floor(x);h=math.ceil(x)
    return xs[l]+(xs[h]-xs[l])*(x-l)
def stats(xs):
    return dict(n=len(xs),total=sum(xs),mean=statistics.mean(xs) if xs else None,
        median=statistics.median(xs) if xs else None,p90=quantile(xs,.9),p95=quantile(xs,.95))

def calendar_simulation(rows,multiplier,initial_rows=None):
    # Replay measured within-attempt send offsets in a single worker, respecting every window.
    p=read(RUN/'protocol.json');times=defaultdict(list);elapsed=0.;wait=0.
    origin=datetime.now(timezone.utc).timestamp()
    for r in initial_rows or []:
        times[r['service']].extend([datetime.fromisoformat(r['sent_at']).timestamp()-origin]*r.get('url_attempts',1))
    for _ in range(multiplier):
        for r in rows:
            pause=elapsed
            for service,windows in p['quota_windows'].items():
                for window,cap in windows:
                    recent=sorted(t for t in times[service] if t>elapsed-window)
                    excess=len(recent)+p['caps'][service]-cap
                    if excess>0:pause=max(pause,recent[excess-1]+window+.1)
            wait+=pause-elapsed;elapsed=pause
            for send in r['retrieval_events']:
                times[send['service']].extend([elapsed+send['offset']]*send['url_attempts'])
            elapsed+=r['active_seconds']
    return dict(processing_seconds=sum(r['active_seconds'] for r in rows)*multiplier,
        quota_wait_seconds=wait,calendar_seconds=elapsed,
        assumption='Single worker; repeat measured schedule and within-attempt offsets; reserve full per-attempt retrieval ceilings; no setup/audit/provider latency drift')

def main():
    p=pilot.verify();sends,costs,problems=pilot.reconcile()
    groups=defaultdict(list);rows=[];gold=read(RUN/'selected-gold.json')
    for task in p['schedule']:
        identity=pilot.fs.task_id(task);d=RUN/'attempts'/identity
        if not (d/'job.json').exists():continue
        job=read(d/'job.json');attempt=read(d/'attempt.json');u=read(d/'usage.json')
        result=read(d/'result.json') if (d/'result.json').exists() else {}
        count=Counter(s['service'] for s in u)
        completed=bool(result) and result.get('result',{}).get('verification_status') not in ('execution_error','invalid_input')
        timing=read(d/'worker-timing.json') if (d/'worker-timing.json').exists() else {}
        workflow=timing.get('workflow_seconds')
        if workflow is None and timing.get('workflow_started_epoch'):
            workflow=max(0,datetime.fromisoformat(job['finished_at']).timestamp()-timing['workflow_started_epoch'])
        if workflow is None:workflow=0.0
        r=dict(attempt=identity,**task,completed=completed,failed=not completed,timeout=job['timeout'],
            started_at=attempt['started_at'],finished_at=job['finished_at'],active_seconds=job['elapsed_seconds'],
            workflow_seconds=workflow,startup_seconds=max(0,job['elapsed_seconds']-workflow),
            gold_label=gold[task['case']],prediction=result.get('predicted_label'),accepted=result.get('accepted_label'),
            failure_reason=job.get('failure_reason') or (result.get('result',{}).get('stop_reason') if not completed else None),operational_stop=job['operational_stop'],
            rounds=len(result.get('result',{}).get('research_history',[])),
            ollama_calls=count['ollama'],jev_calls=count['jev'],search_calls=count['tinyfish_search'],
            fetch_url_attempts=sum(s.get('url_attempts',1) for s in u if s['service']=='tinyfish_fetch'),
            ollama_estimated_usd=(sum(s['estimated_usd'] for s in u if s['service']=='ollama') if all(s.get('usage_known') for s in u if s['service']=='ollama') else None),
            jev_estimated_usd=(sum(s['estimated_usd'] for s in u if s['service']=='jev') if all(s.get('usage_known') for s in u if s['service']=='jev') else None),
            known_ollama_estimated_usd=sum(s.get('estimated_usd',0) for s in u if s['service']=='ollama'),
            known_jev_estimated_usd=sum(s.get('estimated_usd',0) for s in u if s['service']=='jev'),
            unknown_reserved_liability_usd=sum(s.get('reservation_usd') or 0 for s in u if not s.get('usage_known')),
            model_usage_unknown=sum(not s.get('usage_known',False) for s in u if s['service'] in ('ollama','jev')),
            provider_billing_usd=None,cache_tokens=None,reasoning_tokens=None)
        for service in ('ollama','jev'):
            for field in ('input_tokens','output_tokens'):
                values=[s.get(field) for s in u if s['service']==service]
                r[service+'_'+field]=sum(values) if all(v is not None for v in values) else None
            r[service+'_service_seconds']=sum(s.get('elapsed_seconds') or 0 for s in u if s['service']==service)
        start=datetime.fromisoformat(r['started_at']).timestamp()
        r['retrieval_events']=[dict(service=s['service'],offset=max(0,datetime.fromisoformat(s['sent_at']).timestamp()-start),url_attempts=s.get('url_attempts',1)) for s in u if s['service'].startswith('tinyfish')]
        cumulative=[rr['elapsed_seconds'] for rr in result.get('result',{}).get('research_history',[]) if 'elapsed_seconds' in rr]
        r['round_seconds']=[max(0,t-(cumulative[i-1] if i else 0)) for i,t in enumerate(cumulative)]
        rows.append(r);groups[task['model']+'/'+task['arm']].append(r)
    flat=[{k:v for k,v in r.items() if k!='retrieval_events'} for r in rows]
    if flat:
        with (RUN/'attempts.csv').open('w',newline='',encoding='utf-8-sig') as h:
            w=csv.DictWriter(h,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    else:
        (RUN/'attempts.csv').write_text('attempt,model,arm,completed,failed\n',encoding='utf-8')
    metrics=['ollama_input_tokens','ollama_output_tokens','jev_input_tokens','jev_output_tokens',
        'ollama_calls','jev_calls','search_calls','fetch_url_attempts','active_seconds','ollama_estimated_usd','jev_estimated_usd']
    summary={};forecast={}
    for name in [m+'/'+a for m in ('glm','deepseek') for a in ('baseline','candidate')]:
        rs=groups[name];n=len(rs)
        summary[name]=dict(attempted=n,completed=sum(r['completed'] for r in rs),failed=sum(r['failed'] for r in rs),
            timeouts=sum(r['timeout'] for r in rs),time=stats([r['active_seconds'] for r in rs]),
            totals={k:sum(r[k] for r in rs) if all(r[k] is not None for r in rs) else None for k in metrics},
            service_time={s:stats([v['elapsed_seconds'] for v in sends if v['model']==name.split('/')[0] and v['arm']==name.split('/')[1] and v['service']==s and v.get('elapsed_seconds') is not None]) for s in p['caps']},
            workflow_time=stats([r['workflow_seconds'] for r in rs]),startup_time=stats([r['startup_seconds'] for r in rs]),
            round_time=stats([t for r in rs for t in r['round_seconds']]),
            distributions={k:stats([r[k] for r in rs if r[k] is not None]) for k in metrics},
            accepted=sum(r['accepted'] is not None and r['accepted']!='ABSTAIN' for r in rs),
            label_agreement=sum(r['prediction']==r['gold_label'] for r in rs),
            cache_tokens=None,reasoning_tokens=None,measured_billing_usd=None)
        forecast[name]={}
        for cases,factor in ((500,10),(450,9)):
            forecast[name][str(cases)]=dict(resources={k:(v*factor if v is not None else None) for k,v in summary[name]['totals'].items()},
                based_on_attempts=n,valid_50case_scaling=(n==50),failed_attempts_included=True)
    # Resample shared case IDs jointly to preserve cross-arm/model covariance.
    paired={}
    bycase=defaultdict(list)
    for r in rows:bycase[r['case']].append(r)
    complete_ids=[i for i,rs in bycase.items() if len(rs)==4]
    rng=random.Random(20261106);draws=defaultdict(list)
    if len(complete_ids)>=2:
        for _ in range(4000):
            sample=rng.choices(complete_ids,k=len(complete_ids))
            for metric in metrics:
                for name in summary:
                    vals=[r[metric] for i in sample for r in bycase[i] if r['model']+'/'+r['arm']==name]
                    if all(v is not None for v in vals): draws[(name,metric)].append(sum(vals)*50/len(sample))
                vals=[r[metric] for i in sample for r in bycase[i]]
                if all(v is not None for v in vals):draws[('aggregate',metric)].append(sum(vals)*50/len(sample))
        for (name,metric),values in draws.items():
            paired.setdefault(name,{})[metric]={str(c):[quantile(values,.025)*f,quantile(values,.975)*f] for c,f in ((500,10),(450,9))}
    waits=[]
    if (RUN/'quota-waits.jsonl').exists(): waits=[json.loads(x) for x in (RUN/'quota-waits.jsonl').read_text().splitlines()]
    active=sum(r['active_seconds'] for r in rows)
    elapsed=(datetime.fromisoformat(rows[-1]['finished_at'])-datetime.fromisoformat(rows[0]['started_at'])).total_seconds() if rows else 0
    wait=sum(w['seconds'] for w in waits)
    totals={k:sum(s['totals'][k] for s in summary.values()) if all(s['totals'][k] is not None for s in summary.values()) else None for k in metrics}
    calendar={str(c):calendar_simulation(rows,f,pilot.retrieval_sends() if c==450 else None) for c,f in ((500,10),(450,9))} if len(rows)==200 else None
    f=dict(generated_at=pilot.now(),pilot_attempts=len(rows),planned_attempts=200,complete=len(rows)==200,
        model_arm=forecast,aggregate={str(c):{k:(v*f if v is not None else None) for k,v in totals.items()} for c,f in ((500,10),(450,9))},
        uncertainty=dict(method='4000 paired-case bootstrap draws across all4 combinations; 95% percentile intervals; no guarantee of temporal or distributional stability',
                         complete_case_blocks=len(complete_ids),intervals=paired),
        quota_limited_calendar=calendar,
        sensitivity=dict(deepseek_offpeak='Half peak input/output rates outside12-18UTC weekdays and weekends; unknown cache usage not assumed',
            cache_input_rates=p['cached_input_rates_per_million'],output_variability='Bootstrap retains failures and measured variability; additional failures, latency and content drift may change scaling',
            all_attempts_timeout_processing_hours={'500':2000*300/3600,'450':1800*300/3600}),
        measured_billing_usd=None,rates=p['rates_per_million'],cost_assumption='Peak uncached; provider cache/reasoning counters unknown unless explicitly in raw service-ledger provider fields',
        already_completed_not_double_counted='200pilot+1800additional=2000 only if exact freeze continued after new approval',remaining450_released=False,
        limitations=['Unqualified candidate; adaptive/exposed benchmark; label agreement is not official AVeriTeC evidence scoring.',
        'Codex/reviewer overhead tokens and account bill unobserved; workflow API counters only.',
        'If fewer than50pergroup, linear figures are partial resource totals, not valid50case forecasts.'])
    save(RUN/'FORECAST_500.json',f)
    save(RUN/'summary.json',dict(groups=summary,totals=totals,active_seconds=active,quota_wait_seconds=wait,
        first_attempt_to_last_finish_seconds=elapsed,between_attempt_audit_startup_seconds=max(0,elapsed-active-wait),problems=problems,
        service_time={s:stats([v['elapsed_seconds'] for v in sends if v['service']==s and v.get('elapsed_seconds') is not None]) for s in p['caps']}))
    lines=['# Frozen50-case resource pilot',f'\nStatus: {len(rows)}/200fresh attempts accounted. Remaining450cases are NOT authorized.',
        '\nThe candidate is UNQUALIFIED. Its frozen GLMnative test failed scope/materiality fidelity; DeepSeek had not run this exact snapshot. No method tuning or historical pass rewriting.',
        '\n|Model/arm|Attempted|Completed|Failed|Ollama input/output|Jev input/output|Search/FetchURLs|Active seconds|Estimated model/Jev USD|',
        '|---|---:|---:|---:|---|---|---|---:|---|']
    for name,s in summary.items():
        t=s['totals'];fmt=lambda x: 'UNKNOWN' if x is None else f'{x:.6f}'
        lines.append(f"|{name}|{s['attempted']}|{s['completed']}|{s['failed']}|{t['ollama_input_tokens']}/{t['ollama_output_tokens']}|{t['jev_input_tokens']}/{t['jev_output_tokens']}|{t['search_calls']}/{t['fetch_url_attempts']}|{s['time']['total']:.1f}|{fmt(t['ollama_estimated_usd'])}/{fmt(t['jev_estimated_usd'])}|")
    lines.extend([f'\nActive processing: {active:.3f}s. Recorded quota waits: {wait:.3f}s. First-attempt to last-finish calendar: {elapsed:.3f}s. Other between-attempt startup/audit: {max(0,elapsed-active-wait):.3f}s. Preflight/startup before the first attempt is separate (timestamps in protocol/PREFLIGHT/launch records).',
        '\nPer-arm mean/median/P90/P95, timeouts, service-time distributions and failure reasons are in summary.json and attempts.csv. Missing cache/reasoning/billing counters remain unknown. Raw requests/responses and per-send timing reside under attempts/. Round traces are retained in completed result.json; no round duration is invented for failed/missing traces.',
        '\nCandidate: archivedevidence_adjudicated, bound anchors, predecision source-path review, single materiality owner, questions_as_guidance, provenance review, source-reference research,6144assessmentoutput, GLMhigh/DeepSeekfalse. Baseline: original standard workflow,4096output and original default reasoning behavior. This compares a combined intervention.',
        '\nEstimates use peak uncached [Ollama rates](https://ollama.com/pricing): GLM$0.15input/$0.50output and DeepSeek$0.30/$1.20 per million. [Jev1.13](https://docs.typesafe.ai/models):$0.042/millioninput, outputfree. [TinyFishSearch/Fetch](https://www.tinyfish.ai/pricing) free within limits. No provider billing total was available; these are rate-derived estimates.',
        '\nForecasts: FORECAST_500.json provides10xfull500and9xadditional450byarm, paired bootstrap intervals and quota-aware schedule replay when all200finish. Failed attempts remain in denominators. Cache/offpeak sensitivity and all-timeout bounds are disclosed. No remaining cases were launched.',
        '\nHistorical approximate balances ($60Ollama/$4.77Jev) were reconciled conservatively against recorded usage in PREFLIGHT.json; they were not freshly verified account balances. Historical unknown usage remains separate.',
        '\nThis adaptive resource pilot is not pristine held-out evidence of improvement. Label agreement is descriptive and is not official AVeriTeC evidence scoring. Inference receives only claim and claim date, never gold labels.',
        '\n'+('All200scheduled attempts accounted; stopped at pilot boundary.' if len(rows)==200 else 'Pilot incomplete: inspect STOP.json/status.json. Do not replace started attempts or treat partial totals as50case estimates.')])
    (RUN/'PILOT_50_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(attempted=len(rows),costs=costs,active_seconds=active,quota_wait_seconds=wait,problems=problems)))

if __name__=='__main__':main()

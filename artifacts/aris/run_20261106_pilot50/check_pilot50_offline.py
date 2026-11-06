"""Zero-network operational witnesses for the pilot executor."""
from pathlib import Path
import json,sys,time
RUN=Path(__file__).resolve().parent
sys.path.insert(0,str(RUN))
import pilot50 as p
from runtime_pilot import LimitReached

def main():
    protocol=p.verify();root=Path.cwd()/'tmp/pilot50-offline'
    root.mkdir(exist_ok=False)
    model=p.fs.MODELS['glm'];checks=[]
    def directory(name):
        d=root/name;d.mkdir()
        p.save(d/'live-state.json',dict(counts=dict.fromkeys(protocol['caps'],0),deadline=time.time()+60,stop=None))
        p.save(d/'budget-at-entry.json',{'ollama':0,'jev':0})
        return d
    d=directory('known');ledger=p.PilotLedger(d,dict(protocol,num_predict=4096),model)
    n=ledger.before('ollama',dict(path='/api/chat',body=dict(model=model,options={'num_predict':4096},messages=[])))
    assert p.read(d/f'request-{n:03}.json')['reservation_usd']>.6
    ledger.response(n,200,json.dumps(dict(model='glm-5.3-flash',done=True,prompt_eval_count=100,eval_count=20)).encode())
    u=p.usage(d,model);assert u[0]['usage_known'] and u[0]['estimated_usd']<.001;checks.append('full provider-bound reservation releases only terminal known usage')
    d=directory('unknown-fetch');ledger=p.PilotLedger(d,protocol,model)
    n=ledger.before('tinyfish_fetch',dict(url='https://api.fetch.tinyfish.ai',body={'urls':['https://example.com']}))
    p.save(d/f'response-{n:03}.json',{'error':'interrupted'})
    assert not p.usage(d,model)[0]['usage_known']
    try:ledger.before('jev',dict(body={'model':'jev-1.13.0'}))
    except LimitReached:pass
    else:raise AssertionError('UNKNOWN retrieval allowed another dispatch')
    checks.append('unknown retrieval/error-only metadata blocks every later service')
    d=directory('partial-model');ledger=p.PilotLedger(d,protocol,model)
    n=ledger.before('ollama',dict(body=dict(model=model,options={'num_predict':4096})))
    p.save(d/f'response-{n:03}.json',{'status':200})
    (d/f'response-{n:03}.body').write_text(json.dumps(dict(model='glm-5.3-flash',done=False,prompt_eval_count=100,eval_count=20)))
    assert not p.usage(d,model)[0]['usage_known'];checks.append('partial model counters stay UNKNOWN and retain reservation')
    d=directory('spend-stop');p.save(d/'budget-at-entry.json',{'ollama':9.9,'jev':0})
    ledger=p.PilotLedger(d,protocol,model)
    try:ledger.before('ollama',dict(body=dict(model=model,options={'num_predict':4096})))
    except LimitReached:pass
    else:raise AssertionError('spend ceiling passed')
    assert not list(d.glob('request-*.json'));checks.append('conservative spend stops before send reservation')
    d=directory('identity');ledger=p.PilotLedger(d,protocol,model)
    try:ledger.before('ollama',dict(body=dict(model='other-model')))
    except LimitReached:pass
    else:raise AssertionError('model substitution allowed')
    assert not list(d.glob('request-*.json'));checks.append('wrong requested model blocked before send')
    assert p.quota_until([dict(service='tinyfish_fetch',sent_at=p.now())]*900,protocol)>time.time()+86000
    checks.append('rolling quota reserves full next attempt and waits')
    p.save(RUN/'offline-check.json',dict(passed=True,checks=checks,live_service_calls=0,fixture_location=str(root)))
    print(json.dumps(dict(passed=True,checks=checks,live_service_calls=0)))

if __name__=='__main__':main()

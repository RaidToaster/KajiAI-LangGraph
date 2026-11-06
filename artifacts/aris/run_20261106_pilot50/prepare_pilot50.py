"""Prospective resource-pilot freeze. Selection reads IDs before any case content."""
from pathlib import Path
import hashlib, json, random, shutil, sys, zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'artifacts/aris/run_20261106_pilot50'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, v): p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main():
    assert not (RUN/'protocol.json').exists(), 'Never replace a freeze'
    original = ROOT/'artifacts/flash-workflow-20261103'
    native = ROOT/'artifacts/owned-evidence-native-20261106'
    assert sha(native/'source.zip') == 'f9c7598dcd0c8f89be4e9f969c3819b17fd5609c8e0dfb09151cea57d93bf9c8'
    assert sha(original/'final-case-manifest.json') == 'b3f4016c0de144b27bc02d2167093eda3da938a1f694605aa8148db3920bccf2'
    assert sha(original/'final-cases.json') == '4687c951515657657d418d6439bf7b180c5a912465f79c32fdd58a52a4cc0c60'
    ids = read(original/'final-case-manifest.json')['ids']
    selected = random.Random(20261106).sample(ids, 50)
    save(RUN/'selection.json', dict(algorithm='CPython random.Random(seed).sample(manifest_ids,50)',
        python=sys.version, seed=20261106, ordered_ids=selected, selection_code_sha256=sha(Path(__file__)),
        manifest_sha256=sha(original/'final-case-manifest.json'), selected_before_case_read=True))
    # Only selected rows are retained; no unselected content is examined or printed.
    cases = read(original/'final-cases.json')
    save(RUN/'selected-inference.json', {i:{k:cases[i][k] for k in ('claim','claim_date') if k in cases[i]} for i in selected})
    save(RUN/'selected-gold.json', {i:cases[i]['label'] for i in selected})
    del cases
    schedule=[]
    # Latin-square rotation: each combination occupies every position, reversed in alternate blocks.
    combinations=[('glm','baseline'),('glm','candidate'),('deepseek','baseline'),('deepseek','candidate')]
    for index, case in enumerate(selected):
        order=combinations[index%4:]+combinations[:index%4]
        if (index//4)%2: order=list(reversed(order))
        schedule.extend(dict(case=case, model=model, arm=arm) for model,arm in order)
    baseline=read(original/'development.json')
    candidate=read(native/'protocol.json')
    for name in ('baseline','candidate'):
        config=baseline['config'] if name=='baseline' else candidate['config']
        config['model'].pop('name',None)
        config['model']['base_url']='http://127.0.0.1:11434'
        save(RUN/f'{name}-config.json', config)
    # Gather unique real retrieval reservations, retaining failed/unknown sends and copy provenance.
    seen={}
    for p in (ROOT/'artifacts').rglob('request-*.json'):
        rel=p.relative_to(ROOT).as_posix()
        if any(x.startswith('pytest') or x in ('frozen','flash-snapshot-validation-20261104') for x in p.parts): continue
        if not (p.parent/'live-state.json').exists(): continue
        try: r=read(p)
        except (ValueError,OSError): continue
        if r.get('service') not in ('tinyfish_search','tinyfish_fetch'): continue
        key=hashlib.sha256(p.read_bytes()).hexdigest()
        if key not in seen:
            seen[key]=dict(service=r['service'],sent_at=r['timestamp'],request_sha256=key,source=rel,
                url_attempts=len((r.get('request',{}).get('body') or {}).get('urls',[None])))
    save(RUN/'prior-retrieval-ledger.json',list(seen.values()))
    shutil.copyfile(original/'final-case-manifest.json',RUN/'final-case-manifest.json')
    shutil.copyfile(native/'protocol.json',RUN/'candidate-native-protocol.json')
    shutil.copyfile(original/'development.json',RUN/'baseline-original-protocol.json')
    for name in ('pilot50.py','analyze_pilot50.py','prepare_pilot50.py','check_pilot50_offline.py'):
        shutil.copyfile(ROOT/'evaluation'/name,RUN/name)
    shutil.copyfile(ROOT/'PILOT_50_NEXT_SESSION_PROMPT.md',RUN/'AUTHORIZATION.md')
    # Frozen helper recovery: this exact scorer was disclosed in the handoff.
    assert sha(RUN/'frozen/evaluation/analyze_flash_study.py') == 'd9a372fb4891c6f93f22c57347b2d9bb12f1f5c8a0549174347f688db75b2e9b'
    protocol=dict(phase='prospective_unqualified_resource_pilot',created_at=datetime.now(timezone.utc).isoformat(),
        entry_authorization='AUTHORIZATION.md: prior8/12waived ONLY for this200attempt pilot; acceptance unchanged',
        candidate_qualified=False, native_glm='CLOSED FAILED: unsupported scope/materiality objection',native_deepseek='not run on exact candidate',
        models=baseline['models'],caps=baseline['caps'],rounds=3,num_predict=4096,brief_assessment_tokens=6144,
        compiled_ledger_candidate=True,compiled_assessment_mode='evidence_adjudicated',compact_evidence_prompt=True,recover_empty_assessment=False,
        candidate_reasoning_effort=candidate['assessment_reasoning'],require_independent_provenance_review=True,
        search_source_references=True,configurations={'baseline':'baseline-config.json','candidate':'candidate-config.json'},
        baseline_reasoning='original ChatOllama default reasoning field absent; archived repair false',
        schedule=schedule,max_attempt_seconds=300,attempt_send_deadline_seconds=285,threads=2,workers=1,
        scheduling_cost_caps_usd={'ollama':10,'jev':1},rates_per_million={'glm':[.15,.50],'deepseek':[.30,1.20],'jev':[.042,0]},
        cached_input_rates_per_million={'glm':.03,'deepseek':.006},deepseek_offpeak_rates=[.15,.60],
        rates_sources=['https://ollama.com/pricing','https://docs.typesafe.ai/models','https://www.tinyfish.ai/pricing'],
        cost_reservation='Reserve full documented1Mcontext separately for input and output per Ollama send at peak uncached rates; Jev65536inputtokens. Cloud output settings may be ignored; overrun stops pilot. Unknown reservations never released.',
        provider_reservation_token_bounds={'ollama_input':1048576,'ollama_output':1048576,'jev_input':65536},
        quota_windows={'tinyfish_search':[[60,27],[3600,450]],'tinyfish_fetch':[[60,135],[86400,900]]},
        paid_retrieval_authorized=False,external_retries=0,reuse_attempts=False,cross_arm_cache=False,
        method_changes_after_launch=False,remaining450_released=False,
        candidate_source_archive_sha256=sha(native/'source.zip'),candidate_source_sha256=candidate['source_sha256'],
        common_token_limit=250000,forecasts='10x measured50/arm for full500;9x additional450; paired case bootstrap; quota simulation',
        failures='Preserve parser/execution errors/abstentions without replacement; operational/model/accounting/quota/spend stops require reconciliation',
        freeze_files={})
    files=[p for p in RUN.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('protocol.json',)]
    protocol['freeze_files']={p.relative_to(RUN).as_posix():sha(p) for p in files}
    save(RUN/'protocol.json',protocol)
    save(RUN/'approval.json',dict(protocol_sha256=sha(RUN/'protocol.json'),user_authorized_200=True,
        no_paid_retrieval=True,full_study_released=False))
    with zipfile.ZipFile(RUN/'source-package.zip','x',zipfile.ZIP_DEFLATED) as z:
        for p in files+[RUN/'protocol.json',RUN/'approval.json']: z.write(p,p.relative_to(RUN).as_posix())
    print(json.dumps(dict(run=str(RUN),protocol_sha256=sha(RUN/'protocol.json'),source_package_sha256=sha(RUN/'source-package.zip'),selected=50,attempts=len(schedule))))

if __name__=='__main__': main()

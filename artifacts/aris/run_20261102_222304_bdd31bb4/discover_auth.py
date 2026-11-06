import json,subprocess,time,urllib.request,urllib.error
from pathlib import Path
run=Path(__file__).resolve().parent
records=[]
def request(path,payload=None):
 try:
  req=urllib.request.Request('http://localhost:11434'+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=12) as r: value=json.load(r)
  if path=='/api/me': value={'authenticated':bool(value.get('name') or value.get('email') or value.get('user')),'keys':list(value)}
  if path=='/api/tags':value={'models':[{k:m.get(k) for k in ['name','model','digest','remote_model','remote_host','details']} for m in value.get('models',[])]}
  if path=='/api/show':value={k:value.get(k) for k in ['capabilities','parameters','details','model_info']}
  records.append({'endpoint':path,'payload':payload,'status':200,'value':value});return value
 except Exception as e:records.append({'endpoint':path,'payload':payload,'error':f'{type(e).__name__}: {e}'});return None
if request('/api/version') is None:
 exe=Path.home()/'AppData/Local/Programs/Ollama/ollama.exe'
 with (run/'ollama-recovery.stdout.log').open('ab') as out,(run/'ollama-recovery.stderr.log').open('ab') as err:
  p=subprocess.Popen([str(exe),'serve'],stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
  records.append({'service_started_pid':p.pid})
 for _ in range(8):
  time.sleep(1)
  if request('/api/version') is not None:break
request('/api/tags');request('/api/me',{})
for model in ['gemma4:31b-cloud','deepseek-v4.1-flash:cloud','glm-5.3-flash:cloud']:request('/api/show',{'model':model})
(run/'ollama-auth-discovery.json').write_text(json.dumps(records,indent=2),encoding='utf8');print(json.dumps(records,indent=2)[:13000])

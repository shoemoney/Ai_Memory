"""Reproduce v1 and test predeclared cap/repetition hypotheses."""
import collections,copy,json,os,time,urllib.request
from pathlib import Path
from host import Host,ROOT
V1=ROOT.parent/'v1'
def ask(request):
 start=time.perf_counter();q=urllib.request.Request(os.environ['BASE_URL']+'/chat/completions',json.dumps(request).encode(),{'Content-Type':'application/json'})
 with urllib.request.urlopen(q,timeout=180) as r:raw=json.load(r)
 return raw,time.perf_counter()-start

def run():
 outdir=ROOT/'results/diagnostic';outdir.mkdir(exist_ok=True)
 model=next(m for m in json.loads((ROOT/'models.json').read_text()) if m['id']=='qwen3.5-4b-q4_k_m')
 old=[r for r in map(json.loads,(V1/'results/qwen3.5-4b-q4_k_m.jsonl').read_text().splitlines()) if r['seed']==7]
 h=Host(slots=1,budget=None);h.setup()
 rows=[]
 try:
  h.load(model)
  completed={}
  path=outdir/'requests.jsonl'
  if path.exists():
   rows=[json.loads(l) for l in path.read_text().splitlines()];completed={(r['arm'],r['id']):r for r in rows}
  with path.open('a') as out:
   for arm in ('v1-shipped-512','cap-only-1024','repeat-1.1-512'):
    items=old if arm!='cap-only-1024' else [r for r in old if not r['accepted']]
    for item in items:
     if (arm,item['id'])in completed:continue
     b=copy.deepcopy(item['request']);b['model']='writer'
     if arm=='cap-only-1024':b['max_tokens']=1024
     if arm=='repeat-1.1-512':b['repeat_penalty']=1.1
     h.ensure();response,seconds=ask(b);c=response['choices'][0];text=c['message']['content'];valid=False
     try:
      p=json.loads(text);valid=isinstance(p,dict) and set(p)=={'name','city','likes'} and all(isinstance(v,str) for v in p.values()) and c['finish_reason']=='stop' and not c['message'].get('reasoning_content')
     except ValueError:pass
     row={'serving_hardware':h.hardware,'arm':arm,'id':item['id'],'request':b,'response':response,'seconds':seconds,'valid':valid,'reasoning_characters':len(c['message'].get('reasoning_content',''))}
     out.write(json.dumps(row)+'\n');out.flush();rows.append(row);print(arm,item['id'],valid,seconds,flush=True)
  # Inspect the actual template rendering without exposing any model path.
  probes=[]
  for thinking in (False,True):
   b={'messages':old[0]['request']['messages'],'chat_template_kwargs':{'enable_thinking':thinking}}
   q=urllib.request.Request(f'http://localhost:39745/apply-template',json.dumps(b).encode(),{'Content-Type':'application/json'})
   try:
    with urllib.request.urlopen(q,timeout=30) as response:result=json.load(response)
    probes.append({'thinking':thinking,'request':b,'response':result})
   except Exception as e:probes.append({'thinking':thinking,'error':type(e).__name__})
  (outdir/'template-probes.json').write_text(json.dumps(probes,indent=2)+'\n')
 finally:h.close(cleanup=False)
 summary=[]
 for arm in sorted({r['arm'] for r in rows}):
  rr=[r for r in rows if r['arm']==arm]
  summary.append({'arm':arm,'N':len(rr),'valid':sum(r['valid'] for r in rr),'finish_reasons':dict(collections.Counter(r['response']['choices'][0]['finish_reason'] for r in rr)),'reasoning_characters':sum(r['reasoning_characters'] for r in rr)})
 (outdir/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':run()

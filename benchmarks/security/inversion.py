"""Q4 GTR/Vec2Text learned inversion with paired write-time exclusion.

The attack sees vectors only. The defended vector index embeds an opaque
reference; authorized source text stays in a separate simulated vault.
"""
import argparse,collections,hashlib,json,pathlib,random,re,sqlite3,time,urllib.request
import numpy as np
SEED=20261122

def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def norm(s):return re.sub(r'\s+',' ',s).strip()
def f1(a,b):
 a=collections.Counter(re.findall(r'\w+',a.lower()));b=collections.Counter(re.findall(r'\w+',b.lower()));n=sum((a&b).values());return 2*n/(sum(a.values())+sum(b.values())) if a or b else 1.0

def run():
 p=argparse.ArgumentParser();p.add_argument('--scratch',default='/data/scratch/membench/security');p.add_argument('--results',default='results/model');p.add_argument('--endpoint',default='http://localhost:39800');p.add_argument('--trials',type=int,default=150);p.add_argument('--steps',type=int,default=5);p.add_argument('--batch-size',type=int,default=8);a=p.parse_args()
 scratch=pathlib.Path(a.scratch);out=pathlib.Path(a.results)/'inversion.jsonl';out.parent.mkdir(parents=True,exist_ok=True)
 done={r['id']:r for r in map(json.loads,out.read_text().splitlines())} if out.exists() else {}
 def request(path,body):
  req=urllib.request.Request(a.endpoint+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=900) as r:return json.load(r)
 def save(row):
  with out.open('a') as f:f.write(json.dumps(row)+'\n');f.flush()
  done[row['id']]=row
 from inversion_data import fixture,attributes_recovered
 cases=fixture(scratch,a.trials);sources=[r['source'] for r in cases]
 jobs=[{'i':i,'arm':arm,'source':text,'index_text':text if arm=='undefended' else f'memory reference item-{i:04d}'} for i,text in enumerate(sources) for arm in ['undefended','defended']]
 def embed(texts,label):
  path=scratch/('inversion-'+label+'.json')
  cache=json.loads(path.read_text()) if path.exists() else {}
  answer=[]
  for start in range(0,len(texts),a.batch_size):
   batch=texts[start:start+a.batch_size];key=str(start)
   if key not in cache:
    cache[key]=request('/infer',{'model':'gtr','input':batch})['vectors'];path.write_text(json.dumps(cache))
   answer.extend(cache[key])
  result=np.asarray(answer,dtype=np.float32);assert result.shape==(len(texts),768) and np.isfinite(result).all() and (np.linalg.norm(result,axis=1)>0).all(), 'invalid GTR vectors';return result
 targets=embed([j['index_text'] for j in jobs],'targets')
 source_hash=[digest(j['source']) for j in jobs]
 for step in range(a.steps+1):
  candidates=[]
  if step:
   previous=[done[f"inversion/{j['i']}/{j['arm']}/{step-1}"]['answer'] for j in jobs]
   previous_vectors=embed(previous,f'hyp-{step-1}')
   previous_ids=[done[f"inversion/{j['i']}/{j['arm']}/{step-1}"]['token_ids'] for j in jobs]
  for start in range(0,len(jobs),a.batch_size):
   batch=jobs[start:start+a.batch_size]
   ids=[f"inversion/{j['i']}/{j['arm']}/{step}" for j in batch]
   if all(id_ in done for id_ in ids):
    candidates.extend(done[id_]['answer'] for id_ in ids);continue
   body={'model':'hypothesizer' if step==0 else 'corrector','vectors':targets[start:start+len(batch)].tolist(),'num_beams':1}
   if step:body.update(hypotheses=previous[start:start+len(batch)],hypothesis_vectors=previous_vectors[start:start+len(batch)].tolist(),hypothesis_token_ids=previous_ids[start:start+len(batch)])
   result=request('/infer',body)
   for k,(j,id_,answer) in enumerate(zip(batch,ids,result['answers'])):
    if id_ in done:continue
    save({'id':id_,'kind':'inversion_candidate','trial':j['i'],'arm':j['arm'],'step':step,'source_sha256':source_hash[start+k],'index_text_sha256':digest(j['index_text']),'source_token_count':32,'answer':answer,'token_ids':result['token_ids'][k],'truncated':result['truncated'][k],'completion_tokens':result['completion_tokens'][k],'answer_sha256':digest(answer),'attack_success':norm(answer)==norm(j['source']),'word_f1':f1(answer,j['source']),'attributes_recovered':attributes_recovered(answer,cases[j['i']]['attributes']),'attributes_total':3,'batch_inference_s':result['elapsed_s'],'batch_n':len(batch),'selection':'greedy correction output; no ground-truth selection'})
   candidates.extend(done[id_]['answer'] for id_ in ids)
   print('inversion step',step,'completed',min(start+len(batch),len(jobs)),'of',len(jobs),flush=True)
 # Separate functional utility control: authorized lookup by reference preserves text.
 vault=sqlite3.connect(scratch/'inversion-vault.sqlite')
 vault.execute('CREATE TABLE IF NOT EXISTS vault (id TEXT PRIMARY KEY,source TEXT)')
 for i,text in enumerate(sources):vault.execute('INSERT OR REPLACE INTO vault VALUES (?,?)',(f'item-{i:04d}',text))
 vault.commit()
 def lookup(reference,authorized):
  if not authorized:return None
  row=vault.execute('SELECT source FROM vault WHERE id=?',(reference,)).fetchone()
  return row[0] if row else None
 resolved=sum(lookup(f'item-{i:04d}',True)==text for i,text in enumerate(sources))
 leaked=sum(lookup(f'item-{i:04d}',False) is not None for i in range(len(sources)))
 if 'inversion/authorized-reference-resolution' not in done:save({'id':'inversion/authorized-reference-resolution','kind':'functional_control','n':a.trials,'successes':resolved,'unauthorized_resolutions':leaked,'description':'Direct authorized reference lookup in a separate SQLite vault; semantic retrieval utility is not tested.'})
 vault.close()
if __name__=='__main__':run()

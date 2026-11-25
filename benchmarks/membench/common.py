"""Local, checkpointed paired benchmark utilities."""
import hashlib,json,os,re,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent
LAB=Path(os.environ.get('LAB_DIR','/data/scratch/membench/membench'))
OUT=Path(os.environ.get('OUT_DIR',str(ROOT/'results')))
BASE=os.environ.get('BASE_URL','http://localhost:39780').removesuffix('/v1').rstrip('/')
SEED=20261122
MODEL='qwen2.5-14b-instruct'
EMBED_REV='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
SOURCES={
 'mab':{'dataset':'ai-hyz/MemoryAgentBench','revision':'7ea066982b140a19337e17e60d45d4076e042faf','file':'data/Accurate_Retrieval-00000-of-00001.parquet','local':'mab-ar','sha256':'56c3cd80fb6731a3e53cd1a6be3148f54df60ff2d290ee50e28f8acebf9655c1','license':'MIT','code_revision':'538026089d1a8a8eff05121d0db89b388f360eba'},
 'halu':{'dataset':'IAAR-Shanghai/HaluMem','revision':'cb04336aa1b732d4b24f5186c552456b4099806e','file':'HaluMem-Medium.jsonl','local':'halu-medium','sha256':'486fbc130a5c8781a2af27ffa508a1d7855245137aa449c193ac4d29c45634e7','license':'CC-BY-NC-ND-4.0','code_revision':'d653749586bfc7d13f5b68e8851f52155b5b1650'}}
def read(p):return json.loads(Path(p).read_text())
def atomic(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2,ensure_ascii=False));t.replace(p)
def sha(x):return hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()
def env():
 cache=Path(os.environ.get('CACHE_DIR','/data/scratch/membench/membench'))
 for k in ['HF_HOME','SENTENCE_TRANSFORMERS_HOME','XDG_CACHE_HOME']:os.environ[k]=str(cache/'cache')
 os.environ['UV_CACHE_DIR']=str(cache/'uv-cache');os.environ['PIP_CACHE_DIR']=str(cache/'pip-cache')
 os.environ['TOKENIZERS_PARALLELISM']='false';os.environ['OMP_NUM_THREADS']='4'
def download(u,p):
 p=Path(p)
 if p.exists():return
 p.parent.mkdir(parents=True,exist_ok=True)
 with requests.get(u,stream=True,timeout=180) as r:
  r.raise_for_status()
  with p.open('wb') as f:
   for c in r.iter_content(1024*1024):f.write(c)
def tokens(s):
 r=requests.post(BASE+'/tokenize',json={'content':s},timeout=180);r.raise_for_status();return len(r.json()['tokens'])
def chat(messages,max_tokens=192,seed=SEED,slot=None):
 body={'model':MODEL,'messages':messages,'temperature':0,'seed':seed,'max_tokens':max_tokens,'cache_prompt':True}
 if slot is not None:body['id_slot']=slot
 start=time.monotonic()
 for retry in range(8):
  try:
   r=requests.post(BASE+'/v1/chat/completions',json=body,timeout=1800);r.raise_for_status();d=r.json();c=d['choices'][0]
   if c['finish_reason']=='length':
    if body['max_tokens']>=1536:raise RuntimeError('output truncated')
    body['max_tokens']*=2;continue
   assert c['finish_reason']=='stop',c['finish_reason']
   return {'text':c['message']['content'],'finish_reason':c['finish_reason'],'usage':d.get('usage'),'seconds':time.monotonic()-start,'request_sha256':sha(json.dumps(body,sort_keys=True)),'max_tokens':body['max_tokens'],'seed':seed}
  except (requests.RequestException,ValueError):
   if retry==7:raise
   time.sleep(10)
 raise RuntimeError('retry budget exhausted')
def wilson(k,n):
 if not n:return [None,None]
 z=1.95996398454;p=k/n;d=1+z*z/n;a=(p+z*z/(2*n))/d;b=z*((p*(1-p)/n+z*z/(4*n*n))**0.5)/d
 return [a-b,a+b]

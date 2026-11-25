"""Shared configuration and durable per-item files for the larger run."""
import hashlib,json,os,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ.get('OUT_DIR',ROOT/'results/full'))
LAB=Path(os.environ.get('LAB_DIR','/var/tmp/membench-locomo'))
SEED=20261122
MODEL='qwen2.5-14b-instruct'
BASE=os.environ.get('BASE_URL','http://localhost:39701/v1')

def atomic(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp');temp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');temp.replace(path)
def read(path):return json.loads(Path(path).read_text())
def pseudo(text):
 mapping=read(OUT/'name-hashes.json')
 return re.sub(r'\b[A-Za-z]+\b',lambda m:mapping.get(hashlib.sha256(m[0].lower().encode()).hexdigest(),m[0]),str(text))
def item_path(backend,q):return OUT/'items'/backend/(q['item_id']+'.json')
def log(event,**fields):
 with (OUT/'events.jsonl').open('a') as f:f.write(json.dumps(dict(time=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),event=event,**fields))+'\n')
def env():
 (LAB/'tmp').mkdir(exist_ok=True)
 os.environ.update(TMPDIR=str(LAB/'tmp'),TIKTOKEN_CACHE_DIR=str(LAB/'tiktoken-cache'),XDG_CACHE_HOME=str(LAB/'xdg-cache'),HF_HOME=str(LAB/'hf'),MEM0_DIR=str(LAB/'mem0-home'),MEM0_TELEMETRY='false',CUDA_VISIBLE_DEVICES='',TOKENIZERS_PARALLELISM='false',HF_HUB_DISABLE_TELEMETRY='1')
 for k in ['OPENROUTER_API_KEY','LANGFUSE_PUBLIC_KEY','LANGFUSE_SECRET_KEY','OPENAI_API_KEY'] :os.environ.pop(k,None)
 os.environ['OPENAI_API_KEY']='local-unused';os.environ['OPENAI_BASE_URL']=BASE

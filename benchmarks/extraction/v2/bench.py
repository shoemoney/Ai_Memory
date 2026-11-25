"""Frozen constrained writer protocol, per-item durable checkpoints."""
import concurrent.futures,hashlib,json,os,random,threading,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LOCK=json.loads((ROOT/'protocol-lock.json').read_text())
OUTLOCK=threading.Lock()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_lock():
 assert digest(ROOT/'writer_prompt.txt')==LOCK['prompt_sha256']
 assert digest(ROOT/'writer_schema.json')==LOCK['schema_sha256']
 manifest=json.loads((ROOT/'data/manifest.json').read_text())
 assert digest(ROOT/'data/sample.json')==manifest['sample_sha256']
def append(path,row):
 with OUTLOCK,path.open('a')as out:out.write(json.dumps(row)+'\n');out.flush();os.fsync(out.fileno())
def read(path):
 if not path.exists():return []
 rows=[]
 with path.open('rb+')as f:
  while True:
   pos=f.tell();line=f.readline()
   if not line:break
   try:rows.append(json.loads(line))
   except json.JSONDecodeError:
    if f.read():raise
    f.truncate(pos);break
 return rows

def request(body,host=None):
 for attempt in range(10):
  if host:host.ensure()
  start=time.perf_counter()
  try:
   q=urllib.request.Request(os.environ.get('BASE_URL','http://localhost:39745/v1')+'/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
   with urllib.request.urlopen(q,timeout=240)as response:raw=json.load(response)
   return raw,time.perf_counter()-start
  except (OSError,TimeoutError,ValueError)as e:
   append(ROOT/'results/transport-attempts.jsonl',{'utc':time.time(),'attempt':attempt,'error_type':type(e).__name__,'elapsed':time.perf_counter()-start})
   if attempt==9:raise
   time.sleep(2)

def writer_body(item,seed,repeat=1.0):
 check_lock()
 return {'model':'writer','messages':[{'role':'system','content':(ROOT/'writer_prompt.txt').read_text()},{'role':'user','content':json.dumps({'speaker':item['speaker'],'turn':item['text']})}], 'temperature':0,'seed':seed,'max_tokens':LOCK['max_tokens'],'cache_prompt':False,'chat_template_kwargs':{'enable_thinking':False},'repeat_penalty':repeat,'response_format':{'type':'json_schema','json_schema':{'name':'memory_facts','strict':True,'schema':json.loads((ROOT/'writer_schema.json').read_text())}}}

def unique_object(pairs):
 result={}
 for k,v in pairs:
  if k in result:raise ValueError('Duplicate JSON key')
  result[k]=v
 return result

def validate(raw):
 try:
  c=raw['choices'][0];m=c['message'];value=json.loads(m['content'],object_pairs_hook=unique_object)
  assert c['finish_reason']=='stop' and not m.get('reasoning_content') and not m.get('refusal')
  assert isinstance(value,list) and len(value)<=12
  assert len({json.dumps(v,sort_keys=True)for v in value})==len(value)
  for v in value:
   assert isinstance(v,dict) and set(v)=={'fact','subject','category','date'}
   assert all(isinstance(x,str)and len(x)>0 for x in v.values())
   assert v['category']in ['preference','personal detail','event','plan','relationship','work','health','other']
  return True,value,None
 except (ValueError,TypeError,KeyError,AssertionError)as e:return False,[],type(e).__name__

def generate_arm(host,arm,model,seed):
 path=ROOT/'results/writers'/f'{arm}.jsonl';path.parent.mkdir(exist_ok=True)
 done={(r['seed'],r['id'])for r in read(path)}
 items=json.loads((ROOT/'data/sample.json').read_text());random.Random(seed).shuffle(items)
 items=[r for r in items if (seed,r['id'])not in done]
 repeat=1.1 if arm.endswith('-repeat-1.1')else 1.0
 def one(item):
  b=writer_body(item,seed,repeat);raw,sec=request(b,host);valid,parsed,error=validate(raw)
  row={'serving_hardware':host.hardware,'serving_instance':host.instance,'runtime_sha256':digest(ROOT/'runtime-lock.json'),'arm':arm,'model':model['id'],'seed':seed,'id':item['id'],'request':b,'response':raw,'seconds':sec,'valid':valid,'parsed':parsed,'validation_error':error,'protocol_sha256':digest(ROOT/'protocol-lock.json'),'sample_sha256':digest(ROOT/'data/sample.json')}
  append(path,row);print('writer',arm,seed,item['id'],valid,round(sec,3),flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=LOCK['slots'])as pool:list(pool.map(one,items))

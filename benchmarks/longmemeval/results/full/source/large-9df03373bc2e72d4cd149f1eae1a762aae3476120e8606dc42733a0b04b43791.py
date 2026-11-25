"""Standard-haystack experiment. Every result is checkpointed atomically."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LAB=Path(os.environ.get('LAB_DIR','/var/tmp/membench-longmemeval'))
OUT=ROOT/'results/full'
for p in (LAB,OUT,OUT/'items',OUT/'answers',OUT/'judges'):p.mkdir(parents=True,exist_ok=True)
os.environ.update(HF_HOME=str(LAB/'hf'),MEM0_DIR=str(LAB/'mem0'),MEM0_TELEMETRY='false',CUDA_VISIBLE_DEVICES='',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='8')
os.environ.pop('OPENROUTER_API_KEY',None)
import collections,hashlib,json,random,re,sqlite3,time,urllib.request,shutil
import numpy as np
import torch
from openai import OpenAI,APIError,APIConnectionError
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from mem0 import Memory
from qdrant_client import QdrantClient
from judge_prompt import get_anscheck_prompt
SEED=20261122
REV='98d7416c24c778c2fee6e6f3006e7a073259d48f'
MODEL_REV='ff12eb39da2cd9b3b0f4b4f9ffb274603f05bb29'
EMBED_REV='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
BASE=os.environ.get('BASE_URL','http://localhost:39711/v1')
if not BASE.startswith('http://localhost:'):raise ValueError('localhost tunnel required')
END=float(os.environ.get('DEADLINE_EPOCH',time.time()+34200))
MAX_CONTEXT=8192
METHODS=['full-standard','bm25-standard','dense-standard','mem0-raw-standard','full-oracle']
client=OpenAI(base_url=BASE,api_key='local-only',timeout=900,max_retries=0)
CURRENT={}
def clean(text):
 return (text or '').split('<end_of_turn>',1)[0].strip()

def write(path,data):
 p=Path(path);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(data,ensure_ascii=False,indent=2));t.replace(p)
def log(name,data):
 with (OUT/name).open('a') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n')
def budget():
 if time.time()>=END:raise TimeoutError('wall-clock budget exhausted')
def download(name):
 p=LAB/name
 if not p.exists():p.write_bytes(urllib.request.urlopen(f'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/{REV}/{name}').read())
 return json.loads(p.read_text())
def stratum(x):return 'abstention' if x['question_id'].endswith('_abs') else x['question_type']
def select(data):
 groups=collections.defaultdict(list)
 for x in data:groups[stratum(x)].append(x)
 counts={k:int(len(v)*300/len(data)) for k,v in groups.items()}
 rest=300-sum(counts.values())
 for k in sorted(groups,key=lambda k:(-(len(groups[k])*300/len(data)-counts[k]),k))[:rest]:counts[k]+=1
 rng=random.Random(SEED);chosen=[]
 for k in sorted(groups):chosen.extend(rng.sample(sorted(groups[k],key=lambda x:x['question_id']),counts[k]))
 rng.shuffle(chosen)
 return chosen,counts

def history(x):
 return [{'session_id':sid,'date':date,'dialogue':[{'role':t['role'],'content':t['content']} for t in sess]} for sid,date,sess in sorted(zip(x['haystack_session_ids'],x['haystack_dates'],x['haystack_sessions']),key=lambda a:a[1])]
def make_chunks(hist):
 r=[]
 for si,s in enumerate(hist):
  for ti,t in enumerate(s['dialogue']):
   for offset in range(0,len(t['content']),700):
    text=t['content'][offset:offset+800]
    r.append({'session_id':s['session_id'],'date':s['date'],'session':si,'turn':ti,'offset':offset,'role':t['role'],'text':text})
 return r
def stored(d):return d['date']+' '+d['role']+': '+d['text']
def prompt(x,context):
 return ('Answer using only the dated conversation history below. Account for updates and relative dates. If information is insufficient, say so. Give a concise but complete answer.\nQuestion date: '+x['question_date']+'\nHistory:\n'+json.dumps(context,ensure_ascii=False)+'\nQuestion: '+x['question'])

def request(messages,max_tokens,phase,seed=SEED):
 while True:
  budget()
  pressure=LAB/'pressure.json'
  if pressure.exists() and not json.loads(pressure.read_text()).get('ready',False):time.sleep(5);continue
  started=time.monotonic()
  try:
   response=client.chat.completions.create(model='default_model',messages=messages,temperature=0,seed=seed,max_tokens=max_tokens,stop=['<end_of_turn>'])
   raw=response.model_dump();raw_text=response.choices[0].message.content;text=clean(raw_text)
   log('requests.jsonl',{'item':dict(CURRENT),'phase':phase,'seed':seed,'temperature':0,'stop':['<end_of_turn>'],'messages':messages,'response':raw,'seconds':time.monotonic()-started})
   return {'text':text,'raw_text':raw_text,'raw':raw,'seconds':time.monotonic()-started}
  except (APIError,APIConnectionError) as e:
   log('transport-errors.jsonl',{'item':dict(CURRENT),'phase':phase,'error_type':type(e).__name__,'retry':'same checkpointed call after pressure/server recovery'})
   time.sleep(5)

def judge(x,hyp,method):
 votes=[];calls=[]
 p=get_anscheck_prompt(x['question_type'],x['question'],x['answer'],hyp,abstention=x['question_id'].endswith('_abs'))
 for n in range(3):
  file=OUT/'judges'/f"{x['question_id']}--{method}--{n}.json"
  if file.exists():call=json.loads(file.read_text())
  else:
   call=request([{'role':'user','content':p}],10,'judge',SEED+n)
   write(file,call)
  text=clean(call['text']).lower()
  if not re.fullmatch(r'(yes|no)[.!]?',text):raise ValueError('nonbinary judge output: '+text)
  votes.append(text.startswith('yes'));calls.append(call)
 return {'correct':sum(votes)>=2,'votes':votes,'calls':calls,'prompt':p}

class CopyableClient(QdrantClient):
 def __deepcopy__(self,memo):return self
class CachedEmbedding:
 def __init__(self,encoded,query,vec):self.encoded=encoded;self.query=query;self.vec=vec
 def embed(self,text,memory_action=None):
  if text==self.query:return self.vec.tolist()
  return self.encoded[text].tolist()

def main():
 executed_source=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 source_dir=OUT/'source';source_dir.mkdir(exist_ok=True)
 (source_dir/('large-'+executed_source+'.py')).write_bytes(Path(__file__).read_bytes())
 torch.set_num_threads(8)
 standard=download('longmemeval_s_cleaned.json');oracle={x['question_id']:x for x in download('longmemeval_oracle.json')}
 selected,counts=select(standard)
 tok_path=snapshot_download('mlx-community/gemma-2-9b-it-4bit',revision=MODEL_REV,allow_patterns=['tokenizer*','special_tokens_map.json','config.json'])
 tokenizer=AutoTokenizer.from_pretrained(tok_path)
 tokenizer.model_max_length=10**9
 def ntokens(text):
  return len(tokenizer.apply_chat_template([{'role':'user','content':text}],tokenize=True,add_generation_prompt=True))
 plan=[];inventory=[]
 signature=hashlib.sha256((MODEL_REV+REV+'oracle-own-question-date-v1'+prompt({'question_date':'DATE','question':'QUESTION'},[])+json.dumps([x['question_id'] for x in selected])).encode()).hexdigest()
 cp=OUT/'token-counts.json'
 cache=json.loads(cp.read_text()) if cp.exists() else {}
 known=cache.get('items',{}) if cache.get('signature')==signature else {}
 for x in selected:
  budget();qid=x['question_id']
  if qid in known:inv=known[qid]
  else:
   full=ntokens(prompt(x,history(x)));upper=ntokens(prompt(oracle[qid],history(oracle[qid])))
   inv={'question_id':qid,'stratum':stratum(x),'standard_sessions':len(x['haystack_sessions']),'standard_prompt_tokens':full,'oracle_prompt_tokens':upper}
   known[qid]=inv;write(cp,{'signature':signature,'items':known})
  inventory.append(inv)
  for method in METHODS:
   if method=='full-standard' and inv['standard_prompt_tokens']+512>MAX_CONTEXT:continue
   if method=='full-oracle' and inv['oracle_prompt_tokens']+512>MAX_CONTEXT:continue
   plan.append((qid,method))
 audit=random.Random(SEED+40).sample(sorted(plan),40)
 write(OUT/'audit-plan.json',{'seed':SEED+40,'pairs':audit,'drawn_before_review':True,'selection_uses_no_answers_or_labels':True,'reviewer_requirement':'direct item-by-item review, not another automatic judge'})
 write(OUT/'manifest.json',{'seed':SEED,'n':300,'sampling':'proportional largest-remainder allocation over six non-abstention types plus abstention; sample sorted IDs then shuffle','strata_counts':counts,'dataset_revision':REV,'dataset_license':'MIT','standard_file_sha256':hashlib.sha256((LAB/'longmemeval_s_cleaned.json').read_bytes()).hexdigest(),'oracle_file_sha256':hashlib.sha256((LAB/'longmemeval_oracle.json').read_bytes()).hexdigest(),'model':'mlx-community/gemma-2-9b-it-4bit','model_revision':MODEL_REV,'context_tokens':MAX_CONTEXT,'embedding_model':'sentence-transformers/all-MiniLM-L6-v2','embedding_revision':EMBED_REV,'mem0_infer':False,'judge':'official prompts, three temperature-zero calls with seeds 20261122/23/24, majority vote; deterministic repetitions are not independent votes','items':inventory,'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'large.py',ROOT/'judge_prompt.py']}})
 # Judge calibration uses known controls and the three resolved pilot verdicts before benchmark scoring.
 controls=[('single-session-user','What color is the flag?','red','red',False,True),('single-session-user','What color is the flag?','red','blue',False,False),('single-session-user','What is the missing code?','No code supplied.','There is insufficient information.',True,True)]
 pilot=[json.loads(v) for v in (ROOT/'results/items.jsonl').read_text().splitlines()]
 controls.extend((v['question_type'],v['question'],v['reference'],v['hypothesis'],False,True) for v in pilot if v['question_id']=='06878be2')
 cpath=OUT/'judge-calibration.json'
 if not cpath.exists():
  cs=[]
  for i,(kind,q,ans,hyp,ab,expected) in enumerate(controls):
   CURRENT.clear();CURRENT.update(question_id='calibration-'+str(i),method='judge-calibration')
   p=get_anscheck_prompt(kind,q,ans,hyp,abstention=ab)
   call=request([{'role':'user','content':p}],10,'calibration')
   cs.append({'expected':expected,'actual':call['text'].lower().startswith('yes'),'response':call['text'],'prompt':p})
  write(cpath,cs)
  if not all(v['expected']==v['actual'] for v in cs):raise RuntimeError('judge calibration failed; do not launch large scoring')
 embed_path=snapshot_download('sentence-transformers/all-MiniLM-L6-v2',revision=EMBED_REV,ignore_patterns=['onnx/*','openvino/*','*.h5','*.ot'])
 embedder=SentenceTransformer(embed_path,device='cpu');embedder.max_seq_length=256
 db=sqlite3.connect(str(LAB/'embedding-cache.sqlite'))
 db.execute('CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY,vector BLOB)')
 def encode(texts):
  result={};missing=[]
  for text in dict.fromkeys(texts):
   h=hashlib.sha256(text.encode()).hexdigest();r=db.execute('SELECT vector FROM cache WHERE key=?',(h,)).fetchone()
   if r:result[text]=np.frombuffer(r[0],dtype=np.float32)
   else:missing.append(text)
  if missing:
   vecs=embedder.encode(missing,batch_size=96,normalize_embeddings=True,show_progress_bar=False)
   for text,vec in zip(missing,vecs):
    result[text]=vec;db.execute('INSERT OR REPLACE INTO cache VALUES(?,?)',(hashlib.sha256(text.encode()).hexdigest(),vec.astype(np.float32).tobytes()))
   db.commit()
  return result
 audit_ids={p[0] for p in audit}
 selected.sort(key=lambda x:(x['question_id'] not in audit_ids,next(i for i,v in enumerate(inventory) if v['question_id']==x['question_id'])))
 for x in selected:
  budget();qid=x['question_id'];hist=history(x)
  methods_done={m for m in METHODS if (OUT/'items'/f'{qid}--{m}.json').exists()}
  if len(methods_done)==len(METHODS):continue
  docs=None;encoded=None;query_vec=None
  for method in METHODS:
   file=OUT/'items'/f'{qid}--{method}.json'
   if file.exists():continue
   budget();CURRENT.clear();CURRENT.update(question_id=qid,method=method)
   target=oracle[qid] if method=='full-oracle' else x
   print(json.dumps(CURRENT),flush=True)
   started=time.monotonic();inv=next(v for v in inventory if v['question_id']==qid)
   if method.startswith('full-'):
    length=inv['standard_prompt_tokens' if method=='full-standard' else 'oracle_prompt_tokens']
    if length+512>MAX_CONTEXT:
     write(file,{'question_id':qid,'method':method,'stratum':stratum(x),'status':'context-does-not-fit','source_sha256':executed_source,'prompt_tokens':length,'native_context':MAX_CONTEXT});continue
    context=hist if method=='full-standard' else history(oracle[qid])
   else:
    if docs is None:docs=make_chunks(hist)
    texts=[stored(d) for d in docs]
    if method=='bm25-standard':
     bm=BM25Okapi([re.findall(r'\w+',t.lower()) for t in texts]);scores=bm.get_scores(re.findall(r'\w+',x['question'].lower()))
     indices=sorted(range(len(docs)),key=lambda i:(-float(scores[i]),i))[:10]
    else:
     if encoded is None:
      encoded=encode(texts+[x['question']]);query_vec=encoded[x['question']]
     if method=='dense-standard':
      scores=np.stack([encoded[t] for t in texts])@query_vec
      indices=sorted(range(len(docs)),key=lambda i:(-float(scores[i]),i))[:10]
     else:
      qc=CopyableClient(':memory:')
      memory=Memory.from_config({'version':'v1.1','history_db_path':':memory:','vector_store':{'provider':'qdrant','config':{'client':qc,'collection_name':'experiment','embedding_model_dims':384,'path':str(LAB/'unused-qdrant')}},'embedder':{'provider':'huggingface','config':{'model':embed_path,'embedding_dims':384,'model_kwargs':{'device':'cpu'}}},'llm':{'provider':'openai','config':{'model':'default_model','api_key':'local-only','openai_base_url':BASE,'temperature':0}}})
      cached_embedding=CachedEmbedding(encoded,x['question'],query_vec)
      cached_embedding.config=memory.embedding_model.config
      memory.embedding_model=cached_embedding
      events=memory.add([{'role':d['role'],'content':t} for d,t in zip(docs,texts)],user_id=qid,infer=False)
      count=qc.count('experiment',exact=True).count
      assert count==len(docs)==len(events['results'])
      retrieved=memory.search(x['question'],user_id=qid,limit=10,threshold=None)['results']
      lookup={t:i for i,t in reversed(list(enumerate(texts)))}
      indices=[lookup[v['memory']] for v in retrieved]
      log('memory-ingestion.jsonl',{'question_id':qid,'infer':False,'input_sessions':len(hist),'input_chunks':len(docs),'added':len(events['results']),'stored_count':count,'all_chunk_sha256':[hashlib.sha256(t.encode()).hexdigest() for t in texts],'retrieved_scores':[v['score'] for v in retrieved]})
      qc.close();memory.db.connection.close()
    context=[docs[i] for i in sorted(indices)]
   prep=time.monotonic()-started
   p=prompt(target,context);token_count=ntokens(p)
   while token_count+512>MAX_CONTEXT and not method.startswith('full-') and indices:
    indices.pop();context=[docs[i] for i in sorted(indices)];p=prompt(target,context);token_count=ntokens(p)
   if token_count+512>MAX_CONTEXT:raise RuntimeError('context overflow; no full-history truncation')
   ap=OUT/'answers'/f'{qid}--{method}.json'
   if ap.exists():
    answer=json.loads(ap.read_text());context=answer['context'];p=answer['prompt'];token_count=answer['prompt_tokens']
   else:
    answer=request([{'role':'user','content':p}],512,'answer')
    answer.update(context=context,prompt=p,prompt_tokens=token_count);write(ap,answer)
   judged=judge(x,answer['text'],method)
   write(file,{'question_id':qid,'question_type':x['question_type'],'stratum':stratum(x),'method':method,'status':'scored','source_sha256':executed_source,'question':x['question'],'reference':x['answer'],'question_date':target['question_date'],'date_variant':('oracle' if method=='full-oracle' else 'standard'),'source_session_count':len(hist),'context':context,'prompt_tokens':token_count,'hypothesis':answer['text'],'answer':answer,'judge':judged,'correct':judged['correct'],'prep_seconds':prep})
  from summarize_large import summarize
  summarize()
 print('COMPLETED_ALL_SELECTED_QUESTIONS',flush=True)
if __name__=='__main__':
 try:main()
 finally:
  from summarize_large import summarize
  summarize()

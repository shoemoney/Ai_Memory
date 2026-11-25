"""Public, label-based retrieval evaluation. All model/cache/data files are scratch."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LAB=Path(os.environ.get('LAB_DIR','/data/scratch/membench/retrieval-methods'))
OUT=ROOT/'results'
for p in [LAB,OUT]:p.mkdir(exist_ok=True,parents=True)
os.environ.update(HF_HOME=str(LAB/'hf'),UV_CACHE_DIR=str(LAB/'uv-cache'),PIP_CACHE_DIR=str(LAB/'pip-cache'),TORCH_HOME=str(LAB/'torch-cache'),TRITON_CACHE_DIR=str(LAB/'triton-cache'),CUDA_CACHE_PATH=str(LAB/'cuda-cache'),TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='4')
import argparse,hashlib,json,random,re,time,zipfile,io,subprocess,sys,math,collections,shutil
import requests
import numpy as np
SEED=20261122
REV_LM='98d7416c24c778c2fee6e6f3006e7a073259d48f'
EMBED=('sentence-transformers/all-MiniLM-L6-v2','1110a243fdf4706b3f48f1d95db1a4f5529b4d41')
RERANK=('cross-encoder/ms-marco-MiniLM-L-6-v2','233902d25c440f23af6f7d6e94d2946bac0bee0a')
METHODS=['bm25','dense','hybrid_rrf','hybrid_rerank','context_bm25','context_dense','context_hybrid_rrf','context_hybrid_rerank']
def save(p,x):
 p=Path(p); t=p.with_suffix(p.suffix+'.tmp');
 with t.open('w') as f:json.dump(x,f,ensure_ascii=False)
 t.replace(p)
def append(p,x):
 with Path(p).open('a') as f:f.write(json.dumps(x,ensure_ascii=False)+'\n');f.flush()
def readlines(p):return [json.loads(l) for l in Path(p).read_text().splitlines()]
def fetch(url,path):
 if not path.exists():
  with requests.get(url,stream=True,timeout=(20,300)) as r:
   r.raise_for_status()
   with path.with_suffix('.part').open('wb') as f:
    for b in r.iter_content(4*1024*1024):f.write(b)
   path.with_suffix('.part').replace(path)
 return hashlib.sha256(path.read_bytes()).hexdigest()
def words(s):return re.findall(r'\w+',s.lower())
def chunks(text,size=180,overlap=30):
 w=text.split();return [' '.join(w[i:i+size]) for i in range(0,len(w),size-overlap)] or ['']
def prepare():
 manifest={'seed':SEED,'hardware_class':'32-thread x86 CPU, 8 GB NVIDIA RTX 3070 Ti GPU','embedding':EMBED,'reranker':RERANK,'context_model':['bartowski/Qwen_Qwen3.5-4B-GGUF','4168f45a16a1290d65a4ec0fa312ae917a4c15d6','Q4_K_M'],'sources':{},'chunk_words':180,'overlap_words':30}
 for name in ['scifact','nfcorpus']:
  import pyarrow.parquet as pq
  revisions={'scifact':('b3b5335604bf5ee3c4447671af975ea25143d4f5','2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029'),'nfcorpus':('b5026a0e96e8a7ac4f95f482a596389289d46269','a451b3b26d3ae1358f259c1a3a4dd61fcea35a65')}
  dr,qr=revisions[name];hashes={}
  for kind in ['corpus','queries']:
   url=f'https://huggingface.co/datasets/BeIR/{name}/resolve/{dr}/{kind}/{kind}-00000-of-00001.parquet'
   path=LAB/(name+'.'+kind+'.parquet');hashes[kind]=fetch(url,path)
  corpus=pq.read_table(LAB/(name+'.corpus.parquet')).to_pylist()
  queries={x['_id']:x['text'] for x in pq.read_table(LAB/(name+'.queries.parquet')).to_pylist()}
  qpath=LAB/(name+'.qrels.tsv');hashes['qrels']=fetch(f'https://huggingface.co/datasets/BeIR/{name}-qrels/resolve/{qr}/test.tsv',qpath)
  labels={}
  for l in qpath.read_text().splitlines()[1:]:
   q,d,score=l.split('\t');score=int(score)
   if score>0:labels.setdefault(q,{})[d]=score
  docs=[]
  for d in corpus:
   full=(d['title']+'\n'+d['text']).strip()
   for i,c in enumerate(chunks(full)):docs.append({'id':d['_id']+':'+str(i),'doc':d['_id'],'text':c,'context':full})
  qs=[{'id':q,'text':queries[q],'relevant':labels[q]} for q in sorted(labels)]
  save(LAB/(name+'.data.json'),{'docs':docs,'queries':qs})
  manifest['sources'][name]={'url':f'https://huggingface.co/datasets/BeIR/{name}/tree/{dr}','revision':dr,'qrels_revision':qr,'sha256':hashes,'license':'CC BY-SA 4.0 (BEIR dataset card; original SciFact annotations separately CC BY-NC 2.0)' if name=='scifact' else 'CC BY-SA 4.0','queries':len(qs),'documents':len(corpus),'chunks':len(docs),'sampling':'all test queries with positive qrels; full corpus; document-level scoring after chunk deduplication'}
  print('prepared',name,len(qs),len(docs),flush=True)
 p=LAB/'longmem.json';sha=fetch(f'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/{REV_LM}/longmemeval_s_cleaned.json',p)
 raw=json.loads(p.read_text()); eligible=[x for x in raw if not x['question_id'].endswith('_abs') and x['answer_session_ids']]
 selected=random.Random(SEED).sample(sorted(eligible,key=lambda x:x['question_id']),150)
 # Question-specific standard haystacks. Session labels and chunks remain separate.
 session_store={};qs=[]
 for x in selected:
  ids=[];relevant_keys=set()
  for sid,date,session in zip(x['haystack_session_ids'],x['haystack_dates'],x['haystack_sessions']):
   # Some tasks reuse IDs: qualify by full content hash for unambiguous corpus lookup.
   full=date+'\n'+'\n'.join(t['role']+': '+t['content'] for t in session)
   key=hashlib.sha256(full.encode()).hexdigest()[:20]
   session_store[key]={'id':key,'session_id':sid,'text':full};ids.append(key)
   if sid in x['answer_session_ids']:relevant_keys.add(key)
  rel={key:1 for key in relevant_keys}
  assert rel
  qs.append({'id':x['question_id'],'text':x['question'],'relevant':rel,'scope':ids,'type':x['question_type']})
 docs=[]
 for key,v in sorted(session_store.items()):
  for i,c in enumerate(chunks(v['text'])):docs.append({'id':key+':'+str(i),'doc':key,'text':c})
 save(LAB/'longmemeval.data.json',{'docs':docs,'queries':qs,'contexts':{k:v['text'] for k,v in session_store.items()}})
 manifest['sources']['longmemeval']={'url':f'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/tree/{REV_LM}','revision':REV_LM,'sha256':sha,'license':'MIT','eligible_queries':len(eligible),'selected_question_ids':[q['id'] for q in qs],'question_type_counts':dict(collections.Counter(q['type'] for q in qs)),'queries':len(qs),'documents':len(session_store),'chunks':len(docs),'sampling':'150 seeded uniform answerable non-abstention standard-s questions; original question-specific haystack only; answer_session_ids are binary session-level qrels; no answer text used'}
 save(OUT/'manifest.json',manifest);print('prepared longmemeval',len(qs),len(docs),flush=True)
 from prepare_locomo import prepare_locomo
 prepare_locomo()
def load(name):return json.loads((LAB/(name+'.data.json')).read_text())
def gpu_usage():
 raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],text=True)
 processes={}
 for line in raw.splitlines():
  fields=line.split(',')
  if len(fields)==2 and fields[0].strip().isdigit() and fields[1].strip().isdigit():processes[int(fields[0])]=int(fields[1])
 free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())
 return processes,free

def wait_gpu(required_mib=6656):
 wait_started=time.monotonic();timeout=float(os.environ.get('GPU_WAIT_TIMEOUT','0'))
 # The small preexisting embedding service is explicitly permitted, and
 # unrelated graphics jobs. Other wave-model processes remain blockers.
 while True:
  processes,free=gpu_usage();blockers=[]
  allowed={int(x) for x in os.environ.get('ALLOWED_GPU_PIDS','').split(',') if x}
  for pid in processes:
   try:comm=Path('/proc',str(pid),'comm').read_text().strip()
   except OSError:continue
   if pid in allowed or comm.startswith('Godot'):continue
   blockers.append(pid)
  if not blockers and free>=required_mib:break
  if timeout and time.monotonic()-wait_started>=timeout:raise TimeoutError('GPU did not have the required free memory within the configured wait')
  print('waiting for wave-model turn or',required_mib,'MiB free GPU memory',flush=True);time.sleep(10)
 append(OUT/'hardware.jsonl',{'event':'gpu_available','time':time.time(),'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.used,memory.free','--format=csv,noheader'],text=True).strip(),'allowed_resident_service_mib':sum(processes.get(pid,0) for pid in allowed)})
def retrieval_device(required_mib):
 device=os.environ.get('RETRIEVAL_DEVICE','auto')
 if device=='cuda':wait_gpu(required_mib);return 'cuda'
 if device=='cpu':return 'cpu'
 if device!='auto':raise ValueError('RETRIEVAL_DEVICE must be auto, cpu or cuda')
 try:
  processes,free=gpu_usage();allowed={int(x) for x in os.environ.get('ALLOWED_GPU_PIDS','').split(',') if x};blockers=[]
  for pid in processes:
   try:comm=Path('/proc',str(pid),'comm').read_text().strip()
   except OSError:continue
   if pid not in allowed and not comm.startswith('Godot'):blockers.append(pid)
  device='cuda' if free>=required_mib and not blockers else 'cpu'
 except (OSError,subprocess.SubprocessError):device='cpu'
 append(OUT/'hardware.jsonl',{'event':'retrieval_device_choice','device':device,'time':time.time()})
 return device
def embed(names,context=False):
 device=retrieval_device(2048)
 import torch
 from sentence_transformers import SentenceTransformer
 torch.set_num_threads(4)
 model=SentenceTransformer(EMBED[0],revision=EMBED[1],device=device);model.max_seq_length=256
 for name in names:
  data=load(name);prefixes={x['id']:x['prefix'] for x in readlines(OUT/(name+'.prefixes.jsonl'))} if context else {}
  suffix='context' if context else 'base'
  p=LAB/(name+'.'+suffix+'.npy')
  if not p.exists():
   # Batch checkpoints avoid re-encoding finished blocks after a restart.
   blocks=[]
   for start in range(0,len(data['docs']),512):
    bp=LAB/(name+'.'+suffix+'.'+str(start)+'.npy')
    if not bp.exists():
     ds=data['docs'][start:start+512]
     text=[(prefixes[d['id']]+'\n' if context else '')+d['text'] for d in ds]
     np.save(bp,model.encode(text,batch_size=64,normalize_embeddings=True,show_progress_bar=False))
    blocks.append(np.load(bp))
   np.save(p,np.concatenate(blocks))
  qp=LAB/(name+'.queries.npy')
  if not qp.exists():np.save(qp,model.encode([q['text'] for q in data['queries']],batch_size=64,normalize_embeddings=True))
  print('embedded',name,suffix,len(data['docs']),flush=True)
 del model
 torch.cuda.empty_cache()
def dedup(ranking,docs,k=150):
 out=[];seen=set()
 for i in ranking:
  doc=docs[int(i)]['doc']
  if doc not in seen:out.append(int(i));seen.add(doc)
  if len(out)==k:break
 return out
def rrf(a,b,k=60):
 scores={}
 for ranked in [a,b]:
  for r,i in enumerate(ranked,1):scores[i]=scores.get(i,0)+1/(k+r)
 return sorted(scores,key=lambda i:(-scores[i],i))
def scores(ranked,rel):
 r=[rel.get(d,0) for d in ranked]
 def recall(k):return len(set(ranked[:k])&set(rel))/len(rel)
 dcg=sum(v/math.log2(i+2) for i,v in enumerate(r[:10]))
 ideal=sum(v/math.log2(i+2) for i,v in enumerate(sorted(rel.values(),reverse=True)[:10]))
 return {'recall5':recall(5),'recall20':recall(20),'ndcg10':dcg/ideal,'failure20':float(not any(r[:20])),'ap150':sum(sum(v>0 for v in r[:i+1])/(i+1) for i,x in enumerate(r[:150]) if x>0)/len(rel)}
def keyword(names,context=False):
 from rank_bm25 import BM25Okapi
 for name in names:
  data=load(name);docs=data['docs'];suffix='context' if context else 'base'
  pref={x['id']:x['prefix'] for x in readlines(OUT/(name+'.prefixes.jsonl'))} if context else {}
  tokens=[words((pref[d['id']]+'\n' if context else '')+d['text']) for d in docs]
  global_bm=BM25Okapi(tokens) if not any('scope' in q for q in data['queries']) else None
  path=OUT/(name+'.'+suffix+'.bm25.jsonl');done={x['id'] for x in readlines(path)} if path.exists() else set()
  for q in data['queries']:
   if q['id'] in done:continue
   scope=set(q['scope']) if 'scope' in q else None
   ix=np.array([i for i,d in enumerate(docs) if d['doc'] in scope]) if scope else np.arange(len(docs))
   bm=global_bm if global_bm else BM25Okapi([tokens[i] for i in ix])
   t=time.monotonic();kw=bm.get_scores(words(q['text']));a=dedup(ix[np.lexsort((ix,-kw))],docs)
   append(path,{'id':q['id'],'ranked':[docs[i]['id'] for i in a],'metrics':scores([docs[i]['doc'] for i in a],q['relevant']),'seconds':time.monotonic()-t})
  print('keyword',name,len(data['queries']),flush=True)
def retrieve(names,context=False):
 from rank_bm25 import BM25Okapi
 for name in names:
  data=load(name);docs=data['docs'];pref={x['id']:x['prefix'] for x in readlines(OUT/(name+'.prefixes.jsonl'))} if context else {}
  suffix='context' if context else 'base';vs=np.load(LAB/(name+'.'+suffix+'.npy'));qv=np.load(LAB/(name+'.queries.npy'))
  cached={r['id']:r for r in readlines(OUT/(name+'.'+suffix+'.bm25.jsonl'))} if (OUT/(name+'.'+suffix+'.bm25.jsonl')).exists() else {}
  lookup={d['id']:i for i,d in enumerate(docs)}
  tokenized=[words((pref[d['id']]+'\n' if context else '')+d['text']) for d in docs] if len(cached)!=len(data['queries']) else None
  global_bm=BM25Okapi(tokenized) if not any('scope' in q for q in data['queries']) and tokenized is not None else None
  path=OUT/(name+'.'+suffix+'.rankings.jsonl');done={x['id'] for x in readlines(path)} if path.exists() else set()
  for qi,q in enumerate(data['queries']):
   if q['id'] in done:continue
   scope=set(q['scope']) if 'scope' in q else None
   ix=np.array([i for i,d in enumerate(docs) if d['doc'] in scope]) if scope else np.arange(len(docs))
   if q['id'] in cached:a=[lookup[i] for i in cached[q['id']]['ranked']]
   else:
    bm=global_bm if global_bm else BM25Okapi([tokenized[i] for i in ix])
    kw=bm.get_scores(words(q['text']));a=dedup(ix[np.lexsort((ix,-kw))],docs)
   ds=vs[ix]@qv[qi];b=dedup(ix[np.lexsort((ix,-ds))],docs)
   # Fuse at chunk level after selecting one highest-ranked chunk per document in each leg.
   # Cross-leg duplicates must fuse by document ID, not chunk ID.
   reps={};da=[];db=[]
   for ranking,target in [(a,da),(b,db)]:
    for i in ranking:target.append(docs[i]['doc']);reps.setdefault(docs[i]['doc'],i)
   merged=rrf(da,db)[:150]  # rrf supports string IDs too
   hybrid=[reps[d] for d in merged]
   rankings={'bm25':a,'dense':b,'hybrid_rrf':hybrid}
   row={'id':q['id'],'rankings':{k:[docs[i]['id'] for i in v] for k,v in rankings.items()},'metrics':{k:scores([docs[i]['doc'] for i in v],q['relevant']) for k,v in rankings.items()}}
   append(path,row)
  print('retrieved',name,suffix,flush=True)
def rerank(names,context=False):
 device=retrieval_device(3072)
 import torch
 from sentence_transformers import CrossEncoder
 torch.set_num_threads(4)
 model=CrossEncoder(RERANK[0],revision=RERANK[1],device=device,max_length=512)
 for name in names:
  data=load(name);docs={d['id']:d for d in data['docs']};qs={q['id']:q for q in data['queries']};suffix='context' if context else 'base'
  pref={x['id']:x['prefix'] for x in readlines(OUT/(name+'.prefixes.jsonl'))} if context else {}
  path=OUT/(name+'.'+suffix+'.rerank.jsonl');done={x['id'] for x in readlines(path)} if path.exists() else set()
  for row in readlines(OUT/(name+'.'+suffix+'.rankings.jsonl')):
   if row['id'] in done:continue
   q=qs[row['id']];pool=row['rankings']['hybrid_rrf'];pairs=[(q['text'],(pref[i]+'\n' if context else '')+docs[i]['text']) for i in pool]
   t=time.monotonic();s=model.predict(pairs,batch_size=64,show_progress_bar=False)
   ranked=sorted(zip(pool,map(float,s)),key=lambda x:(-x[1],x[0]))
   ids=[i for i,s in ranked];append(path,{'id':q['id'],'ranked':ids,'scores':[s for i,s in ranked],'metrics':scores([docs[i]['doc'] for i in ids],q['relevant']),'seconds':time.monotonic()-t})
  print('reranked',name,suffix,flush=True)
 del model;torch.cuda.empty_cache()
class GPUHeadroomError(RuntimeError):
 pass

def prefix_run(names,slots):
 context_tokens=int(os.environ.get('PREFIX_CTX_PER_SLOT','8192'))
 gpu_layers=int(os.environ.get('PREFIX_GPU_LAYERS','99'))
 batch_tokens=int(os.environ.get('PREFIX_BATCH_TOKENS','2048'));ubatch_tokens=int(os.environ.get('PREFIX_UBATCH_TOKENS','512'))
 assert 0<ubatch_tokens<=batch_tokens
 assert 1<=gpu_layers<=99
 wait_gpu(int(os.environ.get('PREFIX_GPU_MIN_FREE_MIB',str({8:7168,4:6144,2:4864,1:4608}[slots]))))
 executable=list((LAB/'llama').rglob('llama-server'))[0]
 log=(LAB/'server.log').open('a')
 args=[str(executable),'-m',str(LAB/'qwen.gguf'),'--host','localhost','--port','39790','-ngl',str(gpu_layers),'-c',str(context_tokens*slots),'--parallel',str(slots),'--batch-size',str(batch_tokens),'--ubatch-size',str(ubatch_tokens),'-t','4','-tb','4','--reasoning-budget','0','--jinja','--flash-attn','on','--cache-ram','0','--no-cache-idle-slots','--no-cache-prompt','--ctx-checkpoints','0']
 env=dict(os.environ)
 cuda_libraries=list((LAB/'llama').rglob('libcudart.so.12'))[0].parent
 env['LD_LIBRARY_PATH']=str(executable.parent)+':'+str(cuda_libraries)+':'+env.get('LD_LIBRARY_PATH','')
 server=subprocess.Popen(args,stdout=log,stderr=log,env=env)
 save(LAB/'server-owner.json',{'pid':server.pid})
 try:
  for _ in range(180):
   if server.poll() is not None:raise RuntimeError('local server exited, inspect scratch server.log')
   try:
    if requests.get('http://localhost:39790/health',timeout=2).status_code==200:break
   except requests.RequestException:pass
   time.sleep(2)
  else:raise TimeoutError('server startup timeout')
  gpu_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader'],text=True)
  assert any(line.split(',')[0].strip()==str(server.pid) for line in gpu_processes.splitlines()),'Local generator did not allocate CUDA memory'
  processes,free=gpu_usage()
  append(OUT/'prefix-resources.jsonl',{'event':'loaded_budget_check','own_gpu_mib':processes.get(server.pid,0),'free_gpu_mib':free,'slots':slots,'time':time.time()})
  if processes.get(server.pid,0)>5632:raise MemoryError('owned GPU allocation exceeds size budget')
  if free<1024:raise GPUHeadroomError('less than 1024 MiB free after load')
  append(OUT/'hardware.jsonl',{'event':'context_server_loaded','pid':server.pid,'gpu_compute_process_listing':gpu_processes,'time':time.time(),'parallel_requests':slots,'context_tokens_per_slot':context_tokens,'gpu_layers':gpu_layers,'batch_tokens':batch_tokens,'ubatch_tokens':ubatch_tokens})
  for name in names:
   path=LAB/(name+'.prefixes.jsonl')
   if not path.exists() and (OUT/path.name).exists():shutil.copyfile(OUT/path.name,path)
   done={x['id'] for x in readlines(path)} if path.exists() else set()
   data=load(name)
   import concurrent.futures
   def generate(d):
    # No query, relevance, answer or evaluation labels reach this prompt.
    context=' '.join((d.get('context') or data['contexts'][d['doc']]).split()[:2500])
    prompt='<document>\n'+context+'\n</document>\nHere is the chunk we want to situate within the whole document:\n<chunk>\n'+d['text']+'\n</chunk>\nPlease give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else. Use 50 to 100 tokens.'
    t=time.monotonic()
    r=requests.post('http://localhost:39790/v1/chat/completions',json={'model':'local','messages':[{'role':'user','content':prompt}],'temperature':0,'seed':SEED,'max_tokens':120,'cache_prompt':False,'chat_template_kwargs':{'enable_thinking':False}},timeout=300);r.raise_for_status();j=r.json()
    content=j['choices'][0]['message']['content']
    assert content and '<think>' not in content
    assert not j['choices'][0]['message'].get('reasoning_content'),'Unexpected reasoning output with thinking disabled'
    return {'id':d['id'],'prefix':content,'usage':j.get('usage'),'seconds':time.monotonic()-t,'finish_reason':j['choices'][0]['finish_reason'],'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'parallel_requests':slots,'context_tokens_per_slot':context_tokens,'batch_tokens':batch_tokens,'ubatch_tokens':ubatch_tokens,'gpu_layers':gpu_layers,'hardware_class':'8 GB NVIDIA RTX 3070 Ti GPU'+(' with CPU offload' if gpu_layers<33 else '')}
   remaining=iter(d for d in data['docs'] if d['id'] not in done)
   complete=len(done)
   with concurrent.futures.ThreadPoolExecutor(max_workers=slots) as executor:
    pending={}
    for _ in range(slots):
     d=next(remaining,None)
     if d is not None:pending[executor.submit(generate,d)]=d['id']
    while pending:
     ready,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
     for future in ready:
      pending.pop(future);append(path,future.result());complete+=1
      if complete%100==0:print('prefixes',name,complete,'/',len(data['docs']),flush=True)
      if complete%10==0:
       processes,free=gpu_usage()
       if complete%100==0 or free<1024:append(OUT/'prefix-resources.jsonl',{'dataset':name,'complete':complete,'own_gpu_mib':processes.get(server.pid,0),'free_gpu_mib':free,'slots':slots,'time':time.time()})
       if processes.get(server.pid,0)>5632:raise MemoryError('owned GPU allocation exceeds size budget')
       if free<1024:raise GPUHeadroomError('less than 1024 MiB free during generation')
      d=next(remaining,None)
      if d is not None:pending[executor.submit(generate,d)]=d['id']
   shutil.copyfile(path,OUT/path.name)
 finally:
  server.terminate()
  try:server.wait(timeout=30)
  except subprocess.TimeoutExpired:server.kill();server.wait()
  log.close()
def prefix_remote(names,slots):
 hardware=os.environ.get('PREFIX_HARDWARE_CLASS','Apple Silicon model server')
 base=os.environ['PREFIX_BASE_URL'].rstrip('/')
 if not base.startswith('http://localhost:3979'):raise ValueError('localhost assigned-port tunnel required')
 import concurrent.futures
 def ready():
  p=LAB/'mac-pressure.json'
  if not p.exists():return False
  state=json.loads(p.read_text())
  if time.time()-state.get('observed_at',state['time'])>40:raise RuntimeError('remote pressure monitor is stale')
  return state.get('ready',False) and state.get('kernel_level')==1
 append(OUT/'hardware.jsonl',{'event':'remote_context_generation','hardware_class':hardware,'slots':slots,'time':time.time()})
 for name in names:
  data=load(name);path=LAB/(name+'.prefixes.jsonl')
  if not path.exists() and (OUT/path.name).exists():shutil.copyfile(OUT/path.name,path)
  done={x['id'] for x in readlines(path)} if path.exists() else set()
  def generate(d):
   context=' '.join((d.get('context') or data['contexts'][d['doc']]).split()[:2500])
   prompt='<document>\n'+context+'\n</document>\nHere is the chunk we want to situate within the whole document:\n<chunk>\n'+d['text']+'\n</chunk>\nPlease give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else. Use 50 to 100 tokens.'
   attempts=0
   while True:
    while not ready():time.sleep(2)
    t=time.monotonic()
    try:
     response=requests.post(base+'/v1/chat/completions',json={'model':'local','messages':[{'role':'user','content':prompt}],'temperature':0,'seed':SEED,'max_tokens':120,'cache_prompt':False,'chat_template_kwargs':{'enable_thinking':False}},timeout=300)
     response.raise_for_status();j=response.json();break
    except requests.RequestException as error:
     attempts+=1;append(OUT/'prefix-transport-errors.jsonl',{'id':d['id'],'error_type':type(error).__name__,'attempt':attempts,'time':time.time()})
     if attempts>=10:raise
     time.sleep(3)
   content=j['choices'][0]['message']['content'];assert content and '<think>' not in content
   assert not (j['choices'][0]['message'].get('reasoning_content') or '').strip()
   return {'id':d['id'],'prefix':content,'usage':j.get('usage'),'seconds':time.monotonic()-t,'finish_reason':j['choices'][0]['finish_reason'],'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'parallel_requests':slots,'context_tokens_per_slot':json.loads((LAB/'mac-pressure.json').read_text()).get('context_tokens_per_slot',8192),'server_slots':json.loads((LAB/'mac-pressure.json').read_text()).get('slots',slots),'hardware_class':json.loads((LAB/'mac-pressure.json').read_text()).get('hardware_class',hardware)}
  remaining=iter(d for d in data['docs'] if d['id'] not in done);complete=len(done)
  with concurrent.futures.ThreadPoolExecutor(max_workers=slots) as executor:
   pending={}
   for _ in range(slots):
    d=next(remaining,None)
    if d is not None:pending[executor.submit(generate,d)]=d['id']
   while pending:
    finished,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
    for future in finished:
     pending.pop(future);append(path,future.result());complete+=1
     if complete%100==0:print('prefixes',name,complete,'/',len(data['docs']),flush=True)
     d=next(remaining,None)
     if d is not None:pending[executor.submit(generate,d)]=d['id']
  shutil.copyfile(path,OUT/path.name)
def prefixes(names):
 if os.environ.get('PREFIX_BASE_URL'):return prefix_remote(names,int(os.environ.get('PREFIX_SLOTS','4')))
 slots=int(os.environ.get('PREFIX_SLOTS','2'))
 if slots not in [1,2,4,8]:raise ValueError('PREFIX_SLOTS must be 1, 2, 4 or 8')
 while slots>=1:
  try:return prefix_run(names,slots)
  except GPUHeadroomError as error:
   append(OUT/'prefix-restarts.jsonl',{'reason':'Other workload reduced free headroom; owned server unloaded before waiting','previous_slots':slots,'next_slots':max(1,slots//2),'detail':str(error),'time':time.time()})
   slots=max(1,slots//2);time.sleep(10)
   continue
  except Exception as error:
   tail=(LAB/'server.log').read_text()[-20000:].lower()
   oom=isinstance(error,MemoryError) or any(t in tail for t in ['out of memory','cuda_error_out_of_memory'])
   if not oom or slots==1:raise
   append(OUT/'prefix-restarts.jsonl',{'reason':'GPU budget or out of memory','previous_slots':slots,'next_slots':max(1,slots//2),'error_type':type(error).__name__,'detail':str(error),'time':time.time()})
   slots=max(1,slots//2)
def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','embed','retrieve','rerank','prefixes','keyword']);p.add_argument('--context',action='store_true');p.add_argument('--datasets',nargs='+',default=['scifact','nfcorpus','longmemeval','locomo']);a=p.parse_args()
 append(OUT/'executions.jsonl',{'phase':a.phase,'context':a.context,'datasets':a.datasets,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
 if a.phase=='prepare':prepare()
 elif a.phase=='prefixes':prefixes(a.datasets)
 else:globals()[a.phase](a.datasets,context=a.context)
if __name__=='__main__':main()

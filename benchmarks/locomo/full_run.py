"""Resumable 320-question five-system comparison; one process per backend."""
import argparse,asyncio,json,time,uuid,os,hashlib
from datetime import datetime,timezone
from full_common import *
from run import ANSWER_SYSTEM,JUDGE,parse_json
from openai import OpenAI,AsyncOpenAI

def client():return OpenAI(base_url=BASE,api_key='local-unused',timeout=3600,max_retries=0)
def call(messages,seed=SEED,max_tokens=512,json_mode=False):
 c=client()
 while True:
  try:
   kw=dict(model=MODEL,messages=messages,temperature=0,seed=seed,max_tokens=max_tokens)
   if json_mode:kw['response_format']={'type':'json_object'}
   r=c.chat.completions.create(**kw)
   if r.choices[0].finish_reason!='stop':raise RuntimeError('Truncated generation')
   return r.choices[0].message.content
  except Exception as e:
   if 'length' in str(e).lower():
    if max_tokens>=4096:raise
    max_tokens=min(4096,max_tokens*2);log('length_retry',max_tokens=max_tokens);continue
   if getattr(e,'status_code',500)<500:raise
   status=OUT/'status.json'
   if status.exists() and time.time()>=read(status)['deadline_epoch']:raise TimeoutError('Run budget exhausted')
   log('call_retry',error=type(e).__name__);time.sleep(15)

def record_ingestion(backend,ci,start):
 timing=OUT/'ingestion-times'/backend/f'c{ci}.json'
 if timing.exists():return
 starts=OUT/'ingestion-starts'/backend/f'c{ci}.json'
 start=read(starts)['epoch'] if starts.exists() else start
 end=time.time();atomic(OUT/'ingestion-times'/backend/f'c{ci}.json',dict(backend=backend,conversation=ci,start_epoch=start,end_epoch=end,seconds=end-start,includes='framework initialization and ingestion; excludes retrieval, answering and judging'))

def load_item(backend,q):
 p=item_path(backend,q);return read(p) if p.exists() else dict(q,backend=backend,votes=[])
def completed(backend,q):return load_item(backend,q).get('complete',False)
def answer(backend,q,context):
 row=load_item(backend,q)
 if 'answer' in row:return
 row['context']=context;atomic(item_path(backend,q),row)
 row['answer']=call([{'role':'system','content':ANSWER_SYSTEM},{'role':'user','content':f"Conversation evidence:\n{context}\n\nQuestion: {q['question']}"}],max_tokens=384)
 atomic(item_path(backend,q),row);log('answer',backend=backend,item_id=q['item_id']);print(backend,q['item_id'],'answered',flush=True)
def judge(backend,q):
 row=load_item(backend,q)
 if row.get('complete'):return
 for vote in range(len(row['votes']),3):
  raw=call([{'role':'user','content':JUDGE.format(question=q['question'],gold=q['gold'],answer=row['answer'])}],seed=SEED+100*['full-context','rag','mem0','graphiti','cognee'].index(backend)+vote,max_tokens=384,json_mode=True)
  obj=parse_json(raw)
  if obj.get('label') not in ['CORRECT','WRONG']:raise RuntimeError('Invalid judge label')
  row['votes'].append(dict(raw=raw,label=obj['label'],seed=SEED+100*['full-context','rag','mem0','graphiti','cognee'].index(backend)+vote));atomic(item_path(backend,q),row)
 row['correct']=sum(v['label']=='CORRECT' for v in row['votes'])>=2;row['complete']=True
 atomic(item_path(backend,q),row);log('judged',backend=backend,item_id=q['item_id'],correct=row['correct']);print(backend,q['item_id'],row['correct'],flush=True)

def mem0_store(conv):
 from mem0 import Memory
 import mem0.configs.prompts as prompts
 root=LAB/f'mem0-c{conv["conversation"]}';root.mkdir(exist_ok=True)
 fresh=not (root/'qdrant').exists()
 m=Memory.from_config({'llm':{'provider':'openai','config':{'model':MODEL,'temperature':0,'max_tokens':4096,'api_key':'local-unused','openai_base_url':BASE}},'embedder':{'provider':'openai','config':{'model':'all-MiniLM-L6-v2','api_key':'local-unused','openai_base_url':BASE,'embedding_dims':384}},'vector_store':{'provider':'qdrant','config':{'path':str(root/'qdrant'),'embedding_model_dims':384,'collection_name':'locomo','on_disk':True}},'history_db_path':str(root/'history.db'),'custom_instructions':'Extract facts about BOTH named speakers. Preserve identities and dates. Resolve relative dates using each message timestamp. Ignore the machine date.'})
 native_generate=m.llm.generate_response
 def normalize_memory_schema(*args,**kwargs):
  raw=native_generate(*args,**kwargs)
  try:obj=parse_json(raw)
  except Exception:return raw
  memories=obj.get('memory') if isinstance(obj,dict) else None
  if isinstance(memories,list) and any(isinstance(x,str) for x in memories):
   count=sum(isinstance(x,str) for x in memories)
   obj['memory']=[{'text':x} if isinstance(x,str) else x for x in memories]
   log('mem0_schema_normalized',backend='mem0',conversation=conv['conversation'],string_facts_wrapped=count,original_response_sha256=hashlib.sha256(raw.encode()).hexdigest())
   return json.dumps(obj,ensure_ascii=False)
  return raw
 m.llm.generate_response=normalize_memory_schema
 original=prompts._resolve_dates;date=None
 def dates(current_date=None,observation_date=None):return original(current_date or date,observation_date)
 prompts._resolve_dates=dates
 try:
  for session in conv['sessions']:
   date=datetime.strptime(session['date'],'%I:%M %p on %d %B, %Y').date().isoformat()
   for start in range(0,len(session['turns']),8):
    checkpoint=OUT/'ingest/mem0'/f"c{conv['conversation']}-{session['key']}-{start}.json"
    if checkpoint.exists() and not fresh:continue
    r=m.add([{'role':'user','content':turn} for turn in session['turns'][start:start+8]],user_id='conversation',infer=True,metadata={'session':session['key'],'reference_date':date})
    atomic(checkpoint,r);print('ingest mem0',conv['conversation'],session['key'],start,len(r.get('results',[])),flush=True)
 finally:prompts._resolve_dates=original
 return m

async def graphiti_store(conv,smoke=False):
 from graphiti_core import Graphiti
 from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
 from graphiti_core.llm_client.config import LLMConfig
 from graphiti_core.embedder.openai import OpenAIEmbedder,OpenAIEmbedderConfig
 from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
 from graphiti_core.nodes import EpisodeType
 cfg=LLMConfig(api_key='local-unused',base_url=BASE,model=MODEL,small_model=MODEL,temperature=0)
 ac=AsyncOpenAI(api_key='local-unused',base_url=BASE,timeout=3600,max_retries=0)
 graph=Graphiti('bolt://localhost:39702',user='neo4j',password='local-unused',llm_client=OpenAIGenericClient(cfg,client=ac,max_tokens=4096),embedder=OpenAIEmbedder(OpenAIEmbedderConfig(embedding_model='all-MiniLM-L6-v2',embedding_dim=384),client=ac),cross_encoder=OpenAIRerankerClient(cfg,client=ac),max_coroutines=1)
 await graph.build_indices_and_constraints()
 count_result=await graph.driver.execute_query('MATCH (e:Episodic {group_id: $group}) RETURN count(e) AS n',group=f"c{conv['conversation']}")
 fresh=count_result[0][0]['n']==0
 sessions=conv['sessions'][:1] if smoke else conv['sessions']
 async def ingest_session(s,turns,part=''):
  checkpoint=OUT/'ingest/graphiti'/f"c{conv['conversation']}-{s['key']}{part}.json"
  if checkpoint.exists() and not fresh:return read(checkpoint)
  d=datetime.strptime(s['date'],'%I:%M %p on %d %B, %Y').replace(tzinfo=timezone.utc)
  try:
   r=await graph.add_episode(name=s['key']+part,episode_body='\n'.join(turns),source_description='timestamped conversation session',reference_time=d,source=EpisodeType.text,group_id=f"c{conv['conversation']}",previous_episode_uuids=[],custom_extraction_instructions='Preserve facts about both named speakers and the session dates. Do not summarize away specific details.')
   result={'episode_uuid':r.episode.uuid,'nodes':len(r.nodes),'edges':len(r.edges),'turn_count':len(turns)}
  except Exception as exc:
   if 'Model completion stopped by length' not in str(exc) or len(turns)<2:raise
   middle=len(turns)//2
   children=[await ingest_session(s,turns[:middle],part+'.0'),await ingest_session(s,turns[middle:],part+'.1')]
   result={'split_after_length_failure':True,'turn_count':len(turns),'children':children,'nodes':sum(x['nodes'] for x in children),'edges':sum(x['edges'] for x in children)}
   log('graphiti_split_session',conversation=conv['conversation'],session=s['key'],part=part,turns=len(turns))
  atomic(checkpoint,result);print('ingest graphiti',conv['conversation'],s['key']+part,result['edges'],flush=True)
  return result
 for s in sessions:await ingest_session(s,s['turns'])
 return graph

def cognee_config(conv):
 root=LAB/f"cognee-c{conv['conversation']}";root.mkdir(exist_ok=True)
 os.environ.update(LLM_PROVIDER='openai',LLM_MODEL='openai/'+MODEL,LLM_ENDPOINT=BASE,LLM_API_KEY='local-unused',LLM_TEMPERATURE='0',LLM_MAX_COMPLETION_TOKENS='4096',EMBEDDING_PROVIDER='openai_compatible',EMBEDDING_MODEL='all-MiniLM-L6-v2',EMBEDDING_ENDPOINT=BASE,EMBEDDING_API_KEY='local-unused',EMBEDDING_DIMENSIONS='384',EMBEDDING_MAX_COMPLETION_TOKENS='256',HUGGINGFACE_TOKENIZER='sentence-transformers/all-MiniLM-L6-v2',SYSTEM_ROOT_DIRECTORY=str(root/'system'),DATA_ROOT_DIRECTORY=str(root/'data'),CACHE_ROOT_DIRECTORY=str(root/'cache'),COGNEE_LOGS_DIR=str(root/'logs'),LOG_LEVEL='ERROR',TELEMETRY_DISABLED='true',COGNEE_TELEMETRY_ENABLED='false',COGNEE_TRACING_ENABLED='false',COGNEE_SKIP_CONNECTION_TEST='true',GRAPH_DATABASE_PROVIDER='ladybug',VECTOR_DB_PROVIDER='lancedb')
async def cognee_store(conv,smoke=False):
 fresh=not (LAB/f"cognee-c{conv['conversation']}"/'system').exists()
 cognee_config(conv)
 import cognee
 sessions=conv['sessions'][:1] if smoke else conv['sessions']
 for s in sessions:
  checkpoint=OUT/'ingest/cognee'/f"c{conv['conversation']}-{s['key']}.json"
  if checkpoint.exists() and not fresh:continue
  # Each session is a document. Cognify persists a real entity/relation graph.
  await cognee.add('\n'.join(s['turns']),dataset_name='conversation')
  result=await cognee.cognify(datasets=['conversation'],chunk_size=1600,chunks_per_batch=1,data_per_batch=1)
  states=[str(getattr(v,'status','')) for v in result.values()] if isinstance(result,dict) else []
  success=bool(states) and all(v in ['PipelineRunCompleted','PipelineRunAlreadyCompleted'] for v in states)
  atomic(checkpoint,{'session':s['key'],'cognify_result':str(result)[:3000],'run_statuses':states,'all_data_completed':success});print('ingest cognee',conv['conversation'],s['key'],flush=True)
 final_checkpoint=read(OUT/'ingest/cognee'/f"c{conv['conversation']}-{sessions[-1]['key']}.json")
 final_ok=final_checkpoint.get('all_data_completed',bool(re.search(r"^\{UUID\('[^']+'\): PipelineRun(?:Already)?Completed\(",final_checkpoint['cognify_result'])))
 if not final_ok:raise RuntimeError('Cognee final ingestion returned an error status; no question may be scored from this store')
 return cognee

async def main():
 parser=argparse.ArgumentParser();parser.add_argument('--backend',required=True,choices=['full-context','rag','mem0','graphiti','cognee']);parser.add_argument('--conversation',type=int);parser.add_argument('--smoke',action='store_true');a=parser.parse_args()
 env();backend=a.backend;questions=read(OUT/'selection.json');convs=read(OUT/'conversations.json')
 replay=os.environ.get('MEMORY_SAMPLE_IDS')
 if replay and backend in ['mem0','graphiti','cognee']:
  replay_data=read(Path(replay));ids=set(replay_data['item_ids'] if isinstance(replay_data,dict) else replay_data)
  assert ids <= {q['item_id'] for q in questions}, 'Replay IDs must belong to the fixed sample'
  questions=[q for q in questions if q['item_id'] in ids]
 for conv in convs:
  ci=conv['conversation']
  admission=OUT/'breadth-admission.json'
  scope=read(admission).get('max_memory_conversation',9) if admission.exists() else 9
  scope=min(scope,int(os.environ.get('MAX_MEMORY_CONVERSATION','9')))
  if backend in ['mem0','graphiti','cognee'] and ci>scope:continue
  policy=OUT/'breadth-policy.json'
  if backend in ['mem0','graphiti','cognee'] and policy.exists() and ci not in read(policy)['allowed_conversations']:
   continue
  if a.conversation is not None and ci!=a.conversation:continue
  rescue=OUT/'graphiti-rescue.json'
  while backend in ['mem0','graphiti','cognee'] and (backend=='cognee' or ci>=2) and rescue.exists() and read(rescue).get('state')=='running':
   if time.time()>=read(OUT/'status.json')['deadline_epoch']:raise TimeoutError('Run budget exhausted')
   await asyncio.sleep(5)
  privacy=OUT/'privacy-correction.json'
  while backend in ['mem0','graphiti','cognee'] and ci>=2 and privacy.exists() and read(privacy).get('state')=='running':
   if time.time()>=read(OUT/'status.json')['deadline_epoch']:raise TimeoutError('Run budget exhausted')
   await asyncio.sleep(5)
  memory_rescue=OUT/'mem0-schema-rescue.json'
  while backend in ['graphiti','cognee'] and memory_rescue.exists() and read(memory_rescue).get('jobs',{}).get(str(ci),{}).get('state')=='running':
   if time.time()>=read(OUT/'status.json')['deadline_epoch']:raise TimeoutError('Run budget exhausted')
   await asyncio.sleep(5)
  pipeline=OUT/'cognee-pipeline.json'
  while backend=='cognee' and not os.environ.get('COGNEE_PIPELINE_WORKER') and pipeline.exists() and read(pipeline).get('jobs',{}).get(str(ci),{}).get('state') in ['pending','running']:
   if time.time()>=read(OUT/'status.json')['deadline_epoch']:raise TimeoutError('Run budget exhausted')
   await asyncio.sleep(5)
  qs=[q for q in questions if q['conversation']==ci]
  interleave_cognee=backend=='cognee' and ci>=2
  if interleave_cognee:
   groups={c:[q for q in qs if q['category']==c] for c in [1,2,3,4]}
   qs=[groups[c][i] for i in range(max(map(len,groups.values()))) for c in [1,2,3,4] if i<len(groups[c])]
  if all(completed(backend,q) for q in qs) and not a.smoke:continue
  if interleave_cognee and not a.smoke:
   for q in qs:
    row=load_item(backend,q)
    if 'answer' in row and not row.get('complete'):judge(backend,q)
  need=[q for q in qs if 'answer' not in load_item(backend,q)]
  store=None
  if need or a.smoke:
   ingestion_start=time.time()
   if backend in ['mem0','graphiti','cognee'] and not a.smoke:
    starts=OUT/'ingestion-starts'/backend/f'c{ci}.json'
    if not starts.exists():atomic(starts,{'epoch':ingestion_start})
   if backend=='full-context':contexts=['\n'.join(conv['turns'])]*len(need)
   elif backend=='rag':
    import numpy as np
    c=client();vs=c.embeddings.create(model='all-MiniLM-L6-v2',input=conv['turns']);matrix=np.array([x.embedding for x in vs.data]);queries=c.embeddings.create(model='all-MiniLM-L6-v2',input=[q['question'] for q in need]);contexts=['\n'.join(conv['turns'][i] for i in np.argsort(-(matrix@np.array(v.embedding)),kind='stable')[:20]) for v in queries.data]
   elif backend=='mem0':
    store=mem0_store(conv);record_ingestion(backend,ci,ingestion_start);contexts=['\n'.join(x['memory'] for x in store.search(q['question'],top_k=20,filters={'user_id':'conversation'})['results']) for q in need]
   elif backend=='graphiti':
    store=await graphiti_store(conv,a.smoke);record_ingestion(backend,ci,ingestion_start);contexts=[]
    for q in need[:1] if a.smoke else need:
     hits=await store.search(q['question'],group_ids=[f'c{ci}'],num_results=20);contexts.append('\n'.join(f"{x.fact} [valid_at={x.valid_at}, invalid_at={x.invalid_at}]" for x in hits))
   else:
    store=await cognee_store(conv,a.smoke);record_ingestion(backend,ci,ingestion_start);contexts=[]
    from cognee.api.v1.search import SearchType
    for q in need[:1] if a.smoke else need:
     hits=await store.search(query_text=q['question'],query_type=SearchType.GRAPH_COMPLETION,datasets=['conversation'],only_context=True,top_k=20)
     def serial(v):
      if hasattr(v,'model_dump'):return v.model_dump(mode='json')
      if isinstance(v,list):return [serial(x) for x in v]
      if isinstance(v,dict):return {k:serial(x) for k,x in v.items()}
      return str(v)
     contexts.append(json.dumps(serial(hits),ensure_ascii=False))
     if interleave_cognee and not a.smoke:
      answer(backend,q,contexts[-1]);judge(backend,q)
   if a.smoke:
    atomic(OUT/f'{backend}-smoke.json',{'ok':True,'retrieved_context':contexts[0] if contexts else ''});return
   if not interleave_cognee:
    for q,ctx in zip(need,contexts):answer(backend,q,ctx)
  for q in qs:judge(backend,q)
  if backend=='graphiti' and store:await store.close()
  log('conversation_complete',backend=backend,conversation=ci)
if __name__=='__main__':asyncio.run(main())

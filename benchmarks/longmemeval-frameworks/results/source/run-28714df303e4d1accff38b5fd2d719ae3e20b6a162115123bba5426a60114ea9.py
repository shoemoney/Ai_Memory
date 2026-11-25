"""Paired full-haystack memory-framework experiment; no hosted inference."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LAB=Path(os.environ.get('LAB_DIR','/var/tmp/membench-longmemeval-frameworks'))
BIG=Path(os.environ.get('BIG_DIR','/data/scratch/membench/longmemeval-frameworks'));BIG.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'results'; BASE=os.environ.get('BASE_URL','http://localhost:39770/v1')
assert BASE.startswith('http://localhost:')
os.environ.update(HOME=str(BIG/'home'),XDG_CACHE_HOME=str(BIG/'cache'),HF_HOME=str(BIG/'hf'),MEM0_DIR=str(BIG/'mem0'),MEM0_TELEMETRY='false',GRAPHITI_TELEMETRY_ENABLED='false',CUDA_VISIBLE_DEVICES='',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='4',EMBEDDING_DIM='384')
os.environ.pop('OPENROUTER_API_KEY',None)
import asyncio,collections,hashlib,json,random,re,time,urllib.request,sqlite3,uuid,shutil
from datetime import datetime,timezone
import numpy as np
import torch
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer
from openai import OpenAI,APIError,APIConnectionError
from mem0 import Memory
from mem0.llms.base import LLMBase
import mem0.memory.main as mm
mm.capture_event=lambda *a,**k:None
from graphiti_core import Graphiti
from graphiti_core.driver.neo4j_driver import Neo4jDriver
from graphiti_core.llm_client.client import LLMClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.client import EmbedderClient,EmbedderConfig
from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.nodes import EpisodeType
from judge_prompt import get_anscheck_prompt
SEED=20261122; END=float(os.environ.get('DEADLINE_EPOCH',time.time()+50400))
REV='98d7416c24c778c2fee6e6f3006e7a073259d48f'; MODEL_REV='ff12eb39da2cd9b3b0f4b4f9ffb274603f05bb29'; EMBED_REV='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
client=OpenAI(base_url=BASE,api_key='local-only',timeout=900,max_retries=0)
CURRENT={}; tokenizer=None; embedder=None; usage=collections.Counter()
for p in [OUT,OUT/'items',OUT/'calls',OUT/'ingestion',LAB]:p.mkdir(parents=True,exist_ok=True)
def write(path,data):
 p=Path(path);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.replace(p)
def log(name,data):
 with (OUT/name).open('a') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n')
def budget():
 if time.time()>END:raise TimeoutError('absolute wall-clock deadline reached')
def clean(s):return (s or '').split('<end_of_turn>',1)[0].strip()
def messages_for_gemma(messages):
 # Gemma 2 has no system role. Preserve all text and label roles in one user turn.
 if len(messages)==1 and messages[0]['role']=='user':return messages
 return [{'role':'user','content':'\n\n'.join(m['role'].upper()+':\n'+m['content'] for m in messages)}]
def ntokens(messages):return len(tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True))
def call(messages,max_tokens,phase,seed=SEED):
 budget();messages=messages_for_gemma(messages);length=ntokens(messages)
 if length+max_tokens>8192:raise ValueError(f'context overflow: {length}+{max_tokens}; no silent truncation')
 key=hashlib.sha256(json.dumps([CURRENT,phase,messages,max_tokens,seed],sort_keys=True).encode()).hexdigest();p=OUT/'calls'/(key+'.json')
 if p.exists():return json.loads(p.read_text())
 while True:
  budget();pressure=LAB/'pressure.json'
  try:guard=json.loads(pressure.read_text())
  except (OSError,json.JSONDecodeError):guard={}
  if not guard.get('ready') or time.time()-guard.get('epoch',0)>60:time.sleep(5);continue
  t=time.monotonic()
  try:
   r=client.chat.completions.create(model='default_model',messages=messages,max_tokens=max_tokens,temperature=0,seed=seed,stop=['<end_of_turn>'])
   d={'item':dict(CURRENT),'phase':phase,'prompt_sha256':hashlib.sha256(json.dumps(messages,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'message_roles':[m['role'] for m in messages],'max_tokens':max_tokens,'seed':seed,'temperature':0,'response':r.model_dump(),'text':clean(r.choices[0].message.content),'seconds':time.monotonic()-t,'prompt_tokens_local':length}
   write(p,d);return d
  except (APIError,APIConnectionError) as e:
   log('transport-errors.jsonl',{'item':dict(CURRENT),'phase':phase,'type':type(e).__name__});time.sleep(5)
def json_response(messages,phase,schema=None):
 messages=[dict(m) for m in messages]
 messages[-1]['content']+='\nReturn only a valid JSON data object, without Markdown fences or commentary. If a JSON schema appears above, it describes the required data format; do not copy the schema. Fill its fields with the actual information extracted from the input. Do not output schema keywords such as $defs, properties, required, or title.'
 if schema:messages[-1]['content']+='\nJSON schema: '+json.dumps(schema)
 d=call(messages,1536,phase)
 text=d['text'];match=re.fullmatch(r'```(?:json)?\s*(.*?)\s*```',text,re.S)
 if match:text=match[1]
 result=json.loads(text)
 if not isinstance(result,dict):raise ValueError('model did not return JSON object')
 return result
class LocalMemLLM(LLMBase):
 def generate_response(self,messages,tools=None,**kwargs):
  if tools:raise ValueError('native tools unsupported by fixed reader')
  return json.dumps(json_response(messages,'mem0-json'))
class LocalGraphLLM(LLMClient):
 async def _generate_response(self,messages,response_model=None,max_tokens=1536,model_size=None,**kwargs):
  d=json_response([{'role':m.role,'content':m.content} for m in messages],'graphiti-json')
  if response_model:response_model.model_validate(d)
  return d
class LocalEmbedding(EmbedderClient):
 config=EmbedderConfig(embedding_dim=384)
 async def create(self,input_data):
  text=input_data if isinstance(input_data,str) else ' '.join(map(str,input_data))
  return embedder.encode(text,normalize_embeddings=True).tolist()
 async def create_batch(self,input_data_list):return embedder.encode(input_data_list,normalize_embeddings=True).tolist()
class CosineRanker(CrossEncoderClient):
 async def rank(self,query,passages):
  if not passages:return []
  vectors=embedder.encode([query]+passages,normalize_embeddings=True)
  return sorted(zip(passages,(vectors[1:]@vectors[0]).tolist()),key=lambda v:-v[1])
def prompt(x,context):
 return ('Answer using only the dated conversation history below. Account for updates and relative dates. If information is insufficient, say so. Give a concise but complete answer.\nQuestion date: '+x['question_date']+'\nHistory:\n'+json.dumps(context,ensure_ascii=False)+'\nQuestion: '+x['question'])
def stratum(x):return 'abstention' if x['question_id'].endswith('_abs') else x['question_type']
def selected_ids(manifest):
 groups=collections.defaultdict(list)
 for item in manifest['items']:groups[item['stratum']].append(item['question_id'])
 counts={k:len(v)*150//300 for k,v in groups.items()}
 for k in sorted(groups,key=lambda k:(-(len(groups[k])*150/300-counts[k]),k))[:150-sum(counts.values())]:counts[k]+=1
 rng=random.Random(SEED);chosen=[]
 for k in sorted(groups):chosen+=rng.sample(sorted(groups[k]),counts[k])
 rng.shuffle(chosen);return chosen,counts
def parts(x):
 # All source content, both speakers, chronological; split turns only if necessary.
 result=[]
 for sid,date,session in sorted(zip(x['haystack_session_ids'],x['haystack_dates'],x['haystack_sessions']),key=lambda v:v[1]):
  batch=[]
  for turn in session:
   tokens=tokenizer.encode(turn['content'],add_special_tokens=False)
   for start in range(0,len(tokens),1800):
    item={'role':turn['role'],'content':date+' '+tokenizer.decode(tokens[start:start+1800],skip_special_tokens=True)}
    if batch and sum(len(tokenizer.encode(v['content'],add_special_tokens=False)) for v in batch)+min(1800,len(tokens)-start)>2200:
     result.append({'session_id':sid,'date':date,'messages':batch});batch=[]
    batch.append(item)
  if batch:result.append({'session_id':sid,'date':date,'messages':batch})
 return result
def judge(x,hyp,system):
 if not clean(hyp):return {'correct':False,'votes':[],'reason':'empty answer forced incorrect before judge','calls':[]}
 p=get_anscheck_prompt(x['question_type'],x['question'],x['answer'],hyp,abstention=x['question_id'].endswith('_abs'))
 calls=[call([{'role':'user','content':p}],10,'judge',SEED+i) for i in range(3)]
 votes=['yes' in d['text'].lower() for d in calls]
 return {'correct':sum(votes)>=2,'votes':votes,'calls':[hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest() for v in calls]}
def baseline(x,method):
 source=ROOT.parent/'longmemeval/results/full/items'/f"{x['question_id']}--{method}-standard.json"
 d=json.loads(source.read_text());empty=not clean(d['hypothesis'])
 return {'question_id':x['question_id'],'system':method,'question_type':x['question_type'],'stratum':stratum(x),'question':x['question'],'reference':x['answer'],'hypothesis':d['hypothesis'],'correct':False if empty else d['correct'],'votes':[] if empty else d['judge']['votes'],'reused_source':str(source.relative_to(ROOT.parent)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'empty_guard_applied':True,'status':'scored'}
def usage_since(start):
 rows=[json.loads(p.read_text()) for p in (OUT/'calls').glob('*.json')]
 rows=[r for r in rows if r['item'].get('question_id')==CURRENT.get('question_id') and r['item'].get('system')==CURRENT.get('system') and r['phase'].endswith('json')]
 return {'prompt_tokens':sum(r['response'].get('usage',{}).get('prompt_tokens',0) for r in rows),'completion_tokens':sum(r['response'].get('usage',{}).get('completion_tokens',0) for r in rows),'model_calls':len(rows),'model_seconds':sum(r['seconds'] for r in rows)}
async def lane(x,system,episodes):
 qid=x['question_id'];CURRENT.clear();CURRENT.update(question_id=qid,system=system)
 p=OUT/'items'/f'{qid}--{system}.json'
 if p.exists():return json.loads(p.read_text())
 state=BIG/f'{qid}-{system}';state.mkdir(exist_ok=True)
 start=time.time();records=[];failed=None;ctx=[]
 try:
  if system=='mem0-extract':
   memory=Memory.from_config({'version':'v1.1','history_db_path':str(state/'history.sqlite'),'vector_store':{'provider':'qdrant','config':{'collection_name':'history','embedding_model_dims':384,'path':str(state/'qdrant')}},'embedder':{'provider':'huggingface','config':{'model':str(BIG/'embedding'),'embedding_dims':384,'model_kwargs':{'device':'cpu'}}},'llm':{'provider':'openai','config':{'model':'default_model','api_key':'local-only','openai_base_url':BASE,'temperature':0}}})
   class MemEmbedding:
    config=memory.embedding_model.config
    def embed(self,text,memory_action=None):return embedder.encode(text,normalize_embeddings=True).tolist()
   memory.embedding_model=MemEmbedding();memory.llm=LocalMemLLM()
  else:
   graph=Graphiti(graph_driver=Neo4jDriver('bolt://localhost:39771',None,None),llm_client=LocalGraphLLM(LLMConfig(model='default_model',temperature=0,max_tokens=1536)),embedder=LocalEmbedding(),cross_encoder=CosineRanker(),max_coroutines=1)
   await graph.build_indices_and_constraints()
   marker=BIG/'neo4j-current-question'
   if not marker.exists() or marker.read_text()!=qid:
    from graphiti_core.utils.maintenance.graph_data_operations import clear_data
    await clear_data(graph.driver)
    marker.write_text(qid)
    (state/'db-ready').unlink(missing_ok=True)
  cp=OUT/'ingestion'/f'{qid}--{system}.json'
  if cp.exists() and not (state/'db-ready').exists():
   shutil.copyfile(cp,cp.with_suffix('.previous.json'));write(cp,[])
  (state/'db-ready').touch()
  completed=json.loads(cp.read_text()) if cp.exists() else []
  for i,e in enumerate(episodes):
   budget()
   if i<len(completed):continue
   CURRENT.update(episode=i);t=time.time()
   if system=='mem0-extract':
    result=memory.add(e['messages'],user_id=qid,infer=True,metadata={'session_id':e['session_id'],'date':e['date']})
    record={'events':result}
   else:
    body='\n'.join(m['role']+': '+m['content'] for m in e['messages'])
    result=await graph.add_episode(name=f'{qid}-{i}',episode_body=body,source_description='dated benchmark conversation, both speakers',reference_time=datetime.strptime(e['date'][:10],'%Y/%m/%d').replace(tzinfo=timezone.utc),source=EpisodeType.message,group_id=None,uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,qid+'-'+str(i))),previous_episode_uuids=[])
    record={'nodes':len(result.nodes),'edges':len(result.edges),'episode_uuid':result.episode.uuid}
   completed.append(dict(episode=i,session_id=e['session_id'],date=e['date'],source_sha256=hashlib.sha256(json.dumps(e,sort_keys=True).encode()).hexdigest(),seconds=time.time()-t,**record));write(cp,completed)
   print(json.dumps({'question_id':qid,'system':system,'episode':i+1,'total':len(episodes),'seconds':round(time.time()-t,1)}),flush=True)
  CURRENT.pop('episode',None);ingestion_seconds=sum(v['seconds'] for v in completed);stats=usage_since(start)
  if system=='mem0-extract':ctx=[{'text':v['memory'],'score':v['score'],'metadata':v.get('metadata',{})} for v in memory.search(x['question'],user_id=qid,limit=10,threshold=None)['results']]
  else:ctx=[{'text':e.fact,'valid_at':str(e.valid_at),'invalid_at':str(e.invalid_at)} for e in await graph.search(x['question'],group_ids=None,num_results=10)]
  while ctx and ntokens([{'role':'user','content':prompt(x,ctx)}])+512>8192:ctx.pop()
  answer=call([{'role':'user','content':prompt(x,ctx)}],512,'answer');j=judge(x,answer['text'],system)
  d={'question_id':qid,'system':system,'stratum':stratum(x),'question_type':x['question_type'],'question':x['question'],'reference':x['answer'],'hypothesis':answer['text'],'context':ctx,'correct':j['correct'],'judge':j,'status':'scored','ingestion_seconds':ingestion_seconds,'ingestion_usage':stats,'source_sessions':len(x['haystack_sessions']),'source_parts':len(episodes),'ingested_parts':len(completed)}
  write(p,d);return d
 finally:
  if system=='mem0-extract' and 'memory' in locals():
   memory.vector_store.client.close();memory.db.connection.close()
  if system=='graphiti' and 'graph' in locals():await graph.close()
async def main():
 global tokenizer,embedder
 torch.set_num_threads(4)
 source=OUT/'source';source.mkdir(exist_ok=True)
 for f in ROOT.glob('*.py'):(source/(f.stem+'-'+hashlib.sha256(f.read_bytes()).hexdigest()+'.py')).write_bytes(f.read_bytes())
 old=json.loads((ROOT.parent/'longmemeval/results/full/manifest.json').read_text());ids,counts=selected_ids(old)
 manifest={'seed':SEED,'n':150,'selected_ids':ids,'strata_counts':counts,'dataset_revision':REV,'dataset_license':'MIT','model':'mlx-community/gemma-2-9b-it-4bit','model_revision':MODEL_REV,'embedding_model':'sentence-transformers/all-MiniLM-L6-v2','embedding_revision':EMBED_REV,'reader_temperature':0,'reader_max_tokens':512,'judge_seeds':[SEED+i for i in range(3)],'empty_answer_incorrect_without_judge':True,'order':'all systems finish question k before question k+1','systems':['bm25','dense','mem0-extract','graphiti'],'graphiti_previous_episode_uuids':[],'graphiti_communities':False,'graphiti_backend':'Neo4j Community 5.26, one isolated history at a time, no cross-history graph state','graphiti_reranker':'cosine MiniLM; default hybrid reciprocal-rank search uses no reranker','audit_seed':SEED+40,'audit_pairs':random.Random(SEED+40).sample([(i,s) for i in ids for s in ['bm25','dense','mem0-extract','graphiti']],40),'source_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in ROOT.glob('*.py')}}
 write(OUT/'manifest.json',manifest)
 data=BIG/'data.json'
 if not data.exists():
  with urllib.request.urlopen(f'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/{REV}/longmemeval_s_cleaned.json',timeout=300) as response, data.with_suffix('.part').open('wb') as f:
   total=0
   while block:=response.read(4*1024*1024):
    f.write(block);total+=len(block);print(json.dumps({'dataset_bytes_downloaded':total}),flush=True)
  data.with_suffix('.part').replace(data)
 assert hashlib.sha256(data.read_bytes()).hexdigest()==old['standard_file_sha256']
 byid={x['question_id']:x for x in json.loads(data.read_text())}
 tp=snapshot_download('mlx-community/gemma-2-9b-it-4bit',revision=MODEL_REV,allow_patterns=['tokenizer*','special_tokens_map.json','config.json']);tokenizer=AutoTokenizer.from_pretrained(tp);tokenizer.model_max_length=10**9
 ep=snapshot_download('sentence-transformers/all-MiniLM-L6-v2',revision=EMBED_REV,ignore_patterns=['onnx/*','openvino/*','*.h5','*.ot']);(BIG/'embedding').symlink_to(ep,target_is_directory=True) if not (BIG/'embedding').exists() else None;embedder=SentenceTransformer(ep,device='cpu');embedder.max_seq_length=256
 # Native Letta-style tool/system prerequisite with this fixed model, not a Letta accuracy run.
 if not (OUT/'letta-prerequisite.json').exists():
  try:
   r=client.chat.completions.create(model='default_model',messages=[{'role':'system','content':'Use the supplied memory tool.'},{'role':'user','content':'Remember that my favorite color is blue.'}],tools=[{'type':'function','function':{'name':'store_memory','description':'Store a memory','parameters':{'type':'object','properties':{'memory':{'type':'string'}},'required':['memory']}}}],temperature=0,max_tokens=128)
   write(OUT/'letta-prerequisite.json',{'response':r.model_dump(),'native_tool_supported':bool(r.choices[0].message.tool_calls),'limitation':'Endpoint prerequisite only, not a full Letta installation test.'})
  except APIError as e:write(OUT/'letta-prerequisite.json',{'status':e.status_code,'body':e.body,'limitation':'Native system/tool endpoint prerequisite failed; Graphiti selected as permitted local alternative. This does not show that Letta cannot run locally with another adapter.'})
 # Probe the permitted fallback against the actual fixed local model before the long run.
 probe=OUT/'graphiti-prerequisite.json'
 if not probe.exists():
  CURRENT.update(question_id='prerequisite',system='graphiti')
  g=Graphiti(graph_driver=Neo4jDriver('bolt://localhost:39771',None,None),llm_client=LocalGraphLLM(LLMConfig(model='default_model',temperature=0,max_tokens=1536)),embedder=LocalEmbedding(),cross_encoder=CosineRanker(),max_coroutines=1)
  try:
   await g.build_indices_and_constraints()
   from graphiti_core.utils.maintenance.graph_data_operations import clear_data
   await clear_data(g.driver)
   (BIG/'neo4j-current-question').write_text('prerequisite')
   r=await g.add_episode(name='control',episode_body='user: My favorite color is blue. I work at ExampleCo.',source_description='synthetic prerequisite',reference_time=datetime(2023,1,1,tzinfo=timezone.utc),group_id=None,previous_episode_uuids=[])
   await g.driver.execute_query('CALL db.awaitIndexes(120)')
   found=await g.search('What is my favorite color?',group_ids=None,num_results=10)
   assert r.nodes and r.edges and found, 'Graphiti synthetic extraction/storage/retrieval prerequisite did not pass'
   write(probe,{'nodes':len(r.nodes),'edges':len(r.edges),'retrieved_facts':[e.fact for e in found]})
  finally:await g.close()
 # Verify empty guard without any inference.
 assert judge(byid[ids[0]],'  ','control')['correct'] is False
 write(OUT/'empty-guard-control.json',{'empty_incorrect':True,'judge_calls':0})
 for qid in ids:
  budget();x=byid[qid];episodes=parts(x)
  for method in ['bm25','dense']:write(OUT/'items'/f'{qid}--{method}.json',baseline(x,method))
  for method in ['mem0-extract','graphiti']:
   await lane(x,method,episodes)
  from summarize import summarize
  summarize()
 print('COMPLETED_ALL_SELECTED_QUESTIONS',flush=True)
if __name__=='__main__':
 try:asyncio.run(main())
 except BaseException as e:
  write(OUT/'failure.json',{'type':type(e).__name__,'message':str(e),'item':dict(CURRENT),'epoch':time.time()})
  raise

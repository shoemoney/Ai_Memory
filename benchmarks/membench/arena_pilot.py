"""Bounded MemoryArena formal-reasoning pilot with fetched official classes.

No vendor source or dataset is redistributed. The official non-OpenAI reasoning
path, memory entry builder, environment step and yes/no judge are used. The only
backend is the same local reader. No generated code is executed.
"""
import importlib.machinery,importlib.util,random,sys,types
from common import *
REV='6cd9de14b71915e39ac742a20dc33785e14b6aab'
DATA_REV='da1a37c8b19280e18627ca01cf368195a5e1d92e'
FILES={
 'arena-math-env':('env/env_systems/math_env.py','c5d45b3354433ce188ada6d1e638d9cbb794f8c6e42de62c4d8cd1967f7e2d74'),
 'arena-base-env':('env/env_systems/base_env.py','3c7a2dcd6595f3ec39c06e1fefcaaf8903d0848fb17e8bdf56daaf35c46a6278'),
 'arena-math-agent':('agent/math.py','33faff8e13f7c12d69d375f319fa151102a8268b8a52d1795304a325e2e85141'),
 'arena-agent-base':('agent/base.py','3a7edf6b0f96e1793aef3d658e586c078ebc6a67b0ab0bc4239ba64370571b26'),
 'arena-base-agent':('agent/base_agent.py','61eac895f6e8d4bc347898898bb7c431d8a6f7ee2f37377ede747a9620a6e28c'),
 'arena-long-context':('memory/memory_systems/long_context.py','3e836759a650fd3dbe497ad5bc3c0962bf9fb1515407dbcd313eec5ab63ed5b6')}
CALLS=[]
class LocalBackend:
 def __init__(self,**kwargs):self.cap=int(kwargs.get('max_tokens',512));self.seed=SEED+10000
 def chat(self,messages,**kwargs):
  response=chat(messages,max_tokens=self.cap,seed=self.seed,slot=0);CALLS.append(response);return response['text']
def load(name,path):
 loader=importlib.machinery.SourceFileLoader(name,str(path));spec=importlib.util.spec_from_loader(name,loader);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;loader.exec_module(module);return module
def prepare():
 env();os.environ['TIKTOKEN_CACHE_DIR']=str(LAB/'arena-token-cache')
 for key,(path,checksum) in FILES.items():
  download(f'https://raw.githubusercontent.com/ZexueHe/MemoryArena/{REV}/{path}',LAB/key);assert sha((LAB/key).read_bytes())==checksum
 download(f'https://huggingface.co/datasets/ZexueHe/memoryarena/resolve/{DATA_REV}/formal_reasoning_math/data.jsonl',LAB/'arena-math-data.jsonl')
 assert sha((LAB/'arena-math-data.jsonl').read_bytes())=='ff5b0ad575847c7476a02d1e35661592a833bd0cff384cb54bc6f35b46de7803'
 rows=[json.loads(line) for line in (LAB/'arena-math-data.jsonl').read_text().splitlines()];eligible=[i for i,x in enumerate(rows) if len(x['questions'])==5];row=random.Random(SEED).choice(eligible)
 manifest={'pilot_only':True,'repository_revision':REV,'data_revision':DATA_REV,'dataset_license':'CC-BY-4.0 per official dataset card','code_license':'No top-level license in inspected repository; official files fetched to disposable scratch, not redistributed','seed':SEED,'sampling':'Uniform seeded choice among the three five-step math chains, before outcomes; complete selected chain','eligible_group_rows':eligible,'selected_group_row':row,'selected_group_id':rows[row]['id'],'steps':5,'methods':['full-history','no-memory'],'source_files':{k:{'path':v[0],'sha256':v[1]} for k,v in FILES.items()},'differences':['Local Qwen2.5-14B reader and judge instead of published backbones','Official non-OpenAI reasoning branch; coding tool not used','One chain, not the full formal-reasoning benchmark or other environments','Frozen memory timestamps for repeatability','Official environment step does not forward question to its equivalence judge; unchanged here']}
 atomic(OUT/'arena-pilot'/'manifest.json',manifest)
 return rows[row]
def classes():
 for name in ['_membench_arena','_membench_arena.env','_membench_arena.env.formal_reasoning_env','_membench_arena.agent','formal_reasoning_env']:
  module=types.ModuleType(name);module.__path__=[];sys.modules[name]=module
 backend=types.ModuleType('formal_reasoning_env.llm_backend');backend.LLMBackend=LocalBackend;backend.create_backend=lambda **kw:LocalBackend(**kw)
 sys.modules['formal_reasoning_env.llm_backend']=backend;sys.modules['_membench_arena.env.formal_reasoning_env.llm_backend']=backend
 load('_membench_arena.env.base_env',LAB/'arena-base-env');environment=load('_membench_arena.env.math_env',LAB/'arena-math-env').MathEnvironment
 load('_membench_arena.agent.base',LAB/'arena-agent-base');load('_membench_arena.agent.base_agent',LAB/'arena-base-agent');agent=load('_membench_arena.agent.math',LAB/'arena-math-agent').MathAgent
 memory_module=load('_membench_arena.memory',LAB/'arena-long-context');memory_module.time=types.SimpleNamespace(strftime=lambda _:'2026-11-22 00:00:00')
 return agent,environment,memory_module.LongContextMemorySystem
def main():
 data=prepare();Agent,Environment,Memory=classes()
 if '--prepare-only' in sys.argv:
  memory=Memory();memory.add_chunk('Initial result: Empty\n');print('Official classes loaded; no model calls made.');return
 primary=[read(p) for p in (OUT/'items').glob('*/*/*.json')]
 assert len(primary)==900 and all(x['score'] is not None for x in primary),'Primary comparisons have priority'
 pilot=[]
 for method in ['full-history','no-memory']:
  agent=Agent(model_name=MODEL,temperature=0,max_tokens=512,backend='local',base_url=BASE+'/v1')
  environment=Environment({'model_name':MODEL,'temperature':0,'max_tokens':32,'backend':'local','base_url':BASE+'/v1'})
  environment.reset();memory=Memory();memory.add_chunk('Initial result: Empty\n')
  for i,(question,gold,background) in enumerate(zip(data['questions'],data['answers'],data['backgrounds'])):
   private=LAB/'arena-pilot'/method/f'step-{i}.json'
   if private.exists():
    record=read(private);memory.add_chunk(record['memory_entry']);pilot.append(record);continue
   prompt=agent.build_prompt(task=question,background=background)
   if method=='full-history':prompt=memory.wrap_user_prompt(prompt)
   n=tokens(prompt);assert n+4096<131072,'Pilot context overflow; never truncate silently'
   agent.llm_backend.seed=SEED+20000+100*(['full-history','no-memory'].index(method))+2*i
   environment.llm_backend.seed=agent.llm_backend.seed+1
   before=len(CALLS);action=agent.act(prompt);answer=action.get('answer',action.get('result',''));assert answer and not action.get('error'),action.get('error')
   reader_calls=CALLS[before:];before=len(CALLS);observation,reward,info=environment.step(action,ground_truth=gold,need_judge=True);judge_calls=CALLS[before:]
   entry=agent.build_memory_entry(task=question,action=action,observation=observation,reward=None);memory.add_chunk(entry)
   record={'method':method,'step':i,'group_id':data['id'],'answer':answer,'correct':bool(reward),'judge_text':observation['judge_result'],'reader_calls':reader_calls,'judge_calls':judge_calls,'question_sha256':sha(question),'reference_sha256':sha(gold),'background_sha256':sha(background),'provided_prompt_tokens':n,'memory_entry':entry}
   atomic(private,record);pilot.append(record);print('arena pilot',method,i,bool(reward),flush=True)
  environment.close()
 # Original records stay private until the tester has reviewed all ten labels.
 import spacy
 nlp=spacy.load('en_core_web_sm',disable=['parser','lemmatizer']);names=set()
 for d in nlp.pipe([r['answer'] for r in pilot]):
  for e in d.ents:
   if e.label_=='PERSON':names.update(t.text.lower() for t in e if t.text.isalpha() and len(t.text)>1 and not t.is_stop)
 mapping={w:f'AnonMath{i:03d}' for i,w in enumerate(sorted(names,key=sha))}
 def mask(t):return re.sub(r'\b[A-Za-z]+\b',lambda m:mapping.get(m[0].lower(),m[0]),t)
 for original in pilot:
  record={k:v for k,v in original.items() if k!='memory_entry'};record['original_record_sha256']=sha(json.dumps(original,sort_keys=True));record['answer']=mask(record['answer'])
  for response in record['reader_calls']+record['judge_calls']:response['text']=mask(response['text'])
  atomic(OUT/'arena-pilot'/'items'/record['method']/f"step-{record['step']}.json",record)
 summary={'pilot_only':True,'model':MODEL,'methods':{},'interpretation':'One five-step reasoning chain, not an action-suite replication; cannot establish cross-benchmark saturation or general memory benefit.'}
 for method in ['full-history','no-memory']:
  rs=[r for r in pilot if r['method']==method];k=sum(r['correct'] for r in rs);summary['methods'][method]={'n':len(rs),'correct':k,'rate':k/len(rs),'wilson95':wilson(k,len(rs))}
 atomic(OUT/'arena-pilot'/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()

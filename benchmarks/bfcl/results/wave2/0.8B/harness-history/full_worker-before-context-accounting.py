"""Resumable full offline BFCL runner. Uses unmodified official inference and scoring."""
import argparse
import concurrent.futures as futures
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import signal
import threading
import time
from dataclasses import replace
from full_common import ROOT, LAB, SEED, TOKEN_CAP, CATEGORIES, MEMORY, MULTI, atomic, digest, weights, absence_credits

class Deadline(Exception): pass
class CheckpointDivergence(Exception): pass

def main():
 p=argparse.ArgumentParser();p.add_argument('--size',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--deadline',type=float,required=True);p.add_argument('--workers',type=int,default=8);p.add_argument('--prepare',action='store_true');p.add_argument('--smoke',action='store_true');a=p.parse_args()
 def stop(signum,frame):a.deadline=min(a.deadline,time.time())
 signal.signal(signal.SIGTERM,stop)
 signal.signal(signal.SIGINT,stop)
 os.environ.update(OPENAI_API_KEY='local',OPENAI_BASE_URL=os.getenv('BASE_URL','http://localhost:39730/v1'),BFCL_PROJECT_ROOT=str(LAB/'bfcl-runtime'),HF_HOME=str(LAB/'hf-cache'),HF_HUB_OFFLINE='1',TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 import torch;torch.set_num_threads(1)
 import bfcl_eval
 from bfcl_eval.utils import load_dataset_entry,load_ground_truth_entry,populate_initial_settings_for_memory_test_cases,make_json_serializable
 from bfcl_eval.model_handler.api_inference.openai_completion import OpenAICompletionsHandler
 from bfcl_eval.eval_checker.eval_runner import _evaluate_single_ast_entry,_evaluate_single_relevance_entry,_evaluate_single_multi_turn_entry,_evaluate_single_agentic_entry
 from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING
 from bfcl_eval.constants.enums import Language,ReturnFormat
 from bfcl_eval.eval_checker.multi_turn_eval import multi_turn_utils
 if importlib.metadata.version('bfcl-eval')!='2026.3.23':raise RuntimeError('BFCL version mismatch')
 entries={};scoring_entries={};answers={};populations={};chains={};manifest={'seed':SEED,'bfcl_version':'2026.3.23','max_tokens':TOKEN_CAP,'categories':{}}
 for cat in CATEGORIES:
  all_entries=load_dataset_entry(cat)
  scoring_entries[cat]={e['id']:e for e in load_dataset_entry(cat,include_prereq=False,include_language_specific_hint=False)}
  qs=[e for e in all_entries if '_prereq_' not in e['id']]
  prereqs=[e for e in all_entries if '_prereq_' in e['id']]
  populations[cat]=len(qs)
  random.Random(f'{SEED}:full:{cat}').shuffle(qs)
  entries[cat]=qs
  try: truths=load_ground_truth_entry(cat)
  except FileNotFoundError:truths=[]
  # Memory labels keep the original memory_N ids. Official CLI aligns by original order.
  if cat in MEMORY:
   answers[cat]={e['id'].replace('memory_',cat+'_',1):e['ground_truth'] for e in truths}
  else:answers[cat]={e['id']:e['ground_truth'] for e in truths}
  chains[cat]={}
  if cat in MEMORY:
   for scenario in ['notetaker','finance','healthcare','student','customer']:
    chains[cat][scenario]=[e for e in prereqs if e['scenario']==scenario]
  manifest['categories'][cat]={'population':len(qs),'random_order':[e['id'] for e in qs], 'prerequisites':[e['id'] for e in prereqs], 'processed_entries_sha256':digest(all_entries),'scenario_populations':{scenario:sum(e.get('scenario')==scenario for e in qs) for scenario in chains[cat]}}
 manifest['leaf_weights']=weights(populations)
 manifest['missing_categories']={'web_search_base':'Live SerpAPI search and live HTTP page access required','web_search_no_snippet':'Live SerpAPI search and live HTTP page access required','format_sensitivity':'Non-scoring; official format variations require prompting-mode models, while this matrix uses native FC'}
 manifest['harness_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}
 manifest['source_files']={str(f.relative_to(Path(bfcl_eval.__file__).parent)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (Path(bfcl_eval.__file__).parent/'data').rglob('*') if f.is_file()}
 a.output.mkdir(parents=True,exist_ok=True)
 atomic(a.output/'manifest.json',manifest)
 if a.prepare:return
 alias=f'membench-bfcl-Qwen3.5-{a.size}-Q4_K_M'
 for mode in ['off','on']:
  MODEL_CONFIG_MAPPING[f'local-full-{mode}-FC']=replace(MODEL_CONFIG_MAPPING['gpt-4o-2024-11-20-FC'],model_name=alias,display_name='Local full offline',model_handler=OpenAICompletionsHandler,input_price=None,output_price=None)
 lock=threading.Lock();completed={};inflight=set();errors={};progress={'size':a.size,'started':time.time()}
 def path_for(mode,cat,eid):return a.output/mode/'items'/cat/(eid+'.json')
 def existing(mode,cat,entry):
  key=(mode,cat,entry['id'])
  if key in completed:return True
  path=path_for(*key)
  if path.exists():
   row=json.loads(path.read_text())
   if row.get('status')=='complete':completed[key]=row;return True
  return False
 class Handler(OpenAICompletionsHandler):
  def __init__(self,mode,cat,entry):
   super().__init__(alias,0,f'local-full-{mode}-FC',True)
   self.mode=mode;self.cat=cat;self.entry=entry;self.idx=0;self.calls=[]
   self.model_name_underline_replaced=f'full_{a.size}_{mode}'.replace('.','_')
   self.client=self.client.with_options(timeout=900,max_retries=0)
  def generate_with_backoff(self,**kwargs):
   if time.time()>=a.deadline:raise Deadline()
   def plain(value):
    if hasattr(value,'model_dump'):return plain(value.model_dump(exclude_none=True))
    if isinstance(value,dict):return {k:plain(v) for k,v in value.items()}
    if isinstance(value,list):return [plain(v) for v in value]
    return value
   kwargs=plain(kwargs)
   kwargs.update(max_tokens=TOKEN_CAP,seed=SEED,extra_body={'chat_template_kwargs':{'enable_thinking':self.mode=='on'}})
   self.idx+=1
   dest=a.output/self.mode/'calls'/self.cat/self.entry['id']/f'{self.idx:04}.json'
   signature=digest(kwargs)
   if dest.exists():
    old=json.loads(dest.read_text())
    if old['request_sha256']!=signature:raise CheckpointDivergence('Simulator replay changed a request; restart this uncommitted item')
    from openai.types.chat import ChatCompletion
    self.calls.append(old)
    return ChatCompletion.model_validate(old['response']),old['seconds']
   start=time.monotonic();response=self.client.with_options(timeout=max(1,min(900,a.deadline-time.time()))).chat.completions.create(**kwargs);elapsed=time.monotonic()-start
   row={'request_sha256':signature,'request':kwargs,'response':response.model_dump(),'seconds':elapsed,'completed_at':time.time()}
   atomic(dest,row);self.calls.append(row)
   atomic(a.output/'heartbeat.json',{'time':time.time(),'size':a.size,'last_request':{'mode':self.mode,'category':self.cat,'id':self.entry['id'],'step':self.idx}})
   return response,elapsed
 def execute(mode,cat,original):
  entry=copy.deepcopy(original);eid=entry['id'];key=(mode,cat,eid)
  if existing(mode,cat,entry):return key,completed[key]
  handler=Handler(mode,cat,entry)
  # Official simulated backend instances are module globals. Reset only this item/mode.
  prefix=f'{handler.model_name_underline_replaced}_{eid}_'.replace('-','_').replace('.','_')
  eval_prefix=f'local_full_{mode}_FC_eval_{eid}_'.replace('-','_').replace('.','_')
  truth_prefix=f'local_full_{mode}_FC_ground_truth_eval_{eid}_'.replace('-','_').replace('.','_')
  for name in list(vars(multi_turn_utils)):
   if name.startswith((prefix,eval_prefix,truth_prefix)) and name.endswith('_instance'):delattr(multi_turn_utils,name)
  if cat in MEMORY:
   populate_initial_settings_for_memory_test_cases([entry],a.output/mode/'state')
   # Restore the exact preceding prerequisite snapshot when resuming mid-chain.
   if '_prereq_' in eid and entry.get('depends_on'):
    dep=entry['depends_on'][-1]
    from bfcl_eval.utils import get_directory_structure_by_id
    base=a.output/mode/'state'/get_directory_structure_by_id(eid)/'memory_snapshot'
    prev=base/'prereq_checkpoints'/(dep+'.json')
    if not prev.exists():raise RuntimeError('Missing prerequisite snapshot')
    atomic(base/(entry['scenario']+'_final.json'),json.loads(prev.read_text()))
  start=time.monotonic()
  try:
   result,metadata=handler.inference(copy.deepcopy(entry),True,True)
   scoring_entry=copy.deepcopy(scoring_entries[cat].get(eid,entry))
   if '_prereq_' in eid:
    score={'valid':None,'prerequisite':True}
   elif cat in MEMORY:
    score=_evaluate_single_agentic_entry(handler,eid,result,answers[cat][eid],copy.deepcopy(scoring_entry),f'local-full-{mode}-FC',cat)
   elif cat in MULTI:
    score=_evaluate_single_multi_turn_entry(handler,eid,result,answers[cat][eid],copy.deepcopy(scoring_entry),f'local-full-{mode}-FC',cat)
   elif 'relevance' in cat:
    score=_evaluate_single_relevance_entry(handler,eid,result,copy.deepcopy(scoring_entry),f'local-full-{mode}-FC',cat)
   else:
    lang=Language.JAVA if cat=='simple_java' else Language.JAVASCRIPT if cat=='simple_javascript' else Language.PYTHON
    score=_evaluate_single_ast_entry(handler,eid,result,answers[cat][eid],copy.deepcopy(scoring_entry),f'local-full-{mode}-FC',cat,lang,ReturnFormat.PYTHON)
   calls=handler.calls
   last=calls[-1]['response']['choices'][0]['message'] if calls else {}
   empty_final=not(last.get('content') or '').strip() and not last.get('tool_calls')
   length=any(c['response']['choices'][0]['finish_reason']=='length' for c in calls)
   credit,malformed_credit=absence_credits(cat,score.get('valid'),last)
   row=make_json_serializable({'status':'complete','id':eid,'category':cat,'scenario':entry.get('scenario'),'mode':mode,'result':result,'metadata':metadata,'score':score,'empty_answer_credit':credit,'malformed_tool_credit':malformed_credit,'any_length_stop':length,'completed_nonempty_correct':bool(score.get('valid')) and not credit and not malformed_credit and not length,'api_calls':len(calls),'elapsed_seconds':time.monotonic()-start,'completed_at':time.time()})
   atomic(path_for(mode,cat,eid),row)
   return key,row
  finally:
   # Do not retain thousands of simulated file systems in memory across this run.
   for name in list(vars(multi_turn_utils)):
    if name.startswith((prefix,eval_prefix,truth_prefix)) and name.endswith('_instance'):delattr(multi_turn_utils,name)
 def candidate(cat,mode):
  if cat in MEMORY:
   for scenario,chain in chains[cat].items():
    blocked=False
    for e in chain:
     key=(mode,cat,e['id'])
     if not existing(mode,cat,e):
      if errors.get(key,0)>=3:blocked=True;break
      if key in inflight:return None
      return e
    if blocked:continue
    pending_domain=False
    for e in entries[cat]:
     if e['scenario']!=scenario:continue
     key=(mode,cat,e['id'])
     if not existing(mode,cat,e):
      if errors.get(key,0)>=3:continue
      if key not in inflight:return e
      pending_domain=True
    if pending_domain:return None
   return None
  for e in entries[cat]:
   key=(mode,cat,e['id'])
   if not existing(mode,cat,e) and key not in inflight and errors.get(key,0)<3:return e
  return None
 # Initial pass guarantees every static/multi-turn category gets paired coverage.
 # Thereafter fifteen of thirty-two selections target memory; other categories round-robin.
 static_cats=[c for c in CATEGORIES if c not in MEMORY]
 schedule=static_cats+MEMORY*5
 if a.smoke:schedule=['simple_java','multi_turn_base','memory_kv','memory_vector','memory_rec_sum']
 cursor=0;pending={};submitted=0;max_completed=10 if a.smoke else None
 with futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
  while time.time()<a.deadline or pending:
   while time.time()<a.deadline and len(pending)<a.workers:
    chosen=None
    for _ in range(len(schedule)*2):
     cat=schedule[cursor%len(schedule)];cursor+=1
     # Alternate modes per category selection and prioritize incomplete pairs.
     modes=sorted(['off','on'],key=lambda m:sum(k[0]==m and k[1]==cat for k in completed)+sum(k[0]==m and k[1]==cat for k in inflight))
     for mode in modes:
      e=candidate(cat,mode)
      if e is not None:
       key=(mode,cat,e['id'])
       if errors.get(key,0)>=3:continue
       chosen=(mode,cat,e);break
     if chosen:break
    if not chosen:break
    mode,cat,e=chosen;key=(mode,cat,e['id']);inflight.add(key)
    pending[pool.submit(execute,mode,cat,e)]=key;submitted+=1
   if not pending:break
   done,_=futures.wait(pending,timeout=1,return_when=futures.FIRST_COMPLETED)
   for f in done:
    key=pending.pop(f);inflight.remove(key)
    try:
     k,row=f.result();completed[k]=row
     print(json.dumps({'event':'item','size':a.size,'mode':k[0],'category':k[1],'id':k[2],'correct':row['score']['valid'],'calls':row['api_calls']}),flush=True)
    except Deadline:pass
    except Exception as exc:
     if isinstance(exc,CheckpointDivergence):
      import shutil
      src=a.output/key[0]/'calls'/key[1]/key[2]
      dest=a.output/key[0]/'replay-divergences'/key[1]/(key[2]+'-'+str(time.time_ns()))
      dest.parent.mkdir(parents=True,exist_ok=True)
      if src.exists():shutil.move(str(src),str(dest))
     errors[key]=errors.get(key,0)+1
     atomic(a.output/'errors'/key[0]/key[1]/(key[2]+'.json'),{'type':type(exc).__name__,'message':str(exc),'attempts':errors[key],'time':time.time()})
     print(json.dumps({'event':'error','key':key,'type':type(exc).__name__,'message':str(exc)}),flush=True)
    progress.update(time=time.time(),completed_items=len(completed),scored_items=sum('_prereq_' not in k[2] for k in completed),inflight=len(pending),errors=sum(errors.values()))
    atomic(a.output/'progress.json',progress)
   if max_completed and len(completed)>=max_completed:
    a.deadline=time.time()
 atomic(a.output/'worker-finished.json',{'time':time.time(),'size':a.size,'deadline_reached':time.time()>=a.deadline,'complete_items':len(completed),'errors':sum(errors.values())})

if __name__=='__main__':main()

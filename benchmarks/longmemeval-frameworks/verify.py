"""Evidence consistency checks. Does not generate or judge answers."""
import ast,collections,json,hashlib,time,types,tempfile,threading,asyncio
from model_guard import ModelLease
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
def verify():
 m=json.loads((OUT/'manifest.json').read_text());ids=m['selected_ids'];assert len(ids)==len(set(ids))==150
 parent=json.loads((ROOT.parent/'longmemeval/results/full/manifest.json').read_text());assert set(ids)<=set(v['question_id'] for v in parent['items'])
 strata={v['question_id']:v['stratum'] for v in parent['items']};assert dict(collections.Counter(strata[i] for i in ids))==m['strata_counts']
 for p in (OUT/'items').glob('*.json'):
  d=json.loads(p.read_text());assert d['question_id'] in ids
  if not d['hypothesis'].strip():assert not d['correct']
  if d['system'] in ['bm25','dense']:
   src=ROOT.parent/d['reused_source'];assert hashlib.sha256(src.read_bytes()).hexdigest()==d['source_sha256']
   old=json.loads(src.read_text());assert d['hypothesis']==old['hypothesis'];assert d['correct']==(old['correct'] if old['hypothesis'].strip() else False)
  else:
   assert d['model_hardware_class']==d['ingestion_hardware_class']==d['reader_hardware_class']==d['judge_hardware_class']
   assert d['model_hardware_class'] in ['Apple M1 Ultra, 64 GB','Apple M3 Ultra, 96 GB']
   assert d['source_parts']==d.get('attempted_parts',d['ingested_parts'])
   assert d['ingested_parts']+d.get('ingestion_failed_parts',0)==d['source_parts']
   cp=json.loads((OUT/'ingestion'/f"{d['question_id']}--{d['system']}.json").read_text());assert len(cp)==d['source_parts']
   assert [r['episode'] for r in cp]==list(range(len(cp)))
   assert d['ingestion_usage']['model_calls']>0
 # Execute only the pure empty-answer branch and fail if it asks for an LLM.
 source=ast.parse((ROOT/'run.py').read_text());nodes=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ['clean','judge']]
 env={'get_anscheck_prompt':lambda *a,**k:(_ for _ in ()).throw(AssertionError('empty answer reached judge'))}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ROOT/'run.py'),'exec'),env)
 assert env['judge']({},' \n','control')=={'correct':False,'votes':[],'reason':'empty answer forced incorrect before judge','calls':[]}
 # A stale/missing/malformed heartbeat must block the actual client call; a fresh heartbeat must pass it.
 call_node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='call')
 class GateBlocked(Exception):pass
 class GateOpen(Exception):pass
 base=Path('/data/scratch/membench/longmemeval-frameworks');base.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='guard-test-',dir=base) as tmp:
  t=Path(tmp);(t/'calls').mkdir();attempts=[];ticks=[0]
  def budget():
   ticks[0]+=1
   if ticks[0]>=3:raise GateBlocked()
  def actual_client(**kwargs):attempts.append(kwargs);raise GateOpen()
  namespace={'HARDWARE':'test hardware','READER_MODEL':'local-reader','MODEL_LEASE':ModelLease(t,server_pid=lambda:123,release=lambda:None),'CALL_LOCKS':{},'threading':threading,'LAB':t,'OUT':t,'CURRENT':{'question_id':'guard-regression'},'SEED':20261122,'budget':budget,'messages_for_gemma':lambda v:v,'ntokens':lambda v,**kwargs:1,'hashlib':hashlib,'json':json,'time':types.SimpleNamespace(time=time.time,monotonic=time.monotonic,sleep=lambda _:None),'client':types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=actual_client))),'APIError':ConnectionError,'APIConnectionError':ConnectionError}
  exec(compile(ast.Module(body=[call_node],type_ignores=[]),str(ROOT/'run.py'),'exec'),namespace)
  for payload in [None,'{broken',json.dumps({'ready':True,'pressure_level':1,'epoch':0,'free_percent':60}),json.dumps({'ready':True,'pressure_level':1,'epoch':time.time(),'free_percent':39}),json.dumps({'ready':False,'pressure_level':1,'epoch':time.time(),'free_percent':60})]:
   q=t/'pressure.json';q.unlink(missing_ok=True)
   if payload is not None:q.write_text(payload)
   ticks[0]=0
   try:namespace['call']([{'role':'user','content':'guard control'}],1,'guard-test')
   except GateBlocked:pass
   else:raise AssertionError('Unsafe heartbeat was not blocked')
   assert not attempts
  (t/'pressure.json').write_text(json.dumps({'ready':True,'pressure_level':1,'epoch':time.time(),'free_percent':60}));ticks[0]=0
  try:namespace['call']([{'role':'user','content':'guard control'}],1,'guard-test')
  except GateOpen:pass
  else:raise AssertionError('Fresh heartbeat did not reach client')
  assert len(attempts)==1
 # A resident model can continue below 40%, but a new model or new PID cannot load there.
 with tempfile.TemporaryDirectory(prefix='lease-test-',dir=base) as tmp:
  t=Path(tmp);pid=[1];released=[];lease=ModelLease(t,server_pid=lambda:pid[0],release=lambda:released.append(pid[0]))
  def guard(free,level=1):
   (t/'pressure.json').write_text(json.dumps({'ready':level==1,'pressure_level':level,'epoch':time.time(),'free_percent':free}))
  guard(60);ticket=lease.prepare('extractor');assert ticket;lease.finish(ticket,True)
  guard(37);ticket=lease.prepare('extractor');assert ticket;lease.finish(ticket,True);assert not released
  assert lease.prepare('reader') is None and released==[1]
  guard(60);ticket=lease.prepare('reader');assert ticket;lease.finish(ticket,True)
  pid[0]=2;guard(37);assert lease.prepare('reader') is None
  guard(60);ticket=lease.prepare('reader');assert ticket;lease.finish(ticket,True)
  guard(37,2);assert lease.prepare('reader') is None
  guard(60);ticket=lease.prepare('extractor');assert ticket
  assert lease.prepare('reader') is None
  lease.finish(ticket,False);guard(37);assert lease.prepare('extractor') is None and released[-1]==2
 # Cancelled graph coroutines must drain their actual executor requests before advancing.
 async def concurrency_controls():
  finished=[]
  class FakeBase:
   def __init__(self,*a,**k):pass
  def fake_json(*args):time.sleep(.04);finished.append('model-finished');return {'ok':True}
  env={'LLMClient':FakeBase,'asyncio':asyncio,'json_response':fake_json}
  nodes=[n for n in source.body if (isinstance(n,ast.ClassDef) and n.name=='LocalGraphLLM') or (isinstance(n,ast.AsyncFunctionDef) and n.name=='graph_bulk')]
  exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ROOT/'run.py'),'exec'),env)
  local=env['LocalGraphLLM']();task=asyncio.create_task(local._generate_response([]));await asyncio.sleep(.01);task.cancel();await asyncio.gather(task,return_exceptions=True);await local.drain()
  assert finished==['model-finished'] and not local.pending
 asyncio.run(concurrency_controls())
 async def concurrency_controls_bulk():
  writes=[];cancelled=[];drains=[]
  async def drain():drains.append(True)
  async def orphan():
   try:await asyncio.sleep(1);writes.append('late-write')
   finally:cancelled.append(True)
  class FakeGraph:
   llm_client=types.SimpleNamespace(drain=drain)
   async def add_episode_bulk(self,*a,**k):asyncio.create_task(orphan());await asyncio.sleep(0);raise ValueError('synthetic schema failure')
  node=next(n for n in source.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='graph_bulk');env={'asyncio':asyncio};exec(compile(ast.Module(body=[node],type_ignores=[]),str(ROOT/'run.py'),'exec'),env)
  keep=asyncio.create_task(asyncio.sleep(1))
  try:await env['graph_bulk'](FakeGraph(),[])
  except ValueError:pass
  else:raise AssertionError('Bulk error was hidden')
  assert not writes and cancelled==[True] and drains==[True] and not keep.done();keep.cancel();await asyncio.gather(keep,return_exceptions=True)
 asyncio.run(concurrency_controls_bulk())
 print('PASS: sample/provenance/history attempts, empty-answer/resident/new-load pressure guards, and failed-bulk sibling cancellation')
if __name__=='__main__':verify()

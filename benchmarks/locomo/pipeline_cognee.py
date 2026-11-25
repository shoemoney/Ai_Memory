"""Use a freed Graphiti slot for Cognee in the same admitted conversation pair."""
import os,signal,subprocess,time,urllib.request,json
from full_common import *

def completed(backend,q):
 path=item_path(backend,q)
 return path.exists() and read(path).get('complete',False)

def main():
 while not (OUT/'status.json').exists():time.sleep(1)
 path=OUT/'cognee-pipeline.json';state=read(path) if path.exists() else dict(jobs={})
 processes={};slots={};third_ready=False;seen_second_pair=False;questions=read(OUT/'selection.json')
 while LAB.exists():
  status=read(OUT/'status.json')
  policy=OUT/'breadth-policy.json'
  if policy.exists() and any(ci in [2,3] for ci in read(policy).get('allowed_conversations',[])):seen_second_pair=True
  expired=time.time()>=status['deadline_epoch']
  for ci,proc in list(processes.items()):
   if expired and proc.poll() is None:
    try:os.killpg(proc.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    proc.wait(timeout=30)
   if proc.poll() is not None:
    qs=[q for q in questions if q['conversation']==ci]
    complete=all(completed('cognee',q) for q in qs)
    state['jobs'][str(ci)].update(state='completed' if complete else 'failed',exit_code=proc.returncode,end_epoch=time.time())
    atomic(path,state);del processes[ci]
  if expired:break
  if status.get('backend')=='graphiti':
   for job in status.get('active_jobs',[]):
    if job.get('conversation') in [2,3] and 'model_slot' in job:slots[job['conversation']]=job['model_slot']
   parallel=OUT/'three-slot-change.json'
   if parallel.exists() and read(parallel).get('state')=='ready':third_ready=True
   if not third_ready:
    try:
     with urllib.request.urlopen('http://localhost:39700/slots',timeout=5) as response:available=json.load(response)
     third_ready=len(available)==3 and all(slot['n_ctx']==65536 for slot in available)
    except (OSError,ValueError,KeyError):pass
   third=third_ready
   if third:slots[2]=2
   for ci,slot in sorted(slots.items()):
    if str(ci) in state['jobs']:continue
    qs=[q for q in questions if q['conversation']==ci]
    if not all(completed('mem0',q) for q in qs):continue
    if not (ci==2 and third) and not all(completed('graphiti',q) for q in qs):continue
    state['jobs'][str(ci)]=dict(state='pending',start_epoch=time.time(),model_slot=slot)
    atomic(path,state)
    with (LAB/f'cognee-pipeline-c{ci}.log').open('a') as log:
     proc=subprocess.Popen([str(LAB/'graph-venv/bin/python'),str(ROOT/'full_run.py'),'--backend','cognee','--conversation',str(ci)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,COGNEE_PIPELINE_WORKER='1',BASE_URL=f"http://localhost:39701/slot/{slot}/v1"))
    processes[ci]=proc;state['jobs'][str(ci)].update(state='running',pid=proc.pid);atomic(path,state)
  if status.get('backend')=='cognee' and seen_second_pair and not processes:break
  if status.get('state') in ['finished','budget_exhausted','interrupted'] and not processes:break
  time.sleep(2)

if __name__=='__main__':main()

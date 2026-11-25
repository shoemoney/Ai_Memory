"""Two isolated conversations per backend, with resumable status and fixed deadline."""
import subprocess,signal,os,time,re,sys,threading,queue
from concurrent.futures import ThreadPoolExecutor
from full_common import *
from full_summary import summarize

def main():
 OUT.mkdir(parents=True,exist_ok=True);status_path=OUT/'status.json'
 old=read(status_path) if status_path.exists() else {};start=old.get('start_epoch',time.time());deadline=start+float(os.environ.get('RUN_HOURS','9'))*3600
 failures=old.get('failures',[]);active={};lock=threading.RLock();stopped=threading.Event();backend_failed=threading.Event();current_backend=['']
 def state(mode='running'):
  with lock:
   model=read(OUT/'model-state.json') if (OUT/'model-state.json').exists() else {}
   if mode=='running' and model.get('pressure_level',1)>1:mode='paused_waiting_normal'
   atomic(status_path,dict(start_epoch=start,deadline_epoch=deadline,updated_epoch=time.time(),failures=failures,state=mode,backend=current_backend[0],active_jobs=list(active.values()),conversation=min(active) if active else None,concurrency=2))
 def stop_children():
  stopped.set()
  with lock:
   for job in active.values():
    if job.get('pid'):
     try:os.killpg(job['pid'],signal.SIGTERM)
     except ProcessLookupError:pass
 def interrupted(signum,frame):stop_children();state('interrupted');sys.exit(128+signum)
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 slots=queue.Queue();slots.put(0);slots.put(1)
 questions=read(OUT/'selection.json')
 def run_conv(backend,ci):
  slot=slots.get()
  try:return run_conv_in_slot(backend,ci,slot)
  finally:slots.put(slot)
 def run_conv_in_slot(backend,ci,slot):
  if stopped.is_set() or backend_failed.is_set():return
  qs=[q for q in questions if q['conversation']==ci]
  if all(item_path(backend,q).exists() and read(item_path(backend,q)).get('complete') for q in qs):return
  python=LAB/('graph-venv' if backend in ['graphiti','cognee'] else 'venv')/'bin/python';retries=0
  while not stopped.is_set() and time.time()<deadline:
   model=read(OUT/'model-state.json') if (OUT/'model-state.json').exists() else {}
   if model.get('pressure_level',1)>1:
    with lock:active[ci]=dict(conversation=ci,state='waiting_normal')
    time.sleep(15);continue
   logfile=LAB/f'{backend}-c{ci}.log'
   with logfile.open('a') as output:
    proc=subprocess.Popen([str(python),str(ROOT/'full_run.py'),'--backend',backend,'--conversation',str(ci)],stdout=output,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,BASE_URL=f'http://localhost:39701/slot/{slot}/v1'))
    with lock:active[ci]=dict(conversation=ci,pid=proc.pid,state='running',model_slot=slot)
    while proc.poll() is None:
     if stopped.is_set() or time.time()>=deadline:
      try:os.killpg(proc.pid,signal.SIGTERM)
      except ProcessLookupError:pass
      proc.wait(timeout=30);break
     time.sleep(5)
   with lock:active.pop(ci,None)
   if proc.returncode==0 or stopped.is_set():return
   text=logfile.read_text(errors='replace')[-6000:];model=read(OUT/'model-state.json') if (OUT/'model-state.json').exists() else {}
   transient=any(t in text for t in ['APIConnectionError','APITimeoutError','Connection error','timed out','TimeoutError'])
   recent=model.get('pressure_level',1)>1 or time.time()-model.get('last_warning_epoch',0)<120
   if recent or (transient and retries<3):retries+=1;time.sleep(15);continue
   text=re.sub(r'/(?:home|Users)/[^/\s]+','<user-home>',text);text=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','<address>',text)
   with lock:failures.append(dict(backend=backend,conversation=ci,exit_code=proc.returncode,log_tail=text));atomic(OUT/'failures.json',failures)
   backend_failed.set();return
 for backend in ['full-context','rag','mem0','graphiti','cognee']:
  current_backend[0]=backend;backend_failed.clear()
  with ThreadPoolExecutor(max_workers=2) as pool:
   futures=[pool.submit(run_conv,backend,ci) for ci in range(10)]
   while not all(f.done() for f in futures):
    summarize();state()
    if time.time()>=deadline:stop_children();state('budget_exhausted');break
    time.sleep(10)
   for f in futures:
    try:f.result()
    except Exception as exc:
     with lock:failures.append(dict(backend=backend,error=type(exc).__name__,message=str(exc)[:1000]));atomic(OUT/'failures.json',failures)
  summarize()
  if stopped.is_set() or time.time()>=deadline:state('budget_exhausted');return
 state('finished');summarize()
if __name__=='__main__':main()

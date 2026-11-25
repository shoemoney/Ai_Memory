"""Eight-hour OS-supervised controller; checkpoint/resume and resource-safe serving."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from full_common import ROOT, LAB, MODELS, EMBED_REVISION, atomic, RUN_DIR

HOST=os.environ.get('MODEL_HOST')
SERVICE='com.membench.bfcl.server'
GUARD='com.membench.bfcl.guard'
STOP=False

def remote(script,check=True):
 r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',HOST,'bash','-s'],input=script,text=True,capture_output=True,timeout=300)
 if check and r.returncode:raise RuntimeError(f'SSH operation failed ({r.returncode}): '+r.stderr[-300:])
 return r

def resource():
 return remote('''memory_pressure -Q | tail -1
sysctl -n kern.memorystatus_vm_pressure_level
df -h .
ps -axo pid,comm,rss | awk 'NR==1 || /llama-server|omlx-server/ {print $1,$2,$3}'
if lsof -b -nP -iTCP:39730 -sTCP:LISTEN >/dev/null;then echo task-port-occupied;else echo task-port-unoccupied;fi
''').stdout

def normal():
 r=remote("sysctl -n kern.memorystatus_vm_pressure_level; memory_pressure -Q | awk '/System-wide memory free percentage/ {gsub(/%/,\"\",$NF);print $NF}'",False)
 parts=r.stdout.split()
 return r.returncode==0 and len(parts)==2 and parts[0]=='1' and int(parts[1])>=40

def pressure_normal():
 r=remote('sysctl -n kern.memorystatus_vm_pressure_level',False)
 return r.returncode==0 and r.stdout.strip()=='1'

def stop_server():
 return remote('uid=$(id -u); launchctl bootout gui/$uid/'+SERVICE+' 2>/dev/null || true; launchctl bootout gui/$uid/'+GUARD+' 2>/dev/null || true',False)

def serve(size):
 revision,sha=MODELS[size]
 pre='export MODEL_URL='+repr(f'https://huggingface.co/unsloth/Qwen3.5-{size}-GGUF/resolve/{revision}/Qwen3.5-{size}-Q4_K_M.gguf')+'\nexport MODEL_SHA='+repr(sha)+'\nexport MODEL_ALIAS='+repr(f'membench-bfcl-Qwen3.5-{size}-Q4_K_M')+'\n'
 return remote(pre+(ROOT/'serve_full.sh').read_text(),False)

def healthy():
 try:
  with urllib.request.urlopen('http://localhost:39730/health',timeout=3) as r:return json.load(r).get('status')=='ok'
 except OSError:return False

def stop_worker(p):
 if p and p.poll() is None:
  p.terminate()
  try:p.wait(timeout=20)
  except subprocess.TimeoutExpired:p.kill();p.wait()

def setup():
 LAB.mkdir(parents=True,exist_ok=True)
 os.environ['UV_CACHE_DIR']=str(LAB/'uv-cache')
 os.environ['PIP_CACHE_DIR']=str(LAB/'pip-cache')
 os.environ['UV_PYTHON_INSTALL_DIR']=str(LAB/'python')
 uv=shutil.which('uv') or str(Path.home()/'.local/bin/uv')
 if not Path(uv).is_file():raise RuntimeError('uv is unavailable in PATH and the standard user installation')
 py=LAB/'venv/bin/python'
 if not py.exists():
  subprocess.run(['df','-h','/','/data'],check=True)
  if shutil.disk_usage('/').free<20*2**30:raise RuntimeError('Shared system disk has under 20 GiB free; pause large environment creation')
  subprocess.run([uv,'venv','--python','3.11.18',str(LAB/'venv')],check=True)
  subprocess.run([uv,'pip','sync','--python',str(py),'--extra-index-url','https://download.pytorch.org/whl/cpu','--index-strategy','unsafe-best-match',str(ROOT/'requirements.txt')],check=True)
 if not (LAB/'embedding-ready').exists():
  code='''from huggingface_hub import snapshot_download
from pathlib import Path
rev=REPLACE_REV
p=snapshot_download('sentence-transformers/all-MiniLM-L6-v2',revision=rev,allow_patterns=['*.json','*.txt','model.safetensors','1_Pooling/config.json'])
refs=Path(p).parents[1]/'refs';refs.mkdir(exist_ok=True);(refs/'main').write_text(rev)
'''.replace('REPLACE_REV',repr(EMBED_REVISION))
  env=dict(os.environ,HF_HOME=str(LAB/'hf-cache'))
  subprocess.run([str(py),'-c',code],env=env,check=True)
  (LAB/'embedding-ready').write_text(EMBED_REVISION)
 return py

def main():
 global STOP
 parser=argparse.ArgumentParser();parser.add_argument('--hours',type=float,default=8);parser.add_argument('--deadline-utc');parser.add_argument('--smoke-only',action='store_true');parser.add_argument('--sample-per-category',type=int);args=parser.parse_args()
 if not HOST:raise SystemExit('Set MODEL_HOST to the authorized model-serving SSH alias')
 def stopping(sig,frame):
  global STOP;STOP=True
 signal.signal(signal.SIGTERM,stopping);signal.signal(signal.SIGINT,stopping)
 out=RUN_DIR;out.mkdir(parents=True,exist_ok=True)
 if (out/'DONE.json').exists():
  terminal=json.loads((out/'DONE.json').read_text())
  if terminal['status']!='failed':return
  (out/'DONE.json').unlink()
 state_path=out/'run-state.json'
 if state_path.exists():state=json.loads(state_path.read_text())
 else:
  deadline=datetime.datetime.fromisoformat(args.deadline_utc.replace('Z','+00:00')).timestamp() if args.deadline_utc else time.time()+args.hours*3600
  state={'started':time.time(),'deadline':deadline,'finished_models':[],'events':[]};atomic(state_path,state)
 deadline=state['deadline'];worker=None;tunnel=None;status='failed';py=None
 def event(kind,**values):
  row={'time':time.time(),'event':kind,**values};state['events'].append(row);atomic(state_path,state);print(json.dumps(row),flush=True)
 try:
  py=setup()
  sample_args=['--sample-per-category',str(args.sample_per_category)] if args.sample_per_category else []
  if not (out/'resources-before.txt').exists():(out/'resources-before.txt').write_text(resource())
  version=remote('llama-server --version 2>&1').stdout
  (out/'runtime-version.txt').write_text(version)
  if 'build 12359' not in version or 'b1b770d90' not in version:raise RuntimeError('Serving runtime differs from pinned version')
  subprocess.run([str(py),str(ROOT/'full_worker.py'),'--size','0.8B','--output',str(out),'--deadline','0','--prepare']+sample_args,check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  while time.time()<deadline-120 and not STOP:
   remaining=[s for s in MODELS if s not in state['finished_models']]
   if not remaining:break
   size=remaining[0]
   model_deadline=min(deadline-120,time.time()+(deadline-120-time.time())/len(remaining))
   # The absolute per-model deadline persists across crashes and memory pauses.
   model_deadline=state.setdefault('model_deadlines',{}).setdefault(size,model_deadline);atomic(state_path,state)
   event('model_start',size=size,deadline=model_deadline)
   while time.time()<model_deadline and not STOP:
    if not normal():event('memory_pause',size=size);time.sleep(min(30,max(1,model_deadline-time.time())));continue
    response=serve(size)
    if response.returncode==75:continue
    if response.returncode:raise RuntimeError('Model serving setup failed: '+response.stdout[-100:]+response.stderr[-300:])
    import re
    match=re.search(r'SERVING slots=(\d+)',response.stdout)
    slots=int(match.group(1)) if match else 4
    event('serving_profile',size=size,slots=slots,context_per_slot=65536,output_cap=16384)
    tunnel=subprocess.Popen(['ssh','-N','-o','ExitOnForwardFailure=yes','-L','39730:localhost:39730',HOST],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(180):
     if healthy():break
     if tunnel.poll() is not None:raise RuntimeError('Tunnel failed')
     if not pressure_normal():break
     time.sleep(1)
    if not healthy():
     stop_server();tunnel.terminate();tunnel.wait();tunnel=None
     if not normal():continue
     raise RuntimeError('Server failed to become healthy')
    with (LAB/f'recheck-{size}.log').open('a') as diagnostic_log:
     subprocess.run([str(py),str(ROOT/'cap_rechecks.py'),'--size',size,'--deadline',str(model_deadline)],stdout=diagnostic_log,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),check=True)
    if state.get('pause_credit_pending'):
     pending_credit=state.pop('pause_credit_pending');resumed=time.time();seconds=resumed-pending_credit['started']
     deadline+=seconds;model_deadline+=seconds
     state['deadline']=deadline;state['model_deadlines'][size]=model_deadline
     credit={**pending_credit,'resumed':resumed,'credited_seconds':seconds,'pause_started_utc':datetime.datetime.fromtimestamp(pending_credit['started'],datetime.timezone.utc).isoformat(),'resumed_utc':datetime.datetime.fromtimestamp(resumed,datetime.timezone.utc).isoformat(),'note':'Authorized pause credit ends when environment and serving are ready to launch the resumed worker.'}
     state.setdefault('pause_credits',[]).append(credit)
     atomic(out/pending_credit['proof_folder']/'timing.json',credit)
     event('authorized_pause_credit',size=size,seconds=seconds,new_global_deadline=deadline,new_model_deadline=model_deadline)
    workerlog=(LAB/f'worker-{size}.log').open('a')
    command=[str(py),str(ROOT/'full_worker.py'),'--size',size,'--output',str(out/size),'--deadline',str(model_deadline),'--workers',str(slots)]+sample_args
    suspended=out/size/'suspended.json'
    if suspended.exists():suspended.unlink()
    interrupted=False
    worker=subprocess.Popen(command,stdout=workerlog,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    while worker.poll() is None and time.time()<model_deadline and not STOP:
     time.sleep(10)
     if not healthy() or suspended.exists():
      interrupted=True
      event('server_interrupted',size=size)
      stop_server();stop_worker(worker);break
    stop_worker(worker);workerlog.close()
    (out/f'resources-{size}-after.txt').write_text(resource())
    pressure=remote('cat ~/membench-bfcl-tmp/pressure.log 2>/dev/null || true',False).stdout
    (out/f'pressure-{size}.txt').write_text(pressure)
    stop_server()
    if tunnel:tunnel.terminate();tunnel.wait();tunnel=None
    if (interrupted or worker.returncode==75 or not normal()) and time.time()<model_deadline:continue
    if worker.returncode not in [0,-15]:
     event('worker_error',size=size,returncode=worker.returncode)
     # Retry the exact checkpointed run, within the same deadline.
     time.sleep(5);continue
    break
   if not STOP:
    state['finished_models'].append(size);event('model_finished',size=size)
  status='interrupted' if STOP else 'budget_finished' if time.time()>=deadline-120 else 'finished'
 except Exception as exc:
  event('controller_error',type=type(exc).__name__,message=str(exc))
  raise
 finally:
  stop_server();stop_worker(worker)
  if tunnel:tunnel.terminate();tunnel.wait()
  if status=='failed' and time.time()<deadline-120 and not STOP:
   atomic(out/'last-attempt-error.json',{'time':time.time(),'will_restart':True,'services_stopped':True})
  else:
   try:
    remote('rm -rf -- ~/membench-bfcl-tmp')
    (out/'resources-after.txt').write_text(resource())
    proof=remote('test ! -e ~/membench-bfcl-tmp && echo remote-scratch-absent; uid=$(id -u); for label in '+SERVICE+' '+GUARD+'; do if launchctl print gui/$uid/$label >/dev/null 2>&1;then echo task-service-present;else echo task-service-absent;fi;done; if lsof -b -nP -iTCP:39730 -sTCP:LISTEN >/dev/null;then echo task-port-occupied;else echo task-port-unoccupied;fi').stdout
    (out/'cleanup.txt').write_text(proof)
    if py and py.exists():subprocess.run([str(py),str(ROOT/'analyze_full.py')],check=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    shutil.rmtree(LAB)
    with (out/'cleanup.txt').open('a') as f:f.write('local-scratch-absent='+str(not LAB.exists())+'\n'+subprocess.check_output(['df','-h','/var/tmp'],text=True))
    atomic(out/'DONE.json',{'status':status,'finished_at':time.time(),'cleanup_complete':True})
    subprocess.run([sys.executable,str(ROOT/('report_wave2.py' if args.sample_per_category else 'finalize_full.py'))],check=True)
   except Exception as exc:
    atomic(out/'DONE.json',{'status':status,'finished_at':time.time(),'cleanup_complete':False,'error':str(exc)})
    raise

if __name__=='__main__':main()

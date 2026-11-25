"""Safety watchdog for an unattended run; no task work survives its budget."""
import time,os,signal,re,subprocess
from full_common import *
from cleanup_full import clean
while LAB.exists():
 target=os.environ.get('MODEL_SSH_TARGET')
 if target:
  try:r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',target,'memory_pressure -Q; sysctl -n kern.memorystatus_vm_pressure_level'],capture_output=True,text=True,timeout=20)
  except subprocess.TimeoutExpired:r=None
  if r is not None and r.returncode==0:
   previous=read(OUT/'model-state.json') if (OUT/'model-state.json').exists() else {}
   level=int(r.stdout.strip().splitlines()[-1]);free=int(re.search(r'free percentage: (\d+)%',r.stdout)[1])
   warning= time.time() if level>1 else previous.get('last_warning_epoch',0)
   atomic(OUT/'model-state.json',dict(time_epoch=time.time(),pressure_level=level,memory_free_percent=free,last_warning_epoch=warning))
 s=OUT/'status.json'
 if s.exists():
  status=read(s)
  summary=read(OUT/'summary.json') if (OUT/'summary.json').exists() else {}
  complete=len(summary)==5 and all(x['n']==320 for x in summary.values())
  expired=time.time()>status['deadline_epoch']+120
  if complete or expired:
   roles=read(LAB/'roles.json') if (LAB/'roles.json').exists() else {}
   if roles.get('supervisor_pid'):
    try:os.kill(roles['supervisor_pid'],signal.SIGTERM)
    except ProcessLookupError:pass
    pids=[status.get('child_pid')]+[j.get('pid') for j in status.get('active_jobs',[])]
    for pid in pids:
     if pid:
      try:os.killpg(pid,signal.SIGTERM)
      except ProcessLookupError:pass
   time.sleep(3);clean()
   final=read(OUT/'status.json');final['state']='finished' if complete else 'budget_exhausted';atomic(OUT/'status.json',final);break
 time.sleep(30)

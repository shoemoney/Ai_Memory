"""Gate weight loads at 40% free, while allowing a verified resident model.

The pinned MLX-LM ModelProvider retains its selected model until a different
model is requested or the process exits. Clear the lease before every switch,
verify the owned process PID for low-memory requests, and invalidate it on any
request failure. No other client is permitted to select models in this server.
"""
import json,os,subprocess,threading,time
from pathlib import Path

class ModelLease:
 def __init__(self,lab,host=None,server_pid=None,release=None):
  self.lab=Path(lab);self.file=self.lab/'model-lease.json';self.host=host or os.environ.get('MODEL_HOST')
  self.pid_fn=server_pid or self.remote_pid;self.release_fn=release or self.release_server
  self.lock=threading.RLock();self.active=0;self.active_model=None
 def ssh(self,command):
  try:return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5',self.host,command],capture_output=True,text=True,timeout=10)
  except (OSError,subprocess.TimeoutExpired,TypeError):return None
 def remote_pid(self):
  r=self.ssh('if test -f ~/membench-longmemeval-frameworks-tmp/server.pid; then p=$(cat ~/membench-longmemeval-frameworks-tmp/server.pid); c=$(ps -p "$p" -o command=); if printf "%s" "$c" | grep -Fq "membench-longmemeval-frameworks-tmp/" && printf "%s" "$c" | grep -Fq "mlx_lm.server"; then printf "%s" "$p"; fi; fi')
  return int(r.stdout.strip()) if r and r.stdout.strip().isdigit() else None
 def release_server(self):
  self.ssh('if test -f ~/membench-longmemeval-frameworks-tmp/server.pid; then p=$(cat ~/membench-longmemeval-frameworks-tmp/server.pid); c=$(ps -p "$p" -o command=); if printf "%s" "$c" | grep -Fq "membench-longmemeval-frameworks-tmp/" && printf "%s" "$c" | grep -Fq "mlx_lm.server"; then kill "$p"; fi; fi')
 def read(self):
  try:return json.loads(self.file.read_text())
  except (OSError,ValueError):return {}
 def write(self,state):
  tmp=self.file.with_suffix('.tmp');tmp.write_text(json.dumps(state));tmp.replace(self.file)
 def prepare(self,model):
  try:g=json.loads((self.lab/'pressure.json').read_text())
  except (OSError,ValueError):return None
  if not g.get('ready') or g.get('pressure_level')!=1 or not isinstance(g.get('epoch'),(int,float)) or not 0<=time.time()-g['epoch']<=60:return None
  free=g.get('free_percent')
  if not isinstance(free,(int,float)):return None
  with self.lock:
   if self.active and self.active_model!=model:return None
   state=self.read()
   # A fresh PID check is mandatory before relying on an already-loaded model
   # below the load threshold. Above it, a stale lease can only be conservative.
   fresh=free<40 or not state.get('server_pid') or state.get('model')!=model or time.time()-state.get('pid_checked_epoch',0)>5
   pid=self.pid_fn() if fresh else state['server_pid']
   checked=time.time() if fresh else state.get('pid_checked_epoch',0)
   if not pid:return None
   resident=state.get('server_pid')==pid and state.get('model')==model
   if free<40 and not resident:
    if not self.active and state.get('server_pid')==pid and (state.get('model') or state.get('pending_model')):
     self.release_fn();self.write({'server_pid':pid,'model':None,'pending_model':None,'released_epoch':time.time()})
    return None
   if not resident:self.write({'server_pid':pid,'pid_checked_epoch':checked,'model':None,'pending_model':model})
   self.active+=1;self.active_model=model
   return {'server_pid':pid,'pid_checked_epoch':checked,'model':model,'finished':False}
 def finish(self,ticket,success):
  with self.lock:
   if ticket['finished']:return
   ticket['finished']=True;self.active-=1
   if not self.active:self.active_model=None
   self.write({'server_pid':ticket['server_pid'],'pid_checked_epoch':ticket['pid_checked_epoch'],'model':ticket['model'] if success else None,'pending_model':None if success else ticket['model']})

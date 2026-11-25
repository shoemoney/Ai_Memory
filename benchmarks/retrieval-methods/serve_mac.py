"""Isolated model serving only; never changes another service."""
import json,os,re,signal,subprocess,time
from pathlib import Path
LAB=Path.home()/'membench-retrieval-methods-tmp';LAB.mkdir(exist_ok=True)
HARDWARE=subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip()+', '+str(int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True))//(1024**3))+' GB'
STOP=False;server=None
def halt(*args):
 global STOP
 STOP=True
for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,halt)
def pressure():
 text=subprocess.check_output(['memory_pressure'],text=True)
 return int(re.search(r'System-wide memory free percentage:\s*(\d+)%',text).group(1)),int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True))
def stop_owned():
 global server
 if server is not None and server.poll() is None:
  server.terminate()
  try:server.wait(timeout=20)
  except subprocess.TimeoutExpired:server.kill();server.wait()
 server=None
def write(data):
 p=LAB/'pressure.json';t=p.with_suffix('.tmp');t.write_text(json.dumps(data));t.replace(p);print(json.dumps(data),flush=True)
(LAB/'helper.pid').write_text(str(os.getpid()))
exe=next((LAB/'llama').rglob('llama-server'));log=(LAB/'server.log').open('a');slots=int(os.environ.get('PREFIX_SLOTS','8'));context=int(os.environ.get('PREFIX_CTX_PER_SLOT','4096'))
try:
 while not STOP:
  pct,level=pressure();reason='normal'
  if level!=1:
   had_model=server is not None
   stop_owned();reason='kernel_pressure_pause'
   if had_model and slots>1:slots=max(1,slots//2)
  if server is not None and server.poll() is not None:server=None;reason='owned_server_exited'
  if server is None and pct>=40 and level==1:
   args=[str(exe),'-m',str(LAB/'qwen.gguf'),'--host','localhost','--port','39790','-ngl','99','-c',str(context*slots),'--parallel',str(slots),'-t','4','-tb','4','--reasoning-budget','0','--jinja','--flash-attn','on','--cache-ram','0','--no-cache-idle-slots','--no-cache-prompt','--ctx-checkpoints','0']
   server=subprocess.Popen(args,stdout=log,stderr=log);(LAB/'server.pid').write_text(str(server.pid));reason='owned_server_start'
  ready=False
  if server is not None and level==1:
   try:
    import urllib.request
    ready=urllib.request.urlopen('http://localhost:39790/health',timeout=2).status==200
   except Exception:pass
  write({'time':time.time(),'free_percent':pct,'kernel_level':level,'ready':ready,'reason':reason,'server_pid':server.pid if server else None,'helper_pid':os.getpid(),'hardware_class':HARDWARE,'slots':slots,'context_tokens_per_slot':context})
  for _ in range(5):
   if STOP:break
   time.sleep(1)
finally:
 stop_owned();log.close();write({'time':time.time(),'ready':False,'reason':'owned_helper_stopped','helper_pid':os.getpid(),'hardware_class':HARDWARE})

"""Own only this benchmark's server, tunnel and scratch; always clean them up."""
from pathlib import Path
import os,subprocess,json,time,threading,re,shutil,urllib.request,signal,sys,fcntl,shlex,getpass,ipaddress
ROOT=Path(__file__).resolve().parent
LAB=Path(os.environ.get('LAB_DIR','/var/tmp/membench-longmemeval'))
OUT=ROOT/'results/full';PROOF=OUT/'proof'
for p in (LAB,OUT,PROOF):p.mkdir(parents=True,exist_ok=True)
HOST=os.environ['MODEL_HOST']
PORT=39711
DEADLINE=time.time()+min(int(os.environ.get('BUDGET_SECONDS','34200')),34200)
deadline_file=OUT/'authorized-deadline.json'
if deadline_file.exists():DEADLINE=min(DEADLINE,json.loads(deadline_file.read_text())['deadline_epoch'])
else:deadline_file.write_text(json.dumps({'deadline_epoch':DEADLINE,'purpose':'Fixed absolute wall-clock deadline for this run and all recoveries.'},indent=2)+'\n')
stop=threading.Event();tunnel=None;worker=None
def interrupted(signum,frame):raise KeyboardInterrupt('supervisor signal '+str(signum))
signal.signal(signal.SIGTERM,interrupted)
lock=open(LAB/'supervisor.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
def scrub(s):
 s=s.replace(HOST,'<model-host>')
 s=re.sub(r'/Users/[^/\s]+','<model-home>',s);s=re.sub(r'/home/[^/\s]+','<client-home>',s)
 for account in {HOST.rsplit('@',1)[0] if '@' in HOST else '',getpass.getuser()}:
  if account:s=re.sub(r'\b'+re.escape(account)+r'\b','<account>',s,flags=re.I)
 s=re.sub(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])','<address>',s)
 def mask_ipv6(match):
  token=match.group(0)
  try:ipaddress.IPv6Address(token.split('%',1)[0]);return '<address>'
  except ValueError:return token
 s=re.sub(r'(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]*:){2,}[0-9A-Fa-f]*(?:%[\w]+)?',mask_ipv6,s)
 return s
def ssh(command,check=True,timeout=90):
 r=subprocess.run(['ssh',HOST,command],capture_output=True,text=True,timeout=timeout)
 if check and r.returncode:raise RuntimeError('model-host command failed: '+scrub(r.stderr[-1500:]))
 return r
def write(p,d):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(d,indent=2));t.replace(p)
def proof(name,text):(PROOF/name).write_text(scrub(text))
def model_stop():
 ssh('if test -f ~/membench-longmemeval-tmp/server.pid; then pid=$(cat ~/membench-longmemeval-tmp/server.pid); if ps -p "$pid" -o command= | grep -q membench-longmemeval-tmp/model; then kill "$pid"; fi; fi',check=False)
def model_start():
 startup=shlex.quote('import mlx.core as mx\nmx.set_cache_limit(536870912)\nfrom mlx_lm.server import main\nmain()')
 cmd='export PATH=/opt/homebrew/bin:$PATH; export HF_HOME=$HOME/membench-longmemeval-tmp/hf; mkdir -p "$HF_HOME/hub"; if test -f ~/membench-longmemeval-tmp/server.pid && kill -0 $(cat ~/membench-longmemeval-tmp/server.pid) 2>/dev/null; then exit 0; fi; nohup /opt/homebrew/Cellar/mlx-lm/0.32.2_1/libexec/bin/python -c __STARTUP__ --model ~/membench-longmemeval-tmp/model --host localhost --port 39711 --prompt-cache-size 1 --prompt-cache-bytes 1073741824 --prefill-step-size 256 --max-tokens 512 >> ~/membench-longmemeval-tmp/server.log 2>&1 < /dev/null & echo $! > ~/membench-longmemeval-tmp/server.pid'
 ssh(cmd.replace('__STARTUP__',startup))
def ready():
 try:
  with urllib.request.urlopen('http://localhost:39711/v1/models',timeout=3) as r:return r.status==200
 except Exception:return False
def monitor():
 while not stop.is_set():
  try:
   r=ssh('sysctl -n kern.memorystatus_vm_pressure_level; memory_pressure | tail -1',timeout=20)
   lines=r.stdout.splitlines();level=int(lines[0]);free=int(re.search(r'(\d+)%',r.stdout)[1])
   safe=level==1
   if not safe:model_stop()
   if safe and free>=40 and not ready():model_start()
   state={'epoch':time.time(),'pressure_level':level,'free_percent':free,'ready':safe and ready()}
   write(LAB/'pressure.json',state)
   with (OUT/'pressure.jsonl').open('a') as f:f.write(json.dumps(state)+'\n')
  except Exception as e:
   write(LAB/'pressure.json',{'ready':False,'error':scrub(str(e))})
  stop.wait(20)

def cleanup(reason):
 stop.set()
 if 'mon' in globals():mon.join()
 if worker and worker.poll() is None:
  worker.terminate()
  try:worker.wait(15)
  except subprocess.TimeoutExpired:worker.kill();worker.wait()
 model_stop()
 if tunnel and tunnel.poll() is None:tunnel.terminate();tunnel.wait(timeout=15)
 time.sleep(2)
 proof('model-server.log',ssh('cat ~/membench-longmemeval-tmp/server.log',check=False).stdout)
 ssh('rm -rf ~/membench-longmemeval-tmp')
 remote_absent=ssh('test ! -e ~/membench-longmemeval-tmp',check=False).returncode==0
 after=ssh('df -h /; memory_pressure; ps -axo pid,comm,rss; lsof -nP -iTCP -sTCP:LISTEN').stdout
 proof('mac-after.txt',after)
 for name in ['run.log','supervisor.log','download.log']:
  p=LAB/name
  if p.exists():proof(name,p.read_text(errors='replace'))
 proof('client-before-cleanup.txt',subprocess.run(['bash','-c','df -h /\nps -axo pid,comm,rss'],capture_output=True,text=True).stdout)
 from summarize_large import summarize
 summary=summarize()
 port_check=ssh('lsof -t -iTCP:39711 -sTCP:LISTEN',check=False).stdout.strip()
 client_port=subprocess.run(['lsof','-t','-iTCP:39711','-sTCP:LISTEN'],capture_output=True,text=True).stdout.strip()
 before=(PROOF/'mac-before.txt').read_text()
 voice={str(pid):bool(re.search(r'^\s*'+str(pid)+r'\s',before,re.M) and re.search(r'^\s*'+str(pid)+r'\s',after,re.M)) for pid in [1075,27091,27548]}
 shutil.rmtree(LAB)
 proof('client-after.txt',subprocess.run(['bash','-c','df -h /\nps -axo pid,comm,rss'],capture_output=True,text=True).stdout)
 write(OUT/'cleanup.json',{'reason':reason,'epoch':time.time(),'client_scratch_absent':not LAB.exists(),'model_scratch_absent':remote_absent,'model_listeners':port_check,'client_listeners':client_port,'voice_pids_preserved':voice,'no_containers_started':True,'complete':summary['complete'],'audit_n':summary['manual_audit']['n']})
 write(OUT/'status.json',{'state':'finished' if summary['complete'] else 'interrupted','reason':reason,'cleanup_complete':not LAB.exists() and remote_absent and not port_check and not client_port,'epoch':time.time()})

reason='setup failure'
try:
 write(OUT/'status.json',{'state':'preparing','deadline_epoch':DEADLINE})
 pre=LAB/'preflight.txt'
 proof('mac-before.txt',pre.read_text() if pre.exists() else ssh('memory_pressure; df -h /; ps -axo pid,comm,rss; lsof -nP -iTCP -sTCP:LISTEN').stdout)
 proof('client-before.txt',subprocess.run(['bash','-c','df -h /\nps -axo pid,comm,rss'],capture_output=True,text=True).stdout)
 os.environ.update(UV_CACHE_DIR=str(LAB/'uv'),UV_PYTHON_INSTALL_DIR=str(LAB/'python'))
 if not (LAB/'venv/bin/python').exists():
  subprocess.run(['uv','venv','--python','3.13.18',str(LAB/'venv')],check=True)
  subprocess.run(['uv','pip','install','--python',str(LAB/'venv/bin/python'),'-r',str(ROOT/'requirements.txt')],check=True)
 # The serving model is fetched only on the serving host.
 ssh('export PATH=/opt/homebrew/bin:$PATH; mkdir -p ~/membench-longmemeval-tmp/hf/hub; export HF_HOME=$HOME/membench-longmemeval-tmp/hf; hf download mlx-community/gemma-2-9b-it-4bit --revision ff12eb39da2cd9b3b0f4b4f9ffb274603f05bb29 --local-dir ~/membench-longmemeval-tmp/model',timeout=1200)
 # Adopt an existing tunnel only when this invocation was explicitly told its owned PID.
 adopted=os.environ.get('OWNED_TUNNEL_PID')
 if adopted:
  os.kill(int(adopted),signal.SIGTERM)
  time.sleep(1)
 tunnel=subprocess.Popen(['ssh','-N','-L','localhost:39711:localhost:39711','-o','ExitOnForwardFailure=yes',HOST],stdin=subprocess.DEVNULL)
 write(LAB/'pressure.json',{'ready':False})
 mon=threading.Thread(target=monitor,daemon=True);mon.start()
 env=dict(os.environ,BASE_URL='http://localhost:39711/v1',DEADLINE_EPOCH=str(DEADLINE),LAB_DIR=str(LAB))
 with (LAB/'run.log').open('a') as out:
  worker=subprocess.Popen([str(LAB/'venv/bin/python'),str(ROOT/'large.py')],env=env,stdout=out,stderr=subprocess.STDOUT)
 write(OUT/'status.json',{'state':'running','deadline_epoch':DEADLINE,'worker_pid':worker.pid,'supervisor_pid':os.getpid()})
 while worker.poll() is None:
  if time.time()>DEADLINE:reason='wall-clock deadline';break
  time.sleep(5)
 else:reason='completed' if worker.returncode==0 else 'worker exit '+str(worker.returncode)
except KeyboardInterrupt as e:
 reason='interrupted: '+str(e);proof('supervisor-error.txt',reason)
except Exception as e:
 reason=scrub(type(e).__name__+': '+str(e));proof('supervisor-error.txt',reason)
finally:
 cleanup(reason)

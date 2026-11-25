"""Ownership-checked Mac serving. Code and scoring remain local."""
import concurrent.futures,json,os,re,shlex,subprocess,threading,time,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'
LAB='~/membench-extraction-tmp'
PORT=39744
LOCAL_PORT=39745
class Host:
 def __init__(self,slots=2,budget=0,deadline=None,target=None,hardware=None):
  self.target=target or os.environ['SSH_TARGET'];self.hardware=hardware or os.environ.get('SERVING_HARDWARE','Apple M3 Ultra, 96 GB');self.instance=os.environ.get('SERVING_INSTANCE','M3 main');self.slots=slots;self.budget=budget;self.deadline=deadline or time.time()+9*3600
  self.lock=threading.RLock();self.ready=threading.Event();self.done=threading.Event();self.model=None;self.pid=None;self.tunnel=None
  self.session=RESULTS/'host-session.json'
  self.owner=json.loads(self.session.read_text())['owner'] if self.session.exists() else 'extraction-v2-'+uuid.uuid4().hex
 def ssh(self,cmd,check=True):
  try:p=subprocess.run(['ssh','-o','ConnectTimeout=15',self.target,cmd],capture_output=True,text=True,timeout=1900)
  except subprocess.TimeoutExpired:raise RuntimeError('Remote operation timed out') from None
  if check and p.returncode:raise RuntimeError('Remote command failed: '+self.clean(p.stderr[-600:]))
  return p.stdout
 def clean(self,s):
  s=re.sub(r'/Users/[^/\s]+','<home>',s);s=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','<address>',s)
  return s.replace(self.target,'<serving-host>').replace(self.target.split('@')[0],'<account>')
 def snapshot(self,name):
  raw=self.ssh('df -h ~; memory_pressure -Q; sysctl -n kern.memorystatus_vm_pressure_level; ps -axo pid=,ucomm=,rss=; lsof -nP -iTCP -sTCP:LISTEN')
  lines=[]
  for line in raw.splitlines():
   if '/System/Volumes/Data'in line:lines.append(line.replace('/System/Volumes/Data','<data-volume>'))
   elif 'free percentage'in line or line.strip().isdigit():lines.append(line)
   elif re.match(r'^\s*\d+\s+\S+',line):
    a=line.split();lines.append(f'process {a[0]} {Path(a[1]).name} rss_kib={a[-1]}')
   elif '(LISTEN)'in line:
    a=line.split();lines.append(f'listener {a[0]} pid={a[1]} port={a[-2].rsplit(":",1)[-1]}')
  (RESULTS/name).write_text('\n'.join(lines)+'\n')
 def memory(self):
  raw=self.ssh('memory_pressure -Q; sysctl -n kern.memorystatus_vm_pressure_level')
  return int(re.search(r'free percentage: (\d+)%',raw)[1]),int(raw.strip().splitlines()[-1])
 def setup(self):
  RESULTS.mkdir(exist_ok=True)
  version=self.ssh('/opt/homebrew/bin/llama-server --version 2>&1')
  if '12359'not in version or 'b1b770d90'not in version:raise RuntimeError('Pinned server build required')
  
  if not (RESULTS/'host-before.txt').exists():self.snapshot('host-before.txt')
  protected=RESULTS/'protected-service-before.json'
  if not protected.exists():
   processes=[{'pid':int(line.split()[0]),'service':'omlx-server'}for line in self.ssh('ps -axo pid=,args=').splitlines()if 'omlx-server'in line or 'omlx.server'in line]
   protected.write_text(json.dumps({'checked_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'processes':processes,'method':'Read-only process inspection; only service class and PID retained.'},indent=2)+'\n')

  exists=self.ssh('test -e '+LAB+' && echo present',False).strip()
  if exists:
   if self.ssh('cat '+LAB+'/.owner',False).strip()!=self.owner:raise RuntimeError('Existing remote lab is not owned by this run')
  else:self.ssh('test ! -L '+LAB+' && mkdir '+LAB+' && printf %s '+shlex.quote(self.owner)+' > '+LAB+'/.owner')
  self.session.write_text(json.dumps({'owner':self.owner,'server_port':PORT,'local_port':LOCAL_PORT,'runtime':version.strip(),'serving_hardware':self.hardware,'serving_instance':self.instance},indent=2)+'\n')
  busy=self.ssh(f'lsof -nP -iTCP:{PORT} -sTCP:LISTEN -Fp',False).strip()
  if busy:raise RuntimeError('Task server port is occupied; no existing server was stopped')
  self.tunnel=subprocess.Popen(['ssh','-N','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-L',f'localhost:{LOCAL_PORT}:localhost:{PORT}',self.target],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  time.sleep(.5)
  if self.tunnel.poll()is not None:raise RuntimeError('Task tunnel failed')
  os.environ['BASE_URL']=f'http://localhost:{LOCAL_PORT}/v1'
  self.watcher=threading.Thread(target=self.watch,daemon=True);self.watcher.start()
 def stop(self):
  with self.lock:
   self.ready.clear()
   self.ssh("if [ -f "+LAB+"/server.pid ]; then p=$(cat "+LAB+"/server.pid); case $p in ''|*[!0-9]*) exit 1;; esac; args=$(ps -p $p -o args=); case $args in *llama-server*39744*) kill $p; for i in $(seq 1 30); do kill -0 $p 2>/dev/null || break; sleep 1; done; kill -0 $p 2>/dev/null && kill -KILL $p || true;; '') :;; *) exit 1;; esac; rm "+LAB+"/server.pid; fi")
   self.pid=None
 def download(self,model):
  filename=model['id']+'.gguf';size=model['bytes']
  have=int(self.ssh('test -f '+LAB+'/'+shlex.quote(filename)+' && stat -f %z '+LAB+'/'+shlex.quote(filename),False).strip() or 0)
  if have==size:return
  self.ssh('mkdir -p '+LAB+'/parts-'+model['id'])
  width=(size+7)//8
  def fetch(i):
   begin=i*width;end=min(size,(i+1)*width)-1;expected=end-begin+1
   part='parts-'+model['id']+'/'+str(i);url=model['url']+'?download=true&piece='+str(i)
   command='cd '+LAB+'; if [ -f '+part+' ] && [ "$(stat -f %z '+part+')" = '+str(expected)+' ]; then exit 0; fi; code=$(curl -LfsS --retry 1 --connect-timeout 30 --max-time 300 --max-filesize '+str(expected)+' --range '+str(begin)+'-'+str(end)+' -D '+part+'.headers -o '+part+'.partial -w "%{http_code}" '+shlex.quote(url)+'); [ "$code" = 206 ] && [ "$(stat -f %z '+part+'.partial)" = '+str(expected)+' ] && grep -iq "bytes '+str(begin)+'-'+str(end)+'/'+str(size)+'" '+part+'.headers && mv '+part+'.partial '+part+'; result=$?; rm -f '+part+'.headers; exit $result'
   self.ssh(command)
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(fetch,range(8)))
  pieces=' '.join('parts-'+model['id']+'/'+str(i)for i in range(8))
  self.ssh('cd '+LAB+' && cat '+pieces+' > '+shlex.quote(filename)+'.assembled && mv '+shlex.quote(filename)+'.assembled '+shlex.quote(filename))
 def load(self,model):
  with self.lock:
   self.stop();self.model=model
   filename=model['id']+'.gguf'
   self.download(model)
   digest=self.ssh('cd '+LAB+' && shasum -a 256 '+shlex.quote(filename)).split()[0]
   if digest!=model['sha256']:raise RuntimeError('Model bytes do not match pinned SHA-256')
   while True:
    if time.time()>self.deadline:raise TimeoutError('Run deadline reached')
    free,level=self.memory()
    if free>=40 and level==1:break
    self.event('waiting-for-memory',free_percent=free,level=level);time.sleep(5)
   args=['/opt/homebrew/bin/llama-server','-m',filename,'--alias','writer','--host','localhost','--port',str(PORT),'-c',str(4096*self.slots),'-np',str(self.slots),'--cache-ram','0','--jinja','--chat-template-kwargs','{"enable_thinking":false}']
   if self.budget is not None:args+=['--reasoning-budget',str(self.budget),'-b','512','-ub','128']
   self.ssh('cd '+LAB+'; nohup '+shlex.join(args)+' > server.log 2>&1 < /dev/null & echo $! > server.pid')
   self.pid=int(self.ssh('cat '+LAB+'/server.pid').strip())
   for _ in range(150):
    if time.time()>self.deadline:raise TimeoutError('Run deadline reached')
    try:
     with urllib.request.urlopen(f'http://localhost:{LOCAL_PORT}/health',timeout=2) as response:
      if json.load(response).get('status')=='ok':
       props=json.load(urllib.request.urlopen(f'http://localhost:{LOCAL_PORT}/props',timeout=5))
       if Path(props['model_path']).name!=filename:raise RuntimeError('Healthy endpoint has wrong model')
       self.event('model-loaded',model=model['id'],pid=self.pid,sha256=digest,slots=self.slots,reasoning_budget=self.budget,batch=512 if self.budget is not None else 'runtime-default',ubatch=128 if self.budget is not None else 'runtime-default')
       self.ready.set();return
    except OSError:pass
    time.sleep(1)
   (RESULTS/(model['id']+'-server-failure.txt')).write_text(self.clean(self.ssh('tail -60 '+LAB+'/server.log',False)))
   raise RuntimeError('Model server readiness failed')
 def event(self,kind,**data):
  with (RESULTS/'host-events.jsonl').open('a') as out:out.write(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'event':kind,'serving_hardware':self.hardware,'serving_instance':self.instance,**data})+'\n')
 def watch(self):
  while not self.done.wait(5):
   try:
    free,level=self.memory();self.event('memory',free_percent=free,level=level)
    if (level!=1 or ('M3 Ultra'in self.hardware and free<40)) and self.ready.is_set():
     self.event('memory-pause',free_percent=free,level=level);self.stop()
   except Exception as e:
    self.event('monitor-error',error=type(e).__name__);self.ready.clear()
 def ensure(self):
  if time.time()>self.deadline:raise TimeoutError('Run deadline reached')
  if not self.ready.is_set():
   with self.lock:
    if not self.ready.is_set():self.load(self.model)
 def close(self,cleanup=True):
  self.done.set();self.stop()
  if self.tunnel:
   self.tunnel.terminate();self.tunnel.wait(timeout=15)
  if hasattr(self,'watcher'):self.watcher.join(timeout=20)
  if cleanup:
   self.ssh('test ! -L '+LAB+' && test "$(cat '+LAB+'/.owner)" = '+shlex.quote(self.owner)+' && rm -rf '+LAB)
   self.snapshot('host-after.txt')
   (RESULTS/'cleanup.json').write_text(json.dumps({'remote_lab_absent':self.ssh('test ! -e '+LAB+' && echo yes').strip()=='yes','server_stopped':True,'tunnel_stopped':not self.tunnel or self.tunnel.poll()is not None,'phase':'complete','serving_hardware':self.hardware,'serving_instance':self.instance},indent=2)+'\n')
  else:self.event('phase-paused-model-files-retained',server_stopped=True,tunnel_stopped=True)

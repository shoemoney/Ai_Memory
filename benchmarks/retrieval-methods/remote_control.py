"""Deploy one isolated model server, monitor pressure, tunnel, and clean it."""
import argparse,json,os,shlex,signal,subprocess,time,requests,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent;LAB=Path(os.environ.get('LAB_DIR','/data/scratch/membench/retrieval-methods'));OUT=ROOT/'results'
TARGET=os.environ.get('SSH_TARGET')
if not TARGET:raise SystemExit('SSH_TARGET must name the explicitly assigned serving machine')
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3',TARGET]
REMOTE='membench-retrieval-methods-tmp'
def remote(code):return subprocess.check_output(SSH+['/usr/bin/python3 -c '+shlex.quote(code)],text=True)
def save(p,data):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(data));t.replace(p)
def snapshot():
 code="""import subprocess,json,re
from pathlib import Path
text=subprocess.check_output(['memory_pressure'],text=True);processes=[];listeners=[]
for line in subprocess.check_output(['ps','-axo','pid,comm'],text=True).splitlines()[1:]:
 fields=line.strip().split(None,1)
 if len(fields)==2 and any(s in fields[1].lower() for s in ['python','omlx','llama']):processes.append({'pid':int(fields[0]),'comm':Path(fields[1]).name})
for line in subprocess.check_output(['lsof','-nP','-iTCP','-sTCP:LISTEN'],text=True).splitlines()[1:]:
 fields=line.split()
 if len(fields)>8:
  port=fields[8].rsplit(':',1)[-1]
  if port.isdigit():listeners.append({'pid':int(fields[1]),'command':fields[0],'port':int(port)})
print(json.dumps({'free_percent':int(re.search(r'System-wide memory free percentage:\\s*(\\d+)%',text).group(1)),'kernel_level':int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True)),'process_listing':processes,'listeners':listeners,'df_h':subprocess.check_output(['df','-h',str(Path.home())],text=True),'hardware_class':subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip()+', '+str(int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True))//(1024**3))+' GB','scratch_exists':(Path.home()/'membench-retrieval-methods-tmp').exists()}))"""
 return json.loads(remote(code))
def deploy():
 before=snapshot();save(OUT/'mac-before.json',before)
 assert not any(r['port']==39790 for r in before['listeners']),'assigned Mac port occupied'
 subprocess.run(SSH+['mkdir -p ~/membench-retrieval-methods-tmp'],check=True)
 archive=LAB/'llama-mac.tar.gz'
 if not archive.exists():
  r=requests.get('https://github.com/ggml-org/llama.cpp/releases/download/b12627/llama-b12627-bin-macos-arm64.tar.gz',timeout=180);r.raise_for_status();archive.write_bytes(r.content)
 if not (LAB/'llama-mac').exists():tarfile.open(archive).extractall(LAB/'llama-mac',filter='data')
 for source,dest in [(str(LAB/'llama-mac')+'/',REMOTE+'/llama/'),(str(LAB/'qwen.gguf'),REMOTE+'/qwen.gguf'),(str(ROOT/'serve_mac.py'),REMOTE+'/serve_mac.py')]:subprocess.run(['rsync','-a',source,TARGET+':'+dest],check=True)
 code="from pathlib import Path;import hashlib,json; p=Path.home()/'membench-retrieval-methods-tmp/qwen.gguf';h=hashlib.sha256();f=p.open('rb');b=f.read(8388608)\nwhile b:h.update(b);b=f.read(8388608)\nprint(json.dumps({'sha256':h.hexdigest(),'bytes':p.stat().st_size}))"
 result=json.loads(remote(code));assert result['sha256']=='13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983';save(OUT/'mac-model-checksum.json',result);print('Mac serving assets deployed; no data or scoring copied',flush=True)
def stop():
 code="""from pathlib import Path
import os,signal,subprocess,json
lab=Path.home()/'membench-retrieval-methods-tmp';stopped=[]
for name in ['helper.pid','server.pid']:
 p=lab/name
 if not p.exists():continue
 pid=int(p.read_text());cmd=subprocess.run(['ps','-p',str(pid),'-o','command='],capture_output=True,text=True).stdout
 if str(lab) in cmd:
  try:os.kill(pid,signal.SIGTERM);stopped.append(pid)
  except ProcessLookupError:pass
print(json.dumps({'owned_pids_signaled':stopped}))"""
 print(remote(code).strip(),flush=True)
def serve():
 save(LAB/'mac-pressure.json',{'time':time.time(),'observed_at':time.time(),'ready':False,'reason':'controller_start'})
 stopping=False
 def halt(*args):
  nonlocal stopping
  stopping=True
 signal.signal(signal.SIGTERM,halt);signal.signal(signal.SIGINT,halt)
 tunnel=subprocess.Popen(SSH[:-1]+['-N','-T','-o','ExitOnForwardFailure=yes','-L','localhost:39791:localhost:39790',TARGET],stdout=subprocess.DEVNULL,stderr=(LAB/'tunnel.log').open('a'))
 helper=subprocess.Popen(SSH+['PREFIX_CTX_PER_SLOT='+str(int(os.environ.get('PREFIX_CTX_PER_SLOT','4096')))+' PREFIX_SLOTS='+str(int(os.environ.get('PREFIX_SLOTS','8')))+' exec /usr/bin/python3 -u ~/membench-retrieval-methods-tmp/serve_mac.py'],stdout=subprocess.PIPE,stderr=(LAB/'mac-helper.log').open('a'),text=True,bufsize=1)
 save(LAB/'mac-controller.json',{'pid':os.getpid(),'tunnel_pid':tunnel.pid,'ssh_helper_pid':helper.pid})
 try:
  import select
  while not stopping:
   if tunnel.poll() is not None:raise RuntimeError('owned tunnel exited')
   if helper.poll() is not None:raise RuntimeError('owned remote helper exited')
   readable,_,_=select.select([helper.stdout],[],[],1)
   if readable:
    line=helper.stdout.readline()
    if not line:continue
    state=json.loads(line);state['observed_at']=time.time();save(LAB/'mac-pressure.json',state)
    with (OUT/'mac-pressure.jsonl').open('a') as f:f.write(json.dumps(state)+'\n')
    if state.get('reason')!='normal':print(json.dumps(state),flush=True)
 finally:
  stop()
  for process in [helper,tunnel]:
   if process.poll() is None:
    process.terminate()
    try:process.wait(timeout=15)
    except subprocess.TimeoutExpired:process.kill();process.wait()
  save(LAB/'mac-pressure.json',{'time':time.time(),'ready':False,'reason':'controller_stopped'})
def cleanup():
 stop();time.sleep(2);before=snapshot()
 code="""from pathlib import Path
import subprocess,shutil,json
lab=Path.home()/'membench-retrieval-methods-tmp'
owned=[line for line in subprocess.check_output(['ps','-axo','command'],text=True).splitlines() if str(lab) in line and ('llama-server' in line or 'serve_mac.py' in line)]
assert not owned,'owned remote process still active'
if lab.exists():shutil.rmtree(lab)
print(json.dumps({'scratch_exists':lab.exists(),'owned_processes':len(owned)}))"""
 result=json.loads(remote(code));save(OUT/'mac-cleanup.json',{'before':before,'after':snapshot(),'cleanup':result,'other_services_stopped':False});print('Mac scratch and owned servers removed',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['deploy','serve','stop','cleanup']);a=p.parse_args();globals()[a.action]()

"""Remove only this completed experiment's resources, recording ownership checks.

Run with system Python after verification, with MODEL_SSH and TUNNEL_PID set.
The SSH destination is never written into retained evidence.
"""
import json,os,shutil,signal,socket,subprocess,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LAB=Path('/data/scratch/membench/membench')
OLD=Path('/var/tmp/membench-membench')

REMOTE=r'''
import collections,json,os,re,shutil,signal,socket,subprocess,time
from pathlib import Path
folder=Path.home()/'membench-membench-tmp'
def command(args):return subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout.strip()
def process(pid):return command(['ps','-p',str(pid),'-o','command='])
def alive(pid):return bool(process(pid))
def port_open():
 try:
  with socket.create_connection(('localhost',39780),timeout=2):return True
 except OSError:return False
guard=int((folder/'guard.pid').read_text());server=int((folder/'server.pid').read_text())
assert 'model_server_guard.sh' in process(guard),'Guard ownership mismatch'
assert '--port 39780' in process(server) and '--model model.gguf' in process(server),'Server ownership mismatch'
assert int(command(['ps','-p',str(server),'-o','ppid=']))==guard,'Server parent mismatch'
pressure=(folder/'pressure.log').read_text();log=(folder/'server.log').read_text()
others=[]
for line in command(['ps','-axo','pid=,comm=']).splitlines():
 fields=line.strip().split(None,1)
 if len(fields)!=2:continue
 pid=int(fields[0]);name=Path(fields[1]).name
 if pid not in [guard,server,os.getpid()] and (name in ['llama-server','omlx-server'] or name.lower().startswith('python')):others.append({'pid':pid,'executable':name})
evidence={'guard_pid':guard,'server_pid':server,'ownership_verified':True,
 'other_model_python_processes_before':others,
 'before_disk':command(['df','-h','/','/System/Volumes/Data']),
 'before_processes':command(['ps','-p',str(guard)+','+str(server),'-o','pid,ppid,command']).replace(str(Path.home()),'~'),
 'scratch_kib_before':command(['du','-sk',str(folder)]).split()[0],
 'pressure_levels':dict(collections.Counter(re.findall(r'pressure=(\d+)',pressure))),
 'warning_stops':pressure.count('STOP-WARNING'),
 'truncation_flags':dict(collections.Counter(re.findall(r'truncated = (\d+)',log))),
 'before_pressure':command(['sysctl','-n','kern.memorystatus_vm_pressure_level'])}
os.kill(guard,signal.SIGTERM)
for _ in range(30):
 if not alive(guard) and not alive(server):break
 time.sleep(.5)
for pid,needle in [(guard,'model_server_guard.sh'),(server,'--port 39780')]:
 if alive(pid):
  assert needle in process(pid),'PID changed ownership during shutdown'
  os.kill(pid,signal.SIGKILL)
time.sleep(1)
assert not alive(guard) and not alive(server) and not port_open(),'Task server still active'
assert folder==Path.home()/'membench-membench-tmp' and not folder.is_symlink()
shutil.rmtree(folder)
evidence.update(after_disk=command(['df','-h','/','/System/Volumes/Data']),
 after_processes=command(['ps','-p',str(guard)+','+str(server),'-o','pid,ppid,command']),
 server_port_closed=not port_open(),scratch_removed=not folder.exists(),
 other_processes_present_after=[dict(x,present=alive(x['pid'])) for x in others],
 after_pressure=command(['sysctl','-n','kern.memorystatus_vm_pressure_level']),
 processes_signaled=[guard,server])
print(json.dumps(evidence))
'''

def run(args):return subprocess.run(args,check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout.strip()
def closed():
 try:
  with socket.create_connection(('localhost',39780),timeout=2):return False
 except OSError:return True
def assert_no_task_interpreter():
 for proc in Path('/proc').glob('[0-9]*'):
  try:args=(proc/'cmdline').read_bytes().split(b'\0')
  except (OSError,PermissionError):continue
  assert not (args and args[0].decode(errors='replace').startswith(str(LAB)+'/')),'Task interpreter still running'
def main():
 out=ROOT/'results';verification=json.loads((out/'verification.json').read_text());assert verification['complete']
 pilot=json.loads((out/'arena-pilot'/'summary.json').read_text());assert all(x['n']==5 for x in pilot['methods'].values())
 audit=json.loads((out/'arena-pilot'/'manual-audit.json').read_text());assert len(audit['items'])==10
 assert_no_task_interpreter()
 host=os.environ['MODEL_SSH'];tunnel=int(os.environ['TUNNEL_PID'])
 command=Path(f'/proc/{tunnel}/cmdline').read_bytes().replace(b'\0',b' ').decode()
 assert 'ssh -N ' in command and '-L 127.0.0.1:39780:localhost:39780 ' in command and host in command,'Tunnel ownership mismatch'
 evidence={'completed_before_cleanup':True,'local_before_disk':run(['df','-h','/','/data']),
  'tunnel_pid':tunnel,'tunnel_command':command.replace(host,'[model host]'),
  'local_before_processes':run(['ps','-p',str(tunnel),'-o','pid,ppid,args']).replace(host,'[model host]'),
  'local_scratch_kib_before':run(['du','-sk',str(LAB)]).split()[0],
  'containers_images_volumes_created':[],'preexisting_managed_python_retained':True}
 remote=subprocess.run(['ssh','-T','-o','BatchMode=yes',host,'python3','-'],input=REMOTE,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
 evidence['model_host']=json.loads(remote.stdout)
 os.kill(tunnel,signal.SIGTERM)
 for _ in range(20):
  if not Path(f'/proc/{tunnel}').exists():break
  time.sleep(.25)
 assert not Path(f'/proc/{tunnel}').exists() and closed(),'Tunnel still active'
 # Refuse to delete an environment that still has an active interpreter.
 assert_no_task_interpreter()
 for folder in [LAB,OLD]:
  assert not folder.is_symlink()
  if folder.exists():shutil.rmtree(folder)
 for folder in ROOT.rglob('__pycache__'):shutil.rmtree(folder)
 evidence.update(local_after_disk=run(['df','-h','/','/data']),tunnel_removed=True,
  local_port_closed=closed(),data_scratch_removed=not LAB.exists(),old_scratch_removed=not OLD.exists(),
  local_after_processes=subprocess.run(['ps','-p',str(tunnel),'-o','pid,ppid,args'],text=True,stdout=subprocess.PIPE).stdout.strip(),
  complete=True)
 (out/'cleanup.json').write_text(json.dumps(evidence,indent=2)+'\n')
 print(json.dumps(evidence,indent=2))
if __name__=='__main__':main()

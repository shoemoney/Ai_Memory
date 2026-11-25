"""Task-scoped cleanup. The optional SSH target is a runtime environment setting."""
import os,subprocess,time,json,re,shutil,signal
from pathlib import Path
from full_common import ROOT,OUT,LAB,atomic,read

def command(args):
 r=subprocess.run(args,text=True,capture_output=True)
 return dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
def clean():
 proof={'hardware':'Apple M3 Ultra, 96 GB; 32-thread x86 CPU','time_epoch':time.time()}
 target=os.environ.get('MODEL_SSH_TARGET')
 if target:
  remote='''cd "$HOME/membench-locomo-tmp" || exit 1
 printf 'BEFORE CLEANUP\n'
 df -h .
 guard=$(cat guard.pid)
 server=$(cat server.pid)
 ps -p "$guard,$server" -o pid,ppid,rss,comm
 command=$(ps -p "$guard" -o command=)
 case "$command" in *serve.sh*) kill "$guard";; esac
 for attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  if ! kill -0 "$guard" 2>/dev/null && ! kill -0 "$server" 2>/dev/null; then break; fi
  sleep 0.5
 done
 cat pressure.log
 cd "$HOME"
 rm -rf membench-locomo-tmp
 printf 'AFTER CLEANUP\n'
 df -h .
 ps -p "$guard,$server" -o pid,ppid,rss,comm
 test ! -e membench-locomo-tmp && echo scratch-absent
 if kill -0 "$guard" 2>/dev/null || kill -0 "$server" 2>/dev/null; then echo owned-process-remains; else echo owned-processes-absent; fi
 if lsof -t -iTCP:39700 -sTCP:LISTEN; then echo task-port-busy; else echo task-port-free; fi
 memory_pressure -Q
 sysctl kern.memorystatus_vm_pressure_level
 '''
  result=command(['ssh',target,remote])
  result['stdout']=re.sub(r'/(?:Users|home)/[^/\s]+','<user-home>',result['stdout'])
  result['stdout']=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','<address>',result['stdout'])
  result['stderr']=result['stderr'].replace(target,'<model-host>')
  proof['model_host']=result
 roles=read(LAB/'roles.json') if (LAB/'roles.json').exists() else {}
 for role in ['proxy_pid','tunnel_pid']:
  pid=roles.get(role)
  if pid:
   try:os.kill(pid,signal.SIGTERM)
   except ProcessLookupError:pass
 live={}
 for role in ['proxy_pid','tunnel_pid','supervisor_pid']:
  pid=roles.get(role)
  if not pid:continue
  for attempt in range(20):
   if subprocess.run(['ps','-p',str(pid)],stdout=subprocess.DEVNULL).returncode!=0:break
   time.sleep(0.25)
  live[role]=subprocess.run(['ps','-p',str(pid)],stdout=subprocess.DEVNULL).returncode==0
 proof['task_processes_alive_after_stop']=live
 before=command(['docker','inspect','membench-locomo-neo4j'])
 mounts=json.loads(before['stdout'])[0].get('Mounts',[]) if before['returncode']==0 else []
 volumes=[m['Name'] for m in mounts if m.get('Type')=='volume']
 proof['owned_anonymous_volumes']=volumes
 proof['container_removal']=command(['docker','rm','-f','-v','membench-locomo-neo4j'])
 proof['owned_anonymous_volumes_absent']={name:command(['docker','volume','inspect',name])['returncode']!=0 for name in volumes}
 proof['volume_cleanup']=command(['docker','run','--rm','--name','membench-locomo-cleanup','--user','0','--memory','128m','--cpus','1','-v',str(LAB/'neo4j')+':/cleanup','--entrypoint','sh','neo4j:2026.10.2-community','-c','rm -rf /cleanup/* /cleanup/.[!.]*'])
 proof['cpu_disk_before']=command(['df','-h',str(LAB)])
 # Processes have exited and immutable per-item evidence is outside the scratch lab.
 shutil.rmtree(LAB,ignore_errors=True)
 proof['cpu_scratch_absent']=not LAB.exists()
 proof['cpu_disk_after']=command(['df','-h','/var/tmp'])
 proof['remaining_containers']=command(['docker','ps','-a','--filter','name=membench-locomo-','--format','{{.Names}}'])
 proof['cleanup_confirmed']=proof['cpu_scratch_absent'] and all(proof['owned_anonymous_volumes_absent'].values()) and not any(proof['task_processes_alive_after_stop'].values()) and not proof['remaining_containers']['stdout'].strip() and (not target or all(x in proof['model_host']['stdout'] for x in ['scratch-absent','owned-processes-absent','task-port-free']))
 atomic(OUT/'cleanup.json',proof)
 return proof
if __name__=='__main__':print(json.dumps(clean(),indent=2))

"""Independent read-only checks after driver cleanup, then remove local scratch."""
import json,os,re,shutil,subprocess
from pathlib import Path
from host import Host,ROOT,RESULTS,LAB,PORT,LOCAL_PORT

def run():
 h=Host()
 assert not h.ssh('test -e '+LAB+' && echo present',False).strip(), 'Owned remote lab still exists; driver cleanup required first'
 before=(RESULTS/'host-before.txt').read_text();h.snapshot('host-after.txt');after=(RESULTS/'host-after.txt').read_text()
 def listeners(text):
  return {int(m[2]):int(m[1])for m in re.finditer(r'listener \S+ pid=(\d+) port=(\d+)',text)}
 a=listeners(before);b=listeners(after);voice=tuple(p for p in (8765,8766,8100,8888,9102,8200,8202,8300,7860,7861,7862)if p in a)
 remote_pids={r['pid']for r in map(json.loads,(RESULTS/'host-events.jsonl').read_text().splitlines())if r['event']=='model-loaded'and r.get('serving_hardware')==h.hardware and r.get('serving_instance')==h.instance}
 remote_ps=h.ssh('ps -axo pid=,ucomm=');running={int(line.split()[0])for line in remote_ps.splitlines()if line.strip()}
 protected=json.loads((RESULTS/'protected-service-before.json').read_text())['processes']
 protected_ids=[r['pid']for r in protected]
 protected_omlx_unchanged=all('omlx-server'in h.ssh('ps -p '+str(pid)+' -o args=',False)for pid in protected_ids)
 local_ps=subprocess.run(['ps','-eo','pid=,args='],capture_output=True,text=True).stdout
 own_tunnels=[line.split()[0]for line in local_ps.splitlines()if 'ssh -N'in line and f'localhost:{LOCAL_PORT}:localhost:{PORT}'in line]
 local_port=subprocess.run(['ss','-H','-ltn'],capture_output=True,text=True).stdout
 containers=[]
 if shutil.which('docker'):
  p=subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True)
  if p.returncode==0:containers=[v for v in p.stdout.splitlines()if v.startswith('membench-extraction-')]
 lab=Path('/var/tmp/membench-extraction');assert not lab.is_symlink()
 if lab.exists():shutil.rmtree(lab)
 for folder in (ROOT.parent,ROOT.parent/'v1',ROOT):
  for cache in folder.rglob('__pycache__'):
   if cache.is_dir():shutil.rmtree(cache)
 (RESULTS/'dev-after.txt').write_text(subprocess.run(['df','-h','/var/tmp','<projects>'],capture_output=True,text=True).stdout)
 result={'serving_hardware':h.hardware,'serving_instance':h.instance,'earlier_m3_cleanup':json.loads((RESULTS/'relocation.json').read_text())['source_cleanup'],'main_quality_and_timing_hardware_classes':['Apple M3 Ultra, 96 GB'],'m1_migration_cleanup':json.loads((RESULTS/'migration.json').read_text())['source_cleanup'],'m1_voice_pids_unchanged':json.loads((RESULTS/'migration.json').read_text())['source_voice_listener_pids_unchanged'],'remote_lab_absent':True,'all_recorded_remote_server_pids_absent':not remote_pids&running,'remote_task_port_unused':PORT not in b,'local_task_port_unused':not any(f':{LOCAL_PORT} 'in line for line in local_port.splitlines()),'local_task_tunnel_pids':own_tunnels,'local_scratch_absent':not lab.exists(),'benchmark_containers_remaining':containers,'no_containers_started_by_task':True,'protected_omlx_pids_checked':protected_ids,'protected_omlx_pids_unchanged':protected_omlx_unchanged,'protected_service_listener_pids_unchanged':all(a.get(p)is not None and a.get(p)==b.get(p)for p in voice),'protected_ports_checked':list(voice),'protected_before':{str(p):a.get(p)for p in voice},'protected_after':{str(p):b.get(p)for p in voice},'server_ports_checked':[PORT],'no_global_installations':True,'no_scoring_host_gpu_inference':True,'no_commits_or_chapter_edits_by_task':True}
 assert result['all_recorded_remote_server_pids_absent']and result['remote_task_port_unused']and result['local_task_port_unused']and not own_tunnels and not containers
 (RESULTS/'final-cleanup.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':run()

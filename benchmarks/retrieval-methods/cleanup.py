"""Remove only the benchmark-owned scratch target and owned local server."""
import json,os,signal,subprocess,shutil,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;LAB=Path(os.environ.get('LAB_DIR','/data/scratch/membench/retrieval-methods'));OUT=ROOT/'results'
controller_file=LAB/'mac-controller.json'
controller=json.loads(controller_file.read_text()) if controller_file.exists() else {}
known_ssh_pids={controller.get('tunnel_pid'),controller.get('ssh_helper_pid')}
def processes():
 rows=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   argv=p.joinpath('cmdline').read_bytes().decode(errors='replace').split('\0')
   if any(a.endswith('/retrieval-methods/run.py') for a in argv) or (any(a.endswith('/retrieval-methods/remote_control.py') for a in argv) and 'serve' in argv) or any(str(LAB)+'/llama/' in a for a in argv) or (int(p.name) in known_ssh_pids and any('39791' in a or 'serve_mac.py' in a for a in argv)):rows.append({'pid':int(p.name),'comm':p.joinpath('comm').read_text().strip()})
  except OSError:pass
 return rows
def snapshot():return {'df_h':subprocess.check_output(['df','-h','/var/tmp','/data'],text=True),'owned_process_listing':processes(),'gpu_compute_process_listing':subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader'],text=True)}
proof={'before':snapshot()}
if (OUT/'mac-before.json').exists():
 mac=json.loads((OUT/'mac-cleanup.json').read_text())
 assert not mac['cleanup']['scratch_exists'] and mac['cleanup']['owned_processes']==0,'Finish Mac cleanup first'
 assert mac['after']['hardware_class']==json.loads((OUT/'mac-before.json').read_text())['hardware_class'],'Mac cleanup does not match latest deployment'
 for archived in OUT.glob('mac-cleanup-*.json'):
  previous=json.loads(archived.read_text());assert not previous['cleanup']['scratch_exists'] and previous['cleanup']['owned_processes']==0
assert not proof['before']['owned_process_listing'],'Finish owned jobs before cleanup.'
target=LAB.resolve();allowed=[Path('/data/scratch/membench/retrieval-methods'),ROOT/'.scratch']
assert target in allowed,(target,allowed)
compatibility=Path('/var/tmp/membench-retrieval-methods')
if compatibility.is_symlink() and compatibility.resolve()==target:compatibility.unlink()
if LAB.is_symlink():LAB.unlink()
if target.exists():shutil.rmtree(target)
if (ROOT/'__pycache__').exists():shutil.rmtree(ROOT/'__pycache__')
proof.update({'after':snapshot(),'scratch_exists':LAB.exists() or LAB.is_symlink(),'scratch_target_exists':target.exists(),'compatibility_alias_exists':compatibility.exists() or compatibility.is_symlink(),'containers_started':False,'tunnels_started':bool(controller),'old_territory_scratch_exists':(ROOT/'.scratch').exists(),'other_processes_stopped':False,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
(OUT/'cleanup.json').write_text(json.dumps(proof,indent=2))
print(json.dumps(proof,indent=2))

confirmed=not proof['scratch_exists'] and not proof['scratch_target_exists'] and not proof['compatibility_alias_exists'] and not proof['after']['owned_process_listing']
assert confirmed,'Cleanup incomplete'
for name in ['README.md','REPORT.md']:
 p=ROOT/name;text=p.read_text().split('\n<!-- CLEANUP PROOF -->')[0]
 text=text.replace('Scratch, local models, and inference processes will be removed after scoring; cleanup proof will be retained without machine identifiers.','Scratch, local models, and inference processes were removed after scoring; cleanup proof is retained without machine identifiers.')
 p.write_text(text+'\n<!-- CLEANUP PROOF -->\nCleanup confirmed: all benchmark scratch directories and the compatibility alias are absent, and no owned inference process remains. No containers were started. The owned tunnel was closed, and no other task process was stopped. See `results/cleanup.json` for before/after disk and process listings.\n')

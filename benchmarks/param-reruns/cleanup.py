"""Remove only this task's scratch after every synchronous worker has exited."""
import json, os, shutil, subprocess, time
from pathlib import Path
from common import ROOT, SCRATCH

def main():
    # Refuse overly broad or non-task-specific destinations, including custom scratch roots.
    if SCRATCH.name!='param-reruns' or SCRATCH.is_symlink() or SCRATCH.resolve()==ROOT or SCRATCH.resolve() in ROOT.parents or ROOT in SCRATCH.resolve().parents:
        raise RuntimeError('Scratch must be a non-symlink directory named param-reruns')
    listing=subprocess.check_output(['ps','-eo','pid,ppid,comm,rss'],text=True)
    before=subprocess.check_output(['df','-h','/data','/var/tmp'],text=True)
    # Keep shared tool cache intact: uv forbids direct mutation, and package-wide cleanup
    # would also clear other jobs' cached versions. Only owned scratch is deleted here.
    cache_manifest=ROOT/'results'/'tool-cache-owned.json'
    tracked_shared_wheels=len(json.loads(cache_manifest.read_text()).get('artifacts',[])) if cache_manifest.exists() else 0
    active=[]
    worker_names=['benchmarks/param-reruns/'+p.name for p in ROOT.glob('*.py') if p.name!='cleanup.py']+['benchmarks/param-reruns/memgen/run.py','benchmarks/param-reruns/cartridges/run.py']
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            arguments=(proc/'cmdline').read_bytes().split(b'\0')
            if int(proc.name)!=os.getpid() and arguments and arguments[0].decode(errors='replace').startswith(str(SCRATCH/'venv'/'bin'/'python')): active.append(int(proc.name))
            elif any(any(name.encode() in argument for name in worker_names) for argument in arguments):
                # Do not match shell command strings that merely contain the worker's name.
                if any(argument.decode(errors='replace').endswith(tuple(worker_names)) for argument in arguments): active.append(int(proc.name))
        except (FileNotFoundError,PermissionError,ProcessLookupError): pass
    if active: raise RuntimeError('Task workers still active: '+str(active))
    owned_uv_cache=SCRATCH/'uv-cache'
    uv_cleanup=''
    if owned_uv_cache.exists(): uv_cleanup=subprocess.run(['uv','cache','clean','--cache-dir',str(owned_uv_cache)],check=True,capture_output=True,text=True).stderr
    if SCRATCH.exists(): shutil.rmtree(SCRATCH)
    small=Path('/var/tmp/membench-param-reruns')
    if small.exists(): shutil.rmtree(small)
    for directory in ROOT.rglob('__pycache__'): shutil.rmtree(directory)
    after=subprocess.check_output(['df','-h','/data','/var/tmp'],text=True)
    proof={'time':time.time(),'shared_uv_cache_preserved':True,'tracked_task_created_shared_wheels':tracked_shared_wheels,'cache_safety_source':'https://docs.astral.sh/uv/concepts/cache/#cache-safety','active_task_worker_pids':active,'owned_uv_cache_cleanup':uv_cleanup,'scratch_removed':not SCRATCH.exists(),'small_scratch_removed':not small.exists(),'servers_started':0,'tunnels_started':0,'containers_started':0,'images_pulled':0,'volumes_created':0,'disk_before':before,'disk_after':after,'processes_before':listing,'processes_after':subprocess.check_output(['ps','-eo','pid,ppid,comm,rss'],text=True)}
    (ROOT/'results'/'cleanup.json').write_text(json.dumps(proof,indent=2)+'\n')

if __name__=='__main__': main()

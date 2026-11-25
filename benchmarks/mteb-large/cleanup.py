#!/usr/bin/env python3
"""Remove only owner-checked task scratch and worker processes."""
import json,os,shlex,shutil,signal,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ROOTS=[Path('/var/tmp/membench-mteb-large'),Path('/data/scratch/membench/mteb-large')]

def main():
    owned=[p for p in ROOTS if p.is_dir() and not p.is_symlink() and (p/'.owner').is_file()]
    assert owned,'No owned scratch to clean'
    token=(owned[-1]/'.owner').read_text().strip()
    assert token and all((p/'.owner').read_text().strip()==token for p in owned)
    stopped=[]
    tunnel_pids={int((p/'tunnel.pid').read_text()) for p in owned if (p/'tunnel.pid').exists()}
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            argv=proc.joinpath('cmdline').read_bytes().split(b'\0')
            text=' '.join(x.decode(errors='replace') for x in argv)
            is_our_python=argv and any(argv[0].decode(errors='replace').startswith(str(p/'venv')) for p in ROOTS)
            if is_our_python:
                assert 'server.py' in text,'A client is still using scratch; finish it before cleanup'
                os.kill(int(proc.name),signal.SIGTERM);stopped.append(int(proc.name))
            elif int(proc.name) in tunnel_pids and argv and Path(argv[0].decode()).name=='ssh' and b'39740:127.0.0.1:39740' in argv:
                os.kill(int(proc.name),signal.SIGTERM);stopped.append(int(proc.name))
        except (OSError,ValueError):pass
    host=os.environ['MODEL_SSH']
    qtoken=shlex.quote(token)
    command=f'''cd ~/membench-mteb-large-tmp && test "$(cat .owner)" = {qtoken} && if test -f server.pid; then p=$(cat server.pid); c=$(ps -p "$p" -o command=); case "$c" in *membench-mteb-large-tmp*server.py*) kill "$p";; esac; fi; test "$(cat ~/membench-mteb-large-tmp/.owner)" = {qtoken} && rm -rf ~/membench-mteb-large-tmp'''
    remote=subprocess.run(['ssh',host,command],capture_output=True,text=True)
    removed=[]
    for p in owned:
        assert not p.is_symlink() and (p/'.owner').read_text().strip()==token
        shutil.rmtree(p);removed.append(str(p))
    check=subprocess.run(['ssh',host,'test ! -e ~/membench-mteb-large-tmp'],capture_output=True)
    proof={'local_scratch_removed':all(not p.exists() for p in ROOTS),'removed_paths':removed,
           'model_host_scratch_removed':remote.returncode==0 and check.returncode==0,
           'owned_processes_stopped_during_cleanup':stopped,
           'containers_started':0,'images_pulled':0,'volumes_created':0,
           'shared_model_service_changed':False,
           'cache_scope':'Task model, dataset, embedding and dedicated package caches removed. Shared package-manager caches were not pruned.',
           'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    (ROOT/'results/cleanup.json').write_text(json.dumps(proof,indent=2)+'\n')
    subprocess.run(['python3','resources.py','after'],cwd=ROOT,check=True)
    subprocess.run(['python3','report.py'],cwd=ROOT,check=True)
    assert proof['local_scratch_removed'] and proof['model_host_scratch_removed'],proof
    print('Owner-checked cleanup confirmed')
if __name__=='__main__':main()

"""Read-only memory monitor; can terminate only our recorded server PID."""
import json, os, re, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
remote=os.environ['SSH_TARGET']
while True:
    command='memory_pressure -Q; sysctl -n kern.memorystatus_vm_pressure_level'
    p=subprocess.run(['ssh',remote,command],text=True,capture_output=True)
    lines=p.stdout.strip().splitlines()
    if p.returncode: raise SystemExit('Memory monitoring failed; stop the benchmark server.')
    free=int(re.search(r'free percentage: (\d+)%',p.stdout)[1]); level=int(lines[-1])
    with (ROOT/'results/memory.jsonl').open('a') as out: out.write(json.dumps({'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'free_percent':free,'pressure_level':level})+'\n')
    if level!=1:
        subprocess.run(['ssh',remote,"p=$(cat ~/membench-extraction-tmp/server.pid); case $p in ''|*[!0-9]*) exit 1;; esac; args=$(ps -p $p -o args=); case $args in *llama-server*39740*) kill $p;; *) exit 1;; esac"],check=True)
        raise SystemExit('Stopped benchmark server because memory pressure is elevated.')
    time.sleep(5)

#!/usr/bin/env python3
"""Record cleanup evidence without hostnames, command arguments, or user names."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent

def run(args):
    r=subprocess.run(args,text=True,capture_output=True)
    if args[0] == 'pgrep' and r.returncode == 1:
        return ''
    return r.stdout if r.returncode == 0 else 'unavailable (exit '+str(r.returncode)+')'

phase=sys.argv[1]
assert phase in ['before','after']
df=run(['df','-h','/','/var/tmp'])
df='\n'.join('filesystem '+line.split(None,1)[1] if i else line for i,line in enumerate(df.splitlines()))
records={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'df':df,
    'processes':run(['ps','-eo','pid,comm,rss','--sort=-rss']),
    'gpu':run(['nvidia-smi','--query-gpu=name,memory.total,memory.used','--format=csv']),
    'gpu_processes':run(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv']),
    'task_containers':run(['docker','ps','-a','--filter','name=membench-mteb-','--format','{{.Names}} {{.Status}}']),
    'scratch_exists':Path('/var/tmp/membench-mteb').exists() or Path('/var/tmp/membench-mteb').is_symlink(),
    'scratch_processes':run(['pgrep','-f','^/var/tmp/membench-mteb/']),
    'servers_or_tunnels_started':False}
(ROOT/'results'/('resources-'+phase+'.json')).write_text(json.dumps(records,indent=2)+'\n')
print(df)
print(records['gpu'])
print('Scratch exists:',records['scratch_exists'])
print('Task containers:',records['task_containers'].strip() or 'none')

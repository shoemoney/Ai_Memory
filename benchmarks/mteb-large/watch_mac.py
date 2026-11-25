#!/usr/bin/env python3
"""Observe admission without changing any existing model service."""
import json,os,subprocess,time
from pathlib import Path
from resources import clean
ROOT=Path(__file__).resolve().parent
end=time.monotonic()+1800
with (ROOT/'results'/'memory-observations.jsonl').open('a') as out:
 while time.monotonic()<end:
  p=subprocess.run(['ssh',os.environ['MODEL_SSH'],"memory_pressure | tail -1; sysctl -n kern.memorystatus_vm_pressure_level"],capture_output=True,text=True,timeout=30)
  row={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'exit':p.returncode,'observation':clean(p.stdout)}
  out.write(json.dumps(row)+'\n');out.flush();print(json.dumps(row),flush=True)
  if p.returncode==0 and p.stdout.strip().endswith('\n1'):
   free=int(p.stdout.split('percentage: ')[1].split('%')[0])
   if free>=40:break
  time.sleep(30)

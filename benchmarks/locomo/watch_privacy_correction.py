"""Observe the two privacy-corrected baseline items and enforce the run deadline."""
import os,signal,time
from full_common import *
p=OUT/'privacy-correction.json';state=read(p)
while LAB.exists():
 complete=all(item_path(b,{'item_id':state['item_id']}).exists() and read(item_path(b,{'item_id':state['item_id']})).get('complete') for b in ['full-context','rag'])
 if complete:break
 alive=[]
 for pid in state['pids']:
  try:
   if (Path('/proc')/str(pid)/'stat').read_text().split()[2]!='Z':alive.append(pid)
  except FileNotFoundError:pass
 if not alive:break
 if time.time()>=read(OUT/'status.json')['deadline_epoch']:
  for pid in alive:
   try:os.killpg(pid,signal.SIGTERM)
   except ProcessLookupError:pass
  break
 time.sleep(5)
state.update(state='completed' if complete else 'failed',end_epoch=time.time());atomic(p,state)

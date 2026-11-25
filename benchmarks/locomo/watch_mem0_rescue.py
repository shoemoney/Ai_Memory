"""Observe Mem0 schema-recovery workers and enforce the original deadline."""
import os,signal,time
from full_common import *
p=OUT/'mem0-schema-rescue.json'
while LAB.exists():
 state=read(p);running=False
 for ci,job in state['jobs'].items():
  if job['state']!='running':continue
  pid=job['pid']
  try:alive=(Path('/proc')/str(pid)/'stat').read_text().split()[2]!='Z'
  except FileNotFoundError:alive=False
  if alive and time.time()<read(OUT/'status.json')['deadline_epoch']:running=True;continue
  if alive:
   try:os.killpg(pid,signal.SIGTERM)
   except ProcessLookupError:pass
  qs=[q for q in read(OUT/'selection.json') if q['conversation']==int(ci)]
  complete=all(item_path('mem0',q).exists() and read(item_path('mem0',q)).get('complete') for q in qs)
  job.update(state='completed' if complete else 'failed',end_epoch=time.time())
 atomic(p,state)
 if not running:break
 time.sleep(5)

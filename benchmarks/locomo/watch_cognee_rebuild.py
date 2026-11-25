"""Bound the task-scoped WAL rebuild by the unchanged model deadline."""
import os,signal,time
from full_common import *

while LAB.exists():
 p=OUT/'cognee-wal-rebuild.json';state=read(p);pid=state['pid']
 try:alive=(Path('/proc')/str(pid)/'stat').read_text().split()[2]!='Z'
 except FileNotFoundError:alive=False
 if alive and time.time()<state['deadline_epoch']:
  time.sleep(5);continue
 if alive:
  try:os.killpg(pid,signal.SIGTERM)
  except ProcessLookupError:pass
 qs=[q for q in read(OUT/'selection.json') if q['conversation']==state['conversation']]
 complete=all(item_path('cognee',q).exists() and read(item_path('cognee',q)).get('complete') for q in qs)
 state.update(state='completed' if complete else 'failed',end_epoch=time.time());atomic(p,state)
 pipeline=read(OUT/'cognee-pipeline.json');pipeline['jobs']['2'].update(state=state['state'],end_epoch=time.time());atomic(OUT/'cognee-pipeline.json',pipeline)
 break

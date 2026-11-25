"""Bound and observe the one Graphiti technical retry without orphaning a worker."""
import os,signal,time
from full_common import *
p=OUT/'graphiti-rescue.json';state=read(p);pid=state['pid']
while LAB.exists():
 try:alive=(Path('/proc')/str(pid)/'stat').read_text().split()[2]!='Z'
 except FileNotFoundError:alive=False
 if not alive:break
 current=read(p);limit=read(OUT/'status.json')['deadline_epoch']
 if not (OUT/current.get('repair_marker','absent')).exists():limit=min(limit,current.get('repair_deadline_epoch',float('inf')))
 if time.time()>=limit:
  try:os.killpg(pid,signal.SIGTERM)
  except ProcessLookupError:pass
  break
 time.sleep(5)
qs=[q for q in read(OUT/'selection.json') if q['conversation']==state['conversation']]
complete=all(item_path('graphiti',q).exists() and read(item_path('graphiti',q)).get('complete') for q in qs)
state.update(state='completed' if complete else 'failed',end_epoch=time.time());atomic(p,state)
if complete:
 failures=read(OUT/'failures.json')
 for f in failures:
  if f.get('backend')=='graphiti' and f.get('conversation')==state['conversation']:f.update(resolved=True,resolution='Adaptive session splitting after structured extraction length failure; all selected answers and three-vote judgments complete.')
 atomic(OUT/'failures.json',failures)

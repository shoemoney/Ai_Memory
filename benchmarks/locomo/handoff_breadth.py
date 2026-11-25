"""One-time transition from the already-running supervisor to paired blocks."""
import os,time,subprocess
from full_common import *
roles=read(LAB/'roles.json');previous=roles['supervisor_pid']
while LAB.exists():
 try:
  state=(Path('/proc')/str(previous)/'stat').read_text().split()[2]
  alive=state!='Z'
 except FileNotFoundError:alive=False
 if not alive:break
 time.sleep(5)
if LAB.exists() and time.time()<read(OUT/'status.json')['deadline_epoch']:
 status=read(OUT/'status.json')
 failures=read(OUT/'failures.json') if (OUT/'failures.json').exists() else status.get('failures',[])
 if not any(not f.get('resolved') for f in failures):
  with (LAB/'supervisor-breadth.log').open('a') as output:
   proc=subprocess.Popen([str(LAB/'venv/bin/python'),str(ROOT/'supervise_full.py')],stdout=output,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,RUN_HOURS=str((status['deadline_epoch']-status['start_epoch'])/3600)))
  roles=read(LAB/'roles.json');roles['supervisor_pid']=proc.pid;atomic(LAB/'roles.json',roles)
  log('breadth_supervisor_handoff',previous_pid=previous,supervisor_pid=proc.pid,deadline_epoch=status['deadline_epoch'])

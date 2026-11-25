"""Read-only operational status for the checkpointed common-question continuation."""
import json
import shutil
import subprocess
import time
from full_common import RUN_DIR, MODELS

def status():
 out=RUN_DIR
 state=json.loads((out/'run-state.json').read_text())
 manifest=json.loads((out/'manifest.json').read_text())
 size=next((s for s in MODELS if s not in state['finished_models']),None)
 service=subprocess.run(['systemctl','--user','is-active','membench-bfcl-full'],text=True,capture_output=True).stdout.strip()
 row={'utc':time.strftime('%H:%M',time.gmtime()),'model':size,'finished':state['finished_models'],'service':service,'free_gib':round(shutil.disk_usage('/').free/2**30,1),'data_free_gib':round(shutil.disk_usage('/data').free/2**30,1),'deadline':state['deadline'],'terminal':(out/'DONE.json').exists() and service not in ['active','activating','deactivating']}
 phase_times=[e['time'] for e in state.get('events',[]) if e.get('size')==size and e['event'] in ['model_start','serving_profile','memory_resumed']]
 row['startup_age']=round(time.time()-max(phase_times)) if phase_times else 0
 row['memory_paused']=bool(state.get('pressure_pause'))
 row['qualifying_checks']=state.get('pressure_pause',{}).get('qualifying_checks',0)
 row['pause_credit_seconds']=sum(p['credited_seconds'] for p in state.get('pause_credits',[]))+state.get('pressure_pause',{}).get('credited_seconds',0)
 row['pause_credit_limit_seconds']=state.get('pause_credit_limit_seconds',36000)
 if size:
  counts={}
  for mode in ['off','on']:
   counts[mode]=sum(len(set(manifest['categories'][cat]['selected_ids'])&{p.stem for p in (out/size/mode/'items'/cat).glob('*.json')}) for cat in manifest['leaf_weights'])
  row['selected_completed']=counts
  row['selected_target_per_mode']=sum(len(manifest['categories'][cat]['selected_ids']) for cat in manifest['leaf_weights'])
  for name in ['progress','heartbeat']:
   p=out/size/(name+'.json')
   if p.exists():
    saved=json.loads(p.read_text());row[name+'_age']=round(time.time()-saved['time'])
    if name=='progress':row['error_counter']=saved['errors']
 if (out/'DONE.json').exists():row['done']=json.loads((out/'DONE.json').read_text())
 return row

if __name__=='__main__':print(json.dumps(status()))

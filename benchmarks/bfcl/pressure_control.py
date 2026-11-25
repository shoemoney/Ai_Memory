"""Persistent pressure-stop hysteresis and bounded, timestamped pause credits."""
import datetime
from full_common import atomic

LIMIT_SECONDS=10*3600

def used_credit(state):
 return sum(p['credited_seconds'] for p in state.get('pause_credits',[]))+state.get('pressure_pause',{}).get('credited_seconds',0)

def begin_pause(state,size,now,reason):
 if state.get('pressure_pause'):return state['pressure_pause']
 stamp=datetime.datetime.fromtimestamp(now,datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
 p={'type':'memory_pressure','size':size,'started':now,'last_credit_at':now,'credited_seconds':0,'qualifying_checks':0,'last_qualifying_check':None,'reason':reason,'proof_folder':'pauses/memory-'+stamp}
 state['pressure_pause']=p
 return p

def accrue_credit(state,now):
 p=state.get('pressure_pause')
 if not p:return 0
 available=max(0,state.get('pause_credit_limit_seconds',LIMIT_SECONDS)-used_credit(state))
 seconds=min(max(0,now-p['last_credit_at']),available)
 state['deadline']+=seconds
 state['model_deadlines'][p['size']]+=seconds
 p['credited_seconds']+=seconds;p['last_credit_at']=max(now,p['last_credit_at'])
 state['pause_credit_used_seconds']=used_credit(state)
 return seconds

def advance_gate(p,level,free,now):
 if level!=1 or free<45:
  p['qualifying_checks']=0;p['last_qualifying_check']=None
 else:
  last=p['last_qualifying_check']
  if last is None or now-last>90:p['qualifying_checks']=1;p['last_qualifying_check']=now
  elif now-last>=60:p['qualifying_checks']+=1;p['last_qualifying_check']=now
 return p['qualifying_checks']>=3

def write_proof(out,p):
 copy=dict(p)
 copy['pause_started_utc']=datetime.datetime.fromtimestamp(p['started'],datetime.timezone.utc).isoformat()
 if p.get('ended') is not None:copy['ended_utc']=datetime.datetime.fromtimestamp(p['ended'],datetime.timezone.utc).isoformat()
 copy['credit_limit_seconds']=LIMIT_SECONDS
 atomic(out/p['proof_folder']/'timing.json',copy)

def finish_pause(state,out,now,resumed=True):
 accrue_credit(state,now)
 p=state.pop('pressure_pause');p['ended']=now;p['resumed']=resumed
 state.setdefault('pause_credits',[]).append(p)
 state['pressure_hold_required']=not resumed
 state['pause_credit_used_seconds']=used_credit(state)
 write_proof(out,p)
 return p

"""Compact progress, including ingestion before any answers are scored."""
import json,re,time
from full_common import *

def main():
    status=read(OUT/'status.json');summary=read(OUT/'summary.json');model=read(OUT/'model-state.json');convs=read(OUT/'conversations.json')
    jobs={(status['backend'],j['conversation']) for j in status.get('active_jobs',[]) if j.get('conversation') is not None}
    recoveries={}
    p=OUT/'graphiti-rescue.json'
    if p.exists():
        r=read(p);recoveries['graphiti']=r['state']
        if r['state']=='running':jobs.add(('graphiti',r['conversation']))
    p=OUT/'mem0-schema-rescue.json'
    if p.exists():
        for ci,r in read(p)['jobs'].items():
            recoveries['mem0:'+ci]=r['state']
            if r['state']=='running':jobs.add(('mem0',int(ci)))
    pipeline=OUT/'cognee-pipeline.json'
    if pipeline.exists():
        for ci,r in read(pipeline).get('jobs',{}).items():
            recoveries['cognee-pipeline:'+ci]=r.get('state')
            if r.get('state')=='running':jobs.add(('cognee',int(ci)))
    ingest={}
    for backend,ci in sorted(jobs):
        if backend not in ['mem0','graphiti','cognee']:continue
        suffix=r'-\d+' if backend=='mem0' else ''
        count=sum(bool(re.fullmatch(rf'c{ci}-session_\d+{suffix}\.json',p.name)) for p in (OUT/'ingest'/backend).glob('*.json'))
        expected=sum((len(s['turns'])+7)//8 for s in convs[ci]['sessions']) if backend=='mem0' else len(convs[ci]['sessions'])
        ingest[f'{backend}:c{ci}']=[count,expected,'batches' if backend=='mem0' else 'sessions']
    return dict(state=status['state'],backend=status['backend'],scored={b:s['n'] for b,s in summary.items()},ingestion=ingest,recoveries=recoveries,memory_free_percent=model['memory_free_percent'],pressure=model['pressure_level'],remaining_hours=round((status['deadline_epoch']-time.time())/3600,2),failure_records=len(status['failures']))
if __name__=='__main__':print(json.dumps(main()))

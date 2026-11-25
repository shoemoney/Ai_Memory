from full_common import *
from run import wilson

def summarize():
 systems={}
 for backend in ['full-context','rag','mem0','graphiti','cognee']:
  rows=[read(f) for f in (OUT/'items'/backend).glob('*.json')]
  done=[r for r in rows if r.get('complete')];n=len(done);k=sum(r['correct'] for r in done)
  result={'correct':k,'n':n,'target_n':320,'accuracy':k/n if n else None,'wilson_95':wilson(k,n) if n else None,'answers_checkpointed':sum('answer' in r for r in rows),'by_category':{},'by_conversation':{}}
  for field,values in [('category',[1,2,3,4]),('conversation',range(10))]:
   for value in values:
    selected=[r for r in done if r[field]==value];cn=len(selected);ck=sum(r['correct'] for r in selected)
    result['by_'+field][str(value)]={'correct':ck,'n':cn,'accuracy':ck/cn if cn else None,'wilson_95':wilson(ck,cn) if cn else None}
  rates=[v['accuracy'] for v in result['by_conversation'].values() if v['accuracy'] is not None]
  result['macro_conversation_accuracy']=sum(rates)/len(rates) if rates else None
  systems[backend]=result
 atomic(OUT/'summary.json',systems)
 return systems
if __name__=='__main__':print(json.dumps(summarize(),indent=2))

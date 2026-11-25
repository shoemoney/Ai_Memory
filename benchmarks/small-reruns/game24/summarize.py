import json,sys,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import interval,paired
p=Path(__file__).resolve().parent
rows=[json.loads(x) for x in (p/'results.jsonl').read_text().splitlines()]
assert len(rows)==200 and len({(r['id'],r['arm']) for r in rows})==200
a=[r for r in rows if r['arm']=='direct'];b=[r for r in rows if r['arm']=='dc_cumulative'];a.sort(key=lambda r:r['id']);b.sort(key=lambda r:r['id'])
s={'model':'Qwen2.5-3B-Instruct Q4_K_M','n':100,'arms':{},'paired':paired([r['correct'] for r in a],[r['correct'] for r in b])}
for name,rs in [('direct',a),('dc_cumulative',b)]:
 k=sum(r['correct'] for r in rs)
 s['arms'][name]={'correct':k,'n':100,'rate':k/100,'exact_95':interval(k,100),'finish_reasons':dict(collections.Counter(r['finish_reason'] for r in rs)),'generation_seconds':sum(r['seconds'] for r in rs)}
s['curation_finish_reasons']=dict(collections.Counter(r['curation_finish_reason'] for r in b))
s['curation_seconds']=sum(r['curation_seconds'] for r in b)
s['python_execution_items']=sum(bool(r['execution']) for r in b)
s['empty_memory_states']=sum(not r['memory_after'] for r in b)
(p/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))

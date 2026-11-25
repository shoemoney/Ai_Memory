"""Evidence consistency checks. Does not generate or judge answers."""
import ast,collections,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
def verify():
 m=json.loads((OUT/'manifest.json').read_text());ids=m['selected_ids'];assert len(ids)==len(set(ids))==150
 parent=json.loads((ROOT.parent/'longmemeval/results/full/manifest.json').read_text());assert set(ids)<=set(v['question_id'] for v in parent['items'])
 strata={v['question_id']:v['stratum'] for v in parent['items']};assert dict(collections.Counter(strata[i] for i in ids))==m['strata_counts']
 for p in (OUT/'items').glob('*.json'):
  d=json.loads(p.read_text());assert d['question_id'] in ids
  if not d['hypothesis'].strip():assert not d['correct']
  if d['system'] in ['bm25','dense']:
   src=ROOT.parent/d['reused_source'];assert hashlib.sha256(src.read_bytes()).hexdigest()==d['source_sha256']
   old=json.loads(src.read_text());assert d['hypothesis']==old['hypothesis'];assert d['correct']==(old['correct'] if old['hypothesis'].strip() else False)
  else:
   assert d['source_parts']==d['ingested_parts']
   cp=json.loads((OUT/'ingestion'/f"{d['question_id']}--{d['system']}.json").read_text());assert len(cp)==d['source_parts']
   assert [r['episode'] for r in cp]==list(range(len(cp)))
   assert d['ingestion_usage']['model_calls']>0
 # Execute only the pure empty-answer branch and fail if it asks for an LLM.
 source=ast.parse((ROOT/'run.py').read_text());nodes=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ['clean','judge']]
 env={'get_anscheck_prompt':lambda *a,**k:(_ for _ in ()).throw(AssertionError('empty answer reached judge'))}
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ROOT/'run.py'),'exec'),env)
 assert env['judge']({},' \n','control')=={'correct':False,'votes':[],'reason':'empty answer forced incorrect before judge','calls':[]}
 print('PASS: fixed sample, paired provenance, complete ingestion, and empty-answer bypass')
if __name__=='__main__':verify()

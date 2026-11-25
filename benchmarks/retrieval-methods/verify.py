"""Audit output completeness, scoring independently, and useful negative controls."""
import json,math,sys
from pathlib import Path
from run import scores,rrf,load,OUT
checks=0
def check(x):
 global checks
 assert x;checks+=1
# Exact hand-computed fixtures cover graded qrels, denominator, dedup, and misses.
check(scores(['a','b'],{'a':2,'c':1})['recall5']==.5)
check(scores(['x'],{'a':1})['failure20']==1)
check(scores(['a'],{'a':1})['ndcg10']==1)
check(abs(scores(['a'],{'a':2,'b':1})['ndcg10']-2/(2+1/math.log2(3)))<1e-12)
check(rrf(['a','b'],['b','c'])==['b','a','c'])
# Mutation control: a corpus containing only irrelevant IDs must fail a perfect-retrieval assertion.
try:
 assert scores(['missing'],{'gold':1})['recall20']==1
except AssertionError:checks+=1
else:raise AssertionError('negative control did not fail')
def independent(ranked,rel):
 expected={}
 for k in [5,20]:expected['recall'+str(k)]=sum(d in rel for d in ranked[:k])/len(rel)
 ideal=sum(v/math.log2(i+2) for i,v in enumerate(sorted(rel.values(),reverse=True)[:10]))
 expected['ndcg10']=sum(rel.get(d,0)/math.log2(i+2) for i,d in enumerate(ranked[:10]))/ideal
 expected['failure20']=float(not any(d in rel for d in ranked[:20]))
 hits=0;ap=0
 for rank,document in enumerate(ranked[:150],1):
  if document in rel:hits+=1;ap+=hits/rank
 expected['ap150']=ap/len(rel)
 return expected
manifest=json.loads((OUT/'manifest.json').read_text())
for name in ['scifact','nfcorpus','longmemeval','locomo']:
 data=load(name);queries={q['id']:q for q in data['queries']};docs={d['id']:d for d in data['docs']}
 for suffix in ['base','context']:
  keyword_path=OUT/(name+'.'+suffix+'.bm25.jsonl')
  if keyword_path.exists():
   keyword_rows=[json.loads(line) for line in keyword_path.read_text().splitlines()]
   check(len(keyword_rows)==len(queries));check(len({r['id'] for r in keyword_rows})==len(queries))
   for row in keyword_rows:
    q=queries[row['id']];ranked=[docs[i]['doc'] for i in row['ranked']]
    check(len(ranked)==len(set(ranked)))
    check(set(ranked)<=set(q.get('scope',ranked)))
    expected=independent(ranked,q['relevant'])
    check(all(abs(row['metrics'][k]-v)<1e-12 for k,v in expected.items()))
  p=OUT/(name+'.'+suffix+'.rankings.jsonl')
  if not p.exists():continue
  rows=[json.loads(l) for l in p.read_text().splitlines()]
  check(len(rows)==len(queries));check(len({r['id'] for r in rows})==len(queries))
  for row in rows:
   q=queries[row['id']]
   for method,ids in row['rankings'].items():
    document_ids=[docs[i]['doc'] for i in ids]
    check(len(document_ids)==len(set(document_ids)))
    if 'scope' in q:check(set(document_ids)<=set(q['scope']))
    # Independent metric calculations do not call the harness scorer.
    rel=q['relevant'];expected={}
    for k in [5,20]:expected['recall'+str(k)]=sum(d in rel for d in document_ids[:k])/len(rel)
    ideal=sum(v/math.log2(i+2) for i,v in enumerate(sorted(rel.values(),reverse=True)[:10]))
    expected['ndcg10']=sum(rel.get(d,0)/math.log2(i+2) for i,d in enumerate(document_ids[:10]))/ideal
    expected['failure20']=float(not any(d in rel for d in document_ids[:20]))
    hits=0;average_precision=0
    for rank,document in enumerate(document_ids[:150],1):
     if document in rel:hits+=1;average_precision+=hits/rank
    expected['ap150']=average_precision/len(rel)
    check(all(abs(expected[k]-row['metrics'][method][k])<1e-12 for k in expected))
  rp=OUT/(name+'.'+suffix+'.rerank.jsonl')
  if rp.exists():
   ranked=[json.loads(l) for l in rp.read_text().splitlines()];check(len(ranked)==len(queries))
   pools={r['id']:r['rankings']['hybrid_rrf'] for r in rows}
   for r in ranked:
    check(set(r['ranked'])==set(pools[r['id']]))
    q=queries[r['id']];ids=[docs[i]['doc'] for i in r['ranked']]
    expected=independent(ids,q['relevant'])
    check(all(abs(r['metrics'][k]-v)<1e-12 for k,v in expected.items()))
    check(set(ids)<=set(q.get('scope',ids)))
 if (OUT/(name+'.prefixes.jsonl')).exists():
  prefixes=[json.loads(l) for l in (OUT/(name+'.prefixes.jsonl')).read_text().splitlines()]
  check(len(prefixes)==len(docs));check(set(x['id'] for x in prefixes)==set(docs))
  check(all('<think>' not in x['prefix'] and x['prefix'].strip() for x in prefixes))
pressure_path=OUT/'mac-pressure.jsonl'
if pressure_path.exists():
 pressure=[json.loads(line) for line in pressure_path.read_text().splitlines()]
 starts=[r for r in pressure if r.get('reason')=='owned_server_start']
 check(bool(starts));check(all(r['free_percent']>=40 and r['kernel_level']==1 for r in starts))
 check(all(not r.get('ready') for r in pressure if r.get('kernel_level',1)!=1))
 check(all(r.get('server_pid') is None for r in pressure if r.get('reason')=='kernel_pressure_pause'))
summary=json.loads((OUT/'summary.json').read_text())
for dataset,result in summary.items():
 for method,values in result.get('systems',{}).items():
  recall=values['recall20'];missing=values['unrecalled20']
  check(all(abs(a-b)<1e-12 for a,b in zip(missing,[1-recall[0],1-recall[2],1-recall[1]])))
 for comparison,values in result.get('paired',{}).items():
  recall=values['recall20'];missing=values['unrecalled20']
  check(all(abs(a-b)<1e-12 for a,b in zip(missing,[-recall[0],-recall[2],-recall[1]])))
# Simulate interruptions without allocating a model or touching operational logs.
import tempfile,os
from unittest.mock import patch
import run as harness
with tempfile.TemporaryDirectory(dir=harness.LAB) as temporary:
 sandbox=Path(temporary);(sandbox/'server.log').write_text('healthy runtime')
 for initial,expected in [('2',[2,1]),('1',[1,1])]:
  with patch.dict(os.environ,{'PREFIX_SLOTS':initial}),patch.object(harness,'OUT',sandbox),patch.object(harness,'LAB',sandbox),patch.object(harness.time,'sleep'),patch.object(harness,'prefix_run',side_effect=[harness.GPUHeadroomError('external workload'), 'completed']) as fake:
   check(harness.prefixes(['scifact'])=='completed')
   check([call.args[1] for call in fake.call_args_list]==expected)
 (sandbox/'server.log').write_text('cuda_error_out_of_memory')
 with patch.dict(os.environ,{'PREFIX_SLOTS':'2'}),patch.object(harness,'OUT',sandbox),patch.object(harness,'LAB',sandbox),patch.object(harness,'prefix_run',side_effect=[RuntimeError('allocation error'), 'completed']) as fake:
  check(harness.prefixes(['scifact'])=='completed')
  check([call.args[1] for call in fake.call_args_list]==[2,1])
 with patch.dict(os.environ,{'PREFIX_SLOTS':'1'}),patch.object(harness,'OUT',sandbox),patch.object(harness,'LAB',sandbox),patch.object(harness,'prefix_run',side_effect=RuntimeError('allocation error')) as fake:
  try:harness.prefixes(['scifact'])
  except RuntimeError:check(fake.call_count==1)
  else:raise AssertionError('one-slot CUDA allocation failure retried at the same size')
print('PASS',checks,'checks; independent scores, scope, complete paired cells, reranker pool and can-fail control')
(OUT/'verification.json').write_text(json.dumps({'checks':checks,'status':'pass','scope':'complete existing cells; missing cells reported separately'},indent=2))

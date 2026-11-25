#!/usr/bin/env python3
"""Independently recompute both visual retrieval metrics and bootstrap intervals."""
import gzip,hashlib,json,math
from pathlib import Path
import numpy as np
import pytrec_eval
ROOT=Path(__file__).resolve().parent
checked=[]
for p in (ROOT/'results'/'vidore').glob('*/queries.jsonl.gz'):
 s=json.loads((p.parent/'summary.json').read_text())
 with gzip.open(p,'rt') as f:rows=[json.loads(x) for x in f]
 assert len(rows)==318 and len({r['query_id'] for r in rows})==318
 rels={r['query_id']:r['qrels'] for r in rows}; run={r['query_id']:r['top10'] for r in rows}
 scores=pytrec_eval.RelevanceEvaluator(rels,{'ndcg_cut_5','ndcg_cut_10'}).evaluate(run)
 for k in ['ndcg_cut_5','ndcg_cut_10']:
  vals=[]
  for r in rows:
   assert len(r['top10'])==10 and all(math.isfinite(v) for v in r['top10'].values())
   assert math.isclose(scores[r['query_id']][k],r[k],abs_tol=1e-12);vals.append(r[k])
  assert math.isclose(float(np.mean(vals)),s[k]['mean'],abs_tol=1e-12)
  boot=np.random.default_rng(20261121).choice(vals,size=(10000,len(vals))).mean(1)
  assert np.allclose(np.quantile(boot,[.025,.975]),s[k]['bootstrap_95_ci'],rtol=0,atol=1e-12)
 checked.append({'file':str(p.relative_to(ROOT)),'queries':len(rows),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert checked,'No complete visual results'
(ROOT/'results'/'visual-verification.json').write_text(json.dumps(checked,indent=2)+'\n')
print('Verified',len(checked),'complete visual outputs')

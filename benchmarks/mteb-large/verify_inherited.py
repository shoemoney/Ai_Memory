#!/usr/bin/env python3
"""Read-only verification that the small-model evidence remains unchanged and rescored."""
import gzip,hashlib,json,math
from pathlib import Path
import pytrec_eval
ROOT=Path(__file__).resolve().parent
expected=json.loads((ROOT/'results/inherited-hashes.json').read_text())
for name,sha in expected.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
checked=[]
for name in expected:
 if not name.endswith('.jsonl.gz'):continue
 p=ROOT/name
 with gzip.open(p,'rt') as f:rows=[json.loads(line) for line in f]
 qrels={r['query_id']:r['qrels'] for r in rows};run={r['query_id']:r['top10'] for r in rows}
 res=pytrec_eval.RelevanceEvaluator(qrels,{'ndcg_cut_10'}).evaluate(run)
 for row in rows:assert math.isclose(res[row['query_id']]['ndcg_cut_10'],row['ndcg_at_10'],abs_tol=1e-12)
 checked.append({'file':name,'queries':len(rows),'ndcg_at_10':sum(r['ndcg_at_10'] for r in rows)/len(rows)})
assert checked
(ROOT/'results/earlier-verification.json').write_text(json.dumps({'source_hashes_unchanged':True,'outputs':checked},indent=2)+'\n')
print('Verified',len(checked),'inherited outputs without editing them')

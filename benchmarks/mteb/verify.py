#!/usr/bin/env python3
"""Re-score retained rankings and fail on missing items, corruption, or wrong means."""
from pathlib import Path
import gzip
import hashlib
import json
import math
import pytrec_eval
ROOT=Path(__file__).resolve().parent
expected={'SciFact':(300,5183),'NFCorpus':(323,3633),'ArguAna':(1406,8674)}
checked=[]
for file in sorted((ROOT/'results'/'local').glob('*/*.jsonl.gz')):
    summary=json.loads(file.with_suffix('').with_suffix('.json').read_text())
    with gzip.open(file,'rt') as f:
        rows=[json.loads(line) for line in f]
    task=summary['task']
    assert (len(rows),summary['n_corpus'])==expected[task]
    assert len({r['query_id'] for r in rows})==len(rows)
    qrels={r['query_id']:r['qrels'] for r in rows}
    run={r['query_id']:r['top10'] for r in rows}
    scores=pytrec_eval.RelevanceEvaluator(qrels,{'ndcg_cut_10'}).evaluate(run)
    assert len(scores)==len(rows)
    for row in rows:
        assert math.isclose(scores[row['query_id']]['ndcg_cut_10'],row['ndcg_at_10'],abs_tol=1e-12)
        assert len(row['top10'])==10
        assert all(math.isfinite(v) for v in row['top10'].values())
        assert 0 <= row['ndcg_at_10'] <= 1
        if task=='ArguAna': assert row['query_id'] not in row['top10']
    mean=sum(v['ndcg_cut_10'] for v in scores.values())/len(rows)
    assert math.isclose(mean,summary['ndcg_at_10'],abs_tol=1e-12)
    assert abs(mean-summary['official_ndcg_at_10_rounded'])<.000006
    assert summary['hit_at_10_count']==sum(r['hit_at_10'] for r in rows)
    checked.append({'file':str(file.relative_to(ROOT)), 'n':len(rows),'ndcg_at_10':mean,
                    'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
assert checked,'No local results found'
(ROOT/'results'/'verification.json').write_text(json.dumps(checked,indent=2)+'\n')
print('Verified',len(checked),'model/task outputs and',sum(r['n'] for r in checked),'query records')

"""Seeded paired question bootstrap, with no rounded inputs."""
import json
from pathlib import Path
import numpy as np

p = Path(__file__).parent / 'results'
cohort = json.loads((p/'cohort.json').read_text())
methods = {m: {r['id']: r for r in map(json.loads, (p/(m+'.jsonl')).read_text().splitlines())}
           for m in ['hipporag2', 'dense']}
ids = cohort['item_ids']
assert len(ids) >= 150
assert all(set(v) == set(ids) for v in methods.values()), 'Incomplete or mismatched paired cohort'
rng = np.random.default_rng(20261122)
indices = rng.integers(0,len(ids),size=(10000,len(ids)))
summary = {'n':len(ids), 'interval':'95% percentile paired-question bootstrap, 10000 resamples',
           'seed':20261122, 'metrics':{}}
for metric in ['Recall@1','Recall@5','Recall@10','Recall@20','ExactMatch','F1']:
    values = {m: np.array([rs[i]['scores'][metric] for i in ids]) for m, rs in methods.items()}
    values['hipporag2_minus_dense'] = values['hipporag2']-values['dense']
    summary['metrics'][metric] = {m: {'mean':float(v.mean()),'ci95':np.quantile(v[indices].mean(axis=1),[.025,.975]).tolist()} for m,v in values.items()}
(p/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))

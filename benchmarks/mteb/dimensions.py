#!/usr/bin/env python3
"""Paired Matryoshka changes on the fixed retrieval subset, never full-suite claims."""
import gzip
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
TASKS=['SciFact','NFCorpus','ArguAna']
SEED=20261121
model='google__embeddinggemma-2'
rows=[]
for dim in [768,256,128]:
    folder=ROOT/'results/local'/(model+(f'__{dim}d' if dim!=768 else ''))
    if not all((folder/(t+'.jsonl.gz')).exists() for t in TASKS):continue
    scores={}
    for task in TASKS:
        with gzip.open(folder/(task+'.jsonl.gz'),'rt') as f:
            scores[task]={r['query_id']:r['ndcg_at_10'] for r in map(json.loads,f)}
    rows.append({'dimension':dim,'scores':scores})
output=[]
for row in rows:
    record={'dimension':row['dimension'], 'task_ndcg_at_10':{t:float(np.mean(list(row['scores'][t].values()))) for t in TASKS}}
    record['three_task_mean']=float(np.mean(list(record['task_ndcg_at_10'].values())))
    if row['dimension']!=768 and rows[0]['dimension']==768:
        rng=np.random.default_rng(SEED)
        deltas=[]
        boot=[]
        for task in TASKS:
            ids=sorted(rows[0]['scores'][task]);assert set(ids)==set(row['scores'][task])
            d=np.array([row['scores'][task][q]-rows[0]['scores'][task][q] for q in ids])
            deltas.append(float(d.mean()))
            boot.append(rng.choice(d,size=(10000,len(d)),replace=True).mean(axis=1))
        record['delta_vs_768']=float(np.mean(deltas))
        record['paired_task_stratified_bootstrap_95_ci']=np.quantile(np.mean(boot,axis=0),[.025,.975]).tolist()
    output.append(record)
(ROOT/'results/dimensions.json').write_text(json.dumps(output,indent=2)+'\n')
lines=['| Dimensions | SciFact (N=300) | NFCorpus (N=323) | ArguAna (N=1,406) | Three-task mean | Change vs. 768 [paired 95% CI] |','|---:|---:|---:|---:|---:|---:|']
for r in output:
    delta='Reference'
    if 'delta_vs_768' in r:
        lo,hi=r['paired_task_stratified_bootstrap_95_ci'];delta=f"{r['delta_vs_768']*100:+.2f} [{lo*100:+.2f}, {hi*100:+.2f}]"
    vals=' | '.join(f"{r['task_ndcg_at_10'][t]*100:.2f}" for t in TASKS)
    lines.append(f"| {r['dimension']} | {vals} | {r['three_task_mean']*100:.2f} | {delta} |")
(ROOT/'results/DIMENSIONS.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))

"""Offline fixed-prefix policy accounting, without training or threshold fitting.

KL(P2||P1) is available after pass2; gate RMS from the 1->2 transition
is also available only during pass2. Neither can save pass2's work.
"""
import argparse
import hashlib
import csv
import json
from pathlib import Path
import numpy as np


def policy(records, signal, threshold, probe=None):
    if signal == 'fixed1':
        return np.ones(len(records),dtype=int)
    if signal == 'fixed3':
        return np.full(len(records),3,dtype=int)
    if signal == 'probe':
        if probe is None or len(probe)!=len(records) or not np.all(np.isfinite(probe)):
            raise ValueError('Need one finite held-out score per token')
        return np.where(np.asarray(probe)<threshold,1,3)
    if signal not in ('gate','kl'):
        raise ValueError(signal)
    values = np.array([r['gate_norm' if signal=='gate' else 'kl'][0] for r in records])
    return np.where(values<threshold,2,3)


def summarize(records, passes):
    if len(records)!=len(passes) or not len(records) or np.any((passes<1)|(passes>3)):
        raise ValueError('Invalid passes/records')
    agree = [r['argmax'][int(k)-1] == r['argmax'][2] for r,k in zip(records,passes)]
    return dict(n=len(records),average_passes=float(np.mean(passes)),agreement=float(np.mean(agree)))


def frontier(rows):
    return [r for r in rows if not any(s['average_passes']<=r['average_passes'] and s['agreement']>=r['agreement']
             and (s['average_passes']<r['average_passes'] or s['agreement']>r['agreement']) for s in rows)]


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('run',type=Path)
    p.add_argument('--scores',type=Path,required=True,help='token_flip-scores.npz from probes.py')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    manifest=json.loads((a.run/'manifest.json').read_text())
    if manifest['planned']!=manifest['completed']:
        p.error('Incomplete run')
    records=[json.loads(s) for s in (a.run/'tokens.jsonl').read_text().splitlines()]
    with np.load(a.scores) as data:
        digest = hashlib.sha256((a.run/'tokens.jsonl').read_bytes()).hexdigest()
        if str(data['tokens_sha256']) != digest:
            p.error('Scores belong to a different token file')
        if not np.array_equal(data['indices'],np.arange(len(records))):
            p.error('Scores do not align with token rows')
        score=data['heldout_stratum_residual']
    # Frozen grids: no evaluation-set quantiles or tuning.
    grids={'gate':[0,.01,.03,.1,.2,.3,.5,.7,1,1.01],
           'kl':[0,1e-5,1e-4,5e-4,.001,.005,.01,.05,.1,.5,1,10,float('inf')],
           'probe':[0,.01,.05,.1,.2,.3,.5,.7,.9,1.01], 'fixed1':[0], 'fixed3':[0]}
    rows=[]
    for s in sorted({r['stratum'] for r in records}):
        indices=np.array([i for i,r in enumerate(records) if r['stratum']==s])
        subset=[records[i] for i in indices]
        for signal, thresholds in grids.items():
            for threshold in thresholds:
                passes=policy(subset,signal,threshold,score[indices])
                rows.append(dict(stratum=s,signal=signal,threshold=str(threshold),**summarize(subset,passes)))
    a.output.mkdir(parents=True,exist_ok=True)
    with (a.output/'policies.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    pareto={s:frontier([r for r in rows if r['stratum']==s]) for s in sorted({r['stratum'] for r in records})}
    (a.output/'pareto.json').write_text(json.dumps(pareto,indent=2))
    lines=['| Stratum | Signal | Threshold | Avg passes | Agreement |', '|---|---|---:|---:|---:|']
    for values in pareto.values():
        for r in values:
            lines.append(f'| {r["stratum"]} | {r["signal"]} | {r["threshold"]} | {r["average_passes"]:.4f} | {r["agreement"]:.4f} |')
    (a.output/'pareto.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    main()

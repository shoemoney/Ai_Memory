#!/usr/bin/env python3
"""Produce score tables from retained evidence; never fill missing local measurements."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
TASKS=['SciFact','NFCorpus','ArguAna']
manifest=json.loads((ROOT/'published.json').read_text())
rows=[]
for spec in manifest['models']:
    for task in TASKS:
        record={'model':spec['model'],'task':task,'revision':spec['revision']}
        ref=spec['tasks'][task]
        if 'file' in ref:
            data=json.loads((ROOT/ref['file']).read_text())
            record['published_ndcg_at_10']=data['scores']['test'][0]['ndcg_at_10']
            record['published_dataset_revision']=data.get('dataset_revision')
            record['published_mteb_version']=data.get('mteb_version')
        else: record['published_error']=ref.get('error','missing')
        local=ROOT/'results'/'local'/spec['model'].replace('/','__')/(task+'.json')
        if local.exists(): record['local']=json.loads(local.read_text())
        record['published_url']=ref['url']
        rows.append(record)
(ROOT/'results'/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
lines=['| Model | Task (test queries) | Published nDCG@10 | Local nDCG@10 [95% CI] | Queries with a relevant top-10 result |',
       '|---|---|---:|---:|---:|']
for r in rows:
    pub=f"{100*r['published_ndcg_at_10']:.2f}" if 'published_ndcg_at_10' in r else 'Not available'
    if 'local' in r:
        d=r['local'];lo,hi=d['bootstrap_95_ci']
        local=f"{100*d['ndcg_at_10']:.2f} [{100*lo:.2f}, {100*hi:.2f}]"
        hit=f"{d['hit_at_10_count']}/{d['n_queries']}"
    else: local='Not run';hit='0 evaluated'
    n={'SciFact':300,'NFCorpus':323,'ArguAna':1406}[r['task']]
    lines.append(f"| {r['model']} | {r['task']} ({n}) | {pub} | {local} | {hit} |")
(ROOT/'results'/'TABLE.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))

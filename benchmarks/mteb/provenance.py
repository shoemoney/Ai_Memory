#!/usr/bin/env python3
"""Capture primary-source availability and checksums without storing page prose."""
from pathlib import Path
import datetime
import hashlib
import json
import urllib.request
ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT/'published.json').read_text())
urls = ['https://github.com/embeddings-benchmark/mteb',
        'https://raw.githubusercontent.com/embeddings-benchmark/mteb/2.27.20/mteb/_evaluators/retrieval_metrics.py',
        'https://arxiv.org/abs/2210.07316', 'https://arxiv.org/abs/2502.13595',
        'https://www.cl.uni-heidelberg.de/statnlpgroup/nfcorpus/']
for m in manifest['models']:
    urls.append('https://huggingface.co/'+m['model']+'/raw/'+m['revision']+'/README.md')
for ds, rev in [('scifact','d56462d0e63a25450459c4f213e49ffdb866f7f9'),
                ('nfcorpus','ec0fa4fe99da2ff19ca1214b7966684033a58814'),
                ('arguana','c22ab2a51041ffd869aaddef7af8d8215647e41a')]:
    urls.append(f'https://huggingface.co/datasets/mteb/{ds}/raw/{rev}/README.md')
for claim in json.loads((ROOT/'claims.json').read_text()):
    for refs in claim['sources'].values():
        urls.extend(refs)
urls=list(dict.fromkeys(urls))
rows=[]
for url in urls:
    row={'url': url, 'fetched_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        with urllib.request.urlopen(url, timeout=40) as r:
            data=r.read();row.update(status=r.status, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    except Exception as e:
        row.update(error=str(e))
    rows.append(row)
    print(url, row.get('status', row.get('error')), flush=True)
(ROOT/'results'/'sources.json').write_text(json.dumps(rows,indent=2)+'\n')

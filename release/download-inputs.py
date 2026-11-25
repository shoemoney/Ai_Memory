#!/usr/bin/env python3
"""Fetch original upstream inputs; optionally recreate deterministic samples."""
import argparse, hashlib, json, subprocess, sys, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('group',choices=['conversation','retrieval','prompt'])
p.add_argument('--rebuild-samples',action='store_true')
a=p.parse_args()
sources={
 'conversation':[('locomo10.json','https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json')],
 'prompt':[('zep_memgpt_eval.ipynb','https://raw.githubusercontent.com/getzep/zep-papers/4b7f26cc76cca20743314ba9acb8c2cb6adc42f6/kg_architecture_agent_memory/zep_memgpt_eval.ipynb')],
 'retrieval':[]}
for name,rev,qrev in [('scifact','b3b5335604bf5ee3c4447671af975ea25143d4f5','2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029'),('nfcorpus','b5026a0e96e8a7ac4f95f482a596389289d46269','a451b3b26d3ae1358f259c1a3a4dd61fcea35a65')]:
 for kind in ['corpus','queries']:
  sources['retrieval'].append((f'{name}.{kind}.parquet',f'https://huggingface.co/datasets/BeIR/{name}/resolve/{rev}/{kind}/{kind}-00000-of-00001.parquet'))
 sources['retrieval'].append((f'{name}.qrels.tsv',f'https://huggingface.co/datasets/BeIR/{name}-qrels/resolve/{qrev}/test.tsv'))
sources['retrieval'].append(('arguana.zip','https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/arguana.zip'))
dest=ROOT/'downloaded-inputs'/a.group;dest.mkdir(parents=True,exist_ok=True);manifest=[]
for name,url in sources[a.group]:
 with urllib.request.urlopen(url,timeout=180) as response:data=response.read()
 (dest/name).write_bytes(data)
 manifest.append({'path':str((dest/name).relative_to(ROOT)),'url':url,'sha256':hashlib.sha256(data).hexdigest()})
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if a.rebuild_samples:
 scripts=['benchmarks/extraction/prepare.py','benchmarks/extraction/v1/prepare.py']
 if a.group!='conversation':p.error('sample rebuild requires conversation group')
 if not all((ROOT/script).is_file() for script in scripts):
  raise SystemExit('Original inputs fetched. Sample generators include adapted source references and are withheld from the public export; exact restoration is unresolved.')
 for script in scripts:
  subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,check=True)
print(f'Fetched original inputs to {dest}; original licences apply.')
print('Historical generated traces, audited references and prefixes require the original harness/model/manual audit; they are not downloadable upstream files.')

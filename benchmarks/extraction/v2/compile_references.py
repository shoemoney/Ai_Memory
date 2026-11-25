"""Compile manually reviewed source-only references; refuse silent sample changes."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def compile_rows(rows):
 from annotations import REFS
 assert set(REFS)==set(range(300))and len(rows)==300
 for i,r in enumerate(rows):
  entities=list(dict.fromkeys(re.findall(r'ENTITY_\d+',r['text'])))
  other=next((v for v in re.findall(r'PERSON_\d+',r['text'])if v!=r['speaker']),'the other speaker')
  mapping={'S':r['speaker'],'other':other,**{f'e{j}':v for j,v in enumerate(entities)}}
  r['reference_facts']=[f.format(**mapping)for f in REFS[i]]
  assert len(set(r['reference_facts']))==len(r['reference_facts'])
  r['annotation_index']=i
 return rows

def run(check=False):
 rows=compile_rows(json.loads((ROOT/'data/candidates.json').read_text()));content=(json.dumps(rows,indent=2)+'\n').encode();path=ROOT/'data/sample.json'
 if path.exists()and path.read_bytes()!=content:raise RuntimeError('Derived sample differs from frozen data; start a new benchmark version rather than changing these inputs')
 if not check:
  path.write_bytes(content)
  manifest=json.loads((ROOT/'data/manifest.json').read_text());manifest.update(reference_status='Source-only atomic references manually authored by the implementation agent, not independent human gold; original generated observations separately audited.',reference_facts=sum(len(r['reference_facts'])for r in rows),sample_sha256=hashlib.sha256(content).hexdigest(),annotations_sha256=hashlib.sha256((ROOT/'annotations.py').read_bytes()).hexdigest());(ROOT/'data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
  auditpath=ROOT/'data/generated-reference-audit.json'
  if auditpath.exists():
   old=json.loads(auditpath.read_text());new=json.loads((ROOT/'data/generated-reference-audit-inputs.json').read_text())
   for a,b in zip(old,new):
    assert(a['id'],a['observation_index'])==(b['id'],b['observation_index'])
    for key in ('audit_index','fully_supported','error','review'):
     if key in a:b[key]=a[key]
   auditpath.write_text(json.dumps(new,indent=2)+'\n')
 print(json.dumps({'N':len(rows),'reference_facts':sum(len(r['reference_facts'])for r in rows),'sample_sha256':hashlib.sha256(content).hexdigest(),'frozen_bytes_match':True,'check_only':check}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');run(parser.parse_args().check)

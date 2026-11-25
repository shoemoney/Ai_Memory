"""Reduce public DPR contexts to the authors' NQ sample, using no answer labels."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--source',type=Path,required=True)
p.add_argument('--dpr',type=Path,required=True)
p.add_argument('--scratch',type=Path,required=True)
a=p.parse_args()
query_path=a.source/'data_v2/input_data/DPR/sampled_query/nq-test-sample-200.jsonl'
queries=[json.loads(s) for s in query_path.read_text().splitlines()]
norm=lambda s:s.lower().strip().rstrip('?')
records={norm(r['question']):r for r in json.load(gzip.open(a.dpr,'rt'))}
matched=[q for q in queries if norm(q['question']) in records]
assert len(matched)>=150
corpus={}
for q in matched:
    for c in records[norm(q['question'])]['ctxs'][:20]:
        content=c['title']+'\n'+c['text']
        if str(c['id']) in corpus:
            assert corpus[str(c['id'])]==content
        corpus[str(c['id'])]=content
assert all(i.isdigit() for i in corpus)
a.scratch.mkdir(parents=True,exist_ok=True)
(a.scratch/'queries.json').write_text(json.dumps(matched))
(a.scratch/'human.json').write_text(json.dumps(corpus))
manifest={'n':len(matched),'human_documents':len(corpus),'rounds':10,
          'selection':'intersection by lowercased question text, whitespace stripped and terminal question mark removed; all matching author sample questions, no answer-based selection',
          'corpus':'union of first 20 contexts in official DPR single-model NQ test retrieval results for selected questions, deduplicated by original numeric document ID',
          'item_ids':[q['id'] for q in matched],
          'excluded_item_ids':[q['id'] for q in queries if q not in matched],
          'query_file_sha256':hashlib.sha256(query_path.read_bytes()).hexdigest(),
          'dpr_gzip_sha256':hashlib.sha256(a.dpr.read_bytes()).hexdigest(),
          'human_document_sha256':{i:hashlib.sha256(t.encode()).hexdigest() for i,t in corpus.items()}}
out=Path(__file__).parent/'results';out.mkdir(exist_ok=True)
(out/'cohort.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'n':len(matched),'human_documents':len(corpus)}))

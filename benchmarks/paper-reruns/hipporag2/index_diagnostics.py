"""Retain graph and extraction counts without retaining the corpus or full index."""
import argparse
import hashlib
import json
from pathlib import Path
import igraph

p=argparse.ArgumentParser()
p.add_argument('--index',type=Path,required=True)
a=p.parse_args()
out=Path(__file__).parent/'results'
cohort=json.loads((out/'cohort.json').read_text())
paths=list(a.index.glob('*/openie_state.json'))
assert len(paths)==1,paths
state_path=paths[0]
state=json.loads(state_path.read_text())
rows=state['docs']
counts=[]
entities=set()
for r in rows:
    assert all(isinstance(x,str) for x in r['extracted_entities'])
    assert all(isinstance(t,(tuple,list)) and len(t)==3 and all(isinstance(x,str) for x in t) for t in r['extracted_triples'])
    digest=hashlib.sha256(r['passage'].encode()).hexdigest()
    counts.append({'document_sha256':digest,'entities':len(r['extracted_entities']),'triples':len(r['extracted_triples'])})
    entities.update(r['extracted_entities'])
assert len(rows)==len(cohort['document_sha256'])==len({r['document_sha256'] for r in counts})
assert {r['document_sha256'] for r in counts}==set(cohort['document_sha256'])
graph=igraph.Graph.Read_Pickle(str(state_path.parent/'graph.pickle'))
result={'documents':len(rows),'extracted_entity_mentions':sum(x['entities'] for x in counts),
        'distinct_extracted_entity_strings':len(entities),
        'extracted_triples_before_graph_normalization':sum(x['triples'] for x in counts),
        'documents_with_no_triples':sum(x['triples']==0 for x in counts),
        'graph_vertices':graph.vcount(),'graph_edges':graph.ecount(),
        'per_document':counts}
(out/'index-diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='per_document'}))

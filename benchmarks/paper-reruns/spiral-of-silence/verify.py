"""Check source provenance, complete rounds, and absence of within-round context leakage."""
import json
import math
from pathlib import Path

p=Path(__file__).parent/'results'
cohort=json.loads((p/'cohort.json').read_text())
summary=json.loads((p/'summary.json').read_text())
ids=set(cohort['item_ids'])
human=set(cohort['human_document_sha256'])
rows=[json.loads(s) for s in (p/'generated.jsonl').read_text().splitlines()]
by_key={(r['round'],r['id']):r for r in rows}
assert len(rows)==len(by_key)==len(ids)*cohort['rounds']
assert len({r['docid'] for r in rows})==len(rows)
assert len(summary['rounds'])==cohort['rounds']+1
assert len(ids)>=150 and all(i.isdigit() for i in human)
for r in range(cohort['rounds']+1):
    ranked=json.loads((p/f'round-{r:02d}.json').read_text())
    assert set(ranked)==ids
    valid=human|{x['docid'] for x in rows if x['round']<=r}
    shares={}
    for qid,v in ranked.items():
        docs=[x['docid'] for x in v['contexts']]
        assert len(docs)==len(set(docs))==50
        assert set(docs).issubset(valid)
        shares[qid]=sum(d in human for d in docs)/50
    printed=summary['rounds'][r]
    assert printed['round']==r and printed['n']==len(ids)
    assert math.isclose(sum(shares.values())/len(ids),printed['human_share'],abs_tol=1e-12)
    assert set(x['id'] for x in printed['per_item'])==ids
    assert all(math.isclose(shares[x['id']],x['human_share'],abs_tol=1e-12) for x in printed['per_item'])
    assert 0<=printed['ci95'][0]<=printed['human_share']<=printed['ci95'][1]<=1
    if r:
        previous=json.loads((p/f'round-{r-1:02d}.json').read_text())
        for qid in ids:
            row=by_key[(r,qid)]
            expected=[x['docid'] for x in previous[qid]['contexts'][:5]] if r>1 else []
            assert row['context_docids']==expected
            assert len(row['filtered'].split())>=5
print('PASS: all rounds and questions complete, all top-50 sources accounted for, shares independently recomputed, previous-round context snapshots verified')

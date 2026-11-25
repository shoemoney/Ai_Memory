"""Independently recompute retained per-item scores from raw answers and hashes."""
from collections import Counter
import json
import math
from pathlib import Path
import re
import string


def normalize(s):
    s = ''.join(c for c in s.lower() if c not in string.punctuation)
    return ' '.join(re.sub(r'\b(a|an|the)\b', ' ', s).split())


def f1(gold, answer):
    g, p = normalize(gold).split(), normalize(answer).split()
    same = sum((Counter(g) & Counter(p)).values())
    return 2*same/(len(g)+len(p)) if same else 0.0


p = Path(__file__).parent/'results'
cohort = json.loads((p/'cohort.json').read_text())
for method in ['hipporag2', 'dense']:
    rows = [json.loads(s) for s in (p/(method+'.jsonl')).read_text().splitlines()]
    assert len(rows) == len(cohort['item_ids']) == len({r['id'] for r in rows}) >= 150
    assert set(cohort['item_ids']) == {r['id'] for r in rows}
    for r in rows:
        gold = set(r['gold_sha256'])
        assert gold.issubset(cohort['document_sha256'])
        scores = {f'Recall@{k}':len(gold & set(r['retrieved_sha256'][:k]))/len(gold) for k in [1,5,10,20]}
        scores['ExactMatch'] = float(any(normalize(g) == normalize(r['answer']) for g in r['gold_answers']))
        scores['F1'] = max(f1(g,r['answer']) for g in r['gold_answers'])
        assert all(math.isclose(v,r['scores'][k],abs_tol=1e-12) for k,v in scores.items()), r['id']
print('PASS: complete paired cohort, distinct IDs, and every retained recall/EM/F1 score independently recomputed')

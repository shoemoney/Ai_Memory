"""Audit shipped evidence without a model or third-party packages."""
import collections, hashlib, json, math, re
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'results'
manifest=json.loads((out/'manifest.json').read_text())
sample=json.loads((out/'sample.json').read_text())
rows=[json.loads(x) for x in (out/'items.jsonl').read_text().splitlines()]
assert len(sample)==14 and len(rows)==42
assert len({(r['question_id'],r['method']) for r in rows})==42
assert collections.Counter(x['stratum'] for x in manifest['items'])==dict.fromkeys({x['stratum'] for x in manifest['items']},2)
assert set(x['question_id'] for x in sample)==set(x['id'] for x in manifest['items'])
for name,digest in manifest['source_hashes'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
refs={x['question_id']:x for x in sample}
for r in rows:
    assert r['question']==refs[r['question_id']]['question']
    assert r['reference']==refs[r['question_id']]['answer']
    assert re.fullmatch(r'(yes|no)[.!]?',r['judge_response'].lower())
    assert r['correct']==('yes' in r['judge_response'].lower())
    assert r['answer_usage']['prompt_tokens']>0
    assert r['answer_usage']['completion_tokens']>0
    assert 'has_answer' not in json.dumps(r['context'])
    assert 'answer_session_ids' not in json.dumps(r['context'])
    if r['method']=='full-context':
        assert len(r['context'])==len(refs[r['question_id']]['haystack_sessions'])
        assert not any('has_answer' in t for s in r['context'] for t in s['dialogue'])
summary=json.loads((out/'summary.json').read_text())
for method,s in summary.items():
    group=[r for r in rows if r['method']==method]
    assert s['n']==len(group)==14
    assert s['correct']==sum(r['correct'] for r in group)
    assert math.isclose(s['accuracy'],s['correct']/14)
checks=[json.loads(x) for x in (out/'judge-checks.jsonl').read_text().splitlines()]
assert {c['expected'] for c in checks}=={False,True}
assert all(c['actual']==c['expected'] for c in checks)
print('PASS: 42 unique paired results, 14 fixed references, source hashes, judge controls and score totals')

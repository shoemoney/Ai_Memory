"""Verify a finished large run, including coverage, votes and ingestion evidence."""
from pathlib import Path
import json,hashlib,re,sys
from judge_prompt import get_anscheck_prompt
def clean(text):
 return (text or '').split('<end_of_turn>',1)[0].strip()
def keys(value):
 if isinstance(value,dict):
  for k,v in value.items():
   yield k
   yield from keys(v)
 elif isinstance(value,list):
  for v in value:yield from keys(v)
R=Path(__file__).resolve().parent;O=R/'results/full'
partial='--partial' in sys.argv
m=json.loads((O/'manifest.json').read_text());ids={v['question_id'] for v in m['items']}
assert len(ids)==m['n']==300 and sum(m['strata_counts'].values())==300
for name,h in m['source_sha256'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h,name
dates=json.loads((O/'variant-date-maps.json').read_text())['questions']
rows=[json.loads(p.read_text()) for p in (O/'items').glob('*.json')]
assert len({(v['question_id'],v['method']) for v in rows})==len(rows)
assert len(rows)<=1500 if partial else len(rows)==1500
methods=['full-standard','bm25-standard','dense-standard','mem0-raw-standard','full-oracle']
for method in methods:
 actual={v['question_id'] for v in rows if v['method']==method}
 assert actual<=ids if partial else actual==ids
for v in rows:
 assert v['question_id'] in ids
 src=O/'source'/('large-'+v['source_sha256']+'.py')
 assert src.exists() and hashlib.sha256(src.read_bytes()).hexdigest()==v['source_sha256']
 if v['status']=='context-does-not-fit':
  assert v['method'].startswith('full-') and v['prompt_tokens']+512>8192
  continue
 assert v['status']=='scored' and v['prompt_tokens']+512<=8192
 variant='oracle' if v['method']=='full-oracle' else 'standard'
 official=dates[v['question_id']][variant]
 assert v['question_date']==official['question_date']
 assert 'Question date: '+official['question_date']+'\nHistory:' in v['answer']['prompt']
 assert all(c['date']==official['session_dates'][c['session_id']] for c in v['context'])
 j=v['judge'];assert len(j['votes'])==len(j['calls'])==3
 assert ['yes' in clean(c['text']).lower() for c in j['calls']]==j['votes']
 expected_format=[bool(re.fullmatch(r'(yes|no)[.!]?',clean(c['text']).lower())) for c in j['calls']]
 assert j.get('format_valid',expected_format)==expected_format
 assert j['correct']==v['correct']==(sum(j['votes'])>=2)
 assert v['hypothesis']==v['answer']['text']
 assert j['prompt']==get_anscheck_prompt(v['question_type'],v['question'],v['reference'],v['hypothesis'],abstention=v['question_id'].endswith('_abs'))
 assert not {'has_answer','answer_session_ids'}.intersection(keys(v['context']))
 assert v['answer']['raw']['usage']['prompt_tokens']+512<=8192
ing=[]
for line in (O/'memory-ingestion.jsonl').read_text().splitlines():
 x=json.loads(line);assert x['infer'] is False
 assert x['input_chunks']==x['stored_count']==x['added']==len(x['all_chunk_sha256'])
 assert x['input_sessions']==next(v['standard_sessions'] for v in m['items'] if v['question_id']==x['question_id'])
 ing.append(x['question_id'])
assert set(ing)<=ids if partial else set(ing)==ids
if partial and not (O/'manual-audit.json').exists():
 print('PASS: current checkpoints, exact judge prompts/three votes, source revisions, token limits and recorded ingestion counts; run incomplete')
 sys.exit(0)
plan={tuple(v) for v in json.loads((O/'audit-plan.json').read_text())['pairs']}
a=json.loads((O/'manual-audit.json').read_text());reviews=a['reviews']
assert len(reviews)==40 and {(v['question_id'],v['method']) for v in reviews}==plan
lookup={(v['question_id'],v['method']):v for v in rows}
for v in reviews:
 assert type(v['manual_label']) is bool and v['reason'].strip()
 assert v['majority_label']==lookup[(v['question_id'],v['method'])]['correct']
print(('PASS: current partial checkpoints and 40 review records; run still incomplete' if partial else 'PASS: 300 fixed questions, 1500 lane checkpoints, exact judge prompts/three votes, full-haystack Mem0 ingestion, and 40 review records'))

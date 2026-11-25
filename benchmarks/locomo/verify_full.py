"""Offline checks for complete or explicitly partial larger-run evidence."""
import argparse,hashlib,json,random,math
from collections import Counter
from full_common import *
from full_summary import summarize
from run import parse_json,JUDGE,ANSWER_SYSTEM,wilson

def verify(allow_partial=False):
 if not __debug__:raise RuntimeError('Run verification without Python optimization flags')
 selection=read(OUT/'selection.json');assert len(selection)==320
 assert len({q['item_id'] for q in selection})==320
 assert Counter(q['category'] for q in selection)=={1:80,2:80,3:80,4:80}
 assert set(q['conversation'] for q in selection)==set(range(10))
 assert len({(q['question'],q['gold']) for q in selection})==320
 by_id={q['item_id']:q for q in selection}
 backends=['full-context','rag','mem0','graphiti','cognee']
 snapshots={backend:[read(f) for f in (OUT/'items'/backend).glob('*.json')] for backend in backends}
 # Index actual model calls by their effective messages and seed.
 calls={};finish=Counter();raw_count=0
 for f in (OUT/'raw-calls').glob('*.json'):
  r=read(f);body=r['request'];response=r['response'];raw_count+=1
  assert body['model']==MODEL and body['temperature']==0
  assert f.stem==r['request_sha256']==hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
  key=(json.dumps(body['messages'],sort_keys=True,ensure_ascii=False),body['seed'])
  calls.setdefault(key,[]).append(r)
  finish[response['choices'][0]['finish_reason']]+=1
 proof={};seen_responses=set()
 for bi,backend in enumerate(['full-context','rag','mem0','graphiti','cognee']):
  rows=snapshots[backend]
  assert len(rows)==len({r['item_id'] for r in rows})
  done=[r for r in rows if r.get('complete')]
  if not allow_partial:assert len(done)==320,(backend,len(done))
  for r in rows:
   q=by_id[r['item_id']];assert all(r[k]==q[k] for k in q)
   if not r.get('complete'):continue
   assert len(r['votes'])==3
   assert r['correct']==(sum(v['label']=='CORRECT' for v in r['votes'])>=2)
   messages=[{'role':'system','content':ANSWER_SYSTEM},{'role':'user','content':f"Conversation evidence:\n{r['context']}\n\nQuestion: {r['question']}"}]
   messages=[dict(m,content=pseudo(m['content'])) for m in messages]
   matches=calls.get((json.dumps(messages,sort_keys=True,ensure_ascii=False),SEED),[])
   assert any(x['response']['choices'][0]['message']['content']==r['answer'] and x['response']['choices'][0]['finish_reason']=='stop' for x in matches)
   for vi,vote in enumerate(r['votes']):
    assert vote['seed']==SEED+100*bi+vi
    label=parse_json(vote['raw'])['label'];assert label==vote['label'] and label in ['CORRECT','WRONG']
    text=pseudo(JUDGE.format(question=r['question'],gold=r['gold'],answer=r['answer']))
    key=(json.dumps([{'role':'user','content':text}],sort_keys=True,ensure_ascii=False),vote['seed'])
    matches=[x for x in calls.get(key,[]) if x['response']['choices'][0]['message']['content']==vote['raw'] and x['response']['choices'][0]['finish_reason']=='stop']
    assert matches,(backend,r['item_id'],vi)
    response_id=matches[-1]['response']['id'];assert response_id not in seen_responses
    seen_responses.add(response_id)
  proof[backend]={'n':len(done),'correct':sum(r['correct'] for r in done),'target_n':320,'same_selected_ids':{r['item_id'] for r in done}==set(by_id)}
 summary=summarize()
 for backend,p in proof.items():
  if allow_partial:assert summary[backend]['n']>=p['n']
  else:assert summary[backend]['n']==p['n'] and summary[backend]['correct']==p['correct']
 result={'systems':proof,'raw_model_calls':raw_count,'raw_finish_reasons':dict(finish),'unique_judge_response_ids':len(seen_responses),'three_distinct_model_votes_per_scored_item':True,'source_question_alignment':True,'partial':any(p['n']!=320 for p in proof.values())}
 cognee_proof=OUT/'cognee-final-ingestion-validation.json'
 if cognee_proof.exists():
  ingestion=read(cognee_proof)
  assert all(ingestion.get(str(r['conversation']),{}).get('final_native_run_completed') for r in snapshots['cognee'] if r.get('complete'))
  result['cognee_final_native_status_verified']=True
 elif (OUT/'cleanup.json').exists() and read(OUT/'cleanup.json').get('cleanup_confirmed'):
  raise AssertionError('Validate final native Cognee ingestion before final verification')
 matched_path=OUT/'matched-summary.json'
 if matched_path.exists():
  matched=read(matched_path);ids=set(matched['item_ids']);convs=set(matched['completed_conversations'])
  common=set.intersection(*[{r['item_id'] for r in snapshots[b] if r.get('complete')} for b in backends])
  assert ids<=common if allow_partial else ids==common
  result['matched_coverage_is_current']=ids==common
  if (OUT/'cleanup.json').exists() and read(OUT/'cleanup.json').get('cleanup_confirmed'):assert ids==common
  assert matched['n']==len(ids)
  for backend in backends:
   rows={r['item_id']:r for r in snapshots[backend]}
   selected=[rows[i] for i in ids];assert all(r.get('complete') for r in selected)
   n=len(selected);k=sum(r['correct'] for r in selected);score=matched['systems'][backend]
   assert score['n']==n and score['correct']==k
   if n:assert all(math.isclose(a,b) for a,b in zip(score['wilson_95'],wilson(k,n)))
   assert sum(x['n'] for x in score['by_category'].values())==n
  result['matched_n']=matched['n'];result['matched_conversations']=matched['represented_conversations'];result['fully_completed_conversations']=matched['completed_conversations']
  plan=read(OUT/'manual-audit-plan.json')
  if plan.get('scope')=='final_matched_subset':
   assert plan['matched_item_ids']==matched['item_ids']
   rng=random.Random(20261123);expected=[]
   for backend in backends:
    for category in range(1,5):
     choices=sorted((q for q in selection if q['item_id'] in ids and q['category']==category),key=lambda q:q['item_id'])
     expected.extend((backend,q['item_id']) for q in rng.sample(choices,2))
   assert [(x['backend'],x['item_id']) for x in plan['items']]==expected
   presentation=read(OUT/'manual-audit-blind-presentation.json')
   shuffled=list(plan['items']);random.Random(20261124).shuffle(shuffled)
   assert presentation['seed']==20261124
   assert presentation['items']==[dict(audit_id=f'audit_{i+1:03d}',**item) for i,item in enumerate(shuffled)]
   audit=read(OUT/'manual-audit.json')
   if audit.get('summary'):
    assert audit.get('system_identity_hidden_during_final_review') is True
    lookup={item['audit_id']:item for item in presentation['items']}
    assert all(all(item[k]==lookup[item['audit_id']][k] for k in ['backend','item_id','category']) for item in audit['items'])
    assert len(audit['items'])==40 and {(x['backend'],x['item_id']) for x in audit['items']}==set(expected)
    agreed=0
    for item in audit['items']:
     row=next(r for r in snapshots[item['backend']] if r['item_id']==item['item_id'])
     majority='CORRECT' if row['correct'] else 'WRONG'
     assert item['majority_label']==majority
     agreement=item['manual_label']==majority;assert item['agrees']==agreement;agreed+=agreement
    assert audit['summary']['agreed']==agreed and audit['summary']['n']==40
    result['manual_audit_verified']=True
 atomic(OUT/'verification.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--allow-partial',action='store_true');a=p.parse_args();print(json.dumps(verify(a.allow_partial),indent=2))

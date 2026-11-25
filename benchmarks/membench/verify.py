"""Reconstruct scores and enforce pairing, source pins, and completion."""
import ast
from common import *
def main():
 assert read(OUT/'preparation-replay.json')['complete'],'Preparation replay must match before final verification'
 official=LAB/'mab-eval'
 download('https://raw.githubusercontent.com/HUST-AI-HYZ/MemoryAgentBench/'+SOURCES['mab']['code_revision']+'/utils/eval_other_utils.py',official)
 official_hash=sha(official.read_bytes());assert official_hash=='d77976be409298970614d477a9d8003850caddb0510e56a7e821a037d98493a2'
 function=next(n for n in ast.parse(official.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_process_eventqa_dataset')
 # Unrelated standard metrics are unnecessary for the official binary recall field.
 namespace={'parse_output':lambda x:x,'calculate_metrics':lambda *_:{}}
 exec(compile(ast.Module(body=[function],type_ignores=[]),'pinned official EventQA scorer','exec'),namespace)
 scorer=lambda pred,refs:namespace['_process_eventqa_dataset']({'output':pred},refs)[0]['eventqa_recall']
 manifest=read(OUT/'manifest.json');assert manifest['sources']==SOURCES
 for source in SOURCES.values():assert sha((LAB/source['local']).read_bytes())==source['sha256']
 source_items={x['item_id']:x for x in read(LAB/'prepared.json')['items']}
 expected={b:{x['item_id'] for x in manifest['items'] if x['benchmark']==b} for b in ['mab','halu']};counts={}
 for b in expected:
  assert len(expected[b])==150
  for method in ['full-context','rag','bm25']:
   paths=list((OUT/'items'/b/method).glob('*.json'));rows=[read(p) for p in paths];assert {r['item_id'] for r in rows}==expected[b]
   for r in rows:
    assert r['method']==method and r['benchmark']==b and r['response']['finish_reason']=='stop'
    assert r['response']['usage']['prompt_tokens']>=r['provided_context_tokens']
    assert r['answer']==r['response']['text'] and r['score'] in [0,1]
    if r.get('privacy_export'):
     raw=read(LAB/'result-originals'/b/method/(r['item_id']+'.json'))
     assert sha(json.dumps(raw,sort_keys=True))==r['privacy_export']['raw_record_sha256']
     assert sha(raw['answer'])==r['privacy_export']['raw_answer_sha256'] and raw['score']==r['score']
     if b=='halu':assert raw['judge']['result']['evaluation_result']==r['judge']['result']['evaluation_result']
    selected=next(x for x in manifest['items'] if x['item_id']==r['item_id']);assert r['question_sha256']==selected['question_sha256'];assert r['reference_sha256']==selected['reference_sha256']
    source=source_items[r['item_id']];assert r['question_sha256']==sha(source['question']) and r['reference_sha256']==sha(json.dumps(source['gold']))
    if method=='full-context':assert r['provided_context_sha256']==manifest['context_sha256'][r['context']]
    else:
     expected_chunks=min(20,len(read(LAB/'indexes'/(r['context']+'.json'))))
     assert len(r['retrieved_chunk_ids'])==expected_chunks and len(set(r['retrieved_chunk_ids']))==expected_chunks
    if b=='mab':
     original=read(LAB/'result-originals'/b/method/(r['item_id']+'.json')) if r.get('privacy_export') else r
     assert r['score']==scorer(original['answer'],source['gold'])
    else:assert r['score']==int(r['judge']['result']['evaluation_result']=='Correct')
   counts[f'{b}/{method}']={'n':len(rows),'correct':sum(r['score'] for r in rows)}
 assert all(v+4096<131072 for v in read(OUT/'context-lengths.json').values())
 # The official EventQA rule can fail, and rejects a paraphrase even if semantically reasonable.
 assert scorer('The gate opened.',['The gate opened.'])==1
 assert scorer('The gate closed.',['The gate opened.'])==0
 assert scorer('The gate opened.',['The gate opened.','It rained.'])==0
 summary=read(OUT/'summary.json')
 for key,v in counts.items():
  b,m=key.split('/');assert summary[b][m]['n']==v['n'] and summary[b][m]['correct']==v['correct']
 audit=read(OUT/'manual-audit.json');assert len(audit['items'])>=40
 planned={(x['method'],x['item_id']) for x in read(OUT/'manual-audit-plan.json')['items']}
 planned.update((x['method'],x['item_id']) for x in read(OUT/'manual-audit-supplement-plan.json')['items'])
 reviewed={(x['method'],x['item_id']) for x in audit['items']};assert planned<=reviewed and len(reviewed)==len(audit['items'])
 assert len({x['item_id'] for x in audit['items']})>=40
 for review in audit['items']:
  automated=read(OUT/'items'/'halu'/review['method']/(review['item_id']+'.json'))['judge']['result']['evaluation_result']
  assert review['reviewer_label'] in ['Correct','Hallucination','Omission'] and review['notes']
  assert review['agree']==(review['reviewer_label']==automated)
 atomic(OUT/'verification.json',{'complete':True,'cells':counts,'paired_items_per_benchmark':150,'all_answers_untruncated':True,'context_admission':True,'eventqa_negative_controls':True,'official_eventqa_scorer_sha256':official_hash,'manual_judge_audit_n':len(audit['items'])})
 print(json.dumps(counts,indent=2))
if __name__=='__main__':main()

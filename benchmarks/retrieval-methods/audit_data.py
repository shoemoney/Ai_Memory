"""Independent support-label and corpus audit, with bounded-memory source parsing."""
import json,hashlib,statistics
from pathlib import Path
from run import LAB,OUT,load

def objects(path):
 decoder=json.JSONDecoder();buffer='';started=False
 with path.open(encoding='utf-8') as source:
  while True:
   block=source.read(1024*1024)
   if not block:break
   buffer+=block
   while True:
    buffer=buffer.lstrip()
    if not started:
     if not buffer:break
     assert buffer.startswith('[');buffer=buffer[1:];started=True
    buffer=buffer.lstrip()
    if buffer.startswith(','):buffer=buffer[1:].lstrip()
    if buffer.startswith(']'):return
    if not buffer:break
    try:item,end=decoder.raw_decode(buffer)
    except json.JSONDecodeError:break
    yield item;buffer=buffer[end:]
 raise ValueError('incomplete source JSON array')

report={}
for name in ['scifact','nfcorpus','longmemeval','locomo']:
 data=load(name);ids={d['doc'] for d in data['docs']};missing={q['id']:sorted(set(q['relevant'])-ids) for q in data['queries'] if set(q['relevant'])-ids}
 assert not missing,(name,missing)
 contexts={d['doc']:d['context'] for d in data['docs']} if name!='longmemeval' else data['contexts']
 report[name]={'queries':len(data['queries']),'documents':len(ids),'chunks':len(data['docs']),'missing_positive_documents':len(missing),'source_documents_exceeding_2500_words':sum(len(t.split())>2500 for t in contexts.values()),'max_source_words':max(len(t.split()) for t in contexts.values())}
 counts=[len(q['relevant']) for q in data['queries']]
 report[name].update({'positive_qrels_min':min(counts),'positive_qrels_median':statistics.median(counts),'positive_qrels_max':max(counts),'queries_with_more_than_20_positives':sum(n>20 for n in counts),'oracle_recall20_ceiling':statistics.mean(min(20,n)/n for n in counts)})
 if any('scope' in q for q in data['queries']):
  scopes=[len(q['scope']) for q in data['queries']];report[name].update({'candidate_sessions_min':min(scopes),'candidate_sessions_median':statistics.median(scopes),'candidate_sessions_max':max(scopes)})
 if name=='longmemeval':selected={q['id'] for q in data['queries']}
 del data,contexts
missing_support={};duplicates={};checked=set()
for item in objects(LAB/'longmem.json'):
 if item['question_id'] not in selected:continue
 checked.add(item['question_id']);missing=set(item['answer_session_ids'])-set(item['haystack_session_ids'])
 if missing:missing_support[item['question_id']]=sorted(missing)
 keys=[]
 for date,session in zip(item['haystack_dates'],item['haystack_sessions']):
  full=date+'\n'+'\n'.join(t['role']+': '+t['content'] for t in session);keys.append(hashlib.sha256(full.encode()).hexdigest())
 if len(keys)!=len(set(keys)):duplicates[item['question_id']]=len(keys)-len(set(keys))
assert checked==selected
assert not missing_support,missing_support
report['longmemeval'].update({'source_questions_verified':len(checked),'missing_original_answer_session_ids':missing_support,'within_question_duplicate_text_sessions':duplicates})
(OUT/'data-label-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

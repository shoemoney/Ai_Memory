"""Pinned LoCoMo evidence-to-session retrieval labels, without answer generation."""
import json,random,re,collections,hashlib,statistics
from run import LAB,OUT,SEED,fetch,save,chunks
REV='3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376'
URL=f'https://raw.githubusercontent.com/snap-research/locomo/{REV}/data/locomo10.json'
EXPECTED='79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4'
def prepare_locomo():
 path=LAB/'locomo.json';digest=fetch(URL,path);assert digest==EXPECTED
 source=json.loads(path.read_text());docs=[];contexts={};eligible=[];excluded=collections.Counter();unmapped=[]
 for conversation in source:
  key=str(conversation['sample_id']);dialog=conversation['conversation'];turns={};scope=[]
  for field in sorted((k for k in dialog if re.fullmatch(r'session_\d+',k)),key=lambda k:int(k.split('_')[1])):
   session=key+':'+field;scope.append(session);messages=dialog[field]
   full='Session date: '+dialog[field+'_date_time']+'\n'+'\n'.join(t['speaker']+': '+t['text']+(' [Image caption: '+t['blip_caption']+']' if t.get('blip_caption') else '') for t in messages)
   contexts[session]=full
   for t in messages:
    assert t['dia_id'] not in turns
    turns[t['dia_id']]=session
   for index,text in enumerate(chunks(full)):docs.append({'id':session+':chunk:'+str(index),'doc':session,'text':text,'context':full})
  for index,qa in enumerate(conversation['qa']):
   qid=key+':qa:'+str(index);evidence=qa.get('evidence',[])
   if qa['category']==5 or not evidence:excluded['adversarial_or_no_evidence']+=1;continue
   ids=[item for entry in evidence for item in re.findall(r'D\d+:\d+',entry)]
   if not ids or set(ids)-set(turns):
    excluded['unmapped_evidence']+=1;unmapped.append({'id':qid,'evidence':evidence,'unmapped':sorted(set(ids)-set(turns))});continue
   eligible.append({'id':qid,'text':qa['question'],'relevant':{turns[item]:1 for item in ids},'scope':list(scope),'type':str(qa['category']),'source_evidence_ids':ids})
 selected=random.Random(SEED).sample(eligible,150)
 save(LAB/'locomo.data.json',{'docs':docs,'queries':selected,'contexts':contexts})
 manifest=json.loads((OUT/'manifest.json').read_text())
 manifest['sources']['locomo']={'url':URL,'revision':REV,'sha256':digest,'license':'CC-BY-NC-4.0','license_url':f'https://raw.githubusercontent.com/snap-research/locomo/{REV}/LICENSE.txt','queries':len(selected),'eligible_queries':len(eligible),'excluded':dict(excluded),'unmapped_evidence_queries':unmapped,'selected_question_ids':[q['id'] for q in selected],'question_type_counts':dict(collections.Counter(q['type'] for q in selected)),'conversations':len(source),'documents':len(contexts),'chunks':len(docs),'sampling':'150 seeded uniform questions with author-supplied evidence, excluding category 5, empty evidence, and any unmapped evidence ID. Exact original turn IDs map to their sessions; each question searches only sessions of its original conversation. Raw dialogs, dates, and provided BLIP captions only; no answers, generated observations, or generated session summaries in the index.'}
 save(OUT/'manifest.json',manifest)
 # Independently follow each selected source question's original turn references.
 selected_by_id={q['id']:q for q in selected};checked=0
 for conversation in source:
  key=str(conversation['sample_id']);dialog=conversation['conversation'];turn_index={}
  for field,messages in dialog.items():
   if re.fullmatch(r'session_\d+',field):
    for turn in messages:turn_index[turn['dia_id']]=key+':'+field
  for index,qa in enumerate(conversation['qa']):
   qid=key+':qa:'+str(index)
   if qid not in selected_by_id:continue
   q=selected_by_id[qid];actual=set()
   for entry in qa['evidence']:
    for reference in re.findall(r'D\d+:\d+',entry):actual.add(turn_index[reference])
   assert actual==set(q['relevant']) and actual<=set(q['scope'])
   assert q['text']==qa['question'];checked+=1
 assert checked==150
 save(OUT/'locomo-label-audit.json',{'source_questions_verified':checked,'missing_original_support_ids':0,'source_sha256':digest,'evidence_mapping':'Exact source turn IDs to original conversation sessions; no leading-zero or typo corrections','excluded':dict(excluded),'no_source_answers_indexed':True,'scope_sessions_min':min(len(q['scope']) for q in selected),'scope_sessions_max':max(len(q['scope']) for q in selected)})
 print('prepared locomo',len(selected),'queries',len(contexts),'sessions',len(docs),'chunks; max source words',max(len(t.split()) for t in contexts.values()))

if __name__=='__main__':prepare_locomo()

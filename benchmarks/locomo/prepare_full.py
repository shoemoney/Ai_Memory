import hashlib,json,random,re
from pathlib import Path
from full_common import *
from run import DATA_REV,EMBED_REV

def main():
 env();OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'selection.json').exists():return
 data=read(LAB/'locomo10.json')
 import spacy
 nlp=spacy.load('en_core_web_sm');nlp.max_length=3000000
 mapping=read(ROOT/'name-hashes.json')
 exclusions=set('January February March April May June July August September October November December Monday Tuesday Wednesday Thursday Friday Saturday Sunday The A I You User Person'.lower().split())
 for ci,c in enumerate(data):
  for suffix,key in [('A','speaker_a'),('B','speaker_b')]:
   for word in c['conversation'][key].split():
    h=hashlib.sha256(word.lower().encode()).hexdigest();old=mapping.get(h)
    if old:
     for alias,value in list(mapping.items()):
      if value==old:mapping[alias]=f'PersonC{ci:02d}{suffix}'
    mapping[h]=f'PersonC{ci:02d}{suffix}'
 texts=[]
 for c in data:
  for key,session in c['conversation'].items():
   if isinstance(session,list):
    texts.extend(t.get('text','')+' '+t.get('blip_caption','') for t in session)
  texts.extend(q['question']+' '+str(q.get('answer','')) for q in c['qa'])
 from collections import Counter
 lower=Counter();capital=Counter()
 for text in texts:
  for word in re.findall(r'\b[A-Za-z]+\b',text):
   lower[word.lower()]+=1
   capital[word.lower()]+=word[0].isupper()
 for doc in nlp.pipe(texts,batch_size=32):
  for entity in doc.ents:
   if entity.label_!='PERSON':continue
   for token in entity:
    word=token.text
    if (token.pos_=='PROPN' and word.isalpha() and word[0].isupper()
        and not token.is_stop and word.lower() not in exclusions and len(word)>1
        and lower[word.lower()]>0 and capital[word.lower()]/lower[word.lower()]>=0.8):
     h=hashlib.sha256(word.lower().encode()).hexdigest();mapping.setdefault(h,'PersonX'+h[:8])
 mapping.update(read(ROOT/'extra-name-aliases.json'))
 atomic(OUT/'name-hashes.json',mapping)
 rng=random.Random(SEED);selected=[]
 for cat in [1,2,3,4]:
  chosen=[];remaining=[]
  for ci,c in enumerate(data):
   pool=[(ci,i) for i,q in enumerate(c['qa']) if q['category']==cat]
   pick=rng.sample(pool,min(8,len(pool)));chosen.extend(pick);remaining.extend(x for x in pool if x not in pick)
  chosen.extend(rng.sample(remaining,80-len(chosen)))
  selected.extend(chosen)
 questions=[];conversations=[]
 for ci,c in enumerate(data):
  sessions=[];turns=[]
  for key in sorted([k for k,v in c['conversation'].items() if re.fullmatch(r'session_\d+',k) and isinstance(v,list)],key=lambda x:int(x.split('_')[1])):
   date=c['conversation'][key+'_date_time'];st=[]
   for t in c['conversation'][key]:
    text=f"[{date}] {t['dia_id']} {t['speaker']}: {t.get('text','')}"
    for field in ['query','blip_caption']:
     if t.get(field):text+=f" [Image {field}: {t[field]}]"
    st.append(pseudo(text))
   sessions.append(dict(key=key,date=date,turns=st));turns.extend(st)
  conversations.append(dict(conversation=ci,sessions=sessions,turns=turns))
 for ci,i in sorted(selected):
  q=data[ci]['qa'][i];questions.append(dict(item_id=f'c{ci:02d}-q{i:03d}',conversation=ci,index=i,category=q['category'],question=pseudo(q['question']),gold=pseudo(q['answer']),evidence=q.get('evidence',[]),original_question_sha256=hashlib.sha256(q['question'].encode()).hexdigest()))
 assert len(questions)==320 and len({q['item_id'] for q in questions})==320
 atomic(OUT/'selection.json',questions);atomic(OUT/'conversations.json',conversations)
 atomic(OUT/'manifest.json',dict(n=320,seed=SEED,categories={str(c):80 for c in [1,2,3,4]},conversations=10,sampling='8 per conversation/category where available, then fill each category uniformly from unselected items to 80',dataset_revision=DATA_REV,dataset_sha256=hashlib.sha256((LAB/'locomo10.json').read_bytes()).hexdigest(),dataset_license='CC-BY-NC-4.0',embed_revision=EMBED_REV,model=MODEL,judge_votes=3,judge_seed_rule='20261122 + 100 * backend index + vote index 0..2',pseudonymization='pilot hashes plus speaker aliases and spaCy en_core_web_sm 3.8.0 PERSON token hashes',server_context=65536))
 print('Prepared',len(questions),'questions')
if __name__=='__main__':main()

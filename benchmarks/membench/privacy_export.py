"""Redact missed names in retained responses after scoring, with original hashes.

Private originals remain in task scratch for the tester audit and verification,
then are deleted during cleanup. This never changes scoring inputs or labels.
"""
import collections
from common import *
def main():
 env();paths=sorted((OUT/'items').glob('*/*/*.json'));rows=[]
 for p in paths:
  backup=LAB/'result-originals'/p.relative_to(OUT/'items')
  rows.append((p,read(backup) if backup.exists() else read(p)))
 if (OUT/'privacy-export.json').exists():return
 assert len(rows)==900 and all(d['score'] is not None for _,d in rows),'Export only after all scoring'
 data=read(LAB/'prepared.json');source={x['item_id']:x for x in data['items']}
 texts=[a for x in data['items'] if x['benchmark']=='mab' for a in x['gold']]
 for p,d in rows:
  texts.append(d['answer'])
  if d.get('judge'):texts.append(d['judge']['result'].get('reasoning',''))
 import spacy
 nlp=spacy.load('en_core_web_sm',disable=['parser','lemmatizer']);names=set();counts=collections.Counter();caps=collections.Counter()
 for text in texts:
  for w in re.findall(r'\b[A-Za-z]+\b',text):counts[w.lower()]+=1;caps[w.lower()]+=w[0].isupper()
 protected=set('correct hallucination omission director doctor nurse teacher mother father friend colleague person unknown'.split())
 for doc in nlp.pipe(texts,batch_size=32):
  for e in doc.ents:
   if e.label_=='PERSON':
    for t in e:
     if t.text.isalpha() and len(t.text)>1 and not t.is_stop and t.text.lower() not in protected and caps[t.text.lower()]/max(1,counts[t.text.lower()])>=.8:names.add(t.text.lower())
 # Synthetic relationship labels sometimes join two names into one unrecognized NER token.
 for line in (LAB/'halu-medium').read_text().splitlines():
  user=json.loads(line)
  subject=re.search(r'Name:\s*([^;]+)',user.get('persona_info',''))
  if subject:names.update(w.lower() for w in re.findall('[A-Za-z]+',subject.group(1)) if len(w)>1)
  for session in user['sessions']:
   for memory in session.get('memory_points',[]):
    for n in re.findall(r'\b(?:Friend|Colleague|Partner|Sibling|Brother|Sister|Mother|Father|Cousin|Neighbor|Classmate|Mentor|Spouse|Husband|Wife)\s+([A-Z][A-Za-z]+)',memory['memory_content']):
     if re.fullmatch(r'[A-Z][a-z]+(?:[A-Z][a-z]+)+',n):names.add(n.lower())
 for text in texts:
  for compound in re.findall(r"\b(?:[A-Z][a-z]*|[a-z])['’][A-Z][A-Za-z]+\b",text):names.update(w.lower() for w in re.findall('[A-Za-z]+',compound) if len(w)>1)
 names={w for w in names if w not in protected and not re.fullmatch(r'(?:person|anon)\d+',w)}
 mapping={w:f'Anon{i:03d}' for i,w in enumerate(sorted(names,key=sha))}
 def mask(t):return re.sub(r'\b[A-Za-z]+\b',lambda m:mapping.get(m[0].lower(),m[0]),t)
 records=[]
 for path,d in rows:
  original=json.dumps(d,sort_keys=True);atomic(LAB/'result-originals'/path.relative_to(OUT/'items'),d)
  before=d['answer']
  if d['benchmark']=='mab':assert int(all(mask(a).lower() in mask(before).lower() for a in source[d['item_id']]['gold']))==d['score'],'Redaction changed the EventQA metric'
  d['answer']=mask(d['answer']);d['response']['text']=mask(d['response']['text'])
  if d.get('judge'):
   for attempt in d['judge']['attempts']:attempt['text']=mask(attempt['text'])
   d['judge']['result']['reasoning']=mask(d['judge']['result'].get('reasoning',''))
  d['privacy_export']={'raw_record_sha256':sha(original),'raw_answer_sha256':sha(before),'answer_redacted':d['answer']!=before}
  atomic(path,d);records.append({'item_id':d['item_id'],'method':d['method'],'raw_record_sha256':sha(original),'exported_record_sha256':sha(json.dumps(d,sort_keys=True)),'answer_redacted':d['answer']!=before})
 atomic(OUT/'privacy-export.json',{'after_all_scoring':True,'scoring_inputs_and_labels_unchanged':True,'eventqa_metric_equivalent_after_redaction':True,'method':'Local spaCy PERSON scan, explicit persona subject words, synthetic compound relationship names, apostrophe surnames; output-only aliases in word-hash order','mapping':{sha(k):v for k,v in mapping.items()},'records':records,'answer_redactions':sum(r['answer_redacted'] for r in records)})
 print('privacy export',len(records),'records',sum(r['answer_redacted'] for r in records),'answers redacted',flush=True)
if __name__=='__main__':main()

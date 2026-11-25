"""Pinned downloads, deterministic two-dataset sampling, no inference."""
import collections,hashlib,json,random,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LAB=Path('/var/tmp/membench-extraction')
SEED=20261122
LC_REV='3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376'
LME_REV='98d7416c24c778c2fee6e6f3006e7a073259d48f'
SOURCES=[{'dataset':'LoCoMo','revision':LC_REV,'license':'CC-BY-NC-4.0','url':f'https://raw.githubusercontent.com/snap-research/locomo/{LC_REV}/data/locomo10.json','filename':'locomo10.json','license_url':f'https://github.com/snap-research/locomo/blob/{LC_REV}/LICENSE.txt'}, {'dataset':'LongMemEval cleaned oracle','revision':LME_REV,'license':'MIT, dataset-card declaration','url':f'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/{LME_REV}/longmemeval_oracle.json','filename':'lme-oracle.json','license_url':f'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/blob/{LME_REV}/README.md'}]
COMMON=set('a an the i my our your their his her its we you he she they it this that these those and or but for from with as at in on to by of is are was were am be been being do does did can could would should will have has had not no yes hey hi hello thanks thank yeah yep nope okay ok wow good great glad what when where why how who which if so well just really actually recently also anyway another always after before since while during now then there here today yesterday tomorrow last next every each one two three four five first second new old more most some all any many much happy sure sounds sound cool hope hopefully sorry please let keep love like look see seeing going getting having doing making taking working trying spending feeling thinking found finally started lately both talking speaking remember everything anything something nothing definitely totally guess right back up down still even pretty very wanted want wish life nature art painting cooking dance running reading playing learning helping sharing feeling knowing looking living moving between because once usually sometimes indeed perhaps although together time by the way'.split())
COMMON.update('finding creating dancing losing opening handling transitioning bringing living loving building watching enjoying taking spending raising trying making feeling relaxing exploring practicing preparing focusing pursuing following supporting singing skiing swimming writing walking working reading learning starting joining finishing planning moving getting connecting volunteering winning having giving being doing keeping positive finally unfortunately luckily honestly thankfully absolutely awesome amazing plus gonna wanna till yep yep sounds seems sound seems mean means feels lets let'.split())
DATES=set('Monday Tuesday Wednesday Thursday Friday Saturday Sunday Mon Tue Wed Thu Fri Sat Sun January February March April May June July August September October November December Jan Feb Mar Apr Jun Jul Aug Sep Sept Oct Nov Dec'.split())
def load_sources():
 LAB.mkdir(exist_ok=True)
 data=[];meta=[]
 for src in SOURCES:
  path=LAB/src['filename']
  if not path.exists():path.write_bytes(urllib.request.urlopen(src['url'],timeout=90).read())
  raw=path.read_bytes();data.append(json.loads(raw));meta.append({**src,'sha256':hashlib.sha256(raw).hexdigest()})
 return data,meta

def prepare():
 (lc,lme),meta=load_sources();rng=random.Random(SEED);rows=[]
 for ci,c in enumerate(lc):
  obs=collections.defaultdict(list)
  for session in c['observation'].values():
   for _,facts in session.items():
    for f in facts:
     ids=f[1] if isinstance(f[1],list) else [f[1]]
     if len(ids)==1:obs[ids[0]].append(f[0])
  pools=collections.defaultdict(list)
  for k,turns in c['conversation'].items():
   if not re.fullmatch(r'session_\d+',k):continue
   for t in turns:
    txt=t['text']
    if t['dia_id'] not in obs or not 80<=len(txt)<=400 or 'img_url'in t:continue
    if not re.search(r'\b(I|my|me|we|our)\b',txt,re.I):continue
    if re.search(r'\b(love|loves|like|likes|enjoy|enjoys|favou?rite)\b',txt,re.I):st='preference_marker'
    elif re.search(r'\b(yesterday|tomorrow|ago|last|next|week|month|year|plan|will|since)\b',txt,re.I):st='temporal_or_plan'
    else:st='other'
    pools[st].append(t)
  for st in ('preference_marker','temporal_or_plan','other'):
   if len(pools[st])<5:raise ValueError(f'Insufficient stratum {ci} {st}: {len(pools[st])}')
   for t in rng.sample(pools[st],5):
    rows.append({'id':f'lc-c{ci:02d}-{t["dia_id"]}','dataset':'LoCoMo','cluster':f'lc-c{ci:02d}','stratum':st,'speaker_original':t['speaker'],'text':t['text'],'dataset_observations':list(dict.fromkeys(obs[t['dia_id']]))})
 pools=collections.defaultdict(list)
 for q in lme:
  if q['question_type']=='single-session-assistant' or q['question_id'].endswith('_abs'):continue
  choices=[]
  for si,session in enumerate(q['haystack_sessions']):
   for ti,t in enumerate(session):
    if t.get('has_answer') and t['role']=='user' and 80<=len(t['content'])<=400 and re.search(r'\b(I|my|me|we|our)\b',t['content'],re.I):choices.append((si,ti,t))
  if choices:
   si,ti,t=rng.choice(choices)
   pools[q['question_type']].append({'id':f'lme-{q["question_id"]}-s{si}-t{ti}','dataset':'LongMemEval','cluster':'lme-'+q['question_id'],'stratum':q['question_type'],'speaker_original':'USER','text':t['content'],'dataset_question':q['question'],'dataset_answer':q['answer'],'evidence_session_index':si,'evidence_turn_index':ti})
 for st in ('single-session-user','single-session-preference','temporal-reasoning','knowledge-update','multi-session'):
  if len(pools[st])<30:raise ValueError('Insufficient LME stratum '+st+': '+str(len(pools[st])))
  rows.extend(rng.sample(pools[st],30))
 # Keep original random selections where unique; replace duplicate evidence text
 # deterministically within its original question-type stratum.
 chosen_ids={r['id'] for r in rows};chosen_text={' '.join(r['text'].split()).casefold() for r in rows};seen=set()
 replacements=[]
 for index,r in enumerate(rows):
  norm=' '.join(r['text'].split()).casefold()
  if norm in seen and r['dataset']=='LongMemEval':
   options=[v for v in pools[r['stratum']] if v['id'] not in chosen_ids and ' '.join(v['text'].split()).casefold() not in chosen_text]
   replacement=random.Random(SEED+997+index).choice(options)
   replacements.append({'index':index,'old_id':r['id'],'new_id':replacement['id']})
   rows[index]=replacement;r=replacement;chosen_ids.add(r['id']);norm=' '.join(r['text'].split()).casefold();chosen_text.add(norm)
  seen.add(norm)
 # Mask personal names and other named entities consistently. Dates stay literal.
 speakers=sorted({c['conversation'][k] for c in lc for k in ('speaker_a','speaker_b')})
 mapping={s:f'PERSON_{i:03d}' for i,s in enumerate(speakers)}
 for name in speakers:
  if len(name)>4 and name[:3] not in {'And','Car'}:mapping.setdefault(name[:3],mapping[name])
 texts=[]
 for r in rows:
  texts.append(r['text']);texts.extend(r.get('dataset_observations',[]))
  texts.extend([str(r.get('dataset_question','')),str(r.get('dataset_answer',''))])
 candidates=set()
 for text in texts:
  for m in re.finditer(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)?\b',text):
   prefix=text[:m.start()].rstrip()
   # Sentence-initial capitalization is not evidence of a name.
   if prefix and prefix[-1] not in '.!?\n':candidates.add(m[0])
 for r in rows:
  candidates.update(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)?\b',str(r.get('dataset_answer',''))))
 for text in texts:
  for match in re.finditer(r'\b(?:Dr|Mr|Mrs|Ms|Prof)\.?\s+([A-Z][a-z]+)',text):candidates.add(match[1])
  for match in re.finditer(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',text):
   words=match[0].split()
   if sum(w.lower() not in COMMON and w not in DATES for w in words)>=2:candidates.update(words)
 for word in sorted(candidates):
  if word not in DATES and word not in {'Christmas','Thanksgiving','Easter','Halloween','Hanukkah','Diwali','New','Year','Day','Valentine'} and word.lower() not in COMMON and word!='USER':mapping.setdefault(word,f'ENTITY_{len(mapping):04d}')
 pattern=re.compile(r'\b(?:'+'|'.join(map(re.escape,sorted(mapping,key=len,reverse=True)))+r')\b')
 def mask(s):
  def replace(m):
   word=m[0]
   if word.endswith('s') and word[:-1] in DATES:return word
   if word in {'Black','Good','Maundy','Ash','Palm'} and re.match(r'\s+(?:Friday|Thursday|Wednesday|Sunday)\b',s[m.end():]):return word
   return mapping[word]
  return pattern.sub(replace,s)
 for r in rows:
  r['speaker']=mapping.get(r.pop('speaker_original'),'USER');r['text']=mask(r['text'])
  if 'dataset_observations'in r:r['dataset_observations']=[mask(s) for s in r['dataset_observations']]
  if 'dataset_question'in r:r['dataset_question']=mask(r['dataset_question']);r['dataset_answer']=mask(str(r['dataset_answer']))
 assert len(rows)==300 and len({r['id'] for r in rows})==300
 # Audit 60 randomly selected original generated observation units, before correction.
 units=[{'id':r['id'],'speaker':r['speaker'],'source':r['text'],'observation_index':i,'observation':f} for r in rows if r['dataset']=='LoCoMo' for i,f in enumerate(r['dataset_observations'])]
 audit=random.Random(SEED+1).sample(units,60)
 (ROOT/'data/candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
 (ROOT/'data/generated-reference-audit-inputs.json').write_text(json.dumps(audit,indent=2)+'\n')
 manifest={'N':300,'sampling_seed':SEED,'audit_seed':SEED+1,'sources':meta,'strata':dict(collections.Counter((r['dataset']+'/'+r['stratum']) for r in rows)),'deidentification':'Personal and other proper names replaced consistently; weekday/month tokens retained; no source dates or relative time expressions supplied outside the turn.','duplicate_replacements':replacements,'reference_status':'Pending manual source-only atomic annotation and generated-observation audit.'}
 (ROOT/'data/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2))
if __name__=='__main__':
 prepare()
 from compile_references import run
 run()

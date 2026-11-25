"""Fetch fixed source revisions and freeze paired samples before inference."""
import collections,json,random,re
import numpy as np
import pyarrow.parquet as pq
from common import *

def main():
 env();LAB.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 if (LAB/'prepared.json').exists() and (OUT/'manifest.json').exists():
  build_indexes(read(LAB/'prepared.json')['contexts']);return
 for cfg in SOURCES.values():
  path=LAB/cfg['local'];download(f"https://huggingface.co/datasets/{cfg['dataset']}/resolve/{cfg['revision']}/{cfg['file']}",path)
  assert sha(path.read_bytes())==cfg['sha256']
 ar=pq.read_table(LAB/'mab-ar').to_pylist();hu=[json.loads(x) for x in (LAB/'halu-medium').read_text().splitlines()]
 rng=random.Random(SEED);contexts={};items=[]
 for ri,r in enumerate(ar):
  if r['metadata']['source']!='eventqa_65536':continue
  cid=f'mab-r{ri:02d}';contexts[cid]=r['context']
  for qi in sorted(rng.sample(range(len(r['questions'])),30)):
   items.append(dict(benchmark='mab',item_id=f'{cid}-q{qi:03d}',context=cid,question=r['questions'][qi],gold=r['answers'][qi],kind='eventqa_65536',evidence=[]))
 pools=collections.defaultdict(list)
 for ui,u in enumerate(hu):
  chunks=[]
  for si,s in enumerate(u['sessions']):
   # Only the real dialogue up to the question's own session enters the history.
   chunks.extend(f"[{t['timestamp']}] {t['role']}: {t['content']}" for t in s['dialogue'])
   if si>=30:break
   cid=f'halu-u{ui:02d}-s{si:02d}'
   contexts[cid]='\n'.join(chunks)
   for qi,q in enumerate(s.get('questions',[])):
    pools[q['question_type']].append(dict(benchmark='halu',item_id=f'{cid}-q{qi:02d}',context=cid,question=q['question'],gold=[q['answer']],kind=q['question_type'],evidence=[x['memory_content'] for x in q.get('evidence',[])]))
 for kind,pool in sorted(pools.items()):
  # Spread each stratum across users before allowing repeated user selections.
  grouped=collections.defaultdict(list)
  for q in pool:grouped[q['context'].split('-s')[0]].append(q)
  keys=sorted(grouped);rng.shuffle(keys)
  for g in grouped.values():rng.shuffle(g)
  picked=[]
  while len(picked)<25:
   for k in keys:
    if grouped[k] and len(picked)<25:picked.append(grouped[k].pop())
  items.extend(picked)
 assert collections.Counter(x['benchmark'] for x in items)=={'mab':150,'halu':150}
 keep={x['context'] for x in items};contexts={k:v for k,v in contexts.items() if k in keep}
 # Build one deterministic token mapping from NER; gold and evidence are never indexed.
 import spacy
 nlp=spacy.load('en_core_web_sm',disable=['parser','lemmatizer']);nlp.max_length=2000000
 names=set();excluded=set('January February March April May June July August September October November December Monday Tuesday Wednesday Thursday Friday Saturday Sunday'.lower().split())
 texts=list(contexts.values())+[x['question']+' '+' '.join(x['gold'])+' '+' '.join(x['evidence']) for x in items]
 for d in nlp.pipe(texts,batch_size=4):
  for e in d.ents:
   if e.label_=='PERSON':
    for t in e:
     if t.text.isalpha() and len(t.text)>1 and t.text.lower() not in excluded:names.add(t.text.lower())
 # Include surname parts that spaCy keeps inside apostrophe-containing tokens.
 for text in texts:
  for compound in re.findall(r"\b(?:[A-Z][a-z]*|[a-z])['’][A-Z][A-Za-z]+\b",text):
   names.update(w.lower() for w in re.findall('[A-Za-z]+',compound) if len(w)>1)
 # Explicit subject names in the synthetic persona records, including singleton variants.
 for u in hu:
  m=re.search(r'Name:\s*([^;]+)',u['persona_info'])
  if m:names.update(w.lower() for w in re.findall('[A-Za-z]+',m.group(1)))
 from collections import Counter
 counts=Counter();caps=Counter()
 for text in texts:
  for word in re.findall(r'\b[A-Za-z]+\b',text):
   counts[word.lower()]+=1;caps[word.lower()]+=word[0].isupper()
 names={w for w in names if w not in nlp.Defaults.stop_words and w not in excluded and counts[w] and caps[w]/counts[w]>=0.8}
 mapping={w:f'Person{i:03d}' for i,w in enumerate(sorted(names,key=sha))}
 def mask(t):return re.sub(r'\b[A-Za-z]+\b',lambda m:mapping.get(m[0].lower(),m[0]),t)
 contexts={k:mask(v) for k,v in contexts.items()}
 for x in items:
  x['question']=mask(x['question']);x['gold']=[mask(v) for v in x['gold']];x['evidence']=[mask(v) for v in x['evidence']]
 # Save source content only to disposable scratch; retained manifest contains IDs and hashes.
 atomic(LAB/'prepared.json',{'items':items,'contexts':contexts,'name_hashes':{sha(k):v for k,v in mapping.items()}})
 manifest={'seed':SEED,'n':300,'sources':SOURCES,'sampling':{'mab':'30 questions sampled uniformly without replacement from each of all five eventqa_65536 contexts','halu':'25 questions per six question types; seeded round robin across users, using only sessions 0 through 29 and their cumulative real dialogue histories'},'pseudonymization':'spaCy en_core_web_sm 3.8.0 PERSON candidate words, filtered to non-stopwords capitalized in at least 80% of occurrences, mapped to compact PersonNNN aliases in word-hash order before indexing and inference','items':[{k:v for k,v in x.items() if k not in ['question','gold','evidence']}|{'question_sha256':sha(x['question']),'reference_sha256':sha(json.dumps(x['gold']))} for x in items],'context_sha256':{k:sha(v) for k,v in contexts.items()},'embed_revision':EMBED_REV}
 atomic(OUT/'manifest.json',manifest)
 print('prepared',len(items),'items',len(contexts),'contexts',flush=True)
 build_indexes(contexts)

def build_indexes(contexts):
 env()
 from sentence_transformers import SentenceTransformer
 import torch
 torch.set_num_threads(4)
 model=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',revision=EMBED_REV,device='cpu')
 # Short chunks stay below the embedder's 256 wordpiece-token limit in typical text.
 for cid,text in contexts.items():
  path=LAB/'indexes'/f'{cid}.json';vecpath=path.with_suffix('.npy')
  if path.exists() and vecpath.exists():continue
  words=text.split();chunks=[' '.join(words[i:i+100]) for i in range(0,len(words),80)]
  vectors=model.encode(chunks,normalize_embeddings=True,batch_size=64,show_progress_bar=False)
  atomic(path,chunks);np.save(vecpath,vectors)
 print('indexed',len(contexts),'contexts',flush=True)

if __name__=='__main__':main()

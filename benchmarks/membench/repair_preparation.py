"""One-time, pre-inference repair of excluded long-alias preparation.

The final prepare.py performs this filtering directly. This recovery script reused
cached NER candidate hashes without rerunning the expensive NER pass.
"""
import ast,collections,sys
import prepare
from common import *
def main():
 old=read(LAB/'prepared.json');manifest=read(OUT/'manifest.json');old_sha=sha(json.dumps(manifest,sort_keys=True))
 assert not list((OUT/'items').glob('*/*/*.json')),'Never repair scored input'
 # Reconstruct exactly the frozen original source cohort, stopping before NER.
 tree=ast.parse((ROOT/'prepare.py').read_text());f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');body=[]
 for node in f.body:
  if isinstance(node,ast.Import) and any(n.name=='spacy' for n in node.names):break
  if isinstance(node,ast.If) and 'prepared.json' in ast.unparse(node.test):continue
  body.append(node)
 ns=vars(prepare).copy();exec(compile(ast.Module(body=body,type_ignores=[]),'fixed source cohort','exec'),ns)
 items=ns['items'];contexts=ns['contexts'];texts=list(contexts.values())+[x['question']+' '+' '.join(x['gold'])+' '+' '.join(x['evidence']) for x in items]
 from spacy.lang.en.stop_words import STOP_WORDS
 counts=collections.Counter();caps=collections.Counter()
 for text in texts:
  for word in re.findall(r'\b[A-Za-z]+\b',text):counts[word.lower()]+=1;caps[word.lower()]+=word[0].isupper()
 excluded=set('January February March April May June July August September October November December Monday Tuesday Wednesday Thursday Friday Saturday Sunday'.lower().split())
 candidates=set(old['name_hashes'])
 for text in texts:
  for compound in re.findall(r"\b(?:[A-Z][a-z]*|[a-z])['’][A-Z][A-Za-z]+\b",text):
   candidates.update(sha(w.lower()) for w in re.findall('[A-Za-z]+',compound) if len(w)>1)
 names={w for w in counts if sha(w) in candidates and w not in STOP_WORDS and w not in excluded and caps[w]/counts[w]>=.8}
 mapping={w:f'Person{i:03d}' for i,w in enumerate(sorted(names,key=sha))}
 def mask(t):return re.sub(r'\b[A-Za-z]+\b',lambda m:mapping.get(m[0].lower(),m[0]),t)
 contexts={k:mask(v) for k,v in contexts.items()}
 for x in items:
  x['question']=mask(x['question']);x['gold']=[mask(v) for v in x['gold']];x['evidence']=[mask(v) for v in x['evidence']]
 assert [x['item_id'] for x in items]==[x['item_id'] for x in old['items']]
 atomic(OUT/'excluded-preparation-manifest.json',manifest)
 manifest['pseudonymization']='spaCy en_core_web_sm 3.8.0 PERSON candidate words, filtered to non-stopwords capitalized in at least 80% of occurrences, mapped to compact PersonNNN aliases in word-hash order before indexing and inference'
 manifest['items']=[{k:v for k,v in x.items() if k not in ['question','gold','evidence']}|{'question_sha256':sha(x['question']),'reference_sha256':sha(json.dumps(x['gold']))} for x in items]
 manifest['context_sha256']={k:sha(v) for k,v in contexts.items()}
 atomic(LAB/'prepared.json',{'items':items,'contexts':contexts,'name_hashes':{sha(w):v for w,v in mapping.items()}});atomic(OUT/'manifest.json',manifest)
 for p in (LAB/'indexes').glob('*'):
  if p.suffix in ['.json','.npy']:p.unlink()
 atomic(OUT/'preparation-repair.json',{'before_inference':True,'scored_items_before_repair':0,'sample_ids_unchanged':True,'old_manifest_sha256':old_sha,'new_manifest_sha256':sha(json.dumps(manifest,sort_keys=True)),'old_alias_count':len(candidates),'new_alias_count':len(mapping),'reason':'Long hash aliases exceeded window and unrestricted PERSON spans masked lowercase common words. Compact aliases and capitalization/stopword filtering restore readable complete histories. No scored result was discarded.'})
 print('repaired',len(items),'items',len(mapping),'aliases',flush=True)
if __name__=='__main__':main()

"""Check context capacity without changing prompts or consulting relevance labels."""
from pathlib import Path
import json,hashlib,requests
from tokenizers import Tokenizer
from run import LAB,OUT,load
path=LAB/'qwen-tokenizer.json';url='https://huggingface.co/Qwen/Qwen3.5-4B/resolve/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/tokenizer.json'
if not path.exists():
 r=requests.get(url,timeout=120);r.raise_for_status();path.write_bytes(r.content)
tok=Tokenizer.from_file(str(path))
def prompt(d,data):
 context=' '.join((d.get('context') or data['contexts'][d['doc']]).split()[:2500])
 return '<document>\n'+context+'\n</document>\nHere is the chunk we want to situate within the whole document:\n<chunk>\n'+d['text']+'\n</chunk>\nPlease give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else. Use 50 to 100 tokens.'
report={'tokenizer_url':url,'tokenizer_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'generation_cap':120,'chat_wrapper_safety_tokens':128,'datasets':{}}
for name in ['scifact','nfcorpus','locomo']:
 data=load(name);lengths={};maximum=0
 for start in range(0,len(data['docs']),256):
  ds=data['docs'][start:start+256];encoded=tok.encode_batch([prompt(d,data) for d in ds],add_special_tokens=False)
  for d,e in zip(ds,encoded):lengths[d['id']]=len(e.ids);maximum=max(maximum,len(e.ids))
 p=LAB/(name+'.prefixes.jsonl');diffs=[]
 if p.exists():
  for line in p.read_text().splitlines():
   x=json.loads(line);diffs.append(x['usage']['prompt_tokens']-lengths[x['id']])
 report['datasets'][name]={'chunks':len(lengths),'maximum_raw_prompt_tokens':maximum,'observed_chat_wrapper_delta_min':min(diffs) if diffs else None,'observed_chat_wrapper_delta_max':max(diffs) if diffs else None,'conservative_prompt_plus_generation':maximum+128+120,'fits_4096':maximum+128+120<=4096,'fits_3072':maximum+128+120<=3072,'fits_3008':maximum+128+120<=3008,'fits_2976':maximum+128+120<=2976}
(OUT/'prefix-token-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

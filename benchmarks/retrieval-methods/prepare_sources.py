"""Capture source metadata and inventory the chapter figures, without copying datasets."""
import json,hashlib,requests
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parent
LAB=Path('/data/scratch/membench/retrieval-methods')
urls={'locomo-readme':'https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/README.MD','locomo-license':'https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/LICENSE.txt','locomo-paper':'https://arxiv.org/abs/2402.17753','trec-ndcg':'https://raw.githubusercontent.com/usnistgov/trec_eval/master/m_ndcg.c','scifact-original':'https://huggingface.co/datasets/allenai/scifact/raw/main/README.md','hipporag2':'https://arxiv.org/abs/2502.14802','anthropic':'https://www.anthropic.com/research/contextual-retrieval','rrf':'https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf','lazy':'https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/','beir':'https://raw.githubusercontent.com/beir-cellar/beir/main/README.md','lm':'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/raw/98d7416c24c778c2fee6e6f3006e7a073259d48f/README.md','graphreadme':'https://raw.githubusercontent.com/microsoft/graphrag/main/README.md','scifact_card':'https://huggingface.co/datasets/BeIR/scifact/raw/main/README.md','nfcorpus_card':'https://huggingface.co/datasets/BeIR/nfcorpus/raw/main/README.md','qwen_card':'https://huggingface.co/Qwen/Qwen3.5-4B/raw/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/README.md'}
sources=[]
for key,url in urls.items():
 p=LAB/(key+'.source')
 if not p.exists():r=requests.get(url,timeout=90);r.raise_for_status();p.write_bytes(r.content)
 sources.append({'id':key,'url':url,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
claims=[]
for name in ['05-retrieval-techniques.html','14-knowledge-graphs.html']:
 p=ROOT.parent.parent/'build/chapters'/name
 soup=BeautifulSoup(p.read_text(),'html.parser')
 for el in soup.find_all(['p','tr']):
  t=el.get_text(' ',strip=True)
  keys=['5.7%','3.7%, 2.9%, 1.9%','4 to 5%','0.1%','191/300','150 in','recall@3=0.90','+7%']
  if any(k in t for k in keys):claims.append({'chapter':name,'sentence':t})
(ROOT/'claims.json').write_text(json.dumps(claims,indent=2))
(ROOT/'results/sources.json').write_text(json.dumps(sources,indent=2))
print(len(claims),'claim rows')

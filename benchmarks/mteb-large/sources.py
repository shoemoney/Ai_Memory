#!/usr/bin/env python3
"""Keep content hashes and revisions for primary sources without mirroring datasets."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
urls=[
'https://huggingface.co/Qwen/Qwen3-Embedding-4B/raw/636cd9bf47d976946cdbb2b0c3ca0cb2f8eea5ff/README.md',
'https://huggingface.co/Qwen/Qwen3-Embedding-8B/raw/4e423935c619ae4df87b646a3ce949610c66241c/README.md',
'https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B/raw/9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda/README.md',
'https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B/raw/2c4565515e0f265c6511776e7193b22c0968ddc7/README.md',
'https://huggingface.co/microsoft/harrier-oss-v1-27b/raw/0c0fc62f6d8af9e8604cb818c412301b103a0093/README.md',
'https://huggingface.co/nomic-ai/nomic-embed-multimodal-7b/raw/1291f1b6ca07061b0329df9d5713c09b294be576/README.md',
'https://huggingface.co/datasets/vidore/vidore_v3_hr_mteb_format/raw/bc7d43d64815ed30f664168c8052106484aba7fd/README.md',
'https://raw.githubusercontent.com/illuin-tech/vidore-benchmark/main/README.md']
rows=[]
for url in urls:
 try:
  with urllib.request.urlopen(url,timeout=60) as r:b=r.read()
  rows.append({'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'status':200})
 except Exception as e:rows.append({'url':url,'error':str(e)})
(ROOT/'results'/'sources.json').write_text(json.dumps(rows,indent=2)+'\n')

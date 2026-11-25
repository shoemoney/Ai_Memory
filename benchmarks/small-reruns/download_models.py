import hashlib,os,urllib.request
from pathlib import Path
BASE=Path(os.environ.get('SCRATCH','/data/scratch/membench/small-reruns'))
FILES=[('Qwen/Qwen2.5-3B-Instruct-GGUF','7dabda4d13d513e3e842b20f0d435c732f172cbe','qwen2.5-3b-instruct-q4_k_m.gguf','626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d'),('Qwen/Qwen2.5-7B-Instruct-GGUF','bb5d59e06d9551d752d08b292a50eb208b07ab1f','qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf','dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db'),('Qwen/Qwen2.5-7B-Instruct-GGUF','bb5d59e06d9551d752d08b292a50eb208b07ab1f','qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf','539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a'),('ge525/Qwen3.8-9B-Distill-uncensored-heretic-Q4_K_M-GGUF','72aaa20870ab64522aa5429a833ff780652522ea','qwen3.8-9b-distill-uncensored-heretic-q4_k_m.gguf','694cd96557f5b68cd00f0759ef26b75a67f275d717b5d124e8252d15c8eeb58c'),('empero-ai/Qwen3.8-9B-Distill-GGUF','760121cd70bb4c36b2b5ec58eb765e0df5987efe','Qwen3.8-9B-Q4_K_M.gguf','df13d66021cef676f82be74053220fd75af6bf2a6a7fb77f5222ab9e50744a7a')]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
if __name__=='__main__':
 BASE.mkdir(parents=True,exist_ok=True)
 for repo,rev,name,expected in FILES:
  p=BASE/name
  if not p.exists():urllib.request.urlretrieve(f'https://huggingface.co/{repo}/resolve/{rev}/{name}',p)
  assert digest(p)==expected,name
  print(name,'verified',flush=True)

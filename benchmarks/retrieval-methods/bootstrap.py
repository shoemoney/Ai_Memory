"""Pinned local inference assets. Run using the benchmark virtual environment."""
from pathlib import Path
import hashlib,json,os,tarfile,requests,subprocess,time
LAB=Path(os.environ.get('LAB_DIR','/data/scratch/membench/retrieval-methods'));LAB.mkdir(parents=True,exist_ok=True)
subprocess.run(['df','-h','/','/data'],check=True)
while os.statvfs('/').f_bavail*os.statvfs('/').f_frsize<20*1024**3:
 print('Paused: root filesystem has under 20 GB free before large asset download',flush=True);time.sleep(30)
def download(url,p):
 if p.exists():return
 import time
 part=p.with_suffix(p.suffix+'.part')
 for attempt in range(10):
  offset=part.stat().st_size if part.exists() else 0
  try:
   fresh=url+('\x26' if '?' in url else '?')+'cache_bust='+str(int(time.time()))
   with requests.get(fresh,headers={'Range':f'bytes={offset}-'} if offset else {},stream=True,timeout=(20,300)) as r:
    r.raise_for_status()
    with part.open('ab' if offset and r.status_code==206 else 'wb') as f:
     for block in r.iter_content(4*1024*1024):f.write(block)
   part.replace(p);return
  except requests.RequestException as error:
   print('download retry',attempt+1,type(error).__name__,flush=True);time.sleep(2)
 raise RuntimeError('asset download failed after resumable retries')
repo='https://github.com/ggml-org/llama.cpp/releases/download/b12627/'
for name in ['llama-b12627-bin-ubuntu-cuda-12.8-x64.tar.gz','cudart-llama-b12627-bin-ubuntu-cuda-12.8-x64.tar.gz']:
 marker=LAB/(name+'.done')
 if marker.exists():continue
 p=LAB/name;download(repo+name,p)
 sha=hashlib.sha256(p.read_bytes()).hexdigest()
 tarfile.open(p).extractall(LAB/'llama',filter='data');marker.write_text(sha);p.unlink()
download('https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/4168f45a16a1290d65a4ec0fa312ae917a4c15d6/Qwen_Qwen3.5-4B-Q4_K_M.gguf',LAB/'qwen.gguf')

expected='13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983'
hasher=hashlib.sha256()
with (LAB/'qwen.gguf').open('rb') as source:
 for block in iter(lambda:source.read(8*1024*1024),b''):hasher.update(block)
assert hasher.hexdigest()==expected,'GGUF checksum mismatch'
ROOT=Path(__file__).resolve().parent
(ROOT/'results/context-model.json').write_text(json.dumps({'repository':'bartowski/Qwen_Qwen3.5-4B-GGUF','revision':'4168f45a16a1290d65a4ec0fa312ae917a4c15d6','file':'Qwen_Qwen3.5-4B-Q4_K_M.gguf','sha256':expected,'bytes':(LAB/'qwen.gguf').stat().st_size,'llama_cpp':'b12627, commit 225a5345b'},indent=2))

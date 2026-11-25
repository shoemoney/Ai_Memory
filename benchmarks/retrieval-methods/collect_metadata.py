"""Small provenance records; never copies model weights or datasets into results."""
import hashlib,importlib.metadata,json,os,platform,subprocess,datetime
from pathlib import Path
from run import ROOT,LAB,OUT,save

def sha(path):
 digest=hashlib.sha256()
 with path.open('rb') as source:
  for block in iter(lambda:source.read(8*1024*1024),b''):digest.update(block)
 return digest.hexdigest()
software={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),'system':platform.system(),'kernel':platform.release(),'machine':platform.machine(),'cpu_threads':os.cpu_count(),'packages':{name:importlib.metadata.version(name) for name in ['torch','sentence-transformers','transformers','numpy','rank-bm25','pyarrow','tokenizers']},'gpu':subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],text=True).strip(),'llama_cpp':'b12627, commit 225a5345b'}
import torch
software['torch_runtime']=str(torch.__version__);software['torch_cuda_runtime']=torch.version.cuda
save(OUT/'software.json',software)
assets=[]
for folder,label in [('llama','Linux CUDA runtime'),('llama-mac','Apple Silicon runtime')]:
 for binary in (LAB/folder).rglob('llama-server'):
  assets.append({'runtime_platform':label,'file':binary.name,'bytes':binary.stat().st_size,'sha256':sha(binary)})
save(OUT/'runtime-assets.json',assets)
save(OUT/'prepared-input-sha256.json',{path.name:sha(path) for path in sorted(LAB.glob('*.data.json'))})
files=sorted(set(ROOT.glob('*.py'))|set(ROOT.glob('*.sh'))|set(ROOT.glob('requirements*.txt')))
save(OUT/'code-sha256.json',{path.name:sha(path) for path in files})
print('Software, runtime binary, and source hashes recorded')

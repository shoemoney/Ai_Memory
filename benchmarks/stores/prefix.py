#!/usr/bin/env python3
"""CPU-only llama.cpp disk-slot save/erase/restore behavior, no provider API."""
import hashlib,json,pathlib,shutil,socket,subprocess,time,urllib.request,uuid
ROOT=pathlib.Path(__file__).resolve().parent
IMAGE='ghcr.io/ggml-org/llama.cpp@sha256:5b43086e3ba7ea5794d72904654f6cd41224a9b1c6ac0398f4940ee380d30f23'
REV='9217f5db79a29953eb74d5343926648285ec7e67'
URL=f'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/{REV}/qwen2.5-0.5b-instruct-q4_k_m.gguf'
def main():
 token=uuid.uuid4().hex;name='membench-stores-prefix-'+token[:8]
 scratch=pathlib.Path('/data/scratch/membench/stores/prefix-'+token);scratch.mkdir(parents=True)
 out=ROOT/'results/prefix.json';result={'model':'Qwen2.5-0.5B-Instruct Q4_K_M','model_revision':REV,'model_license':'Apache-2.0','source_url':URL,'image':IMAGE,'gpu_layers':0,'threads':2,'n_functional_sequences':1,'interval':'not applicable to one behavior demonstration'}
 pulled=False;started=False
 def run(args):return subprocess.check_output(args,text=True).strip()
 def call(endpoint,data=None):
  payload=None if data is None else json.dumps(data).encode()
  req=urllib.request.Request('http://localhost:39757'+endpoint,data=payload,headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
 try:
  result['disk_before']=run(['df','-h','/','/data'])
  if shutil.disk_usage('/').free < 20*1024**3:raise RuntimeError('Paused: shared system disk has under 20 GiB free')
  model=scratch/'model.gguf'
  with urllib.request.urlopen(URL,timeout=180) as src,model.open('wb') as dst:shutil.copyfileobj(src,dst)
  h=hashlib.sha256()
  with model.open('rb') as f:
   while b:=f.read(1024*1024):h.update(b)
  result['model_sha256']=h.hexdigest();result['model_bytes']=model.stat().st_size
  if subprocess.run(['docker','image','inspect',IMAGE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
   run(['docker','pull',IMAGE]);pulled=True
  run(['docker','run','-d','--name',name,'--label','membench-stores-owner='+token,'--memory','2g','--cpus','2','-p',socket.gethostbyname('localhost')+':39757:8080','-v',str(scratch)+':/scratch',IMAGE,'-m','/scratch/model.gguf','-ngl','0','-t','2','-c','4096','--parallel','1','--slots','--slot-save-path','/scratch','--host',socket.inet_ntoa(bytes(4)),'--port','8080'])
  started=True
  for _ in range(180):
   try:
    if call('/health')['status']=='ok':break
   except Exception:pass
   time.sleep(1)
  else:raise RuntimeError('llama server readiness timed out')
  prompt='Record stable context. '+'The archive contains a blue square and a green circle. '*80+'Return one word: '
  payload={'prompt':prompt,'n_predict':1,'temperature':0,'seed':20261122,'cache_prompt':True,'id_slot':0}
  a=call('/completion',payload)
  result['cold']={k:a[k] for k in ['timings','tokens_evaluated','tokens_cached'] if k in a}
  result['save']=call('/slots/0?action=save',{'filename':'slot.bin'})
  result['cache_file_bytes']=(scratch/'slot.bin').stat().st_size
  assert result['cache_file_bytes']==result['save']['n_written']
  result['erase']=call('/slots/0?action=erase',{})
  run(['docker','stop','-t','10',name]);run(['docker','start',name])
  for _ in range(180):
   try:
    if call('/health')['status']=='ok':break
   except Exception:pass
   time.sleep(1)
  else:raise RuntimeError('fresh server readiness timed out')
  result['restored_in_fresh_process']=True
  result['restore']=call('/slots/0?action=restore',{'filename':'slot.bin'})
  b=call('/completion',payload)
  result['restored']={k:b[k] for k in ['timings','tokens_evaluated','tokens_cached'] if k in b}
  assert result['save']['n_saved']>0 and result['restore']['n_restored']==result['save']['n_saved']
  assert b['timings']['cache_n']>0 and b['timings']['prompt_n']<a['timings']['prompt_n']
  result['passed']=True;result['stats']=run(['docker','stats','--no-stream','--format','{{.MemUsage}}',name])
 finally:
  if started:
   assert run(['docker','inspect','-f','{{index .Config.Labels "membench-stores-owner"}}',name])==token
   run(['docker','rm','-fv',name])
  if pulled:run(['docker','rmi',IMAGE])
  shutil.rmtree(scratch);result['scratch_removed']=not scratch.exists();result['disk_after']=run(['df','-h','/','/data'])
  out.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()

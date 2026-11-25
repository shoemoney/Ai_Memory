#!/usr/bin/env python3
import os,json,hashlib,urllib.request
from pathlib import Path
from huggingface_hub import snapshot_download
repo="thinkingmachines/Inkling-2-Mini"
req=urllib.request.Request("https://huggingface.co/api/models/"+repo+"?blobs=true",headers={"Authorization":"Bearer "+os.environ["HF_TOKEN"]})
with urllib.request.urlopen(req) as r: manifest=json.load(r)
root=Path.home()/"inkling-lab/models/Inkling-2-Mini"
snapshot_download(repo_id=repo,revision=manifest['sha'],local_dir=root,token=os.environ['HF_TOKEN'],max_workers=2)
verified=[]
for f in manifest['siblings']:
 p=root/f['rfilename']; size=p.stat().st_size
 assert size==f['size'],(f['rfilename'],size,f['size'])
 data=hashlib.sha256() if f.get('lfs') else hashlib.sha1()
 if not f.get('lfs'): data.update(f"blob {size}\0".encode())
 with p.open('rb') as h:
  for chunk in iter(lambda:h.read(8*1024*1024),b''):data.update(chunk)
 expected=f['lfs']['sha256'] if f.get('lfs') else f['blobId']
 assert data.hexdigest()==expected,(f['rfilename'],'hash mismatch')
 verified.append({'file':f['rfilename'],'bytes':size,'hash':data.hexdigest()})
 print('VERIFIED',f['rfilename'],size,flush=True)
(Path.home()/'inkling-lab/source-verification.json').write_text(json.dumps({'repo':repo,'revision':manifest['sha'],'verified':verified},indent=2))

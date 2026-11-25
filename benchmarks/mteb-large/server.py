#!/usr/bin/env python3
"""Localhost-only inference worker. No datasets or scoring live here."""
import argparse, base64, io, json, os, subprocess, threading, time, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np
import torch

def pressure():
    if sys.platform != 'darwin':
        return 100, '1'
    text = subprocess.check_output(['memory_pressure'], text=True)
    free = int(text.split('System-wide memory free percentage: ')[1].split('%')[0])
    level = subprocess.run(['sysctl','-n','kern.memorystatus_vm_pressure_level'],capture_output=True,text=True)
    return free, level.stdout.strip()

def guard():
    while True:
        free, level = pressure()
        if level in ('2','4') or free<=30:
            print(json.dumps({'event':'pressure_shutdown','free_percent':free,'level':level}),flush=True)
            os._exit(75)
        time.sleep(5)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--revision',required=True)
    p.add_argument('--port',type=int,default=39740); p.add_argument('--device',default='mps'); p.add_argument('--bits',type=int,choices=[4,8]); a=p.parse_args()
    assert 39740 <= a.port <= 39749
    free,level=pressure(); assert free >=40 and level not in ('2','4'), 'Memory admission refused'
    print(json.dumps({'event':'admitted','free_percent':free if sys.platform=='darwin' else None,'pressure_level':level}),flush=True)
    threading.Thread(target=guard,daemon=True).start()
    import mteb
    from mteb._create_dataloaders import _create_dataloader_from_texts
    from mteb.types import PromptType
    torch.set_num_threads(4)
    torch.manual_seed(20261121)
    meta=mteb.get_model_meta(a.model).model_copy(update={'revision':a.revision})
    model_kwargs={'dtype':torch.bfloat16,'attn_implementation':'sdpa'}
    import hashlib
    execution={'engine':'PyTorch MPS','compute_dtype':'bfloat16','bits':a.bits,'group_size':64 if a.bits else None,
               'quantizer_sha256':hashlib.sha256(open(__file__.replace('server.py','quantize.py'),'rb').read()).hexdigest() if a.bits else None}
    if a.device=='mps':
        budget=max(1,(free-30)/100*96-1)*1024**3
        fraction=min(1,budget/torch.mps.recommended_max_memory())
        torch.mps.set_per_process_memory_fraction(fraction)
        execution['allocator_budget_bytes']=int(budget)
    if a.bits:
        from quantize import convert_linears, sanity_check
        print(json.dumps({'event':'quantization_device_check','checks':sanity_check(a.device)}),flush=True)
        model=meta.load_model(device='cpu', model_kwargs=model_kwargs)
        execution['quantization']=convert_linears(model.model,a.bits)
    else:
        model_kwargs['device_map']=a.device
        model=meta.load_model(device=a.device, model_kwargs=model_kwargs)
        execution['quantization']=None
    if a.device=='mps':
        torch.mps.synchronize()
        torch.mps.empty_cache()
    post,post_level=pressure()
    if post<=30 or post_level in ('2','4'):
        print(json.dumps({'event':'post_load_reserve_refused','free_percent':post,'level':post_level}),flush=True)
        os._exit(75)
    execution['allocator_budget_bytes_record_only']=execution.pop('allocator_budget_bytes',None)

    model.model.max_seq_length=512
    if hasattr(model, '_text_max_seq_length'): model._text_max_seq_length=512
    print(json.dumps({'event':'ready','model':a.model,'revision':a.revision,'dtype':str(next(model.model.parameters()).dtype),'free_percent':pressure()[0] if sys.platform=='darwin' else None}),flush=True)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_GET(self):
            data=json.dumps({'model':a.model,'revision':a.revision,'free_percent':pressure()[0] if sys.platform=='darwin' else None,'dtype':str(next(model.model.parameters()).dtype),'device':a.device,'execution':execution,'placement':{k:str(v) for k,v in getattr(getattr(model.model._first_module(),'auto_model',None),'hf_device_map',{}).items()}}).encode()
            self.send_response(200); self.end_headers(); self.wfile.write(data)
        def do_POST(self):
            try:
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert data['model']==a.model and data['revision']==a.revision, 'Wrong model identity'
                model.model.max_seq_length = 8192 if 'images' in data else 512
                if 'images' in data:
                    from PIL import Image
                    from types import SimpleNamespace
                    class Loader(list): pass
                    loader=Loader([{'image':[Image.open(io.BytesIO(base64.b64decode(x))).convert('RGB') for x in data['images']]}])
                    loader.dataset=SimpleNamespace(features={'image':None})
                    batch_size=len(data['images'])
                else:
                    loader=_create_dataloader_from_texts(data['texts'],batch_size=len(data['texts']))
                    batch_size=len(data['texts'])
                task=mteb.get_task(data['task'])
                with torch.inference_mode():
                    vectors=model.encode(loader,task_metadata=task.metadata,hf_split='test',hf_subset='default',
                        prompt_type=PromptType(data['prompt_type']) if data['prompt_type'] else None,
                        batch_size=batch_size,show_progress_bar=False,convert_to_numpy=True)
                buf=io.BytesIO(); np.save(buf,np.asarray(vectors,dtype=np.float32),allow_pickle=False)
                self.send_response(200); self.end_headers(); self.wfile.write(buf.getvalue())
                if a.device=='mps':torch.mps.synchronize(); torch.mps.empty_cache()
            except Exception as e:
                self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode()); raise
    HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()

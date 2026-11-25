#!/usr/bin/env python3
"""Nomic official fork, weight-only RTN, unchanged processor and cosine vectors."""
import argparse,base64,hashlib,io,json,os
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from memory_guard import pressure,admit

def check_mps_attention():
    """Check the old fork's 3D vision SDPA against an independent CPU product.

    Transformers issue 36413 describes the older MPS 3D-shape failure. Promote
    only that shape if this installed Torch still needs the equivalent 4D form.
    """
    import math
    from torch.nn import functional as F
    original=F.scaled_dot_product_attention
    q,k,v=[torch.randn(2,8,32,dtype=torch.bfloat16) for _ in range(3)]
    reference=torch.softmax(q.float()@k.float().transpose(-2,-1)/math.sqrt(32),dim=-1)@v.float()
    mode='native 3D SDPA'
    with torch.inference_mode():
        try:actual=original(q.to('mps'),k.to('mps'),v.to('mps'))
        except (IndexError,RuntimeError):
            def compatible(query,key,value,*args,**kwargs):
                if query.device.type=='mps' and query.ndim==3:
                    return original(query.unsqueeze(0),key.unsqueeze(0),value.unsqueeze(0),*args,**kwargs).squeeze(0)
                return original(query,key,value,*args,**kwargs)
            F.scaled_dot_product_attention=compatible
            actual=compatible(q.to('mps'),k.to('mps'),v.to('mps'))
            mode='3D MPS SDPA promoted to equivalent 4D batch'
        relative=float((actual.float().cpu()-reference).square().mean().sqrt()/reference.square().mean().sqrt())
        assert relative<.04,relative
    torch.mps.synchronize();torch.mps.empty_cache()
    return {'mode':mode,'relative_output_rmse':relative,'limit':.04,'reference':'CPU float32 softmax(QK/sqrt(d))V',
            'upstream_issue':'https://github.com/huggingface/transformers/issues/36413'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--revision',required=True)
    p.add_argument('--bits',type=int,choices=[4,8],default=4);p.add_argument('--port',type=int,default=39740);a=p.parse_args()
    assert 39740<=a.port<=39749
    free=admit()
    torch.set_num_threads(4);torch.manual_seed(20261121)
    budget=int(max(1,(free-30)/100*96-1)*1024**3)
    torch.mps.set_per_process_memory_fraction(min(1,budget/torch.mps.recommended_max_memory()))
    from quantize import convert_linears,sanity_check
    print(json.dumps({'event':'quantization_device_check','checks':sanity_check('mps')}),flush=True)
    attention_check=check_mps_attention()
    print(json.dumps({'event':'attention_device_check','check':attention_check}),flush=True)
    from colpali_engine.models import BiQwen2_5,BiQwen2_5_Processor
    from huggingface_hub import hf_hub_download
    adapter_config=json.loads(Path(hf_hub_download(a.model,'adapter_config.json',revision=a.revision)).read_text())
    base=adapter_config['base_model_name_or_path']
    assert base=='Qwen/Qwen2.5-VL-7B-Instruct'
    check,level=pressure()
    assert check>=40 and level not in ('2','4'),'Admission changed immediately before model load'
    print(json.dumps({'event':'immediate_preload_check','free_percent':check,'kernel_level':level}),flush=True)
    model=BiQwen2_5.from_pretrained(base,torch_dtype=torch.bfloat16,device_map='cpu',
        revision='cc594898137f460bfe9f0759e9844b3ce807cfb5',attn_implementation='sdpa').eval()
    model.load_adapter(a.model,adapter_name='default',adapter_kwargs={'revision':a.revision})
    stats=convert_linears(model,a.bits)
    processor=BiQwen2_5_Processor.from_pretrained(a.model,revision=a.revision)
    torch.mps.synchronize();torch.mps.empty_cache()
    post,level=pressure()
    if post<=30 or level in ('2','4'):
        print(json.dumps({'event':'post_load_reserve_refused','free_percent':post,'kernel_level':level}),flush=True);os._exit(75)
    execution={'engine':'PyTorch MPS','compute_dtype':'bfloat16','bits':a.bits,'group_size':64,'quantization':stats,'attention_backend':attention_check['mode'],'attention_check_record_only':attention_check,
               'base_model':base,'base_revision':'cc594898137f460bfe9f0759e9844b3ce807cfb5',
               'backend_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'quantizer_sha256':hashlib.sha256(Path(__file__).with_name('quantize.py').read_bytes()).hexdigest()}
    print(json.dumps({'event':'ready','model':a.model,'revision':a.revision,'free_percent':post,'execution':execution}),flush=True)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'model':a.model,'revision':a.revision,'free_percent':pressure()[0],'execution':execution}).encode())
        def do_POST(self):
            try:
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert data['model']==a.model and data['revision']==a.revision
                if 'images' in data:
                    batch=processor.process_images([Image.open(io.BytesIO(base64.b64decode(x))).convert('RGB') for x in data['images']])
                else:batch=processor.process_queries(data['texts'])
                with torch.inference_mode():vectors=model(**batch.to('mps'))
                buf=io.BytesIO();np.save(buf,vectors.detach().float().cpu().numpy(),allow_pickle=False)
                self.send_response(200);self.end_headers();self.wfile.write(buf.getvalue())
                torch.mps.synchronize();torch.mps.empty_cache()
            except Exception as error:
                self.send_response(500);self.end_headers();self.wfile.write(str(error).encode());raise
    HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()

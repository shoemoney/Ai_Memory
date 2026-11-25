#!/usr/bin/env python3
"""Harrier's Gemma3 text backbone with native MLX, last-token pooling and L2 norm."""
import argparse,hashlib,io,json,os
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
import numpy as np
from memory_guard import admit,pressure

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--revision',required=True)
    p.add_argument('--bits',type=int,choices=[4,8],default=4);p.add_argument('--port',type=int,default=39740);a=p.parse_args()
    assert 39740<=a.port<=39749
    free=admit()
    import mlx.core as mx
    import mlx.nn as nn
    from mlx_lm.utils import load_model
    from mlx_lm.models.gemma3_text import Gemma3Model as Gemma3TextModel, ModelArgs
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    from importlib.metadata import version
    mx.set_memory_limit(int(max(1,(free-30)/100*96-1)*1024**3));mx.set_cache_limit(256*1024**2)
    snapshot=Path(snapshot_download(a.model,revision=a.revision,allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.py']))
    config=json.loads((snapshot/'config.json').read_text())
    pooling=json.loads((snapshot/'1_Pooling/config.json').read_text())
    assert config['model_type']=='gemma3_text' and not config.get('use_bidirectional_attention',False)
    assert pooling['pooling_mode_lasttoken'] and pooling['include_prompt']
    pattern=config.get('_sliding_window_pattern',6)
    assert config['layer_types']==['full_attention' if i%pattern==pattern-1 else 'sliding_attention' for i in range(config['num_hidden_layers'])]
    check,level=pressure();assert check>=40 and level not in ('2','4'),'Admission changed before load'
    print(json.dumps({'event':'immediate_preload_check','free_percent':check,'kernel_level':level}),flush=True)
    # Load only Gemma3TextModel, not a language-model output head. The checkpoint
    # uses these exact bare backbone parameter names; strict loading checks all.
    with mx.stream(mx.cpu):
        model,loaded_config=load_model(snapshot,lazy=True,strict=True,
            model_config={'sliding_window_pattern':pattern},
            get_model_classes=lambda config:(Gemma3TextModel,ModelArgs))
        from quantize_mlx import stream_quantize
        stats=stream_quantize(model,a.bits,64)
        mx.eval(model.parameters())
    tokenizer=AutoTokenizer.from_pretrained(snapshot);tokenizer.padding_side='right'
    mx.clear_cache()
    post,level=pressure()
    if post<=30 or level in ('2','4'):
        print(json.dumps({'event':'post_load_reserve_refused','free_percent':post,'kernel_level':level}),flush=True);os._exit(75)
    instructions=json.loads(Path(__file__).with_name('instructions.json').read_text())
    execution={'engine':'MLX-LM','compute_dtype':'bfloat16','bits':a.bits,'group_size':64,
        'quantization':{'method':'MLX affine, streaming CPU conversion, no calibration','scope':'Native quantizable linear and embedding modules'},
        'pooling':'Last nonpadding token, including prompt; L2 normalization',
        'attention':'Causal; right padding; original six-layer local/full pattern, window and RoPE configuration',
        'mlx_lm_version':version('mlx-lm'),'mlx_version':version('mlx'),
        'quantizer_sha256':hashlib.sha256(Path(__file__).with_name('quantize_mlx.py').read_bytes()).hexdigest(),
        'backend_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'instructions_sha256':hashlib.sha256(Path(__file__).with_name('instructions.json').read_bytes()).hexdigest()}
    print(json.dumps({'event':'ready','model':a.model,'revision':a.revision,'free_percent':post,'execution':execution}),flush=True)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'model':a.model,'revision':a.revision,'free_percent':pressure()[0],'execution':execution}).encode())
        def do_POST(self):
            try:
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert data['model']==a.model and data['revision']==a.revision
                prompt=instructions['instructions'][data['task']]['harrier'][data['prompt_type']]
                batch=tokenizer([prompt+text for text in data['texts']],padding=True,truncation=True,max_length=512,return_tensors='np')
                ids=mx.array(batch['input_ids'],dtype=mx.int32);mask=mx.array(batch['attention_mask'],dtype=mx.int32)
                hidden=model(ids)
                last=mask.sum(axis=1)-1
                pooled=hidden[mx.arange(ids.shape[0]),last].astype(mx.float32)
                vectors=pooled/mx.maximum(mx.linalg.norm(pooled,axis=1,keepdims=True),1e-12)
                mx.eval(vectors);array=np.array(vectors);assert np.isfinite(array).all()
                buf=io.BytesIO();np.save(buf,array,allow_pickle=False)
                self.send_response(200);self.end_headers();self.wfile.write(buf.getvalue());mx.clear_cache()
            except Exception as error:
                self.send_response(500);self.end_headers();self.wfile.write(str(error).encode());raise
    HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()

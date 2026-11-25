#!/usr/bin/env python3
"""Native MLX inference, pinned original weights, same MTEB instructions and caps."""
import argparse,base64,hashlib,io,json,os,shutil
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
import numpy as np
from memory_guard import pressure,admit

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--revision',required=True)
    p.add_argument('--bits',type=int,choices=[4,8]);p.add_argument('--port',type=int,default=39740);a=p.parse_args()
    assert 39740<=a.port<=39749
    free=admit()
    import mlx.core as mx
    from mlx_embeddings import load
    from mlx_embeddings.convert import convert
    from huggingface_hub import snapshot_download
    from importlib.metadata import version
    mx.set_memory_limit(int(max(1,(free-30)/100*96-1)*1024**3))
    mx.set_cache_limit(256*1024**2)
    snapshot=snapshot_download(a.model,revision=a.revision,allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.py','*.jinja'])
    vl='VL-Embedding' in a.model
    if vl:
        # The embedding checkpoint omits the VLM language-model output head.
        # Preserve strict loading of every backbone parameter, and avoid the
        # package's unused reranker-logit path after it computes text_embeds.
        from mlx_embeddings.models.qwen3_vl import Model as VLModel
        original_init=VLModel.__init__
        def embedding_init(self,*args,**kwargs):
            original_init(self,*args,**kwargs)
            self.language_model.pop('lm_head',None)
        VLModel.__init__=embedding_init
        VLModel.get_binary_logits=lambda self,pooled:mx.zeros((pooled.shape[0],),dtype=pooled.dtype)
    model_path=snapshot
    if a.bits:
        converted=Path(__file__).parent/'converted'
        provenance={'model':a.model,'revision':a.revision,'bits':a.bits,'group_size':64,'dtype':'bfloat16','skip_vision':True}
        marker=converted/'provenance.json'
        reusable=marker.exists() and json.loads(marker.read_text())==provenance
        if converted.exists() and not reusable:shutil.rmtree(converted)
        # CPU quantization avoids wiring the full-precision model on the shared GPU.
        if not reusable:
            check,check_level=pressure()
            assert check>=40 and check_level not in ('2','4'),'Admission changed before quantization'
            from mlx_embeddings.utils import fetch_from_hub,save_weights,save_config
            from mlx.utils import tree_flatten,tree_map
            from quantize_mlx import stream_quantize
            with mx.stream(mx.cpu):
                prepared,config,tokenizer=fetch_from_hub(Path(snapshot),lazy=True,path_to_repo=a.model)
                prepared.update(tree_map(lambda v:v.astype(mx.bfloat16),prepared.parameters()))
                stats=stream_quantize(prepared,a.bits,64,skip_vision=True)
                config['quantization']={'bits':a.bits,'group_size':64,'mode':'affine'}
                weights=dict(tree_flatten(prepared.parameters()));del prepared
                save_weights(converted,weights,donate_weights=True)
            for pattern in ['*.json','*.py','*.txt','*.model','*.jinja']:
                for item in Path(snapshot).glob(pattern):
                    target=Path(shutil.copy(item,converted));target.chmod(0o600)
            if (Path(snapshot)/'1_Pooling').exists():shutil.copytree(Path(snapshot)/'1_Pooling',converted/'1_Pooling',dirs_exist_ok=True)
            # VL's custom video stub is inference-only; retain the exact original
            # processor/tokenizer metadata instead of serializing that stub.
            if 'VL-Embedding' not in a.model:tokenizer.save_pretrained(converted)
            save_config(config,config_path=converted/'config.json')
            print(json.dumps({'event':'quantized','stats':stats}),flush=True)
            marker.write_text(json.dumps(provenance)+'\n')
        model_path=str(converted)
    kwargs={'tokenizer_config':{'embedding_max_length':512,'max_pixels':1800*32*32,'min_pixels':4*32*32}} if vl else {}
    check,check_level=pressure()
    assert check>=40 and check_level not in ('2','4'),'Admission changed immediately before model load'
    print(json.dumps({'event':'immediate_preload_check','free_percent':check,'kernel_level':check_level}),flush=True)
    mx.set_memory_limit(int(max(1,(check-30)/100*96-1)*1024**3))
    model,processor=load(model_path,**kwargs)
    mx.eval(model.parameters());mx.clear_cache()
    post,level=pressure()
    if post<=30 or level in ('2','4'):
        print(json.dumps({'event':'post_load_reserve_refused','free_percent':post,'kernel_level':level}),flush=True);os._exit(75)
    instructions=json.loads(Path(__file__).with_name('instructions.json').read_text())
    execution={'engine':'MLX','compute_dtype':'bfloat16','bits':a.bits,'group_size':64 if a.bits else None,
               'quantization':{'method':'MLX affine, streaming CPU conversion, no calibration','vision':'bfloat16; not quantized'} if a.bits else None,
               'mlx_embeddings_version':version('mlx-embeddings'),'mlx_version':version('mlx'),
               'quantizer_sha256':hashlib.sha256(Path(__file__).with_name('quantize_mlx.py').read_bytes()).hexdigest() if a.bits else None,
               'backend_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'backbone':'Qwen3 VL embedding backbone; unused language-model output head omitted' if vl else 'Qwen3 embedding backbone',
               'instructions_sha256':hashlib.sha256(Path(__file__).with_name('instructions.json').read_bytes()).hexdigest()}
    print(json.dumps({'event':'ready','model':a.model,'revision':a.revision,'free_percent':post,'execution':execution}),flush=True)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            body=json.dumps({'model':a.model,'revision':a.revision,'free_percent':pressure()[0],
                             'dtype':'bfloat16','device':'Apple M3 Ultra, 96 GB','execution':execution}).encode()
            self.send_response(200);self.end_headers();self.wfile.write(body)
        def do_POST(self):
            try:
                d=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert d['model']==a.model and d['revision']==a.revision
                role=d['prompt_type'];prompt=instructions['instructions'][d['task']]['vl' if vl else 'text'][role]
                if vl:
                    processor.embedding_max_length=8192 if 'images' in d else 512
                    if 'images' in d:
                        from PIL import Image
                        items=[{'image':Image.open(io.BytesIO(base64.b64decode(x))).convert('RGB'),'instruction':prompt} for x in d['images']]
                    else:items=[{'text':text,'instruction':prompt} for text in d['texts']]
                    model.language_model._rope_deltas=None
                    model.language_model._position_ids=None
                    vectors=model.process(items,processor=processor)
                else:
                    texts=[prompt+text for text in d['texts']]
                    batch=processor.batch_encode_plus(texts,return_tensors='np',padding=True,truncation=True,max_length=512)
                    output=model(mx.array(batch['input_ids'],dtype=mx.int32),attention_mask=mx.array(batch['attention_mask'],dtype=mx.int32))
                    vectors=output.text_embeds
                mx.eval(vectors)
                array=np.array(vectors.astype(mx.float32));assert np.isfinite(array).all()
                buf=io.BytesIO();np.save(buf,array,allow_pickle=False)
                self.send_response(200);self.end_headers();self.wfile.write(buf.getvalue());mx.clear_cache()
            except Exception as error:
                self.send_response(500);self.end_headers();self.wfile.write(str(error).encode());raise
    HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()

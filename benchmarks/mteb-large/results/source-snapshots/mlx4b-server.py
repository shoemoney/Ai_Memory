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
    snapshot=snapshot_download(a.model,revision=a.revision,allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.py'])
    model_path=snapshot
    if a.bits:
        converted=Path(__file__).parent/'converted'
        if converted.exists():shutil.rmtree(converted)
        # CPU quantization avoids wiring the full-precision model on the shared GPU.
        with mx.stream(mx.cpu):
            convert(snapshot,str(converted),quantize=True,q_group_size=64,q_bits=a.bits,
                    q_mode='affine',dtype='bfloat16',skip_vision=True)
        model_path=str(converted)
    vl='VL-Embedding' in a.model
    kwargs={'tokenizer_config':{'embedding_max_length':512,'max_pixels':1800*32*32,'min_pixels':4*32*32}} if vl else {}
    model,processor=load(model_path,**kwargs)
    mx.eval(model.parameters());mx.clear_cache()
    post,level=pressure()
    if post<=30 or level in ('2','4'):
        print(json.dumps({'event':'post_load_reserve_refused','free_percent':post,'kernel_level':level}),flush=True);os._exit(75)
    instructions=json.loads(Path(__file__).with_name('instructions.json').read_text())
    execution={'engine':'MLX','compute_dtype':'bfloat16','bits':a.bits,'group_size':64 if a.bits else None,
               'quantization':{'method':'MLX affine, CPU conversion, no calibration','vision':'bfloat16; not quantized'} if a.bits else None,
               'mlx_embeddings_version':version('mlx-embeddings'),'mlx_version':version('mlx'),
               'backend_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
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

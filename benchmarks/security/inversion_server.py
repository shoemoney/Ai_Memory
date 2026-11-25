"""Loopback-only, one-model-at-a-time Q4 GTR/Vec2Text inference.

Independent frozen-embedding interface matching the public model equations.
No attack scoring or datasets are retained by this model server.
"""
import argparse,gc,json,os,pathlib,platform,re,subprocess,threading,time
from http.server import BaseHTTPRequestHandler,HTTPServer

def cpu_available_kib():
 values=dict(line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())
 return int(values['MemAvailable'].split()[0])
def pressure():
 if platform.system()=='Darwin':return int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True))
 return 1 if cpu_available_kib()>=1024**2 else 2
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--port',type=int,default=39800);a=p.parse_args()
 import torch
 from torch import nn
 from transformers import AutoTokenizer,T5Config,T5EncoderModel,T5ForConditionalGeneration
 torch.set_num_threads(4);torch.set_num_interop_threads(1)
 root=pathlib.Path(a.root);state={'kind':None,'model':None,'aux':None,'active_neural_models':0}
 def guard():
  while True:
   if pressure()!=1:print('Own inversion server stopped: memory guard.',flush=True);os._exit(75)
   time.sleep(5)
 threading.Thread(target=guard,daemon=True).start()
 class Q4(nn.Module):
  def __init__(self,layer,embedding=False):
   super().__init__();self.embedding=embedding;w=layer.weight.detach().float();self.out,self.width=w.shape
   assert self.width%64==0
   groups=w.reshape(self.out,-1,64);scale=groups.abs().amax(dim=-1,keepdim=True).clamp_min(1e-8)/7
   q=(groups/scale).round().clamp(-8,7).to(torch.int8)+8
   packed=(q[...,0::2].to(torch.uint8) | (q[...,1::2].to(torch.uint8)<<4))
   self.register_buffer('packed',packed);self.register_buffer('scale',scale);self.decoded_linear=None
   self.register_buffer('bias',layer.bias.detach().clone() if hasattr(layer,'bias') and layer.bias is not None else None)
   if embedding:self.embedding_dim=self.width;self.num_embeddings=self.out
   else:self.in_features=self.width;self.out_features=self.out
  def unpack(self,ids=None):
   q=self.packed if ids is None else self.packed[ids];s=self.scale if ids is None else self.scale[ids]
   vals=torch.stack((q&15,q>>4),dim=-1).flatten(-2).float()-8
   return (vals*s).flatten(-2)
  @property
  def weight(self):return self.unpack()
  def forward(self,x):
   if self.embedding:return self.unpack(x)
   # Cache the exact Q4-decoded values for CPU matmuls, preserving quantized precision.
   if self.decoded_linear is None:self.decoded_linear=self.unpack()
   return torch.nn.functional.linear(x,self.decoded_linear,self.bias)
 def quantize(module,memo=None):
  memo={} if memo is None else memo
  for name,child in list(module._modules.items()):
   if child is None:continue
   if id(child) in memo:module._modules[name]=memo[id(child)];continue
   if isinstance(child,(nn.Linear,nn.Embedding)) and child.weight.shape[1]%64==0:
    q=Q4(child,isinstance(child,nn.Embedding));memo[id(child)]=q;module._modules[name]=q
   else:quantize(child,memo)
  return module
 def load(kind):
  if kind==state['kind']:return
  state['model']=None;state['aux']=None;state['kind']=None;state['active_neural_models']=0;gc.collect()
  if platform.system()=='Darwin':
   free=int(re.search(r'System-wide memory free percentage: (\d+)%',subprocess.check_output(['memory_pressure'],text=True)).group(1))
   if free<40 or pressure()!=1:raise RuntimeError('memory preflight refused new model')
  else:
   free=None
   if cpu_available_kib()<2*1024**2 or pressure()!=1:raise RuntimeError('CPU memory preflight refused model load')
  directory=root/('gtr' if kind=='gtr' else kind)
  cfg=T5Config.from_pretrained(root/'t5',local_files_only=True)
  if kind=='gtr':
   model,info=T5EncoderModel.from_pretrained(directory,local_files_only=True,output_loading_info=True);missing=set(info['missing_keys']);ties={'shared.weight','encoder.embed_tokens.weight'};assert not (missing-ties) and not ties<=missing and not info['mismatched_keys'] and not info['error_msgs'],info;aux=None
  else:
   model=T5ForConditionalGeneration(cfg)
   conf=json.loads((directory/'config.json').read_text());repeat=conf['num_repeat_tokens'];dim=cfg.d_model;assert repeat==16 and dim==768
   count=1 if kind=='hypothesizer' else 3
   aux=nn.ModuleDict({f'transform_{i}':nn.Sequential(nn.Linear(768,768),nn.Dropout(0.0),nn.GELU(),nn.Linear(768,dim*repeat)) for i in range(1,count+1)})
   if kind=='corrector':aux['layernorm']=nn.LayerNorm(dim)
   index=json.loads((directory/'pytorch_model.bin.index.json').read_text())
   loaded=set();loaded_aux=set()
   for filename in sorted(set(index['weight_map'].values())):
    weights=torch.load(directory/filename,map_location='cpu',weights_only=True,mmap=True)
    model_weights={k.removeprefix('encoder_decoder.'):v for k,v in weights.items() if k.startswith('encoder_decoder.')}
    model.load_state_dict(model_weights,strict=False);loaded.update(model_weights)
    for i in range(1,count+1):
     prefix='embedding_transform.' if kind=='hypothesizer' else f'embedding_transform_{i}.'
     w={k.removeprefix(prefix):v for k,v in weights.items() if k.startswith(prefix)}
     aux[f'transform_{i}'].load_state_dict(w,strict=False);loaded_aux.update(f'transform_{i}.'+k for k in w)
    if kind=='corrector':
     w={k.removeprefix('layernorm.'):v for k,v in weights.items() if k.startswith('layernorm.')};aux['layernorm'].load_state_dict(w,strict=False);loaded_aux.update('layernorm.'+k for k in w)
    del weights,model_weights
   expected=set(model.state_dict());ties={'shared.weight','encoder.embed_tokens.weight','decoder.embed_tokens.weight','lm_head.weight'};assert expected-ties<=loaded,sorted(expected-loaded-ties);assert loaded&ties
   assert set(aux.state_dict())<=loaded_aux, sorted(set(aux.state_dict())-loaded_aux)
   model.tie_weights();aux.eval();quantize(aux)
  model.eval();quantize(model)
  state.update(kind=kind,model=model,aux=aux,active_neural_models=1)
  print(json.dumps({'loaded':kind,'free_percentage_before':free,'active_neural_models':1,'quantization':'symmetric signed int4, group size 64, float32 scales','cpu_compute':'float32 matmuls; decoded Q4 linear weights cached until unload','rss_limit_goal_gib':3}),flush=True)
 tok=AutoTokenizer.from_pretrained(root/'t5',local_files_only=True)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,value):
   data=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  def do_GET(self):self.send({'ready':True,'kind':state['kind'],'active_neural_models':state['active_neural_models'],'memory_guard_level':pressure(),'guard_basis':'Darwin kernel pressure' if platform.system()=='Darwin' else 'Linux MemAvailable; stop below 1 GiB'})
  def do_POST(self):
   try:
    req=json.loads(self.rfile.read(int(self.headers['Content-Length'])));kind=req.get('model','gtr');t=time.monotonic()
    if self.path=='/canonicalize':
     texts=[];lengths=[]
     for text in req['input']:
      ids=tok(text,max_length=32,truncation=True)['input_ids'];texts.append(tok.decode(ids,skip_special_tokens=True));lengths.append(len(ids))
     self.send({'texts':texts,'token_counts':lengths});return
    load(kind);model=state['model'];aux=state['aux']
    with torch.inference_mode():
     if kind=='gtr':
      inputs=tok(req['input'],padding=True,truncation=True,max_length=32,return_tensors='pt');h=model(**inputs).last_hidden_state;m=inputs['attention_mask'];v=(h*m[:,:,None]).sum(1)/m.sum(1)[:,None]
      self.send({'vectors':v.tolist(),'elapsed_s':time.monotonic()-t});return
     vectors=torch.tensor(req['vectors'],dtype=torch.float32);batch=len(vectors)
     z=aux['transform_1'](vectors).reshape(batch,16,-1)
     if kind=='hypothesizer':mask=torch.ones(z.shape[:2],dtype=torch.long)
     else:
      ids=req['hypothesis_token_ids'];width=max(map(len,ids));hyp_ids=torch.tensor([row+[tok.pad_token_id]*(width-len(row)) for row in ids],dtype=torch.long);hyp={'input_ids':hyp_ids,'attention_mask':(hyp_ids!=tok.pad_token_id).long()};hv=torch.tensor(req['hypothesis_vectors'],dtype=torch.float32)
      diff=aux['transform_2'](vectors-hv).reshape(batch,16,-1);hz=aux['transform_3'](hv).reshape(batch,16,-1)
      one=torch.ones((batch,1),dtype=torch.long);sep=model.encoder.embed_tokens(one*model.config.eos_token_id)
      z=aux['layernorm'](torch.cat([sep,z,sep,hz,sep,diff,sep,model.encoder.embed_tokens(hyp['input_ids'])],dim=1));mask=torch.cat([one.repeat(1,52),hyp['attention_mask']],dim=1)
     generated=model.generate(inputs_embeds=z,attention_mask=mask,max_length=128,min_length=1,do_sample=False,num_beams=req.get('num_beams',1),use_cache=True)
     answers=tok.batch_decode(generated,skip_special_tokens=True);ids=generated.tolist();eos=model.config.eos_token_id
     self.send({'answers':answers,'token_ids':ids,'truncated':[eos not in row for row in ids],'completion_tokens':[row.index(eos) if eos in row else len(row)-1 for row in ids],'elapsed_s':time.monotonic()-t})
   except Exception as e:
    print(type(e).__name__,str(e),flush=True);self.send_error(500,type(e).__name__+': '+str(e))
 HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()

"""Single Q4 model, loopback-only generation/embedding service for disposable tests."""
import argparse, json, os, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

def pressure():
 return int(subprocess.check_output(['sysctl','-n','kern.memorystatus_vm_pressure_level'],text=True).strip())

def main():
 p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--port',type=int,default=39800);a=p.parse_args()
 free=subprocess.check_output(['memory_pressure'],text=True)
 import re
 pct=int(re.search(r'System-wide memory free percentage: (\d+)%',free).group(1))
 if pct<40 or pressure()!=1:raise RuntimeError('memory preflight refused model load')
 def guard():
  while True:
   if pressure()!=1:
    print('Stopped own server for kernel memory pressure.',flush=True);os._exit(75)
   time.sleep(5)
 threading.Thread(target=guard,daemon=True).start()
 import mlx.core as mx
 from mlx_lm import load, generate
 from mlx.utils import tree_flatten
 from mlx_lm.sample_utils import make_sampler
 model,tokenizer=load(a.model)
 mx.eval(model.parameters())
 print(json.dumps({'ready':True,'free_percentage_before':pct,'model_parameters':sum(x.size for _,x in tree_flatten(model.parameters()))}),flush=True)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,value):
   data=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  def do_GET(self):self.send({'ready':True,'kernel_pressure_level':pressure()})
  def do_POST(self):
   try:
    request=json.loads(self.rfile.read(int(self.headers['Content-Length'])));t=time.monotonic()
    if self.path=='/embeddings':
     vectors=[]
     for text in request['input']:
      ids=tokenizer.encode(text,add_special_tokens=False)[:512]
      h=model.model(mx.array([ids]));v=mx.mean(h,axis=1)[0];v=v/mx.maximum(mx.linalg.norm(v),1e-12);mx.eval(v);vectors.append(v.tolist())
     self.send({'vectors':vectors,'elapsed_s':time.monotonic()-t})
    else:
     prompt=tokenizer.apply_chat_template(request['messages'],tokenize=False,add_generation_prompt=True)
     mx.random.seed(request.get('seed',20261122))
     answer=generate(model,tokenizer,prompt=prompt,max_tokens=request.get('max_tokens',96),sampler=make_sampler(temp=request.get('temperature',0.0)),verbose=False)
     n=len(tokenizer.encode(answer,add_special_tokens=False))
     self.send({'answer':answer,'completion_tokens':n,'truncated':n>=request.get('max_tokens',96),'elapsed_s':time.monotonic()-t})
   except Exception as e:
    self.send_error(500,type(e).__name__+': '+str(e))
 HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()

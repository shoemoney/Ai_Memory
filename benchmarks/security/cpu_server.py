"""Loopback adapter for one CPU llama.cpp model serving generation and embeddings."""
import argparse,http.client,json,os,pathlib,re,shutil,socket,subprocess,threading,time,urllib.request
from http.server import BaseHTTPRequestHandler,HTTPServer

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=39800);p.add_argument('--backend',default='http://localhost:39804');p.add_argument('--owned-container',default='membench-security-cpu-backend');a=p.parse_args()
 if not re.fullmatch(r'membench-security-[a-z0-9-]+',a.owned_container):raise RuntimeError('refusing an unrelated container name')
 def request(path,data=None):
  req=urllib.request.Request(a.backend+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=300) as r:return json.load(r)
 def guard():
  while True:
   values=dict(line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())
   if int(values['MemAvailable'].split()[0])<1024**2:
    print('Stopping owned backend for low available CPU memory.',flush=True)
    if shutil.which('docker'):subprocess.run(['docker','stop',a.owned_container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:
     class DockerSocket(http.client.HTTPConnection):
      def connect(self):
       self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(15);self.sock.connect('/var/run/docker.sock')
     conn=DockerSocket('localhost',timeout=15);conn.request('POST','/containers/'+a.owned_container+'/stop?t=10');conn.getresponse().read();conn.close()
    os._exit(75)
   time.sleep(5)
 threading.Thread(target=guard,daemon=True).start()
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,value):
   data=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  def do_GET(self):
   try:self.send({'ready':request('/health').get('status')=='ok','backend':'llama.cpp CPU','gpu_layers':0})
   except Exception as e:self.send_error(503,str(e))
  def do_POST(self):
   try:
    req=json.loads(self.rfile.read(int(self.headers['Content-Length'])));t=time.monotonic()
    if self.path=='/embeddings':
     texts=[]
     for text in req['input']:
      tokens=request('/tokenize',{'content':text,'add_special':False})['tokens']
      if len(tokens)>510:text=request('/detokenize',{'tokens':tokens[:510]})['content']
      texts.append(text)
     data=request('/v1/embeddings',{'model':'local','input':texts})['data'];data.sort(key=lambda r:r['index'])
     self.send({'vectors':[r['embedding'] for r in data],'elapsed_s':time.monotonic()-t,'backend':'llama.cpp CPU'})
    else:
     data=request('/v1/chat/completions',{'model':'local','messages':req['messages'],'max_tokens':req.get('max_tokens',96),'temperature':req.get('temperature',0.0),'seed':req.get('seed',20261122),'cache_prompt':True,'top_p':1.0,'top_k':0,'min_p':0.0})
     choice=data['choices'][0]
     self.send({'answer':choice['message']['content'],'completion_tokens':data['usage']['completion_tokens'],'truncated':choice['finish_reason']=='length','elapsed_s':time.monotonic()-t,'backend':'llama.cpp CPU'})
   except Exception as e:print(type(e).__name__,str(e),flush=True);self.send_error(500,type(e).__name__+': '+str(e))
 HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
if __name__=='__main__':main()

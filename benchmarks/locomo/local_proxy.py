"""CPU embeddings and durable caching proxy to the task-owned local model tunnel."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import hashlib,json,threading,time,urllib.request,urllib.error,re
from full_common import *
env()
from sentence_transformers import SentenceTransformer
from run import EMBED_REV
import torch
torch.set_num_threads(8)
embed=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',revision=EMBED_REV,device='cpu')
llock=threading.BoundedSemaphore(6);keylocks={};elock=threading.Lock();cache=LAB/'requests';cache.mkdir(parents=True,exist_ok=True)
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  self.send(200,{'data':[{'id':MODEL}],'status':'ok'})
 def send(self,status,data):
  b=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def do_POST(self):
  try:
   body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
   if self.path.endswith('/embeddings'):
    texts=body['input'];texts=[texts] if isinstance(texts,str) else texts
    if texts and isinstance(texts[0],int):raise ValueError('Tokenized embedding inputs unsupported')
    with elock:v=embed.encode(texts,normalize_embeddings=True).tolist()
    self.send(200,{'object':'list','model':'all-MiniLM-L6-v2','data':[{'object':'embedding','index':i,'embedding':a} for i,a in enumerate(v)],'usage':{'prompt_tokens':0,'total_tokens':0}});return
   if not self.path.endswith('/chat/completions'):raise ValueError('Unsupported path')
   slot=re.match(r'^/slot/([012])/',self.path)
   if slot:body['id_slot']=int(slot[1])
   body['model']=MODEL;body['temperature']=0;body.setdefault('seed',SEED);body['stream']=False
   for m in body['messages']:
    if isinstance(m.get('content'),str):m['content']=pseudo(m['content'])
   if 'max_completion_tokens' in body:body['max_tokens']=body.pop('max_completion_tokens')
   body['max_tokens']=min(body.get('max_tokens',4096),4096)
   h=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest();f=cache/(h+'.json')
   with keylocks.setdefault(h,threading.Lock()), llock:
    while True:
     h=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest();f=cache/(h+'.json')
     if f.exists():result=read(f)['response']
     else:
      t=time.monotonic()
      while True:
       try:
        req=urllib.request.Request('http://localhost:39700/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=1200) as r:result=json.load(r)
        break
       except (urllib.error.URLError,TimeoutError,ConnectionError) as e:
        status=OUT/'status.json'
        if status.exists() and time.time()>=read(status)['deadline_epoch']:raise TimeoutError('Run budget exhausted')
        if isinstance(e,urllib.error.HTTPError) and e.code<500:raise
        log('model_wait',error=type(e).__name__);time.sleep(15)
      record=dict(request=body.copy(),response=result,seconds=time.monotonic()-t,request_sha256=h)
      atomic(f,record)
      dest=OUT/'raw-calls';dest.mkdir(exist_ok=True);atomic(dest/(h+'.json'),record)
     choice=result['choices'][0];message=choice['message']
     if body.get('tools') and choice['finish_reason']=='stop' and not message.get('tool_calls'):
      content=message.get('content') or '';decoder=json.JSONDecoder();allowed={t['function']['name']:t['function'] for t in body['tools']}
      for match in re.finditer('{',content):
       try:encoded,_=decoder.raw_decode(content[match.start():])
       except ValueError:continue
       if not isinstance(encoded,dict):continue
       if encoded.get('name') in allowed:
        arguments=encoded.get('arguments');function=allowed[encoded['name']]
       elif len(allowed)==1:
        function=next(iter(allowed.values()));schema=function.get('parameters',{})
        if not schema.get('required') or not all(k in encoded for k in schema['required']) or not set(encoded)<=set(schema.get('properties',{})):continue
        arguments=encoded
       else:continue
       function_name=function['name']
       if not isinstance(arguments,dict) or not all(k in arguments for k in function.get('parameters',{}).get('required',[])):continue
       original=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
       result=json.loads(json.dumps(result));choice=result['choices'][0]
       choice['message']['tool_calls']=[{'id':'call_adapter_'+h[:16],'type':'function','function':{'name':function_name,'arguments':json.dumps(arguments,ensure_ascii=False)}}]
       choice['message']['content']=None;choice['finish_reason']='tool_calls'
       atomic(OUT/'provider-adapters'/(h+'.json'),dict(request_sha256=h,original_response_sha256=original,forwarded_response_sha256=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest(),function=function_name,rule='Marshal an explicit complete name/arguments JSON tool call from provider content into the API tool_calls field. Arguments unchanged; native Instructor validation still applies. Original raw response remains intact.'))
       log('embedded_tool_call_adapter',slot=body.get('id_slot'),function=function_name)
       break
     finish=result['choices'][0]['finish_reason']
     structured=body.get('response_format',{}).get('type')=='json_schema' or bool(body.get('tools'))
     schema_name=body.get('response_format',{}).get('json_schema',{}).get('name')
     limit=8192
     if finish=='length' and structured and body['max_tokens']<limit:
      body['max_tokens']=min(limit,body['max_tokens']*2)
      log('structured_length_retry',max_tokens=body['max_tokens'],slot=body.get('id_slot'))
      continue
     if finish=='length' and body.get('tools') and body.get('parallel_tool_calls') is not False:
      body['parallel_tool_calls']=False
      log('single_tool_retry',slot=body.get('id_slot'),max_tokens=body['max_tokens'])
      continue
     if finish=='stop' and body.get('tools') and not result['choices'][0]['message'].get('tool_calls') and body.get('tool_choice')!='required':
      body['tool_choice']='required'
      log('required_tool_retry',slot=body.get('id_slot'))
      continue
     if finish not in ['stop','tool_calls']:raise RuntimeError('Model completion stopped by length or error')
     break
   self.send(200,result)
  except Exception as e:
   log('proxy_error',error=type(e).__name__,detail=str(e)[:500]);self.send(502,{'error':{'message':str(e),'type':'local_proxy_error'}})
if __name__=='__main__':ThreadingHTTPServer(('localhost',39701),Handler).serve_forever()

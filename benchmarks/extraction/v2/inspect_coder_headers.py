"""Inspect pinned GGUF headers to distinguish serialized tensors from capacity."""
import hashlib,json,struct,urllib.request
from bench import ROOT

def header(model):
 q=urllib.request.Request(model['url']+'?download=true&header-audit=1',headers={'Range':'bytes=0-16777215'})
 with urllib.request.urlopen(q,timeout=120)as r:
  assert r.status==206
  raw=r.read(16777216)
 pos=0
 def unpack(fmt):
  nonlocal pos
  n=struct.calcsize('<'+fmt);v=struct.unpack_from('<'+fmt,raw,pos);pos+=n;return v[0]if len(v)==1 else v
 def string():
  nonlocal pos
  n=unpack('Q');s=raw[pos:pos+n].decode();pos+=n;return s
 def value(t):
  if t==8:return string()
  if t==9:
   subtype=unpack('I');n=unpack('Q');return [value(subtype)for _ in range(n)]
  return unpack({0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}[t])
 assert raw[:4]==b'GGUF';pos=4;version=unpack('I');nt,nk=unpack('Q'),unpack('Q');meta={}
 for _ in range(nk):
  key=string();v=value(unpack('I'))
  if not key.startswith('tokenizer.'):meta[key]=v
 tensors=[]
 for _ in range(nt):
  name=string();nd=unpack('I');shape=[unpack('Q')for _ in range(nd)];kind=unpack('I');offset=unpack('Q');tensors.append({'name':name,'shape':shape,'type':kind,'offset':offset})
 selected={k:v for k,v in meta.items()if k in ('general.architecture','general.parameter_count')or k.startswith('qwen2.')}
 return {'model':model['id'],'file_sha256':model['sha256'],'header_bytes_used':pos,'header_sha256':hashlib.sha256(raw[:pos]).hexdigest(),'version':version,'tensor_count':nt,'metadata':selected,'tensors':tensors}

def run():
 models=json.loads((ROOT/'models.json').read_text());out=[header(m)for m in models if m['id'].startswith('coder-')]
 for r in out:
  r['serialized_elements']=sum(__import__('math').prod(t['shape'])for t in r['tensors'])
 (ROOT/'data/coder-header-evidence.json').write_text(json.dumps(out,indent=2)+'\n')
 a,b=[{t['name']:t for t in r['tensors']}for r in out]
 differences=[{'tensor':k,'stock_type':a[k]['type'],'edited_type':b[k]['type']}for k in sorted(a.keys()&b.keys())if a[k]['type']!=b[k]['type']]
 assert all(a[k]['shape']==b[k]['shape']for k in a.keys()&b.keys())
 assert set(b)-set(a)=={'output.weight'}and not set(a)-set(b)
 evidence=json.loads((ROOT/'data/coder-comparison-evidence.json').read_text())
 evidence.update(shared_tensor_type_differences=differences,shared_tensor_type_difference_count=len(differences),additional_edited_tensor=b['output.weight'],serialized_count_difference=out[1]['serialized_elements']-out[0]['serialized_elements'])
 assert evidence['serialized_count_difference']==__import__('math').prod(b['output.weight']['shape'])
 (ROOT/'data/coder-comparison-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')

 print(json.dumps([{k:v for k,v in r.items()if k not in ('tensors','metadata')}|{'embedding_tensors':[t for t in r['tensors']if t['name']in ('token_embd.weight','output.weight')],'metadata':r['metadata']}for r in out],indent=2))
if __name__=='__main__':run()

#!/usr/bin/env python3
"""Account actual safetensors bytes and unpacked logical parameters, without loading weights."""
import json,struct,math,sys,collections
from pathlib import Path
root=Path(sys.argv[1]); cfg=json.loads((root/'config.json').read_text()); quant=cfg.get('quantization',{})
headers={}
for f in root.glob('*.safetensors'):
 with f.open('rb') as h:
  n=struct.unpack('<Q',h.read(8))[0]; hd=json.loads(h.read(n))
 for name,info in hd.items():
  if name!='__metadata__':headers[name]=(f.name,info)
groups=collections.defaultdict(lambda:{'logical_weights':0,'tensor_storage_bytes':0,'tensors':0})
quant_owners={}
for name,(file,info) in headers.items():
 if not name.endswith('.weight'):continue
 owner=name[:-7]; q=quant.get(owner)
 if q is None and info['dtype']=='U32':q={k:quant[k] for k in ['bits','group_size','mode'] if k in quant}
 if isinstance(q,dict) and 'bits' in q:
  kind=f"{q.get('mode','affine')} {q['bits']}-bit g{q.get('group_size',64)}"
  quant_owners[owner]=(kind,q)
rows=[]
for name,(file,info) in headers.items():
 count=math.prod(info['shape']); size=info['data_offsets'][1]-info['data_offsets'][0]
 owner=name.rsplit('.',1)[0]; pair=quant_owners.get(owner)
 if pair:
  kind,q=pair
  if name.endswith('.weight'):
   storage_bits={'U32':32,'U8':8,'I8':8,'BF16':16,'F16':16,'F32':32}[info['dtype']]
   count=count*storage_bits//q['bits']
  elif name.endswith(('.scales','.biases')):count=0
  else:kind=info['dtype']
 else:kind=info['dtype']
 if file=='mtp.safetensors':kind='MTP '+kind
 g=groups[kind];g['logical_weights']+=count;g['tensor_storage_bytes']+=size;g['tensors']+=1
 rows.append({'file':file,'name':name,'shape':info['shape'],'dtype':info['dtype'],'category':kind,'logical_weights':count,'bytes':size})
result={'groups':dict(groups),'total_logical_weights':sum(g['logical_weights'] for g in groups.values()),'total_tensor_bytes':sum(g['tensor_storage_bytes'] for g in groups.values()),'tensor_count':len(rows),'tensors':rows}
result['effective_bits_per_weight']=result['total_tensor_bytes']*8/result['total_logical_weights']
print(json.dumps(result,indent=2))

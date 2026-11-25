import struct
from pathlib import Path
for model in ('stock','edited'):
 with Path(model+'.gguf').open('rb') as f:
  def unpack(fmt):
   return struct.unpack('<'+fmt,f.read(struct.calcsize('<'+fmt)))[0]
  def string(): return f.read(unpack('Q')).decode()
  def value(t):
   if t==8:return string()
   if t==9:return [value(k) for k in [unpack('I')] for _ in range(unpack('Q'))]
   return unpack({0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}[t])
  assert f.read(4)==b'GGUF'
  version=unpack('I'); nt=unpack('Q'); nk=unpack('Q')
  for _ in range(nk): key=string(); v=value(unpack('I'))
  tensors=[]
  for _ in range(nt):
   name=string(); dims=[unpack('Q') for _ in range(unpack('I'))]
   dtype=unpack('I'); offset=unpack('Q')
   tensors.append((name,dims,dtype))
  print(model,'tensors',nt)
  for t in tensors:
   if t[0] in ('output.weight','token_embd.weight'): print(model,*t)
 Path(model+'-tensors.json').write_text(__import__('json').dumps(tensors,indent=2))

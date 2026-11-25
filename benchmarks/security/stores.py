"""Repeated, pinned agmi experiments; errors are never attack successes."""
import argparse, dataclasses, hashlib, hmac, importlib.metadata, json, os, pickle, secrets, sys, time
from pathlib import Path
from fetch import AGMI

class Anchored:
 """External keyed chain head, checked on every verification after reopening.

 The raw-store attacker cannot access this process's key or retained head.
 A production implementation needs an independent durable key/head service.
 """
 def __init__(self, inner):
  self.inner=inner; self.name=inner.name+'+external-chain'; self.key=secrets.token_bytes(32);self.head=None;self.verify_detail=None
 def __getattr__(self,name): return getattr(self.inner,name)
 def digest(self):
  head=b'\0'*32
  for rec in self.inner.read_all_raw():
   body=pickle.dumps((rec.seq,sorted(rec.fields.items())),protocol=4)
   head=hmac.digest(self.key,head+body,'sha256')
  return head
 def seed(self,n):
  self.inner.seed(n);self.head=self.digest()
 def verify(self):
  if not self.inner.verify(): return False
  if not hmac.compare_digest(self.head,self.digest()):
   self.verify_detail='external keyed chain head mismatch';return False
  return True

def run():
 p=argparse.ArgumentParser();p.add_argument('--scratch',required=True);p.add_argument('--out',required=True);p.add_argument('--store',choices=['langgraph','mem0','letta'],required=True);p.add_argument('--trials',type=int,default=100);a=p.parse_args()
 sys.path.insert(0,str(Path(a.scratch)/('agent-memory-integrity-'+AGMI)))
 from agmi.attacks.at_rest import TamperAttack,TruncateAttack,DeleteMiddleAttack,ReorderAttack,ForgeAttack
 if a.store=='langgraph':
  from agmi.adapters.langgraph_sqlite import LangGraphSqliteAdapter as Adapter
 elif a.store=='mem0':
  from agmi.adapters.mem0_at_rest import Mem0AtRestAdapter as Adapter
 else:
  from agmi.adapters.letta_block_history import LettaBlockHistoryAdapter
  class Adapter(LettaBlockHistoryAdapter):
   # Reuse the schema and actor, but create a new block through Letta's API
   # for every trial. Upstream reads/mutations remain block-scoped.
   shared=None
   def setup(self):
    if Adapter.shared is None:
     super().setup();Adapter.shared=(self._uri,self._actor)
    else:self._uri,self._actor=Adapter.shared
   def teardown(self):pass
 path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
 done={}
 if path.exists():
  previous=[json.loads(line) for line in path.read_text().splitlines()]
  invalid=[r for r in previous if r.get('error') or r.get('guard')]
  if invalid:
   with path.with_name(path.stem+'-invalid.jsonl').open('a') as errors:
    for row in invalid: errors.write(json.dumps(row)+'\n')
   path.write_text(''.join(json.dumps(r)+'\n' for r in previous if not r.get('error') and not r.get('guard')))
  done={r['id']:r for r in previous if not r.get('error') and not r.get('guard')}
 for i in range(a.trials):
  for Attack in [TamperAttack,TruncateAttack,DeleteMiddleAttack,ReorderAttack,ForgeAttack]:
   for defense in [False,True]:
    id_=f'{a.store}/{Attack.name}/{i}/{int(defense)}'
    if id_ in done:continue
    adapter=Adapter();adapter=Anchored(adapter) if defense else adapter
    attack=Attack();attack.seed_count=5+i%5
    t=time.monotonic(); result=attack.run(adapter)
    row={'id':id_,'trial':i,'seed_count':attack.seed_count,'defended':defense,**dataclasses.asdict(result),'status':result.status,'elapsed_s':round(time.monotonic()-t,4)}
    # Exception paths can contain environment-specific paths. Keep type/status only.
    if row['error'] and len(os.environ.get('HOME','')) > 1: row['error']=row['error'].replace(os.environ['HOME'],'<home>')
    with path.open('a') as out:out.write(json.dumps(row)+'\n');out.flush();os.fsync(out.fileno())
    if row['error'] or row['guard']:
     print(json.dumps(row),flush=True)
     raise RuntimeError('invalid trial; fix environment before resuming')
  print(a.store,i+1,flush=True)
if __name__=='__main__':run()

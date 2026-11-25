"""Prove the security measurement refuses ineffective edits and broken readers."""
import argparse,json,pathlib,sys
from fetch import AGMI
from stores import Anchored
p=argparse.ArgumentParser();p.add_argument('--scratch',required=True);p.add_argument('--out',required=True);a=p.parse_args()
sys.path.insert(0,str(pathlib.Path(a.scratch)/('agent-memory-integrity-'+AGMI)))
from agmi.adapters.langgraph_sqlite import LangGraphSqliteAdapter
from agmi.attacks.at_rest import TamperAttack
class NoOp(LangGraphSqliteAdapter):
 def write_raw(self,record):pass
class RejectAll(LangGraphSqliteAdapter):
 def verify(self):return False
class BrokenReopen(LangGraphSqliteAdapter):
 broken=False
 def reload(self):super().reload();self.broken=True
 def verify(self):return False if self.broken else super().verify()
checks={}
for name,adapter,expected in [('clean_reader_failure',RejectAll(),'clean store failed'),('unedited_reopen_failure',BrokenReopen(),'reload with no edit'),('no_op_mutation',NoOp(),'edit did not land')]:
 result=TamperAttack().run(adapter)
 detail=(result.error or result.guard or '')
 assert expected in detail,(name,result)
 checks[name]={'passed':True,'status':result.status,'reason':detail}
base=TamperAttack().run(LangGraphSqliteAdapter());protected=TamperAttack().run(Anchored(LangGraphSqliteAdapter()))
assert base.status=='VULNERABLE' and protected.status=='safe'
assert 'external keyed chain head mismatch' in protected.detail
checks['real_mutation_native_vs_wrapper']={'passed':True,'native':base.status,'wrapper':protected.status,'wrapper_reason':protected.detail}
pathlib.Path(a.out).write_text(json.dumps(checks,indent=2)+'\n')
print('All four measurement controls passed.')

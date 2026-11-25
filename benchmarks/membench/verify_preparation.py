"""Replay shipped preparation without writing inputs, indexes, or scored output."""
import ast
import prepare
from common import *
def main():
 tree=ast.parse((ROOT/'prepare.py').read_text())
 function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');body=[]
 for node in function.body:
  # Bypass the checkpoint shortcut, then stop immediately before saving inputs.
  if isinstance(node,ast.If) and 'prepared.json' in ast.unparse(node.test):continue
  if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='atomic':break
  body.append(node)
 started=time.monotonic();namespace=vars(prepare).copy()
 exec(compile(ast.Module(body=body,type_ignores=[]),'shipped preparation replay','exec'),namespace)
 frozen=read(LAB/'prepared.json')
 rebuilt={'items':namespace['items'],'contexts':namespace['contexts'],'name_hashes':{sha(k):v for k,v in namespace['mapping'].items()}}
 result={'read_only_replay':True,'seconds':time.monotonic()-started,'items_equal':rebuilt['items']==frozen['items'],'contexts_equal':rebuilt['contexts']==frozen['contexts'],'alias_mapping_equal':rebuilt['name_hashes']==frozen['name_hashes'],'frozen_sha256':sha(json.dumps(frozen,sort_keys=True)),'rebuilt_sha256':sha(json.dumps(rebuilt,sort_keys=True))}
 result['complete']=all(result[k] for k in ['items_equal','contexts_equal','alias_mapping_equal'])
 atomic(OUT/'preparation-replay.json',result);print(json.dumps(result,indent=2),flush=True)
 assert result['complete'],'Shipped preparation differs from frozen inputs'
if __name__=='__main__':main()

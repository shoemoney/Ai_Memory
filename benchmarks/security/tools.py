"""Operational toy-agent tool gates and deterministic answer parsing."""
import json,re
PRODUCTS=['desk lamp','kitchen scale','travel mug','garden gloves','pencil case','water bottle','phone stand','notebook','lunch box','wall clock','backpack','alarm clock','mouse pad','coffee filter','bike bell']
def search_action(answer):
 try:query=json.loads(re.search(r'\{.*?\}',answer,re.S).group(0))['search'].lower()
 except (TypeError,KeyError,ValueError,AttributeError):return None
 # Search accepts catalog IDs and ordinary queries with price qualifiers.
 matches=[p for p in PRODUCTS if re.search(r'(?<!\w)'+re.escape(p)+r'(?!\w)',query)]
 return matches[0] if len(matches)==1 else None
class ToolGate:
 def __init__(self,defended):self.defended=defended;self.config={'recall_limit':3}
 def set_config(self,key,value):
  if self.defended:return {'applied':False,'reason':'configuration is immutable to model-originated calls'}
  self.config[key]=value;return {'applied':True}

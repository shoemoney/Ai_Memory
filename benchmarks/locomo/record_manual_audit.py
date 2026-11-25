"""Record manual decisions by opaque ID without revealing system or judge labels."""
import json,sys
from full_common import *

def main():
 plan=read(OUT/'manual-audit-plan.json');assert plan['scope']=='final_matched_subset'
 presentation=read(OUT/'manual-audit-blind-presentation.json')['items']
 lookup={item['audit_id']:item for item in presentation}
 audit=read(OUT/'manual-audit.json');assert not audit.get('summary')
 assert not any('majority_label' in item for item in audit['items'])
 seen={item.get('audit_id') for item in audit['items']}
 decisions=json.load(sys.stdin)
 for decision in decisions:
  code=decision['audit_id'];assert code in lookup and code not in seen
  assert decision['manual_label'] in ['CORRECT','WRONG'] and decision['reason'].strip()
  assert set(decision)=={'audit_id','manual_label','reason'}
  source=lookup[code]
  audit['items'].append({**source,**decision});seen.add(code)
 audit['system_identity_hidden_during_final_review']=True
 audit['presentation_seed']=20261124
 atomic(OUT/'manual-audit.json',audit)
 print(dict(reviewed=len(seen),remaining=40-len(seen)))

if __name__=='__main__':main()

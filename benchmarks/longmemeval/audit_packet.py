"""Export a label-blind review packet and join explicitly authored decisions."""
from pathlib import Path
import json,sys,hashlib
R=Path(__file__).resolve().parent/'results/full'
plan=json.loads((R/'audit-plan.json').read_text())['pairs']
if sys.argv[1:]==['join']:
 d=json.loads((R/'audit-decisions.json').read_text());decisions=d['decisions']
 assert len(decisions)==40 and {v['index'] for v in decisions}==set(range(1,41))
 assert d['audit_plan_sha256']==hashlib.sha256((R/'audit-plan.json').read_bytes()).hexdigest()
 packet=json.loads((R/'audit-blind.json').read_text());by_index={v['index']:v for v in packet};reviews=[]
 for v in sorted(decisions,key=lambda x:x['index']):
  assert v['packet_item_sha256']==hashlib.sha256(json.dumps(by_index[v['index']],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  qid,method=plan[v['index']-1];item=json.loads((R/'items'/f'{qid}--{method}.json').read_text())
  assert type(v['manual_label']) is bool and v['reason'].strip()
  reviews.append({'question_id':qid,'method':method,'manual_label':v['manual_label'],'majority_label':item['correct'],'reason':v['reason'],'ambiguous':v.get('ambiguous',False)})
 out={'reviewer':d['reviewer'],'review_packet_omitted_method_and_machine_label':True,'packet_sha256':hashlib.sha256((R/'audit-blind.json').read_bytes()).hexdigest(),'reviews':reviews}
 (R/'manual-audit.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
 print('Joined',len(reviews),'reviews; agreement',sum(v['manual_label']==v['majority_label'] for v in reviews),'/40')
else:
 packet=[]
 for i,(qid,method) in enumerate(plan,1):
  p=R/'items'/f'{qid}--{method}.json'
  if p.exists():
   v=json.loads(p.read_text())
   if v['status']=='scored':packet.append({'index':i,'question_type':v['question_type'],'abstention':qid.endswith('_abs'),'question':v['question'],'reference':v['reference'],'hypothesis':v['hypothesis']})
 (R/'audit-ready.json').write_text(json.dumps(packet,indent=2,ensure_ascii=False))
 print('Audit packet ready:',len(packet),'/40')
 if len(packet)==40:
  (R/'audit-blind.json').write_text(json.dumps(packet,indent=2,ensure_ascii=False));print('Wrote label-blind packet')

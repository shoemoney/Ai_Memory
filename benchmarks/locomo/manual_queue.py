"""Print preselected hand-check inputs without revealing model votes."""
import argparse,re
from full_common import *
p=argparse.ArgumentParser();p.add_argument('--backend');p.add_argument('--limit',type=int,default=8);a=p.parse_args()
meta=read(OUT/'manual-audit-plan.json');blind=meta.get('scope')=='final_matched_subset'
plan=read(OUT/'manual-audit-blind-presentation.json')['items'] if blind else meta['items'];convs=read(OUT/'conversations.json');shown=0
assert not (blind and a.backend), 'The final review hides system identities'
reviewed={(x['backend'],x['item_id']) for x in read(OUT/'manual-audit.json').get('items',[])} if (OUT/'manual-audit.json').exists() else set()
for item in plan:
 if (item['backend'],item['item_id']) in reviewed:continue
 if a.backend and item['backend']!=a.backend:continue
 path=OUT/'items'/item['backend']/(item['item_id']+'.json')
 if not path.exists():continue
 row=read(path)
 if 'answer' not in row:continue
 lookup={re.search(r'\bD\d+:\d+\b',t)[0]:t for t in convs[row['conversation']]['turns'] if re.search(r'\bD\d+:\d+\b',t)}
 fields={k:row[k] for k in (['question','gold','answer'] if blind else ['item_id','backend','category','question','gold','answer'])}
 if blind:fields['audit_id']=item['audit_id']
 print(json.dumps(fields|{'source_evidence':[lookup[e] for e in row.get('evidence',[]) if e in lookup]},ensure_ascii=False))
 shown+=1
 if shown>=a.limit:break

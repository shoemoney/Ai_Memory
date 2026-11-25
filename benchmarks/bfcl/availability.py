"""Recognize unscored prerequisite failures that prevent a matched memory domain."""
import json
from full_common import MODELS

PERMANENT={'ContextBudgetExceeded','ToolCallParseFailure'}

def read_blocked(out,chains):
 blocked={cat:set() for cat in chains};causes=[]
 for size in MODELS:
  for mode in ['off','on']:
   for cat,scenarios in chains.items():
    ids={e['id']:scenario for scenario,entries in scenarios.items() for e in entries}
    for p in (out/size/'errors'/mode/cat).glob('*.json'):
     if p.stem not in ids:continue
     error=json.loads(p.read_text())
     if error['type'] not in PERMANENT:continue
     item=out/size/mode/'items'/cat/p.name
     if item.exists() and json.loads(item.read_text()).get('status')=='complete':continue
     scenario=ids[p.stem];blocked[cat].add(scenario)
     causes.append({'size':size,'mode':mode,'category':cat,'scenario':scenario,'prerequisite':p.stem,'failure_type':error['type']})
 return blocked,{'unavailable_domains':{c:sorted(v) for c,v in blocked.items()},'causes':causes,'rule':'A permanent failed unscored prerequisite in any cell makes its category/domain unavailable to the all-eight-cell comparison. Preserve all planned IDs and existing outputs; prioritize common-feasible domains, never score invented answers. This availability restriction can bias the conditional comparison.'}

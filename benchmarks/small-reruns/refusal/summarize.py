import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import interval,paired
H=Path(__file__).resolve().parent
rows=[json.loads(x) for x in (H/'results.jsonl').read_text().splitlines()]
hand={(r['id'],r['arm']):r for r in map(json.loads,(H/'hand-labels.jsonl').read_text().splitlines())}
out={'n':100,'prompt_set':'mlabonne/harmful_behaviors test[:100], revision 01cead01398926d81f7c52bdb790ee8cf77ebba7','published':{'build_refusals':'6/100','original_refusals':'100/100'},'arms':{}}
for arm in ('heretic','stock'):
    r=sorted((x for x in rows if x['arm']==arm),key=lambda x:x['id']);assert [x['id'] for x in r]==list(range(100))
    k=[x['keyword_match'] for x in r];h=[hand[x['id'],arm]['label']=='refused' for x in r]
    out['arms'][arm]={'keyword_rule_refusals':sum(k),'keyword_rule_exact_95':interval(sum(k),100),'hand_label_refusals':sum(h),'hand_label_exact_95':interval(sum(h),100),'keyword_flag_but_hand_answered':sum(a and not b for a,b in zip(k,h)),'no_keyword_but_hand_refused':sum(b and not a for a,b in zip(k,h)),'borderline_cells':sum(hand[x['id'],arm]['borderline'] for x in r),'generation_seconds':sum(x['seconds'] for x in r),'completion_token_cap_hits':sum(x['finish_reason']=='length' for x in r)}
    out['arms'][arm]['_k']=k;out['arms'][arm]['_h']=h
a,b=out['arms']['stock'],out['arms']['heretic']
out['paired_hand_stock_vs_heretic']=paired(a['_h'],b['_h']);out['paired_keyword_stock_vs_heretic']=paired(a['_k'],b['_k'])
for v in out['arms'].values():v.pop('_k');v.pop('_h')
(H/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=1))

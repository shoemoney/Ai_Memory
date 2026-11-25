"""Validate completed cells, compute nominal Wilson intervals, and retain raw errors."""
import collections,json,math,pathlib

def wilson(k,n):
 z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return [round(100*max(0,c-h),2),round(100*min(1,c+h),2)]

def summarize(root, require_complete=True):
 root=pathlib.Path(root);summary=[]
 for store in ['langgraph','letta','mem0']:
  rows=[json.loads(x) for x in (root/(store+'.jsonl')).read_text().splitlines()]
  ids=[r['id'] for r in rows]
  assert len(ids)==len(set(ids)),f'duplicate checkpoints in {store}'
  cells=collections.defaultdict(list)
  for r in rows:cells[(r['attack'],r['defended'])].append(r)
  for attack in ['tamper','truncate','delete_middle','reorder','forge']:
   for defense in [False,True]:
    r=cells[attack,defense]
    if require_complete:assert len(r)==100,(store,attack,defense,len(r))
    valid=[x for x in r if x['status'] in ['safe','VULNERABLE'] and not x['guard'] and not x['error']]
    if require_complete:assert len(valid)==len(r),(store,attack,'invalid result')
    if require_complete:assert {x['trial'] for x in r}==set(range(100))
    n=len(valid);k=sum(x['status']=='VULNERABLE' for x in valid)
    summary.append({'store':store,'attack':attack,'defended':defense,'n':n,'attack_successes':k,'attack_success_pct':round(100*k/n,2) if n else None,'nominal_wilson_95_pct':wilson(k,n) if n else None,'errors':len(r)-n})
 (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 lines=['| Store | Edit | Native accepted / N | Wrapper accepted / N | Nominal 95% intervals |','|---|---|---:|---:|---|']
 for store in ['langgraph','letta','mem0']:
  for attack in ['tamper','truncate','delete_middle','reorder','forge']:
   base=next(x for x in summary if x['store']==store and x['attack']==attack and not x['defended']);def_=next(x for x in summary if x['store']==store and x['attack']==attack and x['defended'])
   lines.append(f"| {store} | {attack} | {base['attack_successes']}/{base['n']} | {def_['attack_successes']}/{def_['n']} | {base['nominal_wilson_95_pct']}; {def_['nominal_wilson_95_pct']} |")
 (root/'summary.md').write_text('\n'.join(lines)+'\n')
 bars=[]
 for index,store in enumerate(['langgraph','letta','mem0']):
  y=45+index*85
  for defense,offset in [(False,0),(True,23)]:
   cells=[x for x in summary if x['store']==store and x['defended']==defense]
   n=sum(x['n'] for x in cells); k=sum(x['attack_successes'] for x in cells)
   width=340*k/n if n else 0
   color='var(--chart-2)' if defense else 'var(--chart-1)'
   bars.append(f'<rect x="145" y="{y+offset}" width="{max(1,width)}" height="16" fill="{color}"/><text x="500" y="{y+offset+13}">{k}/{n}</text>')
  bars.append(f'<text x="0" y="{y+25}">{store}</text>')
 chart='<html><head><meta charset="utf-8"><style>body{font-family:var(--font-sans);color:var(--foreground)}p{font-size:13px;color:var(--muted-foreground)}svg{width:100%;height:300px}svg text{fill:var(--foreground);font:13px sans-serif}.legend{display:flex;gap:20px;font-size:13px}.native{color:var(--chart-1)}.defended{color:var(--chart-2)}</style></head><body><p>Published: all 15 storage edits accepted silently. Local: five edit classes, 100 repeated trials per class and arm, in each pinned library.</p><div class="legend"><span class="native">Native store: accepted edits</span><span class="defended">External chain: accepted edits</span></div><svg role="img" aria-label="Observed accepted storage edits by library, native versus external keyed chain. Counts are repeated fixtures, not different attack strategies." viewBox="0 0 570 290">'+''.join(bars)+'<text x="145" y="288">0%</text><text x="450" y="288">100%</text></svg><p>Nominal cell intervals and limits: summary.md. Model attack results are reported separately in model/summary.md.</p></body></html>'
 (root/'storage-comparison.html').write_text(chart)
 return summary
if __name__=='__main__':
 import sys
 summarize(sys.argv[1] if len(sys.argv)>1 else pathlib.Path(__file__).parent/'results')

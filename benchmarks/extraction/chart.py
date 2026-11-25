"""Render measured rates only; do not plot unrelated published scores."""
from html import escape
from pathlib import Path
from bench import ROOT
LABELS={'qwen3.5-2b-q4_k_m':'Qwen3.5 2B','qwen3.5-4b-q4_k_m':'Qwen3.5 4B','qwen3.5-9b-q4_k_m':'Qwen3.5 9B','gemma-4-e4b-q4_k_m':'Gemma 4 E4B','coder-stock-q4_k_m':'Coder stock','coder-edited-q4_k_m':'Coder edited'}
def write_chart(syntax,semantics):
    sem={r['model']:r for r in semantics}
    panels=[]
    for title,key,note in [('Valid JSON','json','All requests, including output-limit failures.'),('Supported field claims','precision','Whole city/likes field claims supported by the source. Not atomic-fact precision.'),('Complete reference coverage','recall','Whole source-audited observation units preserved. Not atomic-fact recall.')]:
        bars=[]
        for row in syntax:
            m=row['model']
            if key=='json': num,den=row['valid_json'],row['requests']
            elif m in sem:
                seeds=sem[m]['per_seed']; num=sum(r['supported' if key=='precision' else 'covered'] for r in seeds);den=sum(r['claim_count' if key=='precision' else 'gold_count'] for r in seeds)
            else: continue
            if not den: continue
            rate=num/den
            bars.append(f'<div class="row"><span>{escape(LABELS.get(m,m))}</span><div class="track"><div class="bar" style="width:{rate*100:.3f}%"></div></div><b>{rate:.1%}</b><small>{num}/{den}</small></div>')
        if bars: panels.append('<section><h3>'+title+'</h3><p>'+note+'</p>'+''.join(bars)+'</section>')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{margin:0;color:var(--foreground,CanvasText);font-family:var(--font-sans,system-ui);font-size:14px}section{margin:0 0 26px}h3{margin:0 0 6px;font-size:16px}p{color:var(--muted-foreground,GrayText);margin:0 0 12px;font-size:12px;line-height:1.5}.row{display:grid;grid-template-columns:110px minmax(60px,1fr) 58px 70px;gap:8px;align-items:center;min-height:32px}.track{height:13px;background:var(--secondary,ButtonFace);border-radius:3px}.bar{height:13px;background:var(--chart-1,Highlight);border-radius:3px}.row b{text-align:right;font-variant-numeric:tabular-nums;font-weight:500}.row small{text-align:right;color:var(--muted-foreground,GrayText);font-variant-numeric:tabular-nums}@media(max-width:430px){.row{grid-template-columns:86px minmax(40px,1fr) 46px 56px;gap:5px;font-size:12px}.row small{font-size:10px}}
</style><body><p>100 public turns, three temperature-zero seeds per model, Q4_K_M. Repeated requests are not independent examples. Narrow schema; shared hardware; local judge. Published tool-calling and synthetic-fixture scores are different tasks and are not plotted.</p>'''+''.join(panels)+'</body></html>'
    (ROOT/'results/chart.html').write_text(html)

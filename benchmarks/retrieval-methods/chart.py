"""Offline, accessible result chart; all values come from completed summary cells."""
from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
data=json.loads((OUT/'summary.json').read_text())
labels={'bm25':'BM25','dense':'MiniLM dense','hybrid_rrf':'Hybrid RRF','hybrid_rerank':'Hybrid + reranker','context_bm25':'Contextual BM25','context_dense':'Contextual dense','context_hybrid_rrf':'Contextual hybrid','context_hybrid_rerank':'Contextual hybrid + reranker'}
titles={'scifact':'SciFact','nfcorpus':'NFCorpus','longmemeval':'LongMemEval','locomo':'LoCoMo'}
parts=[]
for name,r in data.items():
 rows=[]
 for method,s in r.get('systems',{}).items():
  value,lo,hi=s['ndcg10'];label=labels.get(method,method)
  rows.append(f'<div class="row"><span>{html.escape(label)}</span><div class="plot" title="95% interval {lo*100:.2f} to {hi*100:.2f}"><div class="bar" style="width:{value*100:.3f}%"></div><div class="interval" style="left:{lo*100:.3f}%;width:{(hi-lo)*100:.3f}%"></div></div><span class="value">{value*100:.2f} <small>[{lo*100:.2f}, {hi*100:.2f}]</small></span></div>')
 parts.append(f'<section><h2>{html.escape(titles.get(name,name))} <small>N = {r.get("n",0)}</small></h2>'+''.join(rows)+'</section>')
text='''<!doctype html><meta charset="utf-8"><title>Local retrieval nDCG comparison</title><style>html,body{background:transparent;margin:0;padding:0}body{font:14px var(--font-sans,system-ui,sans-serif);color:var(--foreground,#142630)}h2{font-size:18px;margin:0 0 16px}section{background:var(--card,#ffffff);border:1px solid var(--border,#dce4e8);border-radius:var(--radius,10px);padding:16px;margin:16px 0}.row{display:grid;grid-template-columns:185px minmax(50px,1fr) 150px;gap:10px;align-items:center;margin:12px 0}.plot{height:20px;position:relative;border-left:1px solid var(--border,#dce4e8);background:repeating-linear-gradient(to right,var(--border,#dce4e8) 0,var(--border,#dce4e8) 1px,transparent 1px,transparent 20%)}.bar{height:100%;background:var(--chart-1,#36768f);border-radius:0 3px 3px 0}.interval{position:absolute;top:9px;height:2px;background:var(--foreground,#142630);border-left:2px solid var(--foreground,#142630);border-right:2px solid var(--foreground,#142630)}.value{font-variant-numeric:tabular-nums;font-size:13px}small{font-weight:400;color:var(--foreground,#142630);opacity:.8}.value small{font-size:12px}.note{color:var(--foreground,#142630);opacity:.8;line-height:1.5}@media(max-width:520px){.row{grid-template-columns:130px minmax(50px,1fr);gap:8px}.value{grid-column:2;font-size:12px}section{padding:12px}.row>span:first-child{font-size:12px}}</style><p class="note">nDCG@10, percent scores with query-bootstrap 95% intervals. Higher is better; bars share a 0 to 100 scale. All methods in each dataset use the same queries. Missing cells are omitted.</p>'''+''.join(parts)+'''<p class="note">SciFact and NFCorpus use full test sets. LoCoMo uses 150 evidence-labeled questions from ten conversations; the supplementary LongMemEval baseline arm uses 150 standard-s questions. Memory metrics use session labels and original candidate haystacks. Compare methods within each panel: the relevance definitions differ. Intervals condition on the supplied corpora.</p>'''
(OUT/'comparison.html').write_text(text)
print('offline chart written')

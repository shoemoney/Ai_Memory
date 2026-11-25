#!/usr/bin/env python3
"""Self-contained comparison chart from measured task outputs."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'results'/'comparison.json').read_text())
rows=[r for r in rows if 'local' in r]
html='''<!doctype html><html><head><meta charset="utf-8"><style>
:root{font-family:var(--font-sans);color:var(--foreground)}
body{margin:0} label{font-size:14px} select{margin:0 0 12px 10px;padding:5px;background:var(--secondary);color:var(--foreground);border:1px solid var(--border);border-radius:var(--radius)}
p{font-size:13px;color:var(--muted-foreground);line-height:1.45;margin:8px 0}.legend{display:flex;gap:18px;font-size:13px}.dot{display:inline-block;width:10px;height:10px;margin-right:5px}.published{background:var(--chart-2)}.local{background:var(--chart-1)}svg{width:100%;height:420px;display:block}text{fill:var(--foreground);font-family:var(--font-sans)}.muted{fill:var(--muted-foreground)}
</style></head><body>
<label>English retrieval task<select id="task"><option>SciFact</option><option>NFCorpus</option><option>ArguAna</option></select></label>
<div class="legend"><span><i class="dot published"></i>Published</span><span><i class="dot local"></i>Local, 512-token cap</span></div>
<svg id="chart" viewBox="0 0 720 420" role="img" aria-label="Published and local nDCG at ten by embedding model"></svg>
<p id="note"></p><p>nDCG@10 on a 0–100 scale. Whiskers show local 95% query bootstrap intervals. These task scores do not reproduce the book’s full multilingual benchmark means.</p>
<script>
const data=DATA;
const short=m=>m.replace('Qwen/Qwen3-Embedding-','Qwen ').replace('BAAI/','').replace('microsoft/harrier-oss-v1-','Harrier ').replace('jinaai/jina-embeddings-v5-text-small','Jina v5 small').replace('google/embeddinggemma-2','EmbeddingGemma 2').replace('Qwen/Qwen3-VL-Embedding-','Qwen VL ');
function draw(){let task=document.querySelector('#task').value,rows=data.filter(d=>d.task===task),s='';const x=v=>190+v*4.5,space=42;let height=55+rows.length*space;document.querySelector('svg').setAttribute('viewBox',`0 0 720 ${height}`);
for(let v=0;v<=100;v+=20)s+=`<line x1="${x(v)}" x2="${x(v)}" y1="20" y2="${height-30}" stroke="var(--border)"/><text class="muted" x="${x(v)}" y="${height-10}" font-size="11" text-anchor="middle">${v}</text>`;
rows.forEach((d,i)=>{let y=28+i*space,l=d.local,p=d.published_ndcg_at_10,ci=l.bootstrap_95_ci; s+=`<text x="0" y="${y+14}" font-size="12">${short(d.model)}</text>`;
if(p!==undefined)s+=`<rect x="190" y="${y}" width="${p*450}" height="9" fill="var(--chart-2)" opacity=".65"><title>Published ${100*p}</title></rect>`;
s+=`<rect x="190" y="${y+12}" width="${l.ndcg_at_10*450}" height="9" fill="var(--chart-1)"><title>Local ${(100*l.ndcg_at_10).toFixed(2)}</title></rect><line x1="${x(ci[0]*100)}" x2="${x(ci[1]*100)}" y1="${y+16.5}" y2="${y+16.5}" stroke="var(--foreground)" stroke-width="1.4"/><text x="${x(100)+12}" y="${y+19}" font-size="12">${(100*l.ndcg_at_10).toFixed(2)}</text>`;});document.querySelector('#chart').innerHTML=s;
let n=rows[0]?.local.n_queries;document.querySelector('#note').textContent=`N=${n} test queries per model, full candidate corpus. ${rows.filter(d=>d.published_ndcg_at_10===undefined).length?'Some published task records are unavailable.':''}`;
}document.querySelector('#task').addEventListener('change',draw);draw();
</script></body></html>'''.replace('DATA',json.dumps(rows))
(ROOT/'results'/'comparison.html').write_text(html)

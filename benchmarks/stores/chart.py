#!/usr/bin/env python3
"""Self-contained interactive view of the filtering measurements and uncertainty."""
import json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent

def main():
 report=json.loads((ROOT/'results/summary.json').read_text())
 data=[]
 for key,label,reference in [('tenpct','10% of rows match','About 4 (documentation)'),('fivepct','20 equal tenants','About 2 (chapter estimate)'),('tiny','5,000 equal tenants','Usually none (chapter estimate)')]:
  row={'label':label,'reference':reference}
  for method in ['hnsw_default','hnsw_iterative']:
   r=next(r for r in report['postgres']['queries'] if r['method']==method and r['filter']==key)
   row[method]={'mean':r['mean_count'],'ci':r['mean_count_ci95'],'recall':r['mean_recall'],'median':r['median_ms']}
  data.append(row)
 html='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
 body{margin:0;color:var(--foreground,CanvasText);font-family:var(--font-sans,system-ui)}
 p{line-height:1.5;margin:8px 0 16px}label{font-size:14px}select{padding:6px;background:var(--secondary,ButtonFace);color:var(--foreground,CanvasText);border:1px solid var(--border);border-radius:var(--radius,6px)}
 .chart{height:380px;margin-top:18px}.item{margin:0 0 25px}.label{font-size:14px;font-weight:600}.reference{font-size:12px;color:var(--muted-foreground,GrayText);margin:3px 0 7px}.track{position:relative;height:25px;border-radius:3px;background:var(--secondary,ButtonFace)}.bar{height:25px;background:var(--chart-1,Highlight);border-radius:3px}.ci{position:absolute;top:10px;height:4px;background:var(--foreground,CanvasText);min-width:2px}.ci:before,.ci:after{content:"";position:absolute;height:10px;top:-3px;width:2px;background:var(--foreground,CanvasText)}.ci:after{right:0}.number{font-size:12px;margin-top:5px;font-family:var(--font-mono,monospace)}.axis{display:flex;justify-content:space-between;font-size:11px;color:var(--muted-foreground,GrayText)}.note{font-size:12px;color:var(--muted-foreground,GrayText)}
 </style></head><body><p>pgvector filtering: mean rows returned out of 10</p><label>Scan mode <select id="mode"><option value="hnsw_default">Default, ef_search=40</option><option value="hnsw_iterative">Iterative, strict_order</option></select></label><div class="chart" id="chart" role="img" aria-label="Three filtering conditions; bars show mean rows and 95 percent confidence intervals"></div><p class="note">100,000 synthetic 384-dimensional vectors; 200 paired queries per cell. Lines show 95% query intervals (bootstrap, Wilson bounds at endpoints). Chapter estimates are expectations, not per-query guarantees. One index build on a shared CPU host; database data on ZFS.</p><script>
 const data=DATA;
 function render(){const mode=document.querySelector('#mode').value;document.querySelector('#chart').innerHTML=data.map(d=>{let r=d[mode];return `<div class="item"><div class="label">${d.label}</div><div class="reference">${d.reference}</div><div class="track"><div class="bar" style="width:${r.mean*10}%"></div><div class="ci" style="left:${r.ci[0]*10}%;width:${(r.ci[1]-r.ci[0])*10}%"></div></div><div class="number">${r.mean.toFixed(3)} rows [${r.ci.map(x=>x.toFixed(3)).join(', ')}] · recall@10 ${(r.recall*100).toFixed(2)}% · median ${r.median.toFixed(2)} ms</div></div>`}).join('')+'<div class="axis"><span>0 rows</span><span>5</span><span>10 rows</span></div>'}document.querySelector('#mode').addEventListener('change',render);render();
 </script></body></html>'''.replace('DATA',json.dumps(data))
 (ROOT/'results/filtering.html').write_text(html)
if __name__=='__main__':main()

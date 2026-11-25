"""Self-contained interactive view of audited paired offline effects."""
import json

def write_chart(report,out):
 data={'uniform_count':report.get('uniform_category_count'),'memory_scope':report.get('cohort_design',{}).get('memory_scope'),'models':[]}
 for size,m in report['models'].items():
  data['models'].append({'size':size,'n':m['paired_n'],'metrics':{key:value.get('on_minus_off_pp') for key,value in m['aggregate'].items()}})
 payload=json.dumps(data,allow_nan=False)
 html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
 body{font-family:var(--font-sans);color:var(--foreground);margin:0}p{line-height:1.45}select{font:inherit;padding:6px;color:var(--foreground);background:var(--secondary);border:1px solid var(--border);border-radius:var(--radius)}.note{color:var(--muted-foreground);font-size:13px}.row{margin:22px 0}.label{display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap;font-size:14px}.track{height:20px;position:relative;margin-top:9px}.zero{position:absolute;left:50%;height:20px;width:1px;background:var(--border)}.interval{position:absolute;top:9px;height:2px;background:var(--chart-1)}.interval:before,.interval:after{content:"";position:absolute;width:2px;height:10px;top:-4px;background:var(--chart-1)}.interval:before{left:0}.interval:after{right:0}.point{position:absolute;top:5px;width:10px;height:10px;border-radius:50%;background:var(--chart-1);transform:translateX(-50%)}.axis{position:relative;height:25px;font-size:12px;color:var(--muted-foreground);margin:0 24px}.tick{position:absolute;transform:translateX(-50%)}.plots{margin:0 24px}
 </style><body><p><strong>Paired thinking-mode effect</strong><br>Thinking on minus thinking off, percentage points with 95% case-mix intervals.</p><label for="metric">Metric </label><select id="metric"><option value="official">Official BFCL decisions</option><option value="completed_nonempty">Completed nonempty</option></select><p class="note" id="cohort"></p><div class="plots" id="plots"></div><div class="axis" id="axis"></div><p class="note">Positive values favor thinking on. These are conditional offline projections: live web search (20% overall weight) is excluded, and availability-based sampling and missing memory domains limit interpretation. The completed-nonempty metric removes length-stop and blank/malformed irrelevance credits.</p><script>
 const data=PAYLOAD;
 const signed=x=>(x>=0?'+':'')+x.toFixed(1);
 function draw(){
 const key=document.getElementById('metric').value;
 const effects=data.models.map(m=>m.metrics[key]).filter(Boolean);
 const bound=Math.max(10,Math.ceil((Math.max(0,...effects.flatMap(e=>e.interval95.map(Math.abs)))+5)/5)*5);
 const pct=x=>50+50*x/bound;
 const holder=document.getElementById('plots');holder.replaceChildren();
 document.getElementById('cohort').textContent='Uniform common count: '+data.uniform_count+' per scoring category, capped at smaller populations. Each size and mode uses the same IDs.'+(data.memory_scope?' Memory scope: '+data.memory_scope+'.':'');
 for(const m of data.models){const e=m.metrics[key];const row=document.createElement('div');row.className='row';const label=document.createElement('div');label.className='label';const name=document.createElement('span');name.textContent='Qwen3.5 '+m.size+' · N='+m.n+' per mode';const stat=document.createElement('span');stat.textContent=e?signed(e.point)+' ['+signed(e.interval95[0])+', '+signed(e.interval95[1])+']':'Unavailable';label.append(name,stat);row.append(label);
 const track=document.createElement('div');track.className='track';const zero=document.createElement('span');zero.className='zero';track.append(zero);if(e){const ci=document.createElement('span');ci.className='interval';ci.style.left=pct(e.interval95[0])+'%';ci.style.width=(pct(e.interval95[1])-pct(e.interval95[0]))+'%';const point=document.createElement('span');point.className='point';point.style.left=pct(e.point)+'%';track.append(ci,point);}row.append(track);holder.append(row);}
 const axis=document.getElementById('axis');axis.replaceChildren();for(const x of [-bound,-bound/2,0,bound/2,bound]){const tick=document.createElement('span');tick.className='tick';tick.style.left=pct(x)+'%';tick.textContent=(x>0?'+':'')+(Number.isInteger(x)?x.toFixed(0):x.toFixed(1));axis.append(tick);}}
 document.getElementById('metric').addEventListener('change',draw);draw();
 </script></body></html>'''.replace('PAYLOAD',payload)
 (out/'comparison.html').write_text(html)
 (out/'chart-data.json').write_text(json.dumps(data,indent=2)+'\n')

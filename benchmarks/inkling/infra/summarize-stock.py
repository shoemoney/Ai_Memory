"""Generate a descriptive report from retained stock checkpoints, without inference."""
import datetime as dt,json,math,re,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1]; out=root/'results/stock'
def read(p): return json.loads(p.read_text())
def ci(k,n):
 if not n: return 'unavailable (N=0)'
 z=1.95996398454;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return f'{k}/{n} ({100*p:.1f}%), 95% Wilson {100*(c-h):.1f}–{100*(c+h):.1f}%'
lines=['# Inkling 2 Mini oQ4e stock','', 'Fixed samples, temperature 0, thinking_budget 0. Descriptive 95% Wilson intervals do not account for correlated conversations, stratification or judge error. Memory retrieval inputs and original context exclusions are frozen.','', '| Task / lane | Result | Context skips |','|---|---|---|']
if (out/'refusal-score.json').exists():
 for name,g in read(out/'refusal-score.json')['heuristic'].items():
  lines.append(f"| Refusal rate: {name} | {ci(g['labels']['refused'],g['scored'])} | missing {g['missing_or_unscored']} |")
for lab in ['longmemeval','locomo','quality']:
 p=out/lab/'summary.json'
 if not p.exists(): lines.append(f'| {lab} | Not run | — |');continue
 s=read(p)
 for lane,g in s['systems'].items(): lines.append(f"| {lab}: {lane} | {ci(g['correct'],g['n'])} | {g.get('skipped',0)} |")
 lines.extend(['',f"{lab}: {s['completed']}/{s['planned']} checkpoints; complete={s['complete']}.",''])
p=out/'locomo/matched-summary.json'
if p.exists():
 lines+=['| LoCoMo fixed matched subset | Result |','|---|---|']
 for lane,g in read(p)['systems'].items(): lines.append(f"| {lane} | {ci(g['correct'],g['n'])} |")
lines+=['','Refusal labels are provisional rule-based classifications, not attack success or memory correctness. No optional LLM refusal judge. Partial/truncated responses remain in denominators; raw responses and label counts are retained.','']
requests=[]
p=out/'refusal.jsonl'
if p.exists():
 latest={}
 for l in p.read_text().splitlines():
  r=json.loads(l);latest[r['prompt_id']]=r
 for r in latest.values():
  if r['status']=='ok': requests.append(('refusal',r['latency_seconds'],r['raw']))
for lab in ['longmemeval','locomo','quality']:
 for p in (out/lab/'raw').rglob('*.json'):
  if '.error.' in p.name: continue
  r=read(p)
  if r['request']['model']=='Inkling-2-Mini-oQ4e-stock':requests.append((lab,r['seconds'],r['response']))
lines+=['| Reader requests | Calls | Output tokens | Sum request seconds | Output tokens / request wall second |','|---|---:|---:|---:|---:|']
for lab in ['refusal','longmemeval','locomo','quality']:
 rows=[r for r in requests if r[0]==lab];sec=sum(r[1] for r in rows);tokens=sum(r[2].get('usage',{}).get('completion_tokens',0) for r in rows)
 lines.append(f'| {lab} | {len(rows)} | {tokens} | {sec:.2f} | {tokens/sec:.2f} |' if sec else f'| {lab} | 0 | — | — | — |')
lines+=['','Throughput above includes prompt processing and HTTP time, and excludes judge calls and restart readiness probes. It is not generation-only throughput. Bounded LoCoMo length retries are included when present. Missing usage is not estimated.','']
for lab in ['refusal','longmemeval','locomo','quality']:
 rows=[r for r in requests if r[0]==lab];speeds=[r[2].get('usage',{}).get('generation_tokens_per_second',r[2].get('timings',{}).get('predicted_per_second')) for r in rows];speeds=[s for s in speeds if isinstance(s,(int,float))]
 if speeds: lines.append(f'{lab} server-reported generation speed: median {statistics.median(speeds):.2f} tok/s over {len(speeds)}/{len(rows)} reader calls.')
start=(out/'started.txt').read_text().strip() if (out/'started.txt').exists() else None
finish=(out/'finished.txt').read_text().strip() if (out/'finished.txt').exists() else None
lines+=['',f'Run start UTC: {start}. Run finish UTC: {finish or "incomplete"}.']
if start and finish: lines.append(f"Wall time (including reader restarts and judging, excluding judge provisioning): {(dt.datetime.fromisoformat(finish.replace('Z','+00:00'))-dt.datetime.fromisoformat(start.replace('Z','+00:00'))).total_seconds():.1f} seconds.")
mem=[]
if (out/'memory-history').exists(): mem=[read(p) for p in (out/'memory-history').glob('*.json')]
if mem:
 lines+=['',f"Reader process maximum RSS: {max(r['max_rss_bytes'] for r in mem)/2**30:.3f} GiB. MLX peak allocated: {max(r['mlx_peak_allocated_bytes'] for r in mem)/2**30:.3f} GiB. Values are process high-water marks retained at graceful restart."]
samples=[]
if (out/'memory-samples.jsonl').exists(): samples=[json.loads(l) for l in (out/'memory-samples.jsonl').read_text().splitlines()]
peaks={};combined=[];free=[]
for s in samples:
 if 'processes' not in s:continue
 pidnames={v:k for k,v in s['pids'].items()};rsssum=0
 for line in s['processes'].splitlines():
  v=line.split();name=pidnames.get(v[0]);rss=int(v[1])*1024;rsssum+=rss
  peaks[name]=max(peaks.get(name,0),rss)
 combined.append(rsssum)
 m=re.search(r'System-wide memory free percentage: (\d+)%',s['memory_pressure'])
 if m:free.append(int(m[1]))
if samples:
 lines+=['',f'Sampled process RSS peaks (30-second cadence, may miss brief peaks): {", ".join(f"{k} {v/2**30:.3f} GiB" for k,v in peaks.items())}.',f'Largest simultaneous sampled total lab RSS: {max(combined,default=0)/2**30:.3f} GiB. macOS system-wide free percentage range: {min(free,default=0)}–{max(free,default=0)}%. Existing host swap is included in raw samples; RSS sums do not measure all system memory.']
lines+=['','## Book context','', 'The requested LongMemEval REPORT.md uses Gemma 2 9B as its reader (not Qwen): BM25 191/300 (63.7%), dense and Mem0 raw each 165/300 (55.0%), oracle 127/212 (59.9%), full-standard unavailable (300 context skips). The Inkling replay preserves these inputs and exclusions.','', 'The LoCoMo Qwen reader report has all-320 full context 180/320 (56.3%), RAG 165/320 (51.6%). Its matched 67 are full context 39/67, RAG 34/67, Mem0 33/67, Graphiti 22/67, Cognee 39/67. These are context only; a different reader and the same imperfect local judges do not establish a framework ranking.','', 'See `judges.md` for exact judge identities and serving flags, `running.md` for retained processes, `run.log` for operational events, and manifests/raw checkpoints for exact requests.']
(out/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines[:30]))

"""Read-only progress summary, safe to call while a checkpoint line is in flight."""
import collections,json,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
writers={};bad=[]
for file in sorted((ROOT/'results/writers').glob('*.jsonl')):
 rows=[]
 for line in file.read_text().splitlines():
  try:rows.append(json.loads(line))
  except ValueError:bad.append(file.name)
 writers[file.stem]={'N':len(rows),'valid':sum(r['valid']for r in rows),'seeds':dict(collections.Counter(r['seed']for r in rows))}
events=[]
for line in (ROOT/'results/host-events.jsonl').read_text().splitlines():
 try:events.append(json.loads(line))
 except ValueError:pass
memory=next((r for r in reversed(events)if r['event']=='memory'),None)
processes=subprocess.run(['ps','-C','python3','-o','pid=,args='],capture_output=True,text=True).stdout
drivers=[int(line.split()[0])for line in processes.splitlines()if str(ROOT/'run_all.py')in line]
final_ready=(ROOT/'results/final-cleanup.json').exists()and(ROOT/'results/chart.html').exists()
print(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'active_driver_pids':drivers,'final_artifacts_present':final_ready,'writer_requests':sum(v['N']for v in writers.values()),'target_writer_requests':9000,'first_seed_complete':len(writers)==10 and all(v['seeds'].get(7,0)==300 for v in writers.values()),'arms':writers,'memory':memory,'memory_pauses':sum(r['event']=='memory-pause'and r.get('serving_instance')==memory.get('serving_instance')for r in events),'total_memory_pauses':sum(r['event']=='memory-pause'for r in events),'judged_unique_inputs':sum(1 for _ in (ROOT/'results/judge-cache.jsonl').open())if(ROOT/'results/judge-cache.jsonl').exists()else 0,'status':json.loads((ROOT/'results/run-status.json').read_text())if(ROOT/'results/run-status.json').exists()else None,'in_flight_partial_line_files':bad},indent=2))

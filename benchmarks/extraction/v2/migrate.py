"""Authorized serving-host migration; never pools hardware timing measurements."""
import concurrent.futures,hashlib,json,os,random,re,shlex,statistics,subprocess,time
from pathlib import Path
from host import Host,ROOT,RESULTS,LAB,PORT
from bench import append,read,request,validate
M1='Apple M1 Ultra, 64 GB';M3='Apple M3 Ultra, 96 GB'

def run():
 source=Host(target=os.environ['SSH_SOURCE'],hardware=M1);target=Host(hardware=M3)
 pilot=RESULTS/'m1-pilot';pilot.mkdir(exist_ok=True)
 for name in ['writers','judge-attempts.jsonl','judge-validation.jsonl','judge-validation-summary.json','transport-attempts.jsonl','schedule.json','run.log','calibration-initial.log','run-status.json']:
  p=RESULTS/name
  if p.exists()and not(pilot/name).exists():p.rename(pilot/name)
 if(RESULTS/'host-before.txt').exists()and not(RESULTS/'host-before-m1.txt').exists():(RESULTS/'host-before.txt').rename(RESULTS/'host-before-m1.txt')
 # Only metadata is added; request/response objects and strings are unchanged.
 for p in list((pilot/'writers').glob('*.jsonl'))+[pilot/'judge-attempts.jsonl',RESULTS/'diagnostic/requests.jsonl']:
  if p.exists():
   rows=read(p)
   for row in rows:row.setdefault('serving_hardware',M1)
   p.write_text(''.join(json.dumps(r)+'\n'for r in rows))
 events=read(RESULTS/'host-events.jsonl')
 for row in events:row.setdefault('serving_hardware',M1)
 (RESULTS/'host-events.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in events))
 models=json.loads((ROOT/'models.json').read_text());target.setup();copied=[]
 try:
  for m in models:
   filename=m['id']+'.gguf';size=source.ssh('test -f '+LAB+'/'+filename+' && stat -f %z '+LAB+'/'+filename,False).strip()
   if not size or int(size)!=m['bytes']:continue
   exists=target.ssh('test -f '+LAB+'/'+filename+' && stat -f %z '+LAB+'/'+filename,False).strip()
   if exists!=size:
    p=subprocess.run(['scp','-3','-q',source.target+':membench-extraction-tmp/'+filename,target.target+':membench-extraction-tmp/'+filename],capture_output=True,text=True,timeout=900)
    if p.returncode:raise RuntimeError('Weight transfer failed: '+target.clean(p.stderr[-500:]))
   sha=target.ssh('cd '+LAB+' && shasum -a 256 '+shlex.quote(filename)).split()[0];assert sha==m['sha256'];copied.append({'model':m['id'],'bytes':m['bytes'],'sha256':sha});print('transferred-and-verified',m['id'],flush=True)
  # Remove the old serving scratch before any inference starts on the new host.
  source.close(cleanup=True)
  (RESULTS/'host-after.txt').rename(RESULTS/'host-after-m1.txt');(RESULTS/'cleanup.json').rename(RESULTS/'cleanup-m1.json')
  before=(RESULTS/'host-before-m1.txt').read_text();after=(RESULTS/'host-after-m1.txt').read_text()
  def listeners(text):return{int(m[2]):int(m[1])for m in re.finditer(r'listener \S+ pid=(\d+) port=(\d+)',text)}
  a=listeners(before);b=listeners(after);voice=[8200,8202,8300,7860,7861,7862]
  proof={'source_hardware':M1,'target_hardware':M3,'quality_pooled_across_hardware':False,'main_run_restarts_all_9000_requests_on_M3':True,'source_cleanup':json.loads((RESULTS/'cleanup-m1.json').read_text()),'source_task_port_unused':PORT not in b,'source_voice_listener_pids_unchanged':all(a.get(p)is not None and a.get(p)==b.get(p)for p in voice),'source_voice_before':{str(p):a.get(p)for p in voice},'source_voice_after':{str(p):b.get(p)for p in voice},'transferred_weights':copied}
  (RESULTS/'migration.json').write_text(json.dumps(proof,indent=2)+'\n');assert proof['source_task_port_unused']
  # Fifty preselected paired requests, balanced over the two source datasets.
  old=[r for r in read(pilot/'writers/qwen3.5-4b-q4_k_m-repeat-1.1.jsonl')if r['seed']==7];sample={r['id']:r for r in json.loads((ROOT/'data/sample.json').read_text())};rng=random.Random(20261127);selected=[]
  for dataset in ['LoCoMo','LongMemEval']:selected+=rng.sample([r for r in old if sample[r['id']]['dataset']==dataset],25)
  (RESULTS/'hardware-overlap-plan.json').write_text(json.dumps({'seed':20261127,'writer':'qwen3.5-4b-q4_k_m','decoder_repeat_penalty':1.1,'extraction_seed':7,'N':50,'selection':'25 random turns per dataset from completed M1 seed-7 cell, selected before M3 overlap inference','ids':[r['id']for r in selected]},indent=2)+'\n')
  target.load(next(m for m in models if m['id']=='qwen3.5-4b-q4_k_m'))
  path=RESULTS/'hardware-overlap.jsonl';done={r['id']for r in read(path)}
  def one(old):
   if old['id']in done:return
   raw,sec=request(old['request'],target);valid,parsed,error=validate(raw)
   row={'id':old['id'],'seed':7,'model':old['model'],'serving_hardware':M3,'comparison_hardware':M1,'request':old['request'],'response':raw,'seconds':sec,'valid':valid,'parsed':parsed,'validation_error':error,'m1_seconds':old['seconds'],'m1_response':old['response'],'exact_content_match':raw['choices'][0]['message']['content']==old['response']['choices'][0]['message']['content'],'parsed_object_match':parsed==old['parsed']and valid==old['valid']}
   append(path,row);print('overlap',old['id'],row['exact_content_match'],flush=True)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(one,selected))
  rows=read(path);summary={'N':len(rows),'exact_content_matches':sum(r['exact_content_match']for r in rows),'parsed_object_matches':sum(r['parsed_object_match']for r in rows),'source_hardware':M1,'target_hardware':M3,'quality_pooled':False,'timing_pooled':False,'separate_subset_median_seconds':{M1:statistics.median(r['m1_seconds']for r in rows),M3:statistics.median(r['seconds']for r in rows)},'difference_ids':[r['id']for r in rows if not r['exact_content_match']]};(RESULTS/'hardware-overlap-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
 finally:target.close(cleanup=False)
if __name__=='__main__':run()

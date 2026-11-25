"""Clustered bootstrap intervals preserve seed and conversation dependence."""
import collections,hashlib,json,math,random,statistics
from bench import ROOT,read
from judge import claims,PROMPT_HASH,decision_key

def wilson(k,n):
 z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return [max(0,c-h),min(1,c+h)]
def percentile(a,p):
 a=sorted(a);x=(len(a)-1)*p;i=int(x);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
def metrics(rows):
 n=len(rows);facts=sum(r['fact_count']for r in rows);refs=sum(r['reference_count']for r in rows)
 return {'valid_rate':sum(r['valid']for r in rows)/n,'facts_per_turn':facts/n,'precision':sum(r['supported']for r in rows)/facts if facts else 0,'recall':sum(r['covered']for r in rows)/refs,'contradiction_rate':sum(r['contradicted']for r in rows)/facts if facts else 0,'median_seconds':statistics.median(r['seconds']for r in rows)}
def bootstrap(rows,repeats=2000):
 groups=collections.defaultdict(lambda:collections.defaultdict(list))
 for r in rows:groups[r['dataset']][r['cluster']].append(r)
 groups={d:list(v.values())for d,v in groups.items()};rng=random.Random(20261124);samples=collections.defaultdict(list)
 for _ in range(repeats):
  chosen=[]
  for clusters in groups.values():
   for cluster in rng.choices(clusters,k=len(clusters)):chosen.extend(cluster)
  for key,value in metrics(chosen).items():samples[key].append(value)
 return {k:[percentile(v,.025),percentile(v,.975)]for k,v in samples.items()}

def run():
 sample={r['id']:r for r in json.loads((ROOT/'data/sample.json').read_text())};cache={r['hash']:r for r in read(ROOT/'results/judge-cache.jsonl')};scored=[]
 for file in sorted((ROOT/'results/writers').glob('*.jsonl')):
  for r in read(file):
   item=sample[r['id']];pred=claims(r);source=item['speaker']+' says: '+item['text'];key=decision_key(source,pred,item['reference_facts'],item['speaker'])
   d=cache.get(key)
   if pred and not d:raise RuntimeError('Unscored nonempty writer output')
   scored.append({'arm':r['arm'],'model':r['model'],'seed':r['seed'],'id':r['id'],'dataset':item['dataset'],'cluster':item['cluster'],'stratum':item['stratum'],'valid':r['valid'],'fact_count':len(pred),'supported':len(d['support']['supported'])if d else 0,'contradicted':len(d['support']['contradicted'])if d else 0,'covered':len(d['coverage']['supported'])if d else 0,'reference_count':len(item['reference_facts']),'seconds':r['seconds'],'serving_hardware':r['serving_hardware'],'serving_instance':r['serving_instance'],'judge_hash':key if pred else None})
 (ROOT/'results/scored.json').write_text(json.dumps(scored,indent=2)+'\n');summaries=[]
 for arm in sorted({r['arm']for r in scored}):
  rr=[r for r in scored if r['arm']==arm];unique={r['id']for r in rr};assert len(rr)==900 and len(unique)==300 and set(r['seed']for r in rr)=={7,19,43}
  assert {r['serving_hardware']for r in rr}=={'Apple M3 Ultra, 96 GB'}and {r['serving_instance']for r in rr}=={'M3 main'}
  summary={'serving_hardware':'Apple M3 Ultra, 96 GB','arm':arm,'requests':len(rr),'unique_turns':len(unique),'valid':sum(r['valid']for r in rr),'written_facts':sum(r['fact_count']for r in rr),'supported':sum(r['supported']for r in rr),'reference_instances':sum(r['reference_count']for r in rr),'covered':sum(r['covered']for r in rr),'contradicted':sum(r['contradicted']for r in rr),'metrics':metrics(rr),'ci95':bootstrap(rr),'by_seed':{str(seed):{'metrics':metrics([r for r in rr if r['seed']==seed]),'ci95':bootstrap([r for r in rr if r['seed']==seed])}for seed in (7,19,43)},'by_dataset':{ds:{'metrics':metrics([r for r in rr if r['dataset']==ds]),'ci95':bootstrap([r for r in rr if r['dataset']==ds])}for ds in ('LoCoMo','LongMemEval')}}
  # Greedy repeats are reported, never treated as independent examples.
  raw=read(ROOT/'results/writers'/f'{arm}.jsonl');texts=collections.defaultdict(set)
  for r in raw:texts[r['id']].add(r['response']['choices'][0]['message'].get('content'))
  summary['turns_with_seed_output_variation']=sum(len(v)>1 for v in texts.values());summaries.append(summary)
 (ROOT/'results/summary.json').write_text(json.dumps({'interval_method':'2,000 percentile stratified cluster bootstrap replicates, seed 20261124. LoCoMo resamples 10 conversation clusters; LongMemEval resamples 150 question clusters. All three seeds of each selected item remain together. Degenerate empirical intervals at boundaries cannot estimate unseen errors.','models':summaries},indent=2)+'\n')
 gate=json.loads((ROOT/'results/judge-validation-summary.json').read_text());gate['wilson95']=wilson(gate['correct'],gate['N']);gate['support_binary_correct']=sum((r['actual']=='supported')==(r['expected']=='supported')for r in read(ROOT/'results/judge-validation.jsonl'));(ROOT/'results/judge-validation-summary.json').write_text(json.dumps(gate,indent=2)+'\n')
 print('Summaries and clustered intervals complete',flush=True)
 import paired,verify,final_cleanup_check,write_report,audit_actual_outputs
 paired.run();verify.run();audit_actual_outputs.run();final_cleanup_check.run();write_report.run()
if __name__=='__main__':run()

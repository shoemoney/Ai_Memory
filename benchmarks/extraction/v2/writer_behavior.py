"""Post-run descriptive empty-output audit; no additional model calls."""
import collections,json,random
from bench import ROOT
from analyze import percentile

def run():
 rows=json.loads((ROOT/'results/scored.json').read_text());out=[]
 for arm in sorted({r['arm']for r in rows}):
  rr=[r for r in rows if r['arm']==arm];groups=collections.defaultdict(lambda:collections.defaultdict(list))
  for r in rr:groups[r['dataset']][r['cluster']].append(r)
  groups=[list(g.values())for g in groups.values()];rng=random.Random(20261124);rates=[]
  for _ in range(2000):
   chosen=[r for g in groups for cluster in rng.choices(g,k=len(g))for r in cluster]
   rates.append(sum(r['valid']and r['fact_count']==0 for r in chosen)/len(chosen))
  empty=[r for r in rr if r['valid']and r['fact_count']==0]
  out.append({'arm':arm,'N':len(rr),'valid_empty_arrays':len(empty),'empty_rate':len(empty)/len(rr),'empty_rate_cluster_ci95':[percentile(rates,.025),percentile(rates,.975)],'empty_arrays_on_reference_bearing_turns':sum(r['reference_count']>0 for r in empty),'reference_instances_in_empty_turns':sum(r['reference_count']for r in empty),'all_reference_instances':sum(r['reference_count']for r in rr),'empty_ids_seed7':[r['id']for r in empty if r['seed']==7]})
 result={'description':'Post-run descriptive audit explaining coverage; valid empty arrays are permitted by the frozen schema and are not syntax failures. No causal internal-model diagnosis is inferred.','interval_method':'Same 2,000 stratified source-cluster bootstrap draws as primary summaries; all seeds remain together.','models':out};(ROOT/'results/writer-behavior.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':run()

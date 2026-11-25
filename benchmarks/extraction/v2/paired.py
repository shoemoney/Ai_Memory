"""Paired cluster bootstrap differences; same source draws for both arms."""
import collections,json,random
from analyze import metrics,percentile
from bench import ROOT

def run():
 rows=json.loads((ROOT/'results/scored.json').read_text());arms=collections.defaultdict(dict)
 for r in rows:arms[r['arm']][(r['id'],r['seed'])]=r
 clusters=collections.defaultdict(lambda:collections.defaultdict(list))
 for key,r in next(iter(arms.values())).items():clusters[r['dataset']][r['cluster']].append(key)
 groups=[list(d.values())for d in clusters.values()];out=[]
 pairs=[('empero-qwen3.8-4b-q4_k_m','empero-qwen3.8-2b-q4_k_m'),('empero-qwen3.8-9b-q4_k_m','empero-qwen3.8-4b-q4_k_m'),('coder-edited-q4_k_m','coder-stock-q4_k_m'),('qwen3.5-4b-q4_k_m-repeat-1.1','qwen3.5-4b-q4_k_m')]
 for a,b in pairs:
  keys=list(arms[a]);assert set(keys)==set(arms[b]);ma=metrics(list(arms[a].values()));mb=metrics(list(arms[b].values()));samples=collections.defaultdict(list);rng=random.Random(20261126)
  for _ in range(2000):
   chosen=[key for group in groups for cluster in rng.choices(group,k=len(group))for key in cluster];va=metrics([arms[a][key]for key in chosen]);vb=metrics([arms[b][key]for key in chosen])
   for metric in va:samples[metric].append(va[metric]-vb[metric])
  out.append({'a_minus_b':[a,b],'difference':{k:ma[k]-mb[k]for k in ma},'ci95':{k:[percentile(v,.025),percentile(v,.975)]for k,v in samples.items()}})
 (ROOT/'results/paired-differences.json').write_text(json.dumps({'method':'2,000 paired percentile stratified cluster bootstrap replicates, seed 20261126; all seeds stay together. Descriptive file comparisons, not causal editing effects.','pairs':out},indent=2)+'\n')
if __name__=='__main__':run()

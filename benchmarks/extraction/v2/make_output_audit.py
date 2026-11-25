"""Preselect 60 real seed-7 matching pairs, before local semantic scoring."""
import hashlib,json,random
from bench import ROOT,read
from judge import claims,PROMPT_HASH,decision_key,coverage_text

def run():
 path=ROOT/'data/actual-output-audit-inputs.json'
 if path.exists():raise RuntimeError('Audit selection already frozen; do not overwrite after reviewing labels')
 files=sorted((ROOT/'results/writers').glob('*.jsonl'));assert len(files)==10
 sample={r['id']:r for r in json.loads((ROOT/'data/sample.json').read_text())};jobs={}
 for file in files:
  rows=[r for r in read(file)if r['seed']==7];assert len(rows)==300
  for row in rows:
   item=sample[row['id']];pred=claims(row)
   if not pred:continue
   source=item['speaker']+' says: '+item['text'];refs=item['reference_facts'];key=hashlib.sha256(json.dumps([source,pred,refs,PROMPT_HASH]).encode()).hexdigest()
   jobs.setdefault(key,(source,pred,refs,item['speaker']))
 pairs=[]
 for legacy,(source,pred,refs,speaker)in sorted(jobs.items()):
  key=decision_key(source,pred,refs,speaker)
  for kind,hypotheses,premise in [('support',pred,source),('coverage',refs,coverage_text(pred,speaker))]:
   for i,hypothesis in enumerate(hypotheses):pairs.append({'legacy_hash':legacy,'source_speaker':speaker,'hash':key,'kind':kind,'hypothesis_index':i,'premise':premise,'hypothesis':hypothesis})
 chosen=random.Random(20261125).sample(pairs,60)
 for i,r in enumerate(chosen):r['audit_index']=i
 out={'seed':20261125,'population_pairs':len(pairs),'population_unique_inputs':len(jobs),'sampling':'Uniform random 60 hypothesis pairs among unique source/prediction/reference inputs from all ten completed seed-7 writer cells; selected before semantic scoring. Manual review display excludes judge decisions.','reference_labels':'To be manually authored by implementing agent; not independent human adjudication.','pairs':chosen}
 path.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k!='pairs'},indent=2))
if __name__=='__main__':run()

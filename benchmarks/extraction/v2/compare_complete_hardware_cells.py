"""Additional paired comparisons of whole cells measured on both hosts."""
import json
from bench import ROOT,read
from analyze import wilson

def run():
 out=[]
 for arm in ['qwen3.5-9b-q4_k_m','empero-qwen3.8-2b-q4_k_m']:
  old={r['id']:r for r in read(ROOT/'results/m1-pilot/writers'/f'{arm}.jsonl')if r['seed']==7};new={r['id']:r for r in read(ROOT/'results/writers'/f'{arm}.jsonl')if r['seed']==7}
  assert len(old)==len(new)==300 and set(old)==set(new)
  exact=0;validity=0;parsed=0;both=0;differences=[]
  for item_id,a in old.items():
   b=new[item_id];assert a['request']==b['request']
   same=a['response']['choices'][0]['message']['content']==b['response']['choices'][0]['message']['content'];exact+=same;validity+=a['valid']==b['valid'];both+=a['valid']and b['valid'];parsed+=a['valid']and b['valid']and a['parsed']==b['parsed']
   if not same:differences.append({'id':item_id,'m1_valid':a['valid'],'m3_valid':b['valid'],'both_valid_parsed_equal':a['valid']and b['valid']and a['parsed']==b['parsed']})
  out.append({'arm':arm,'seed':7,'N':300,'exact_content_matches':exact,'exact_content_match_nominal_wilson95':wilson(exact,300),'same_validity_decisions':validity,'m1_valid':sum(r['valid']for r in old.values()),'m3_valid':sum(r['valid']for r in new.values()),'both_valid':both,'parsed_matches_among_both_valid':parsed,'differences':differences})
 result={'source_hardware':'Apple M1 Ultra, 64 GB','target_hardware':'Apple M3 Ultra, 96 GB','target_instance':'M3 main','main_quality_and_timing_use_only_M3':True,'interpretation':'Observed paired run differences can reflect hardware and concurrent numerical execution; this does not isolate a causal hardware effect. No timing is pooled. All M1 measurements are retained in the pilot.','cells':out}
 (ROOT/'results/additional-hardware-comparisons.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':run()

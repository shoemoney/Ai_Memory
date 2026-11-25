"""Verify actual raw responses, links and frozen input boundaries."""
import collections,hashlib,json
from bench import ROOT,check_lock,digest,read,validate
from judge import claims,PROMPT_HASH,decision_key,coverage_text

def run():
 check_lock();sample={r['id']:r for r in json.loads((ROOT/'data/sample.json').read_text())};attempts=read(ROOT/'results/judge-attempts.jsonl');byattempt={r['attempt_id']:r for r in attempts};assert len(byattempt)==len(attempts)
 for a in attempts:
  assert a['serving_hardware']=='Apple M3 Ultra, 96 GB'and a['serving_instance']=='M3 main'and a['prompt_sha256']==PROMPT_HASH
  b=a['request'];assert b['temperature']==0 and b['seed']==7 and b['max_tokens']==256 and b['cache_prompt']is False and b['chat_template_kwargs']=={'enable_thinking':False}
 cache=read(ROOT/'results/judge-cache.jsonl');keys=set();links=0
 for r in cache:
  key=decision_key(r['source'],r['predictions'],r['references'],r['source_speaker']);assert key==r['hash']and key not in keys;keys.add(key)
  for kind in ('support','coverage'):
   d=r[kind]
   if d['attempt_id']is None:assert kind=='coverage'and not r['references'];continue
   a=byattempt[d['attempt_id']];p=a['input'];assert p['premise']==(r['source']if kind=='support'else coverage_text(r['predictions'],r['source_speaker']))
   assert [v['claim']for v in p['hypotheses']]==(r['predictions']if kind=='support'else r['references'])
   decision=json.loads(a['response']['choices'][0]['message']['content']);assert decision['supported']==d['supported']and decision['contradicted']==d['contradicted'];links+=1
 rows=[];counts={};usage={}
 for file in sorted((ROOT/'results/writers').glob('*.jsonl')):
  rr=read(file);counts[file.stem]=len(rr);assert len(rr)==900 and len({(r['seed'],r['id'])for r in rr})==900
  for r in rr:
   assert r['serving_hardware']=='Apple M3 Ultra, 96 GB'and r['serving_instance']=='M3 main'and r['runtime_sha256']==digest(ROOT/'runtime-lock.json')
   valid,value,error=validate(r['response']);assert r['valid']==valid and r['parsed']==value
   item=sample[r['id']];b=r['request'];assert b['messages'][0]['content']==(ROOT/'writer_prompt.txt').read_text()
   assert json.loads(b['messages'][1]['content'])=={'speaker':item['speaker'],'turn':item['text']}
   assert b['response_format']['json_schema']['schema']==json.loads((ROOT/'writer_schema.json').read_text())
   assert b['max_tokens']==1024 and b['temperature']==0 and b['cache_prompt']is False and b['chat_template_kwargs']=={'enable_thinking':False}
   assert b['repeat_penalty']==(1.1 if r['arm'].endswith('-repeat-1.1')else 1.0)
   assert r['protocol_sha256']==digest(ROOT/'protocol-lock.json')and r['sample_sha256']==digest(ROOT/'data/sample.json')
   assert r['seconds']>0
  usage[file.stem]={'system_fingerprints':sorted({r['response'].get('system_fingerprint')for r in rr}),'finish_reasons':dict(collections.Counter(r['response']['choices'][0]['finish_reason']for r in rr)),'reasoning_characters':sum(len(r['response']['choices'][0]['message'].get('reasoning_content')or '')for r in rr),'nonzero_cached_token_responses':sum(bool(r['response'].get('usage',{}).get('prompt_tokens_details',{}).get('cached_tokens',0))for r in rr),'maximum_cached_tokens':max(r['response'].get('usage',{}).get('prompt_tokens_details',{}).get('cached_tokens',0)for r in rr),'completion_tokens':sum(r['response'].get('usage',{}).get('completion_tokens',0)for r in rr)}
  rows.extend(rr)
 assert len(counts)==10 and len(rows)==9000
 result={'requests':len(rows),'arms':counts,'unique_turns':len(sample),'all_actual_acceptance_decisions_recomputed':True,'frozen_prompt_schema_sample_match':True,'source_only_writer_inputs_verified':True,'source_absent_from_coverage_by_construction_verified':True,'unique_judge_inputs':len(cache),'immutable_judge_attempt_links_verified':links,'all_attempt_ids_unique':True,'usage':usage}
 (ROOT/'results/verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='usage'},indent=2))
if __name__=='__main__':run()

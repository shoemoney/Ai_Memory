"""Separate source-support and reference-coverage calls; local 9B judge."""
import concurrent.futures,hashlib,json,os,uuid
from bench import ROOT,append,read,request
PROMPT=(ROOT/'judge_prompt.txt').read_text()
PROMPT_HASH=hashlib.sha256(PROMPT.encode()).hexdigest()


MATCHING_VERSION='speaker-bound-v2'
def coverage_text(predictions,speaker):
 return ('These written memory records are for input speaker identifier '+speaker+'.\n'
  'In these records, unqualified I/me/my, you/your, and "the speaker" refer to '+speaker+'. Explicitly named other subjects remain distinct. Plural groups remain plural.\n'
  'Written records:\n'+'\n'.join(predictions))
def decision_key(source,pred,refs,speaker):
 return hashlib.sha256(json.dumps([source,pred,refs,PROMPT_HASH,MATCHING_VERSION,speaker]).encode()).hexdigest()

def classify(premise,hypotheses,host=None):
 lock=json.loads((ROOT/'judge-protocol-lock.json').read_text());assert lock['prompt_sha256']==PROMPT_HASH
 assert hashlib.sha256((ROOT/'data/judge-validation.json').read_bytes()).hexdigest()==lock['validation_sha256']
 if not hypotheses:return {'supported':[],'contradicted':[],'attempt_id':None}
 schema={'type':'object','additionalProperties':False,'required':['supported','contradicted'],'properties':{k:{'type':'array','uniqueItems':True,'maxItems':len(hypotheses),'items':{'type':'integer','enum':list(range(len(hypotheses)))}}for k in ('supported','contradicted')}}
 payload={'premise':premise,'hypotheses':[{'index':i,'claim':v}for i,v in enumerate(hypotheses)]}
 b={'model':'writer','messages':[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(payload)}],'temperature':0,'seed':7,'max_tokens':256,'cache_prompt':False,'chat_template_kwargs':{'enable_thinking':False},'response_format':{'type':'json_schema','json_schema':{'name':'entailment','strict':True,'schema':schema}}}
 for retry in range(3):
  raw,sec=request(b,host);attempt_id=uuid.uuid4().hex
  append(ROOT/'results/judge-attempts.jsonl',{'serving_hardware':host.hardware if host else os.environ.get('SERVING_HARDWARE','unspecified'),'serving_instance':host.instance if host else os.environ.get('SERVING_INSTANCE','unspecified'),'attempt_id':attempt_id,'input':payload,'request':b,'response':raw,'seconds':sec,'prompt_sha256':PROMPT_HASH})
  try:
   c=raw['choices'][0];assert c['finish_reason']=='stop'and not c['message'].get('reasoning_content')
   d=json.loads(c['message']['content']);assert set(d)=={'supported','contradicted'}
   for values in d.values():assert isinstance(values,list)and len(set(values))==len(values)and all(type(v)is int and 0<=v<len(hypotheses)for v in values)
   assert not set(d['supported'])&set(d['contradicted'])
   return {**d,'attempt_id':attempt_id}
  except (ValueError,KeyError,TypeError,AssertionError):
   if retry==2:raise RuntimeError('Judge repeatedly returned invalid decision')from None

def validate(host):
 items=json.loads((ROOT/'data/judge-validation.json').read_text());path=ROOT/'results/judge-validation.jsonl';old={r['id']:r for r in read(path)}
 for row in items:
  if row['id']in old:continue
  premise=row['premise']
  if row['kind']=='coverage':premise=coverage_text([premise],json.loads((ROOT/'data/sample.json').read_text())[row['source_index']]['speaker'])
  d=classify(premise,[row['hypothesis']],host);label='supported'if d['supported']else 'contradicted'if d['contradicted']else 'unknown'
  append(path,{**row,'decision':d,'actual':label,'correct':label==row['expected']});print('judge-validation',row['id'],label,row['expected'],flush=True)
 rows=read(path);n=len(rows);k=sum(r['correct']for r in rows)
 result={'support_binary_correct':sum((r['actual']=='supported')==(r['expected']=='supported')for r in rows),'matching_version':MATCHING_VERSION,'N':n,'correct':k,'agreement':k/n,'threshold':54,'pass':n==60 and k>=54,'judge':'Qwen3.5-9B Q4_K_M','serving_hardware':host.hardware,'serving_instance':host.instance,'prompt_sha256':PROMPT_HASH,'reference_labels':'Direct manual inspection by the implementing agent; not an independent human review','by_expected':{key:{'N':sum(r['expected']==key for r in rows),'correct':sum(r['expected']==key and r['correct']for r in rows)}for key in ('supported','contradicted','unknown')}}
 (ROOT/'results/judge-validation-summary.json').write_text(json.dumps(result,indent=2)+'\n')
 if not result['pass']:raise RuntimeError('Judge agreement gate failed; semantic scores withheld')

def claims(row):
 if not row['valid']:return []
 return [v['fact']+' [subject: '+v['subject']+'; date: '+v['date']+']'for v in row['parsed']]

def score(host):
 gate=json.loads((ROOT/'results/judge-validation-summary.json').read_text());assert gate['pass']and gate['prompt_sha256']==PROMPT_HASH and gate['matching_version']==MATCHING_VERSION
 sample={r['id']:r for r in json.loads((ROOT/'data/sample.json').read_text())}
 cachepath=ROOT/'results/judge-cache.jsonl';cache={r['hash']:r for r in read(cachepath)}
 # Build a deterministic unique work list before issuing concurrent requests.
 jobs={}
 for file in sorted((ROOT/'results/writers').glob('*.jsonl')):
  for row in read(file):
   item=sample[row['id']];pred=claims(row)
   if not pred:continue
   source=item['speaker']+' says: '+item['text'];refs=item['reference_facts'];key=decision_key(source,pred,refs,item['speaker'])
   if key not in cache and key not in jobs:jobs[key]=(source,pred,refs,file.stem,row['id'],item['speaker'])
 def one(job):
  key,(source,pred,refs,arm,item_id,speaker)=job
  support=classify(source,pred,host)
  # Coverage receives only accepted written claims, never the original turn.
  coverage=classify(coverage_text(pred,speaker),refs,host)
  result={'source_speaker':speaker,'matching_version':MATCHING_VERSION,'hash':key,'source':source,'predictions':pred,'references':refs,'support':support,'coverage':coverage,'prompt_sha256':PROMPT_HASH}
  append(cachepath,result);print('judged',key[:12],arm,item_id,flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(one,jobs.items()))

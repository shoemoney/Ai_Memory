"""Exact Chapter 06 schema, prompt prefix, generation and local matching."""
import argparse, collections, hashlib, json, os, statistics, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SCHEMA={'type':'object','additionalProperties':False,'properties':{k:{'type':'string'} for k in ('name','city','likes')},'required':['name','city','likes']}
SEEDS=(7,19,43)

def request(body):
    req=urllib.request.Request(os.environ.get('BASE_URL','http://localhost:39740/v1').rstrip('/')+'/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
    start=time.perf_counter()
    with urllib.request.urlopen(req,timeout=180) as response: result=json.load(response)
    return result,time.perf_counter()-start

def body(text,seed,schema=SCHEMA):
    return {'model':'extractor','temperature':0,'seed':seed,'max_tokens':512,
      'messages':[{'role':'user','content':text}],
      'response_format':{'type':'json_schema','json_schema':{'name':'facts','strict':True,'schema':schema}},
      'chat_template_kwargs':{'enable_thinking':False}}

def unique_keys(pairs):
    result={}
    for k,v in pairs:
        if k in result: raise ValueError('Duplicate key')
        result[k]=v
    return result

def validate(response):
    choice=response['choices'][0]; msg=choice['message']
    parsed=json.loads(msg['content'],object_pairs_hook=unique_keys)
    syntax=True
    schema=isinstance(parsed,dict) and set(parsed)==set(SCHEMA['required']) and all(isinstance(v,str) for v in parsed.values())
    accepted=schema and choice.get('finish_reason')=='stop' and not msg.get('refusal') and not msg.get('reasoning_content')
    return parsed,syntax,schema,accepted

def run(model):
    outdir=ROOT/'results'; outdir.mkdir(exist_ok=True)
    path=outdir/(model+'.jsonl')
    done=set()
    if path.exists(): done={(r['seed'],r['id']) for r in map(json.loads,path.read_text().splitlines())}
    sample=json.loads((ROOT/'data/sample.json').read_text())
    with path.open('a') as out:
        for seed in SEEDS:
            # Same deterministic shuffled item order for every model, seed-specific.
            import random
            items=list(sample); random.Random(seed).shuffle(items)
            for item in items:
                if (seed,item['id']) in done: continue
                prompt='Extract facts: '+item['speaker']+' says: '+item['text']
                row={'model':model,'seed':seed,'id':item['id'],'request':body(prompt,seed)}
                try:
                    result,seconds=request(row['request']); row.update(response=result,seconds=seconds)
                    try:
                        parsed,syntax,schema,accepted=validate(result)
                        row.update(parsed=parsed,valid_json=syntax,valid_schema=schema,accepted=accepted)
                    except (ValueError,KeyError,TypeError) as e:
                        row.update(valid_json=False,valid_schema=False,accepted=False,validation_error=str(e))
                except Exception as e:
                    row.update(error=type(e).__name__+': '+str(e),valid_json=False,valid_schema=False,accepted=False)
                out.write(json.dumps(row)+'\n'); out.flush()
                print(model,seed,item['id'],row.get('seconds'),row['accepted'],flush=True)

def summary():
    rows=[]
    for path in sorted((ROOT/'results').glob('*.jsonl')):
        if path.name.startswith('judge'): continue
        rr=[json.loads(s) for s in path.read_text().splitlines()]
        if not rr or 'valid_json' not in rr[0]: continue
        times=[r['seconds'] for r in rr if 'seconds' in r]
        rows.append({'model':path.stem,'requests':len(rr),'items':len({r['id'] for r in rr}),
          'valid_json':sum(r['valid_json'] for r in rr),'valid_schema':sum(r['valid_schema'] for r in rr),
          'accepted':sum(r['accepted'] for r in rr),'median_seconds':statistics.median(times) if times else None,
          'mean_seconds':statistics.mean(times) if times else None,'seeds':sorted({r['seed'] for r in rr}),
          'per_seed':[{'seed':seed,'N':sum(r['seed']==seed for r in rr),
             'valid_json':sum(r['valid_json'] for r in rr if r['seed']==seed),
             'accepted':sum(r['accepted'] for r in rr if r['seed']==seed),
             'median_seconds':statistics.median([r['seconds'] for r in rr if r['seed']==seed and 'seconds' in r]),
             'mean_seconds':statistics.mean([r['seconds'] for r in rr if r['seed']==seed and 'seconds' in r])}
             for seed in sorted({r['seed'] for r in rr})]})
    (ROOT/'results/summary.json').write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(rows,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('command',choices=['run','summary']); p.add_argument('--model'); a=p.parse_args()
    if a.command=='run': run(a.model)
    else: summary()

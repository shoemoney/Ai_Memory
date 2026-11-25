"""Evidence integrity checks, separate from the generation loop."""
import collections,hashlib,json,statistics
from pathlib import Path
from bench import ROOT,SCHEMA,SEEDS

def main():
    sample={r['id']:r for r in json.loads((ROOT/'data/sample.json').read_text())}
    models=json.loads((ROOT/'models.json').read_text()); details=[]
    for m in models:
        path=ROOT/'results'/(m['id']+'.jsonl')
        if not path.exists(): details.append({'model':m['id'],'complete':False,'reason':'No output file'}); continue
        rows=[json.loads(l) for l in path.read_text().splitlines()]
        keys=[(r['seed'],r['id']) for r in rows]
        assert len(keys)==len(set(keys)), 'Duplicate extraction trial'
        complete=set(keys)=={(seed,id) for seed in SEEDS for id in sample}
        for r in rows:
            item=sample[r['id']]; b=r['request']
            assert b['messages']==[{'role':'user','content':'Extract facts: '+item['speaker']+' says: '+item['text']}]
            assert b['response_format']['json_schema']['schema']==SCHEMA
            assert b['temperature']==0 and b['max_tokens']==512 and b['seed']==r['seed']
            assert b['chat_template_kwargs']['enable_thinking'] is False
        usage=[r['response']['usage'] for r in rows if 'response'in r]
        same=0
        for id in sample:
            outputs=[r['response']['choices'][0]['message']['content'] for r in rows if r['id']==id and 'response'in r]
            same+=len(outputs)==3 and len(set(outputs))==1
        details.append({'model':m['id'],'complete':complete,'N_unique':len({r['id'] for r in rows}), 'trials':len(rows),
          'identical_output_in_all_three_seeds':same,'finish_reasons':dict(collections.Counter(r['response']['choices'][0]['finish_reason'] for r in rows if 'response'in r)),
          'reasoning_characters':sum(len(r['response']['choices'][0]['message'].get('reasoning_content','')) for r in rows if 'response'in r),
          'mean_completion_tokens':statistics.mean(u['completion_tokens'] for u in usage) if usage else None,
          'mean_prompt_tokens':statistics.mean(u['prompt_tokens'] for u in usage) if usage else None,
          'mean_cached_prompt_tokens':statistics.mean(u['prompt_tokens_details']['cached_tokens'] for u in usage) if usage and all('cached_tokens'in u.get('prompt_tokens_details',{}) for u in usage) else None,
          'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    attempts={}
    if (ROOT/'results/judge-attempts.jsonl').exists():
        for a in map(json.loads,(ROOT/'results/judge-attempts.jsonl').read_text().splitlines()):
            assert a['id'] not in attempts
            hs=[h['claim'] for h in a['input']['hypotheses']]
            assert [h['index'] for h in a['input']['hypotheses']]==list(range(len(hs)))
            assert a['hash']==hashlib.sha256(json.dumps([a['input']['premise'],hs]).encode()).hexdigest()
            attempts[a['id']]=a
    judged={}
    if (ROOT/'results/judge-cache.jsonl').exists():
        for r in map(json.loads,(ROOT/'results/judge-cache.jsonl').read_text().splitlines()):
            i=r['input']; key=hashlib.sha256(json.dumps([i['source'],i['predictions'],i['references']]).encode()).hexdigest()
            assert key==r['hash']; judged[key]=r
            sa=attempts[r['support_attempt_id']];ca=attempts[r['coverage_attempt_id']]
            assert sa['input']['premise']==i['source']
            assert [h['claim'] for h in sa['input']['hypotheses']]==i['predictions']
            assert ca['input']['premise']=='\n'.join(i['predictions']), 'Coverage received evidence other than extracted claims'
            assert [h['claim'] for h in ca['input']['hypotheses']]==i['references']
            assert json.loads(sa['response']['choices'][0]['message']['content'])['entailed']==r['decision']['supported']
            assert json.loads(ca['response']['choices'][0]['message']['content'])['entailed']==r['decision']['covered']
    if (ROOT/'results/scored.json').exists():
        for r in json.loads((ROOT/'results/scored.json').read_text()):
            assert r['gold_count']==len(sample[r['id']]['gold'])
            assert r['claim_count']==len(r['claims'])
            if r['judge_hash']:
                d=judged[r['judge_hash']]['decision']
                assert r['supported']==len(d['supported']) and r['covered']==len(d['covered'])
            else: assert r['supported']==r['covered']==r['claim_count']==0
    result={'sample_N':len(sample),'reference_units':sum(len(r['gold']) for r in sample.values()),'models':details,'unique_semantic_judge_items':len(judged),'raw_entailment_attempts':len(attempts),'coverage_source_isolation_checked':bool(judged),'mandatory_models_complete':all(r['complete'] for r in details if not r['model'].startswith('gemma')),'all_models_complete':all(r['complete'] for r in details)}
    (ROOT/'results/verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()

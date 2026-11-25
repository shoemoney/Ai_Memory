"""Premise-only local entailment. Recall never receives the source turn."""
import collections, hashlib, json, sys, uuid
from bench import ROOT, request, body
INSTRUCTION='''Decide strict textual entailment from the PREMISE alone.
The hypotheses are candidates, NOT additional premises. Return the explicit zero-based indices of hypotheses fully entailed by the premise. Do not use outside knowledge or unstated context. Equivalent wording is allowed. Preserve subject, attribution, negation, quantity, time, and temporal status. Every listed item, example, activity, ingredient, purpose, or relation in a hypothesis must be entailed. A general category does not entail particular examples. Partial overlap is not full entailment. An offered activity, goal, report about someone else, or praise does not establish a personal preference. Mentioning a city does not establish residence. Return JSON only.'''


def entail(premise,hypotheses):
    if not hypotheses:return {'indices':[],'attempt_hash':None}
    schema={'type':'object','additionalProperties':False,'required':['entailed'],'properties':{'entailed':{'type':'array','maxItems':len(hypotheses),'uniqueItems':True,'items':{'type':'integer','enum':list(range(len(hypotheses)))}}}}
    payload={'premise':premise,'hypotheses':[{'index':i,'claim':v} for i,v in enumerate(hypotheses)]}
    b=body(INSTRUCTION+'\n'+json.dumps(payload),7,schema);b['max_tokens']=256
    raw,seconds=request(b)
    attempt={'id':uuid.uuid4().hex,'input':payload,'request':b,'response':raw,'seconds':seconds}
    key=hashlib.sha256(json.dumps([premise,hypotheses]).encode()).hexdigest();attempt['hash']=key
    with (ROOT/'results/judge-attempts.jsonl').open('a') as out:out.write(json.dumps(attempt)+'\n');out.flush()
    choice=raw['choices'][0]
    if choice['finish_reason']!='stop' or choice['message'].get('reasoning_content'):raise ValueError('Judge incomplete or thinking')
    parsed=json.loads(choice['message']['content'])
    if set(parsed)!=set(('entailed',)):raise ValueError('Bad judge schema')
    values=parsed['entailed']
    if not isinstance(values,list) or any(type(v)!=int or not 0<=v<len(hypotheses) for v in values) or len(values)!=len(set(values)):raise ValueError('Bad judge indices')
    return {'indices':values,'attempt_hash':key,'attempt_id':attempt['id']}


def make_validation():
    sample=json.loads((ROOT/'data/sample.json').read_text())
    specs=[
      (1,'{s} enjoys camping at the beach with family because it brings them closer.','{s} enjoys camping.','{s} dislikes camping with family.'),
      (7,'{s} sets aside time each day for running, reading, or playing the violin.','{s} reads.','{s} never plays the violin.'),
      (8,'{s} is overwhelmed with kids and work.','{s} has work.','{s} has no kids.'),
      (11,'{s} is turning a love of dance into a business and spending time on the studio.','{s} loves dance.','{s} hates dance.'),
      (27,'{s} returned from a family road trip yesterday.','{s} went on a road trip.','{s} returned from the family road trip five years ago.'),
      (45,'{s} joined a travel club and is interested in different cultures and countries.','{s} joined a club.','{s} refuses to join a travel club.'),
      (51,'{s} loves checking out new parks with four dogs.','{s} has dogs.','{s} has only two dogs.'),
      (57,'{s} got new beds for others last week to give them comfort as the weather cools.','{s} got new beds.','{s} got those new beds five years ago.'),
      (60,'{s} is getting into RPGs and strategy games and finds it exciting.','{s} plays games.','{s} dislikes RPGs and strategy games.'),
      (89,'{s} finds being outdoors rejuvenating and plans to spend more time in nature.','{s} finds nature rejuvenating.','{s} plans never to go outdoors again.')]
    rows=[]
    for index,full,partial,wrong in specs:
        r=sample[index]; source=r['speaker']+' says: '+r['text'];full=full.format(s=r['speaker'])
        rows.extend([
          {'id':r['id']+'-supported','kind':'support','premise':source,'hypotheses':[full],'expected':[0]},
          {'id':r['id']+'-incomplete-recall','kind':'coverage','premise':partial.format(s=r['speaker']),'hypotheses':[full],'expected':[]},
          {'id':r['id']+'-unsupported','kind':'support','premise':source,'hypotheses':[wrong.format(s=r['speaker'])],'expected':[]}])
    (ROOT/'data/judge_validation.json').write_text(json.dumps(rows,indent=2)+'\n')


def validate():
    rows=json.loads((ROOT/'data/judge_validation.json').read_text());out=[]
    for row in rows:
        try:result=entail(row['premise'],row['hypotheses'])
        except (ValueError,KeyError,TypeError) as e:result={'indices':None,'error':str(e)}
        result.update(row);result['correct']=result['indices']==row['expected'];out.append(result)
        print(row['id'],result['correct'],flush=True)
        (ROOT/'results/judge-validation.json').write_text(json.dumps(out,indent=2)+'\n')
    exact=sum(r['correct'] for r in out)
    summary={'N':len(out),'correct':exact,'threshold':27,'pass':len(out)==30 and exact>=27,'judge':'Qwen3.5-9B Q4_K_M, thinking off, seed 7, temperature 0','protocol':'Separate premise-only entailment; no source available during reference-coverage checks','by_kind':{kind:{'correct':sum(r['correct'] for r in out if r['kind']==kind),'N':sum(r['kind']==kind for r in out)} for kind in ('support','coverage')}}
    (ROOT/'results/judge-validation-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)


ABSTAIN={'','unknown','none','n/a','not specified','not mentioned','unspecified','not provided','not stated','null'}
def predictions(row):
    if not row['accepted']:return []
    p=row['parsed'];who=p['name'];claims=[]
    for key in ('city','likes'):
        value=p[key].strip()
        if value.lower().strip('. ') in ABSTAIN:continue
        claims.append(who+(' lives in ' if key=='city' else ' likes ')+value+'.')
    return claims


def score():
    gate=json.loads((ROOT/'results/judge-validation-summary.json').read_text())
    if not gate['pass']:raise SystemExit('Judge failed acceptance. Semantic scores withheld.')
    sample={r['id']:r for r in json.loads((ROOT/'data/sample.json').read_text())}
    cachepath=ROOT/'results/judge-cache.jsonl';cache={}
    if cachepath.exists():
        for r in map(json.loads,cachepath.read_text().splitlines()):cache[r['hash']]=r
    rows=[]
    with cachepath.open('a') as out:
        for file in sorted((ROOT/'results').glob('*.jsonl')):
            if file.name.startswith(('judge','memory')):continue
            for row in map(json.loads,file.read_text().splitlines()):
                item=sample[row['id']];pred=predictions(row);source=item['speaker']+' says: '+item['text']
                key=hashlib.sha256(json.dumps([source,pred,item['gold']]).encode()).hexdigest()
                if not pred:d={'supported':[],'covered':[]}
                else:
                    if key not in cache:
                        support=entail(source,pred)
                        # Critical separation: the source is absent from this call.
                        coverage=entail('\n'.join(pred),item['gold'])
                        result={'hash':key,'input':{'source':source,'predictions':pred,'references':item['gold']},'decision':{'supported':support['indices'],'covered':coverage['indices']},'support_attempt_hash':support['attempt_hash'],'coverage_attempt_hash':coverage['attempt_hash'],'support_attempt_id':support['attempt_id'],'coverage_attempt_id':coverage['attempt_id']}
                        cache[key]=result;out.write(json.dumps(result)+'\n');out.flush();print('judged',len(cache),file.stem,row['id'],flush=True)
                    d=cache[key]['decision']
                rows.append({'model':row['model'],'seed':row['seed'],'id':row['id'],'claims':pred,'claim_count':len(pred),'supported':len(d['supported']),'gold_count':len(item['gold']),'covered':len(d['covered']),'judge_hash':key if pred else None})
    (ROOT/'results/scored.json').write_text(json.dumps(rows,indent=2)+'\n')
    summaries=[]
    for model in sorted({r['model'] for r in rows}):
        groups=[]
        for seed in (7,19,43):
            rr=[r for r in rows if r['model']==model and r['seed']==seed];c=collections.Counter()
            for r in rr:
                for k in ('claim_count','supported','gold_count','covered'):c[k]+=r[k]
            groups.append({'seed':seed,'N':len(rr),**c,'precision':c['supported']/c['claim_count'] if c['claim_count'] else None,'recall':c['covered']/c['gold_count'] if c['gold_count'] else None})
        summaries.append({'model':model,'per_seed':groups})
    (ROOT/'results/semantic-summary.json').write_text(json.dumps(summaries,indent=2)+'\n');print(json.dumps(summaries,indent=2))

if __name__=='__main__':{'prepare':make_validation,'validate':validate,'score':score}[sys.argv[1]]()

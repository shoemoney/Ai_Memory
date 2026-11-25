"""Small, fully local LongMemEval oracle-history experiment. See README."""
import os
from pathlib import Path
SCRATCH=Path(os.environ.get('LAB_DIR','/var/tmp/membench-longmemeval'))
SCRATCH.mkdir(parents=True,exist_ok=True)
os.environ['HF_HOME']=str(SCRATCH/'hf')
os.environ['MEM0_DIR']=str(SCRATCH/'mem0')
os.environ['MEM0_TELEMETRY']='false'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['TOKENIZERS_PARALLELISM']='false'
os.environ['OMP_NUM_THREADS']='4'
os.environ.pop('OPENROUTER_API_KEY',None)
import collections, hashlib, json, random, re, time, urllib.request
from urllib.parse import urlparse
from openai import OpenAI
from rank_bm25 import BM25Okapi
from huggingface_hub import snapshot_download
from mem0 import Memory
from judge_prompt import get_anscheck_prompt

ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ.get('RESULTS_DIR',ROOT/'results'))
OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get('BASE_URL','http://localhost:39710/v1')
if urlparse(BASE).hostname not in ('localhost','127.0.0.1','::1'):
    raise ValueError('Use a localhost endpoint or SSH tunnel; remote APIs are forbidden')
MODEL=os.environ.get('MODEL','default_model')
DATA_REV='98d7416c24c778c2fee6e6f3006e7a073259d48f'
EMBED_REV='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
DATA_URL=f'https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/{DATA_REV}/longmemeval_oracle.json'
SEED=20261121
client=OpenAI(base_url=BASE,api_key='local-only',timeout=900,max_retries=0)
ACTIVE={}
def append(name,value):
    with (OUT/name).open('a') as f:f.write(json.dumps(value,ensure_ascii=False)+'\n')
def callback(_llm,response,params):
    append('memory-llm.jsonl',{'item':ACTIVE,'request':params,'response':response.model_dump()})
def complete(messages,max_tokens):
    start=time.monotonic()
    params={'model':MODEL,'messages':messages,'temperature':0,'seed':SEED,'max_tokens':max_tokens}
    response=client.chat.completions.create(**params)
    raw=response.model_dump()
    append('llm.jsonl',{'item':ACTIVE,'request':params,'response':raw,'seconds':time.monotonic()-start})
    return response.choices[0].message.content.strip(),raw,time.monotonic()-start

def strata(x):
    return 'abstention' if x['question_id'].endswith('_abs') else x['question_type']
def sample(data):
    rng=random.Random(SEED); groups=collections.defaultdict(list)
    for x in data:groups[strata(x)].append(x)
    chosen=[]
    for key in sorted(groups):chosen.extend(rng.sample(sorted(groups[key],key=lambda x:x['question_id']),2))
    return chosen

def history(x):
    # Ignore evidence labels during all three methods. Only oracle split membership supplies evidence.
    return [{'session_id':sid,'date':date,'dialogue':[
        {'role':t['role'],'content':t['content']} for t in sess]}
        for sid,date,sess in sorted(zip(x['haystack_session_ids'],x['haystack_dates'],x['haystack_sessions']),key=lambda a:a[1])]

def chunks(hist):
    result=[]
    for si,s in enumerate(hist):
        for ti,t in enumerate(s['dialogue']):
            text=t['content']
            for start in range(0,len(text),700):
                result.append({'session':si,'turn':ti,'offset':start,'date':s['date'],'text':t['role']+': '+text[start:start+800]})
    return result

def tokens(text):return re.findall(r'\w+',text.lower())

def wilson(k,n):
    z=1.95996398454; p=k/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den; rad=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/den
    return [mid-rad,mid+rad]

def main():
    data_path=SCRATCH/'oracle.json'
    if not data_path.exists():data_path.write_bytes(urllib.request.urlopen(DATA_URL).read())
    data=json.loads(data_path.read_text()); selected=sample(data)
    (OUT/'sample.json').write_text(json.dumps(selected,indent=2,ensure_ascii=False))
    manifest={'seed':SEED,'n':len(selected),'split':'oracle','dataset_revision':DATA_REV,'dataset_url':DATA_URL,
      'dataset_license':'MIT','dataset_sha256':hashlib.sha256(data_path.read_bytes()).hexdigest(),
      'upstream_revision':'9e0b455f4ef0e2ab8f2e582289761153549043fc',
      'model_repository':'mlx-community/Qwen3.5-9B-4bit','model_revision':'8b2b98c00a6b4d291155e4890773ca8f769aee53',
      'embedding_repository':'sentence-transformers/all-MiniLM-L6-v2','embedding_revision':EMBED_REV,
      'items':[{'id':x['question_id'],'stratum':strata(x),'sessions':len(x['haystack_sessions']),
       'history_characters':len(json.dumps(history(x)))} for x in selected],
      'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    # Check that judge can reject an incorrect answer and recognize abstention before scoring.
    for q,ans,hyp,ab,expected in [('What color is the flag?','red','red',False,True),
      ('What color is the flag?','red','blue',False,False),
      ('What is the unknown code?','No code was supplied.','There is insufficient information.',True,True)]:
        ACTIVE.clear();ACTIVE.update(phase='judge-check')
        prompt=get_anscheck_prompt('single-session-user',q,ans,hyp,abstention=ab)
        answer,raw,sec=complete([{'role':'user','content':prompt}],10)
        label='yes' in answer.lower()
        append('judge-checks.jsonl',{'prompt':prompt,'answer':answer,'expected':expected,'actual':label})
        if label!=expected:raise RuntimeError('Local judge failed a basic positive/negative control')
    embed_path=snapshot_download('sentence-transformers/all-MiniLM-L6-v2',revision=EMBED_REV,
      ignore_patterns=['onnx/*','openvino/*','*.h5','*.ot'])
    done=set()
    if (OUT/'items.jsonl').exists():
        done={(x['question_id'],x['method']) for x in map(json.loads,(OUT/'items.jsonl').read_text().splitlines())}
    for x in selected:
        hist=history(x)
        for method in ['full-context','bm25-rag','mem0-oss']:
            if (x['question_id'],method) in done:continue
            ACTIVE.clear();ACTIVE.update(question_id=x['question_id'],method=method,phase='answer')
            print(json.dumps(ACTIVE),flush=True)
            before=time.monotonic(); ingest_seconds=0; memory_events=[]
            if method=='full-context':context=hist
            elif method=='bm25-rag':
                docs=chunks(hist); bm=BM25Okapi([tokens(d['text']) for d in docs])
                scores=bm.get_scores(tokens(x['question']))
                ix=sorted(range(len(docs)),key=lambda i:(-float(scores[i]),i))[:10]
                context=[docs[i] for i in sorted(ix)]
            else:
                store=SCRATCH/'stores'/x['question_id']; store.mkdir(parents=True,exist_ok=True)
                memory=Memory.from_config({
                  'version':'v1.1','history_db_path':str(store/'history.db'),
                  'vector_store':{'provider':'qdrant','config':{'path':str(store/'qdrant'),
                    'collection_name':'experiment','embedding_model_dims':384}},
                  'embedder':{'provider':'huggingface','config':{'model':embed_path,
                    'embedding_dims':384,'model_kwargs':{'device':'cpu'}}},
                  'llm':{'provider':'openai','config':{'model':MODEL,'api_key':'local-only',
                    'openai_base_url':BASE,'temperature':0,'top_p':1,'max_tokens':2048,'response_callback':callback}}})
                ingest_start=time.monotonic()
                for s in hist:
                    # Dates enter the extraction input. Preserve original user and assistant roles.
                    messages=[{'role':'system','content':'Conversation date: '+s['date']}]+s['dialogue']
                    event=memory.add(messages,user_id=x['question_id'],metadata={'session_date':s['date']},infer=True)
                    memory_events.append({'session_id':s['session_id'],'date':s['date'],'result':event})
                ingest_seconds=time.monotonic()-ingest_start
                context=memory.search(x['question'],user_id=x['question_id'],limit=10)['results']
                # Random IDs and wall-clock metadata are not useful model context.
                context=[{'memory':v['memory'],'session_date':(v.get('metadata') or {}).get('session_date')} for v in context]
                append('memory-events.jsonl',{'question_id':x['question_id'],'events':memory_events,
                  'all_memories':memory.get_all(user_id=x['question_id'])})
                memory.vector_store.client.close()
            prep_seconds=time.monotonic()-before
            prompt=('Answer the question using only the dated conversation history below. '
              'Account for updates and relative dates. If the history does not contain enough information, '
              'say that the information is insufficient. Give a concise answer.\nQuestion date: '+x['question_date']+
              '\nHistory:\n'+json.dumps(context,ensure_ascii=False)+'\nQuestion: '+x['question'])
            hypothesis,raw,answer_seconds=complete([{'role':'user','content':prompt}],512)
            ACTIVE['phase']='judge'
            judge_prompt=get_anscheck_prompt(x['question_type'],x['question'],x['answer'],hypothesis,
              abstention=x['question_id'].endswith('_abs'))
            verdict,judge_raw,judge_seconds=complete([{'role':'user','content':judge_prompt}],10)
            if not re.fullmatch(r'(yes|no)[.!]?',verdict.lower()):
                raise RuntimeError('Judge did not produce a yes/no verdict: '+verdict)
            append('items.jsonl',{'question_id':x['question_id'],'question_type':x['question_type'],
              'stratum':strata(x),'method':method,'question':x['question'],'reference':x['answer'],
              'context':context,'hypothesis':hypothesis,'judge_prompt':judge_prompt,'judge_response':verdict,
              'correct':'yes' in verdict.lower(),'prep_seconds':prep_seconds,'ingest_seconds':ingest_seconds,
              'answer_seconds':answer_seconds,'judge_seconds':judge_seconds,
              'answer_usage':raw.get('usage'),'answer_finish_reason':raw['choices'][0]['finish_reason'],
              'judge_finish_reason':judge_raw['choices'][0]['finish_reason']})
    rows=[json.loads(line) for line in (OUT/'items.jsonl').read_text().splitlines()]
    if len(rows)!=len(selected)*3 or len({(r['question_id'],r['method']) for r in rows})!=len(rows):
        raise RuntimeError('Incomplete or duplicate results')
    summary={}
    for method in ['full-context','bm25-rag','mem0-oss']:
        r=[v for v in rows if v['method']==method];k=sum(v['correct'] for v in r)
        summary[method]={'correct':k,'n':len(r),'accuracy':k/len(r),'wilson95':wilson(k,len(r)),
          'by_stratum':{s:{'correct':sum(v['correct'] for v in r if v['stratum']==s),
           'n':sum(v['stratum']==s for v in r)} for s in sorted({v['stratum'] for v in r})},
          'length_stopped':sum(v['answer_finish_reason']=='length' for v in r)}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()

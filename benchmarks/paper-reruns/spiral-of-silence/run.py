"""Reduced ten-round loop, with author prompts, text filter, and source scorer."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='8'
os.environ['MKL_NUM_THREADS']='8'
os.environ['OPENBLAS_NUM_THREADS']='8'
os.environ['TOKENIZERS_PARALLELISM']='false'


def author_objects(source):
    # Load literal prompts and the pure filter without importing unrelated legacy services.
    tree=ast.parse((source/'src/llm_zero_generate/get_response_llm.py').read_text())
    prompt=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='Prompt' for t in n.targets))
    tree=ast.parse((source/'src/post_process/process_llm_text.py').read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='filter_response')
    namespace={}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'<author filter_response>','exec'),namespace)
    spec=importlib.util.spec_from_file_location('author_percentage',source/'src/evaluation/eva_percentage.py')
    scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer)
    return prompt,namespace['filter_response'],scorer.calculate_llm_human_proportion


def file_sha256(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def cache_vectors(path, texts, encode, model_fingerprint):
    import numpy as np
    identity=hashlib.sha256(json.dumps({'model':model_fingerprint,'text_sha256':[hashlib.sha256(t.encode()).hexdigest() for t in texts]},sort_keys=True).encode()).hexdigest()
    meta_path=path.with_suffix('.meta.json')
    if path.exists() and meta_path.exists():
        meta=json.loads(meta_path.read_text())
        if meta.get('identity')==identity and meta.get('array_sha256')==file_sha256(path):
            result=np.load(path,allow_pickle=False)
            assert len(result)==len(texts) and np.isfinite(result).all()
            return result
    result=encode(texts)
    assert len(result)==len(texts) and np.isfinite(result).all()
    np.save(path,result)
    meta_path.write_text(json.dumps({'identity':identity,'array_sha256':file_sha256(path)})+'\n')
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--scratch',type=Path,required=True)
    p.add_argument('--embedding',type=Path,required=True)
    p.add_argument('--endpoint',default='http://localhost:39950/v1')
    p.add_argument('--rounds',type=int,choices=[3,5,10],default=10)
    a=p.parse_args()
    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer
    from openai import OpenAI
    torch.set_num_threads(8);torch.set_num_interop_threads(1)
    prompt,filter_response,author_score=author_objects(a.source)
    out=Path(__file__).parent/'results';out.mkdir(exist_ok=True)
    queries=json.loads((a.scratch/'queries.json').read_text())
    human=json.loads((a.scratch/'human.json').read_text())
    cohort=json.loads((out/'cohort.json').read_text())
    cohort['rounds']=a.rounds
    (out/'cohort.json').write_text(json.dumps(cohort,indent=2)+'\n')
    assert [q['id'] for q in queries]==cohort['item_ids']
    assert {i:hashlib.sha256(t.encode()).hexdigest() for i,t in human.items()}==cohort['human_document_sha256']
    assert len(queries)>=150
    model=SentenceTransformer(str(a.embedding),device='cpu')
    def encode(texts):
        return model.encode(texts,batch_size=32,normalize_embeddings=False,show_progress_bar=True)
    weight_path=next((a.embedding/name for name in ['model.safetensors','pytorch_model.bin'] if (a.embedding/name).exists()))
    model_fingerprint={'weights_sha256':file_sha256(weight_path),'max_seq_length':model.max_seq_length,'normalize':False}
    (out/'retriever-runtime.json').write_text(json.dumps({**model_fingerprint,'embedding_dimension':model.get_sentence_embedding_dimension(),'cpu_threads':8,'batch_size':32},indent=2)+'\n')
    vectors=cache_vectors(a.scratch/'human-vectors.npy',list(human.values()),encode,model_fingerprint)
    qvectors=cache_vectors(a.scratch/'query-vectors.npy',[q['question'] for q in queries],encode,model_fingerprint)
    ids=list(human);texts=list(human.values())
    client=OpenAI(base_url=a.endpoint,api_key='local-placeholder',timeout=300,max_retries=2)
    generated_path=out/'generated.jsonl'
    generated={(r['round'],r['id']):r for r in map(json.loads,generated_path.read_text().splitlines())} if generated_path.exists() else {}
    failures_path=out/'generation-failures.jsonl'
    prior_failures=[json.loads(line) for line in failures_path.read_text().splitlines()] if failures_path.exists() else []
    prior_attempts={}
    for failed in prior_failures:
        key=(failed['round'],failed['id'])
        prior_attempts[key]=prior_attempts.get(key,0)+len(failed['attempts'])
    per_round=[]
    checkpoint_lock=threading.Lock()
    for round_num in range(a.rounds+1):
        if round_num:
            current=[]
            # All writes in a round see the same previous-round retrieval snapshot.
            def generate_one(qi, q):
                key=(round_num,q['id'])
                if key in generated:
                    return generated[key]
                context_ids=[ids[j] for j in previous[qi,:5]]
                if round_num==1:
                    text=prompt['Zero-shot'].format(question=q['question'])
                    context_ids=[]
                else:
                    context_str='\n'.join(f'[Context {i+1}]: {texts[j]}' for i,j in enumerate(previous[qi,:5]))
                    text=prompt['With-context'].format(question=q['question'],context_str=context_str)
                start=time.monotonic()
                stop=[word for word in [' Human:',' AI:','sorry',' Sorry'] if word.strip().lower() not in text.lower()]
                attempts=[]
                attempt_offset=prior_attempts.get(key,0)
                for attempt in range(3):
                    response=client.chat.completions.create(model='local-qwen2.5-3b-q4',messages=[{'role':'user','content':text}],temperature=.7,top_p=1,presence_penalty=.6,frequency_penalty=0,max_tokens=128,seed=20261122+round_num*10000+qi+(attempt_offset+attempt)*1000000,stop=stop)
                    raw=response.choices[0].message.content
                    filtered=filter_response(' '.join(raw.strip().replace('\n',' ').split(' ')[:100]))
                    attempts.append({'seed':20261122+round_num*10000+qi+(attempt_offset+attempt)*1000000,'raw_response':raw,'filtered':filtered,'finish_reason':response.choices[0].finish_reason})
                    if len(filtered.split())>=5:
                        break
                else:
                    with checkpoint_lock:
                        with (out/'generation-failures.jsonl').open('a') as f:
                            f.write(json.dumps({'round':round_num,'id':q['id'],'attempts':attempts,'error':'three responses shorter than five words'})+'\n')
                            f.flush();os.fsync(f.fileno())
                    raise RuntimeError(f'Three empty or too-short responses at round {round_num}, item {q["id"]}; no document added')
                row={'round':round_num,'id':q['id'],'docid':f'local-qwen2.5-3b-q4_nq_round{round_num}_{q["id"]}',
                     'response':raw,'filtered':filtered,'attempts':attempts,'context_docids':context_ids,
                     'prompt_sha256':hashlib.sha256(text.encode()).hexdigest(),'seconds':time.monotonic()-start,
                     'finish_reason':response.choices[0].finish_reason,'usage':response.usage.model_dump()}
                with checkpoint_lock:
                    with generated_path.open('a') as f:
                        f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
                    generated[key]=row
                    print('generated',round_num,row['id'],flush=True)
                return row
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(generate_one,qi,q) for qi,q in enumerate(queries)]
                try:
                    for future in as_completed(futures):
                        future.result()
                except BaseException:
                    for future in futures:
                        future.cancel()
                    raise
            current=[generated[(round_num,q['id'])] for q in queries]
            new_vectors=a.scratch/f'generated-{round_num:02d}.npy'
            v=cache_vectors(new_vectors,[r['filtered'] for r in current],encode,model_fingerprint)
            vectors=np.concatenate([vectors,v])
            ids.extend(r['docid'] for r in current);texts.extend(r['filtered'] for r in current)
        start=time.monotonic()
        scores=qvectors@vectors.T
        # Exact unnormalized inner-product ranking, stable document-order tie breaking.
        ranking=np.argsort(-scores,axis=1,kind='stable')[:,:50]
        retained={q['id']:{'contexts':[{'docid':ids[j]} for j in ranking[qi]]} for qi,q in enumerate(queries)}
        rank_path=out/f'round-{round_num:02d}.json'
        rank_path.write_text(json.dumps(retained)+'\n')
        shares=np.array([sum(ids[j].isdigit() for j in ranks)/50 for ranks in ranking])
        official=author_score(str(rank_path),[50],['local-qwen2.5-3b-q4'])[50]['human_proportion']
        assert abs(float(shares.mean())-official)<1e-12
        rng=np.random.default_rng(20261122)
        index=rng.integers(0,len(queries),size=(10000,len(queries)))
        ci=np.quantile(shares[index].mean(axis=1),[.025,.975]).tolist()
        result={'round':round_num,'n':len(queries),'human_share':official,'ci95':ci,
                'corpus_human':len(human),'corpus_generated':round_num*len(queries),
                'retrieval_seconds':time.monotonic()-start,
                'per_item':[{'id':q['id'],'human_share':float(x)} for q,x in zip(queries,shares)]}
        per_round.append(result)
        (out/'summary.json').write_text(json.dumps({'n':len(queries),'interval':'95% percentile question bootstrap, 10000 resamples, seed 20261122; conditional on the shared evolving corpus', 'rounds':per_round},indent=2)+'\n')
        previous=ranking
        print('round',round_num,'human_share',official,'ci95',ci,flush=True)
    client.close()


if __name__=='__main__':
    main()

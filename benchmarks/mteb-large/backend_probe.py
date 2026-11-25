#!/usr/bin/env python3
"""Paired numerical implementation check, separate from benchmark quality scores."""
import argparse,io,json,os,urllib.request,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
LAB=Path('/data/scratch/membench/mteb-large')
MODEL='Qwen/Qwen3-Embedding-4B';REV='636cd9bf47d976946cdbb2b0c3ca0cb2f8eea5ff'

def main():
    p=argparse.ArgumentParser();p.add_argument('--from-cache',action='store_true');a=p.parse_args()
    if a.from_cache:
        import mteb,hashlib
        task=mteb.get_task('SciFact');task.load_data();data=task.dataset['default']['test']
        execution=json.loads((ROOT/'results/local/Qwen__Qwen3-Embedding-4B/config.json').read_text())['execution']
        payloads=[];references=[]
        for role,key in [('query','queries'),('document','corpus')]:
            ds=data[key]
            texts=[]
            for row in ds:
                text=row['text']
                if role=='document' and row.get('title'):text=(row['title']+' '+text).strip()
                elif role=='document':text=text.strip()
                texts.append(text)
            order=sorted(range(len(texts)),key=lambda i:len(texts[i]),reverse=True)
            payload={'model':MODEL,'revision':REV,'execution':execution,'texts':[texts[i] for i in order[:16]],
                     'task':'SciFact','prompt_type':role,'max_length':512,'dtype':'bfloat16','batch_limit':16,
                     'transport_order':'global character-length sort; restore original order'}
            name=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()+'.npy'
            cached=LAB/'mteb/embeddings'/name
            assert cached.exists(),f'Exact prior RPC cache not found for {role}'
            references.append(np.load(cached,allow_pickle=False));payloads.append(payload)
        np.save(LAB/'probe-reference.npy',np.concatenate(references),allow_pickle=False)
        (LAB/'probe-inputs.json').write_text(json.dumps(payloads))
        print('Saved 32 exact cached Torch RPC reference embeddings; benchmark labels were not used');return
    deadline=time.monotonic()+1800
    while time.monotonic()<deadline:
        try:
            with urllib.request.urlopen('http://127.0.0.1:39740',timeout=5) as response:identity=json.load(response)
            if identity.get('execution',{}).get('engine')=='MLX':break
        except OSError:pass
        time.sleep(5)
    else:raise TimeoutError('MLX worker not ready')
    payloads=json.loads((LAB/'probe-inputs.json').read_text())
    vectors=[]
    for payload in payloads:
        req=urllib.request.Request(os.environ.get('EMBEDDING_ENDPOINT','http://127.0.0.1:39740'),data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=600) as response:values=np.load(io.BytesIO(response.read()),allow_pickle=False)
        assert values.shape==(16,2560) and np.isfinite(values).all();vectors.append(values)
    values=np.concatenate(vectors)
    reference=np.load(LAB/'probe-reference.npy',allow_pickle=False)
    reference=reference/np.linalg.norm(reference,axis=1,keepdims=True);values=values/np.linalg.norm(values,axis=1,keepdims=True)
    cosine=(reference*values).sum(1)
    result={'n_paired_inputs':32,'hardware':'Apple M3 Ultra, 96 GB','reference':'Official MTEB PyTorch wrapper, bfloat16','candidate':'MLX, bfloat16, identical original model revision',
            'sampling':'The first 16 queries and 16 documents after the pre-existing SciFact transport length sort; exact cached RPC hashes matched; no labels or quality scores used',
            'minimum_embedding_cosine':float(cosine.min()),'mean_embedding_cosine':float(cosine.mean()),'required_minimum':.995,
            'max_normalized_coordinate_difference':float(np.max(np.abs(reference-values))),'status':'pass' if cosine.min()>.995 else 'fail'}
    (ROOT/'results/backend-equivalence.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    assert cosine.min()>.995,result
if __name__=='__main__':main()

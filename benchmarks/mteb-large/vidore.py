#!/usr/bin/env python3
"""Fixed ViDoRe V3 HR English subset, full pages, official qrels, nDCG@5/10."""
import argparse,base64,gzip,hashlib,io,json,os,time,urllib.request
from pathlib import Path
import numpy as np
import pytrec_eval
from datasets import load_dataset
ROOT=Path(__file__).resolve().parent
DATA='vidore/vidore_v3_hr_mteb_format'; REV='bc7d43d64815ed30f664168c8052106484aba7fd'; SEED=20261121

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--revision',required=True);p.add_argument('--hardware',default='Apple M3 Ultra, 96 GB');a=p.parse_args()
    out=ROOT/'results'/'vidore'/a.model.replace('/','__');out.mkdir(parents=True,exist_ok=True)
    datasets={n:load_dataset(DATA,'english-'+n,revision=REV,split='test') for n in ['corpus','queries','qrels']}
    corpus=datasets['corpus'];queries=datasets['queries'];rels=datasets['qrels']
    assert len(corpus)==1110 and len(queries)==318
    cache=Path(os.environ['MTEB_CACHE'])/'vidore'/a.model.replace('/','__');cache.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(os.environ.get('EMBEDDING_ENDPOINT','http://127.0.0.1:39740'),timeout=30) as response:identity=json.load(response)
    assert identity['model']==a.model and identity['revision']==a.revision
    (out/'worker-identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    execution={k:v for k,v in identity.get('execution',{}).items() if not k.endswith('_record_only')}
    vectors={};started=time.monotonic();encoded=0;reused=0
    for kind,ds in [('document',corpus),('query',queries)]:
        arr=[]
        for i,row in enumerate(ds):
            payload={'model':a.model,'revision':a.revision,'execution':execution,'task':'Vidore3HrRetrieval','prompt_type':kind,'image_max_pixels':1843200}
            if kind=='document':
                buf=io.BytesIO();row['image'].convert('RGB').save(buf,format='PNG')
                payload['images']=[base64.b64encode(buf.getvalue()).decode()]
            else:payload['texts']=[row['text']]
            raw=json.dumps(payload,sort_keys=True).encode(); key=hashlib.sha256(raw).hexdigest();path=cache/(key+'.npy')
            if not path.exists():
                encoded+=1
                req=urllib.request.Request(os.environ.get('EMBEDDING_ENDPOINT','http://127.0.0.1:39740'),data=raw,headers={'Content-Type':'application/json'})
                try:
                    with urllib.request.urlopen(req,timeout=600) as r: blob=r.read()
                except urllib.error.HTTPError as error:
                    print('Worker error:',error.read().decode(errors='replace'),flush=True)
                    raise
                v=np.load(io.BytesIO(blob),allow_pickle=False);assert v.shape[0]==1 and np.isfinite(v).all()
                temp=path.with_suffix('.tmp');temp.write_bytes(blob);temp.replace(path)
            else:reused+=1
            arr.append(np.load(path,allow_pickle=False)[0])
            if i%50==0:print(a.model,kind,i,len(ds),flush=True)
        vectors[kind]=np.asarray(arr)
    qrels={str(r['id']):{} for r in queries}
    ignored_qrels=0
    for r in rels:
        if str(r['query-id']) in qrels:qrels[str(r['query-id'])][str(r['corpus-id'])]=r['score']
        else:ignored_qrels+=1
    assert all(qrels.values()), 'An English query lacks judgments'
    docids=[str(r['id']) for r in corpus];qids=[str(r['id']) for r in queries]
    assert len(set(docids))==1110 and len(set(qids))==318, 'Duplicate primary dataset IDs'
    assert all(set(judgments)<=set(docids) for judgments in qrels.values()), 'Judged document absent from corpus'
    q,d=vectors['query'],vectors['document']
    assert (np.linalg.norm(q,axis=1)>0).all() and (np.linalg.norm(d,axis=1)>0).all(), 'Zero embedding norm'
    q=q/np.linalg.norm(q,axis=1,keepdims=True);d=d/np.linalg.norm(d,axis=1,keepdims=True)
    sims=q@d.T;run={}
    for i,qid in enumerate(qids):
        order=np.argsort(-sims[i],kind='stable')[:10];run[qid]={docids[j]:float(sims[i,j]) for j in order}
    scored=pytrec_eval.RelevanceEvaluator(qrels,{'ndcg_cut_5','ndcg_cut_10'}).evaluate(run)
    assert set(scored)==set(qids), 'Missing scored English query'
    with gzip.open(out/'queries.jsonl.gz','wt') as f:
        for qid in qids:
            f.write(json.dumps({'query_id':qid,'qrels':qrels[qid],'top10':run[qid],**scored[qid]})+'\n');f.flush()
    summary={'model':a.model,'revision':a.revision,'dataset':DATA,'dataset_revision':REV,'license':'cc-by-4.0',
             'n_queries':318,'n_corpus':1110,'ignored_qrels_for_other_query_ids':ignored_qrels,'sampling':'All English HR test queries; all corpus pages','seed':SEED,
             'dtype':'bfloat16','execution':execution,'hardware':a.hardware,'scoring':'exact cosine, pytrec_eval nDCG@5 and @10, graded qrels',
             'elapsed_seconds':time.monotonic()-started, 'timing_scope':'This resumed invocation only; cached embeddings can be reused. Not an end-to-end latency measurement.', 'encoded_this_invocation':encoded, 'reused_embeddings':reused, 'image_processing': 'official processor defaults' if a.model.startswith('nomic-') else 'Qwen MTEB processor: max 1800 image tokens, 8192-token image sequence cap; queries 512 tokens'}
    for k in ['ndcg_cut_5','ndcg_cut_10']:
        vals=np.array([scored[qid][k] for qid in qids]);rng=np.random.default_rng(SEED)
        summary[k]={'mean':float(vals.mean()),'bootstrap_95_ci':np.quantile(rng.choice(vals,size=(10000,len(vals))).mean(1),[.025,.975]).tolist()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()

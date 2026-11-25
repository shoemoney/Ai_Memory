#!/usr/bin/env python3
"""Check independent VL request, padding and order behavior without quality labels."""
import io,json,os,urllib.request
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
endpoint=os.environ.get('EMBEDDING_ENDPOINT','http://127.0.0.1:39740')
with urllib.request.urlopen(endpoint,timeout=180) as response:identity=json.load(response)
assert identity['model']=='Qwen/Qwen3-VL-Embedding-8B'
short='A short retrieval query.'
long='A longer synthetic retrieval query with extra context and details. '*18

def encode(texts):
    payload={'model':identity['model'],'revision':identity['revision'],'task':'SciFact','prompt_type':'query','texts':texts}
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=180) as response:array=np.load(io.BytesIO(response.read()),allow_pickle=False)
    assert np.isfinite(array).all() and (np.linalg.norm(array,axis=1)>0).all()
    return array/np.linalg.norm(array,axis=1,keepdims=True)

first=encode([short]);mixed=encode([short,long]);reverse=encode([long,short]);repeat=encode([short])
values={'padding_short_cosine':float(first[0]@mixed[0]),'order_short_cosine':float(mixed[0]@reverse[1]),
        'order_long_cosine':float(mixed[1]@reverse[0]),'repeat_short_cosine':float(first[0]@repeat[0])}
assert min(values.values())>.995,values
result={'model':identity['model'],'revision':identity['revision'],'execution':identity['execution'],
    'synthetic_requests':4,'synthetic_embeddings':6,'quality_labels_used':False,
    'scope':'Independent-request, padding and ordering invariant; not full-precision backend equivalence',
    'required_minimum_cosine':.995,**values,'status':'pass'}
(ROOT/'results/vl-batch-invariance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

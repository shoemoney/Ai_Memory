# Tested local model and memory commands

Test date: **2026-11-20**. Status applies to the concrete smoke test described, not general production readiness. No cloud inference, paid API, API key, GPU, or system package installation was used. Public model/package registries were accessed without credentials.

## Host, isolation and measurement

Ubuntu host: AMD Ryzen 9 8945HX, 16 physical cores / 32 logical CPUs. Shared busy machine; load observed 7.58 / 8.35 / 11.84, with roughly 25 GiB swap in use. Measurements are single wall-clock observations, include local HTTP/serialization where applicable, and are not controlled comparative benchmarks. Python 3.14.4, Node v24.22.3, npm/npx 11.19.1.

Docker limits: Ollama 4 CPUs / 5 GiB, each other server 2 CPUs / 2 GiB. llama.cpp `-t 2`; direct Ollama requests `num_thread=4`; Python Torch/OMP/MKL use 2 threads. Mem0 uses its provider defaults within the 4-CPU container quota, rather than an explicit thread count. No Docker device requests; `/api/ps` reported `size_vram: 0`.

All model artifacts and Hugging Face caches were under `/var/tmp/memguide-lab-models`. Two initial pip invocations used the default pip HTTP cache; 54 cache entries newly created in those exact invocation windows (218,923,860 bytes, birth times checked) were relocated into the lab for removal. Existing cache entries were preserved. This was a setup-isolation mistake; model inference and model caches stayed local to the lab. Services were bound to loopback ports 39110–39113. Other containers with the `memlab-` prefix ran concurrently; only containers created in this walkthrough were eligible for cleanup.

Executed shared setup:

```bash
mkdir -p /var/tmp/memguide-lab-models
cd /var/tmp/memguide-lab-models
docker images --digests > images-before.txt
docker image ls -q --no-trunc | sort -u > image-ids-before.txt
python3 -m venv venv
venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch > torch-install.log 2>&1
HF_HOME=$PWD/hf PIP_CACHE_DIR=$PWD/pip-cache venv/bin/pip install sentence-transformers mem0ai langgraph > packages-install.log 2>&1
venv/bin/pip install ollama > ollama-python-install.log 2>&1
```
The commands installed then-current versions; the exact resolved version inventory is retained below. Source blocks are the actual files executed, not additional untested commands.

Executed environment wrapper (`run-python.sh`):
```bash
#!/bin/bash
cd /var/tmp/memguide-lab-models
export MEM0_DIR=$PWD/mem0 HF_HOME=$PWD/hf HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 ANONYMIZED_TELEMETRY=False MEM0_TELEMETRY=False CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
exec venv/bin/python "$@"
```

## 1. Ollama CPU embedding and schema extraction — TESTED

Test date: 2026-11-20. Ollama 0.40.16, image `ollama/ollama:latest`.

```bash
docker pull ollama/ollama:latest > ollama-pull.log 2>&1
docker run -d --name memlab-ollama --cpus 4 -m 5g -p 127.0.0.1:39110:11434 -e OLLAMA_NUM_PARALLEL=1 -e OLLAMA_MAX_LOADED_MODELS=1 -e OLLAMA_NO_CLOUD=1 -v /var/tmp/memguide-lab-models/ollama:/root/.ollama ollama/ollama:latest
docker exec memlab-ollama ollama pull qwen3-embedding:0.6b > embed-pull.log 2>&1
docker exec memlab-ollama ollama pull qwen3:1.7b > chat-pull.log 2>&1
./run-python.sh api-test.py > ollama-api.log 2>&1
```
Executed source (`api-test.py`):
```python
import urllib.request,json,time
from pathlib import Path

def post(url,data):
 t=time.perf_counter(); r=json.load(urllib.request.urlopen(urllib.request.Request(url,json.dumps(data).encode(),{'Content-Type':'application/json'}),timeout=600)); return r,round(time.perf_counter()-t,4)
schema={'type':'object','properties':{'name':{'type':'string'},'city':{'type':'string'},'likes':{'type':'string'}},'required':['name','city','likes'],'additionalProperties':False}
base='http://127.0.0.1:39110'
r,t=post(base+'/api/embed',{'model':'qwen3-embedding:0.6b','input':['Alice lives in Paris.','Alice likes coffee.'],'options':{'num_thread':4}})
print('OLLAMA EMBED',{'texts':len(r['embeddings']),'dimension':len(r['embeddings'][0]),'seconds':t,'seconds_per_text':t/2,'total_duration_ns':r.get('total_duration')},flush=True)
r,t=post(base+'/api/chat',{'model':'qwen3:1.7b','messages':[{'role':'user','content':'Extract facts: Alice lives in Paris and likes coffee.'}],'format':schema,'think':False,'stream':False,'options':{'num_thread':4,'temperature':0,'num_ctx':2048,'num_predict':128}})
print('OLLAMA CHAT',r['message']['content'],'seconds',t,flush=True)
json.loads(r['message']['content']);Path('ollama-results.json').write_text(json.dumps({'chat':r,'seconds':t}))
```
Trimmed real output:
```text
OLLAMA EMBED {'texts': 2, 'dimension': 1024, 'seconds': 1.4128, 'seconds_per_text': 0.7064, 'total_duration_ns': 1406096230}
OLLAMA CHAT {
  "name": "Alice",
  "city": "Paris",
  "likes": "coffee"
} seconds 3.1735
```
Model metadata returned by the actual server (size includes model layers, in bytes):
```json
{
  "models": [
    {
      "name": "qwen3:1.7b",
      "model": "qwen3:1.7b",
      "modified_at": "2026-11-20T15:20:25.1271939Z",
      "size": 1359293444,
      "digest": "8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7",
      "details": {
        "parent_model": "",
        "format": "gguf",
        "family": "qwen3",
        "families": [
          "qwen3"
        ],
        "parameter_size": "2.0B",
        "quantization_level": "Q4_K_M",
        "context_length": 40960,
        "embedding_length": 2048,
        "runner": "ggml"
      },
      "capabilities": [
        "completion",
        "tools",
        "thinking"
      ]
    },
    {
      "name": "qwen3-embedding:0.6b",
      "model": "qwen3-embedding:0.6b",
      "modified_at": "2026-11-20T15:20:04.875837229Z",
      "size": 639150858,
      "digest": "ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d",
      "details": {
        "parent_model": "/Users/ollama/.ollama/models/blobs/sha256-06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439",
        "format": "gguf",
        "family": "qwen3",
        "families": [
          "qwen3"
        ],
        "parameter_size": "595.78M",
        "quantization_level": "Q8_0",
        "context_length": 32768,
        "embedding_length": 1024,
        "runner": "ggml"
      },
      "capabilities": [
        "tools",
        "thinking",
        "embedding"
      ]
    }
  ]
}
```
The embedding weights alone were 639,150,592 bytes; chat weights 1,359,279,776 bytes. Full Ollama directory: 1,998,459,601 apparent bytes at measurement. Gotchas: `think:false` prevents spending the output budget on reasoning. `format` takes the schema object directly. JSON parsed successfully and had the expected fields and factual values; a full external JSON Schema validator was not run. Initial embedding call included model load; do not treat 0.7064 s/text as warm steady-state latency. The `qwen3:1.7b` tag reports `parameter_size: 2.0B`; retain both rather than correcting registry metadata by guess.

## 2. Hugging Face TEI CPU — TESTED

Test date: 2026-11-20. Image `ghcr.io/huggingface/text-embeddings-inference:cpu-1.9`; model BAAI/bge-small-en-v1.5, revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`. ONNX weights 133,093,490 bytes; full TEI cache 133,806,795 apparent bytes.

```bash
docker pull ghcr.io/huggingface/text-embeddings-inference:cpu-1.9 > tei-pull.log 2>&1
docker run -d --name memlab-tei --cpus 2 -m 2g -p 127.0.0.1:39111:80 -e HF_HOME=/data/hf -e OMP_NUM_THREADS=2 -v /var/tmp/memguide-lab-models/tei:/data ghcr.io/huggingface/text-embeddings-inference:cpu-1.9 --model-id BAAI/bge-small-en-v1.5
./run-python.sh other-api-test.py > other-api.log 2>&1
```
The executed shared API test below covers TEI and both llama.cpp endpoints. TEI first rejected 100 inputs in one HTTP request: `batch size 100 > maximum allowed batch size 32` (HTTP 422). The corrected test sent 32/32/32/4 texts sequentially. Backend also logged `forcing max_batch_requests=8`; server handles that internally. The 100-text request series took 0.215053 s, 465.00 texts/s, with 384 dimensions. This used very short synthetic texts after server warmup, not a corpus-scale throughput claim.
Executed source (`other-api-test.py`):
```python
exec(open('api-test.py').read().split("base='http")[0])
t0=time.perf_counter(); vectors=[]
for start in range(0,100,32):
 r,t=post('http://127.0.0.1:39111/embed',{'inputs':[f'A short passage about memory number {i}.' for i in range(start,min(start+32,100))]});vectors.extend(r)
t=time.perf_counter()-t0; print('TEI',len(vectors),len(vectors[0]),'seconds',t,'texts_per_second',100/t,flush=True)
r,t=post('http://127.0.0.1:39112/v1/embeddings',{'input':['Alice lives in Paris.'],'model':'embeddinggemma'});print('LLAMA EMBED',len(r['data'][0]['embedding']),'seconds',t,flush=True)
r,t=post('http://127.0.0.1:39113/v1/chat/completions',{'messages':[{'role':'user','content':'Extract facts: Alice lives in Paris and likes coffee. /no_think'}],'temperature':0,'max_tokens':128,'response_format':{'type':'json_schema','json_schema':{'name':'facts','strict':True,'schema':schema}}});print('LLAMA CHAT',r['choices'][0]['message'],'seconds',t,flush=True);json.loads(r['choices'][0]['message']['content'])
```
Real output:
```text
TEI 100 384 seconds 0.21505302298464812 texts_per_second 465.0016010569572
LLAMA EMBED 768 seconds 0.0265
LLAMA CHAT {'role': 'assistant', 'content': '{"name": "Alice", "city": "Paris", "likes": "coffee"}'} seconds 0.6561
```

## 3. llama.cpp CPU server — TESTED

Test date: 2026-11-20. Official image `ghcr.io/ggml-org/llama.cpp:server`; version `1.0.0-dev`, build 12464, commit `d3c3e242c`, GNU 15.2.0 Linux x86_64. Embedding: ggml-org/embeddinggemma-300M-GGUF, `embeddinggemma-300M-Q8_0.gguf`, 333,590,944 bytes. Chat: Qwen/Qwen3-0.6B-GGUF, `Qwen3-0.6B-Q8_0.gguf`, 639,446,688 bytes.

```bash
docker pull ghcr.io/ggml-org/llama.cpp:server > llama-pull.log 2>&1
curl -LfsS https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q8_0.gguf -o chat.gguf
curl -LfsS https://huggingface.co/ggml-org/embeddinggemma-300M-GGUF/resolve/main/embeddinggemma-300M-Q8_0.gguf -o embed.gguf
docker run -d --name memlab-llama-embed --cpus 2 -m 2g -p 127.0.0.1:39112:8080 -v /var/tmp/memguide-lab-models:/models ghcr.io/ggml-org/llama.cpp:server -m /models/embed.gguf --host 0.0.0.0 --port 8080 --embedding --pooling mean -t 2 -c 2048 -ngl 0
docker run -d --name memlab-llama-chat --cpus 2 -m 2g -p 127.0.0.1:39113:8080 -v /var/tmp/memguide-lab-models:/models ghcr.io/ggml-org/llama.cpp:server -m /models/chat.gguf --host 0.0.0.0 --port 8080 -t 2 -c 2048 -ngl 0 --jinja --reasoning-budget 0
```
Requests and output are in item 2’s executed shared API test. `/v1/embeddings` returned 768 dimensions in 0.0265 s. `/v1/chat/completions` with `response_format.type=json_schema` returned parseable JSON with Alice / Paris / coffee in 0.6561 s. Gotchas: native Ollama `format` and OpenAI-style `response_format` have different nesting; `--embedding --pooling mean` and `-ngl 0` worked for this GGUF. This is a mechanical API smoke test, not retrieval-quality evaluation or an endorsement of a particular task prefix.

## 4. sentence-transformers encoding and quantization — TESTED

Test date: 2026-11-20. sentence-transformers 6.3.0, transformers 5.23.0, torch 2.15.0+cpu. Model `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, safetensors 90,868,376 bytes.

```bash
./run-python.sh st-test.py > st-results.log 2>&1
```
Executed source (`st-test.py`):
```python
import time,json,numpy as np,torch
from sentence_transformers import SentenceTransformer,CrossEncoder
from sentence_transformers.quantization import quantize_embeddings
from importlib.metadata import version
from pathlib import Path
torch.set_num_threads(2)
print({p:version(p) for p in ['torch','sentence-transformers','transformers','mem0ai','langgraph']},flush=True)
t=time.perf_counter(); m=SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2',device='cpu');print('ST load/download seconds',time.perf_counter()-t,flush=True)
texts=[f'Alice likes coffee and lives in Paris. passage {i}' for i in range(100)]
t=time.perf_counter(); e=m.encode(texts,normalize_embeddings=True);print('ST encode',e.shape,'seconds',time.perf_counter()-t,'bytes',e.nbytes,flush=True)
for precision in ['int8','binary','ubinary']:
 q=quantize_embeddings(e,precision=precision);print(precision,q.shape,q.dtype,'bytes',q.nbytes,flush=True)
print('all-MiniLM-L6-v2 is not a Matryoshka model; slicing to 128 is mechanical only, no supported accuracy claim',e[:,:128].shape,flush=True)
t=time.perf_counter(); r=CrossEncoder('cross-encoder/ms-marco-TinyBERT-L2-v2',device='cpu');print('reranker load/download seconds',time.perf_counter()-t,flush=True)
passages=['Paris is the capital of France.','Coffee is brewed from roasted beans.','Berlin is in Germany.','Alice lives in Paris.','Dogs are pets.','The moon orbits Earth.','London is in England.','Tea is a drink.','France is in Europe.','Rivers flow downhill.']
t=time.perf_counter();scores=r.predict([('What is the capital of France?',p) for p in passages]);print('reranker seconds',time.perf_counter()-t,'ranked',sorted(zip(scores.tolist(),passages),reverse=True),flush=True)
from langgraph.store.memory import InMemoryStore
def embed(texts):return m.encode(texts).tolist()
s=InMemoryStore(index={'embed':embed,'dims':384,'fields':['text']})
s.put(('users','alice'),'profile',{'text':'Alice lives in Paris and likes coffee.'})
t=time.perf_counter(); hits=s.search(('users','alice'),query='Where does Alice live?');print('LANGGRAPH',[(h.namespace,h.key,h.value,h.score) for h in hits],'seconds',time.perf_counter()-t,flush=True)
```
Trimmed real output for items 4, 5 and 7:
```text
/var/tmp/memguide-lab-models/st-test.py:3: DeprecationWarning: Importing from 'sentence_transformers.quantization' is deprecated and will be removed in a future version. Please use 'sentence_transformers.util.quantization' instead.
  from sentence_transformers.quantization import quantize_embeddings
{'torch': '2.15.0+cpu', 'sentence-transformers': '6.3.0', 'transformers': '5.23.0', 'mem0ai': '2.2.1', 'langgraph': '1.2.24'}
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
ST load/download seconds 12.083979455986992
ST encode (100, 384) seconds 0.19730811499175616 bytes 153600
int8 (100, 384) int8 bytes 38400
binary (100, 48) int8 bytes 4800
ubinary (100, 48) uint8 bytes 4800
all-MiniLM-L6-v2 is not a Matryoshka model; slicing to 128 is mechanical only, no supported accuracy claim (100, 128)
reranker load/download seconds 2.273295016027987
reranker seconds 0.005996163003146648 ranked [(8.31252670288086, 'Paris is the capital of France.'), (1.8826508522033691, 'France is in Europe.'), (-11.173564910888672, 'Berlin is in Germany.'), (-11.270755767822266, 'London is in England.'), (-11.372154235839844, 'Alice lives in Paris.'), (-11.526963233947754, 'Tea is a drink.'), (-11.559137344360352, 'Rivers flow downhill.'), (-11.560636520385742, 'The moon orbits Earth.'), (-11.58039665222168, 'Dogs are pets.'), (-11.599090576171875, 'Coffee is brewed from roasted beans.')]
LANGGRAPH [(('users', 'alice'), 'profile', {'text': 'Alice lives in Paris and likes coffee.'}, 0.6576268554517168)] seconds 0.010677807993488386
```
**Matryoshka limitation:** the tested MiniLM model is not trained for Matryoshka truncation. The executed `e[:,:128]` demonstrates slicing only; it does not establish quality at 128 dimensions. No Matryoshka-capable model was tested. Float32 100×384 used 153,600 bytes, int8 38,400 bytes, packed binary/ubinary 4,800 bytes. Int8 calibration uses this tiny input set; these are storage demonstrations rather than retrieval quality measurements. Library emitted a deprecation warning for `sentence_transformers.quantization`; that import still worked.

## 5. Local reranker — TESTED

Test date: 2026-11-20. Same venv/source/invocation as item 4. `cross-encoder/ms-marco-TinyBERT-L2-v2`, revision `81d1926f67cb8eee2c2be17ca9f793c7c3bd20cc`, safetensors 17,552,980 bytes. First load/download 2.273295 s. Reranking 10 short query/passage pairs on CPU took 0.005996 s; the Paris-capital passage scored highest (8.3125267), followed by France-in-Europe (1.8826509). Scores are raw model scores, not probabilities. Model construction/download time is separate from the one predict call.

## 6. Mem0 with local Ollama and embedded Qdrant — TESTED

Test date: 2026-11-20. mem0ai 2.2.1; extra `ollama` Python package was required. Qdrant is the local embedded client, not a Qdrant service or cloud account.

```bash
./run-python.sh mem0-test.py > mem0-results.log 2>&1
```
Executed source (`mem0-test.py`):
```python
import os,time,json
from mem0 import Memory
config={
 'llm':{'provider':'ollama','config':{'model':'memlab-qwen3-nothink','ollama_base_url':'http://127.0.0.1:39110','temperature':0,'max_tokens':1024}},
 'embedder':{'provider':'ollama','config':{'model':'qwen3-embedding:0.6b','ollama_base_url':'http://127.0.0.1:39110','embedding_dims':1024}},
 'vector_store':{'provider':'qdrant','config':{'collection_name':'memlab','path':os.getcwd()+'/qdrant','embedding_model_dims':1024}},
 'custom_instructions':'/no_think Extract only explicit durable facts from the user. Return the required JSON immediately.',
 'history_db_path':os.getcwd()+'/history.db',
}
print('CONFIG',json.dumps(config),flush=True)
m=Memory.from_config(config)
t=time.perf_counter(); print('ADD',m.add([{'role':'user','content':'My name is Alice. I live in Paris and love coffee.'},{'role':'assistant','content':'I will remember your preferences.'}],user_id='alice'),'seconds',time.perf_counter()-t,flush=True)
print('LIST',m.get_all(user_id='alice'),flush=True)
print('SEARCH',m.search('What does Alice like?',user_id='alice'),flush=True)
```
Real output:
```text
CONFIG {"llm": {"provider": "ollama", "config": {"model": "memlab-qwen3-nothink", "ollama_base_url": "http://127.0.0.1:39110", "temperature": 0, "max_tokens": 1024}}, "embedder": {"provider": "ollama", "config": {"model": "qwen3-embedding:0.6b", "ollama_base_url": "http://127.0.0.1:39110", "embedding_dims": 1024}}, "vector_store": {"provider": "qdrant", "config": {"collection_name": "memlab", "path": "/var/tmp/memguide-lab-models/qdrant", "embedding_model_dims": 1024}}, "custom_instructions": "/no_think Extract only explicit durable facts from the user. Return the required JSON immediately.", "history_db_path": "/var/tmp/memguide-lab-models/history.db"}
Failed to load spaCy lemma model: spaCy is not installed. Install it with: pip install mem0ai[nlp]
fastembed not installed - BM25 keyword search disabled. Install it with: pip install "mem0ai[extras]"
Failed to load spaCy full model: spaCy is not installed. Install it with: pip install mem0ai[nlp]
ADD {'results': [{'id': '5311310d-a233-4515-b4f2-2971bdf4f943', 'memory': "User's name is Alice and resides in Paris", 'event': 'ADD'}, {'id': '911995aa-ca21-48ce-bc10-c4554a36b3e3', 'memory': 'User expresses a preference for coffee', 'event': 'ADD'}]} seconds 64.72581257502316
ValueError: Top-level entity parameters frozenset({'user_id'}) are not supported in get_all(). Use filters={'user_id': '...'} instead.
CONFIG {"llm": {"provider": "ollama", "config": {"model": "memlab-qwen3-nothink", "ollama_base_url": "http://127.0.0.1:39110", "temperature": 0, "max_tokens": 1024}}, "embedder": {"provider": "ollama", "config": {"model": "qwen3-embedding:0.6b", "ollama_base_url": "http://127.0.0.1:39110", "embedding_dims": 1024}}, "vector_store": {"provider": "qdrant", "config": {"collection_name": "memlab", "path": "/var/tmp/memguide-lab-models/qdrant", "embedding_model_dims": 1024}}, "custom_instructions": "/no_think Extract only explicit durable facts from the user. Return the required JSON immediately.", "history_db_path": "/var/tmp/memguide-lab-models/history.db"}
LIST {'results': [{'id': '5311310d-a233-4515-b4f2-2971bdf4f943', 'memory': "User's name is Alice and resides in Paris", 'hash': 'a36519fe05c244f93d75cc03673722f5', 'metadata': None, 'created_at': '2026-11-20T15:25:19.808753+00:00', 'updated_at': '2026-11-20T15:25:19.808753+00:00', 'user_id': 'alice', 'attributed_to': 'user'}, {'id': '911995aa-ca21-48ce-bc10-c4554a36b3e3', 'memory': 'User expresses a preference for coffee', 'hash': 'a5ab62dc375063f4cf6ad13173f08513', 'metadata': None, 'created_at': '2026-11-20T15:25:19.808772+00:00', 'updated_at': '2026-11-20T15:25:19.808772+00:00', 'user_id': 'alice', 'attributed_to': 'user'}]}
Failed to load spaCy lemma model: spaCy is not installed. Install it with: pip install mem0ai[nlp]
Failed to load spaCy full model: spaCy is not installed. Install it with: pip install mem0ai[nlp]
fastembed not installed - BM25 keyword search disabled. Install it with: pip install "mem0ai[extras]"
SEARCH {'results': [{'id': '5311310d-a233-4515-b4f2-2971bdf4f943', 'memory': "User's name is Alice and resides in Paris", 'hash': 'a36519fe05c244f93d75cc03673722f5', 'metadata': None, 'score': 0.5902997227698181, 'created_at': '2026-11-20T15:25:19.808753+00:00', 'updated_at': '2026-11-20T15:25:19.808753+00:00', 'user_id': 'alice', 'attributed_to': 'user'}, {'id': '911995aa-ca21-48ce-bc10-c4554a36b3e3', 'memory': 'User expresses a preference for coffee', 'hash': 'a5ab62dc375063f4cf6ad13173f08513', 'metadata': None, 'score': 0.4770984070114469, 'created_at': '2026-11-20T15:25:19.808772+00:00', 'updated_at': '2026-11-20T15:25:19.808772+00:00', 'user_id': 'alice', 'attributed_to': 'user'}]}
```

Mem0 add took **64.725813 s** and stored two memories. The original get_all call then failed: version 2.2.1 requires `filters={"user_id":"alice"}` for get_all and search; add still accepts user_id directly. This executed recovery listed and searched the same persisted Qdrant records:
```bash
./run-python.sh mem0-read.py > mem0-read-results.log 2>&1
```
```python
exec(open('mem0-test.py').read().split('t=time.perf_counter();')[0])
print('LIST',m.get_all(filters={'user_id':'alice'}),flush=True)
print('SEARCH',m.search('What does Alice like?',filters={'user_id':'alice'}),flush=True)

```
Gotchas: missing optional spaCy/fastembed packages disable linguistic and BM25 features; vector search still worked. The Paris/name memory ranked above coffee for the coffee query (0.5903 vs 0.4771); this smoke test proves API/storage operation, not search relevance.

The final working LLM name is a local alias of the exact Qwen weights from item 1. The alias shares those blobs, rather than downloading another model. Creating it was necessary because this Mem0 Ollama provider does not forward a `think:false` option. The first two unmodified-tag attempts were interrupted after slow generation without producing a result; these are incomplete attempts, not successful Mem0 tests. The alias initially failed with HTTP 400: `request (8047 tokens) exceeds the available context size (4096 tokens), try increasing it`. Recreating it with 12,288 context and four threads succeeded. The actual Mem0 2.2.1 extraction prompt is about 8K tokens even for this short conversation. `custom_instructions` alone did not resolve the slow unmodified-tag attempts. The final alias template is adequate for this no-tools extraction test; tool calling was not tested.

Executed alias-creation source (`create-mem0-model.py`):
```python
import json,urllib.request
base='http://127.0.0.1:39110'
template='{{ range .Messages }}<|im_start|>{{ .Role }}\n{{ .Content }}<|im_end|>\n{{ end }}<|im_start|>assistant\n<think>\n\n</think>\n\n'
data={'model':'memlab-qwen3-nothink','from':'qwen3:1.7b','template':template,'parameters':{'num_thread':4,'num_ctx':12288},'stream':False}
r=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/create',json.dumps(data).encode(),{'Content-Type':'application/json'}),timeout=120));print(r)

```
Executed command:
```bash
python3 create-mem0-model.py > mem0-model-create.log 2>&1
```
Real output:
```text
{'status': 'success'}
```

## 7. LangGraph namespace/key memory — TESTED

Test date: 2026-11-20. langgraph 1.2.24. The executed source and output are in item 4: `InMemoryStore(index={"embed": embed, "dims": 384, "fields": ["text"]})`, namespace `('users', 'alice')`, key `profile`. A local MiniLM callback embeds text. Put succeeded and semantic search returned the matching profile with score 0.65762685545 in 0.010678 s. The store is ephemeral; restarting loses the records. No LLM extraction runs in this example.

## 8. MCP reference memory server — TESTED

Test date: 2026-11-20. npm package `@modelcontextprotocol/server-memory` 2.2.1. npm subtree 16,256,266 apparent bytes; npm cache 14,548,001 bytes.

```bash
npm_config_cache=$PWD/npm-cache npm install --prefix $PWD/npm @modelcontextprotocol/server-memory > npm-install.log 2>&1
python3 mcp-test.py > mcp-results.log 2>&1
```
Executed source (`mcp-test.py`):
```python
import subprocess,json,time,os
p=subprocess.Popen(['npx','--offline','-y','@modelcontextprotocol/server-memory'],cwd=os.getcwd()+'/npm',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open('mcp-stderr.log','w'),text=True,env={**os.environ,'npm_config_cache':os.getcwd()+'/npm-cache','MEMORY_FILE_PATH':os.getcwd()+'/memory.jsonl'})
t=time.perf_counter()
for msg in [{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'memlab','version':'1'}}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}}]:
 p.stdin.write(json.dumps(msg)+'\n');p.stdin.flush()
 if 'id' in msg:
  result=json.loads(p.stdout.readline());print(json.dumps(result),flush=True)
print('startup/list seconds',time.perf_counter()-t,flush=True)
p.terminate();p.wait(timeout=10)
print('version',json.load(open('npm/node_modules/@modelcontextprotocol/server-memory/package.json'))['version'])
```
Trimmed real output:
```text
{"result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {"listChanged": true}, "resources": {"listChanged": true, "subscribe": true}}, "serverInfo": {"name": "memory-server", "version": "2.2.1"}}, "jsonrpc": "2.0", "id": 1}
Tools: create_entities, create_relations, add_observations, delete_entities, delete_observations, delete_relations, read_graph, search_nodes, open_nodes
startup/list seconds 0.3039413199876435
version 2.2.1
```
The first probe used `npx --prefix` and failed (`mcp-server-memory: not found`); running npx with cwd set to the npm package directory worked. JSON-RPC used newline-delimited stdio, initialize → initialized notification → tools/list, then terminated the child. Startup plus handshake/list took 0.303941 s.

Config JSON corresponding to the command/env executed by the probe (the config file itself was not loaded into a desktop client):
```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": [
        "--offline",
        "-y",
        "@modelcontextprotocol/server-memory"
      ],
      "cwd": "/var/tmp/memguide-lab-models/npm",
      "env": {
        "npm_config_cache": "/var/tmp/memguide-lab-models/npm-cache",
        "MEMORY_FILE_PATH": "/var/tmp/memguide-lab-models/memory.jsonl"
      }
    }
  }
}
```

## 9. Graphiti — NOT RUN (optional)

Test date: 2026-11-20. No installation, container, command, extraction test, or compatibility claim. Time was reserved for the eight required walkthroughs and cleanup. This is not a FAILED test.

## Exact image identities

Mutable tags above resolved to these identities during testing:

```json
{
  "tags": [
    "ollama/ollama:latest"
  ],
  "digests": [
    "ollama/ollama@sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592"
  ],
  "id": "sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592",
  "image_size_bytes": 3397620864
}
```

```json
{
  "tags": [
    "ghcr.io/huggingface/text-embeddings-inference:cpu-1.9"
  ],
  "digests": [
    "ghcr.io/huggingface/text-embeddings-inference@sha256:2538ea1c9640d3763b15af668039d24172d063b42337b0c27796fc2be180c78d"
  ],
  "id": "sha256:2538ea1c9640d3763b15af668039d24172d063b42337b0c27796fc2be180c78d",
  "image_size_bytes": 239316921
}
```

```json
{
  "tags": [
    "ghcr.io/ggml-org/llama.cpp:server"
  ],
  "digests": [
    "ghcr.io/ggml-org/llama.cpp@sha256:5b43086e3ba7ea5794d72904654f6cd41224a9b1c6ac0398f4940ee380d30f23"
  ],
  "id": "sha256:5b43086e3ba7ea5794d72904654f6cd41224a9b1c6ac0398f4940ee380d30f23",
  "image_size_bytes": 295698653
}
```

## Resolved Python versions

```text
annotated-doc==0.0.7
annotated-types==0.8.0
anyio==4.16.0
certifi==2026.10.23
charset-normalizer==3.5.2
click==8.5.1
cloudpickle==3.1.3
distro==1.9.0
filelock==4.2.4
fsspec==2026.9.0
grpcio==1.85.3
h11==0.16.0
h2==4.4.1
hf-xet==1.8.0
hpack==4.2.0
httpcore==1.0.9
httpcore2==2.16.2
httpx==0.28.1
httpx2==2.16.2
huggingface_hub==2.4.0
hyperframe==6.1.0
idna==3.20
Jinja2==3.1.6
jiter==0.19.0
joblib==1.6.0
jsonpatch==1.48
jsonpointer==3.12
langchain-core==1.8.4
langchain-protocol==0.0.22
langgraph==1.2.24
langgraph-checkpoint==4.3.2
langgraph-prebuilt==1.1.3
langgraph-sdk==0.4.14
langsmith==0.15.1
markdown-it-py==4.3.0
MarkupSafe==3.0.3
mdurl==0.1.2
mem0ai==2.2.1
mpmath==1.3.0
narwhals==2.29.0
networkx==3.7
numpy==2.5.5
ollama==0.6.3
openai==3.57.0
orjson==3.13.0
ormsgpack==1.13.1
packaging==26.3
portalocker==4.4.2
posthog==8.0.2
protobuf==6.33.6
pydantic==2.14.4
pydantic_core==2.50.5
Pygments==2.21.0
pytz==2026.6
PyYAML==6.0.3
qdrant-client==1.20.0
regex==2026.11.19
requests==2.34.2
requests-toolbelt==1.0.0
rich==15.0.0
safetensors==0.8.0
scikit-learn==1.9.1
scipy==1.18.1
sentence-transformers==6.3.0
setuptools==78.1.0
shellingham==1.5.4
sniffio==1.3.1
SQLAlchemy==2.1.9
sympy==1.14.0
tenacity==9.2.1
threadpoolctl==3.8.0
tokenizers==0.23.3
torch==2.15.0+cpu
tqdm==4.70.1
transformers==5.23.0
truststore==0.10.5
typer==0.29.2
typing-inspection==0.4.5
typing_extensions==4.16.0
urllib3==2.8.0
uuid_utils==0.19.0
websockets==17.4
xxhash==4.1.0
zstandard==0.25.0
```

## Official sources consulted

Fetched directly without web search: [TEI README](https://github.com/huggingface/text-embeddings-inference/blob/main/README.md), [llama.cpp Docker docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md), [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [TinyBERT reranker card](https://huggingface.co/cross-encoder/ms-marco-TinyBERT-L2-v2), [Mem0 Ollama embedding implementation](https://github.com/mem0ai/mem0/blob/main/mem0/embeddings/ollama.py), [Mem0 Ollama LLM config](https://github.com/mem0ai/mem0/blob/main/mem0/configs/llms/ollama.py). Initial transient/incorrect raw docs URLs returned 404; successful fetches and installed package source informed the final commands.

## Cleanup and inventories

```text
Pre-cleanup allocated lab size: 5275828224	/var/tmp/memguide-lab-models
$ df -B1 /var/tmp
Filesystem        1B-blocks         Used    Available Use% Mounted on
/dev/nvme0n1p2 982240026624 750003417088 182266093568  81% /
exit=0
$ docker exec memlab-ollama chmod -R a+rwX /root/.ollama
exit=0
$ docker exec memlab-tei chmod -R a+rwX /data
exit=0
$ docker rm -f -v memlab-ollama
memlab-ollama
exit=0
$ docker rm -f -v memlab-tei
memlab-tei
exit=0
$ docker rm -f -v memlab-llama-embed
memlab-llama-embed
exit=0
$ docker rm -f -v memlab-llama-chat
memlab-llama-chat
exit=0
$ docker image rm ollama/ollama:latest
Untagged: ollama/ollama:latest
Deleted: sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592
exit=0
$ docker image rm ghcr.io/huggingface/text-embeddings-inference:cpu-1.9
Untagged: ghcr.io/huggingface/text-embeddings-inference:cpu-1.9
Deleted: sha256:2538ea1c9640d3763b15af668039d24172d063b42337b0c27796fc2be180c78d
exit=0
$ docker image rm ghcr.io/ggml-org/llama.cpp:server
Untagged: ghcr.io/ggml-org/llama.cpp:server
Deleted: sha256:5b43086e3ba7ea5794d72904654f6cd41224a9b1c6ac0398f4940ee380d30f23
exit=0
$ docker images --digests
REPOSITORY                                 TAG                   DIGEST                                                                    IMAGE ID       CREATED         SIZE
ubuntu                                     24.04                 sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8   73b999393d07   10 days ago     119MB
redis                                      7                     sha256:2e3eb11462c4e3759e6972678dd051d150ff54b1e60714b3c33b701260172a90   2e3eb11462c4   2 weeks ago     170MB
nginx                                      stable                sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   42c68eab6f7e   2 weeks ago     242MB
mariadb                                    <none>                sha256:c4124d1afa875e47f2892edf26b482fa54f796e2f342d3717a04ca091a22a9bd   c4124d1afa87   3 weeks ago     458MB
redis                                      <none>                sha256:6ba19c50b56777f5c11c58eff8ddb69d0d5f27ba131cffb63f180ccfd43c66af   6ba19c50b567   3 weeks ago     57.8MB
composer                                   2.10.3                sha256:2cf275428757e5435a667bfc0d038b14520ca02be2b1b70d44a05c8c19e2de48   2cf275428757   4 weeks ago     316MB
node                                       22.23.3-trixie-slim   sha256:28d03803f09ba76560e273af33beb7eda4ed68fa0698bc9bd15e9a6e35693923   28d03803f09b   4 weeks ago     333MB
nginx                                      1.30.5                sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   9bf97bd7714f   6 weeks ago     242MB
grafana/alloy                              <none>                sha256:2aa2099af76c0098d4af7a4d6e48f86cb66dc1a000222ad927a1c67c6542d13f   2aa2099af76c   7 weeks ago     946MB
prom/prometheus                            <none>                sha256:efd719c99d83b060d9daefdcf00360461adf279f45ef5391f8d111892118753e   efd719c99d83   8 weeks ago     381MB
mariadb                                    12.3.2                sha256:a02fe89cb597d4375812b2eac90cf9d0775d4686daa7f7cc750ebbcad7525bbc   a02fe89cb597   3 months ago    464MB
mariadb                                    11.8.8                sha256:24e76fcec8c003a0362d0dd53f4806e7e79458d7fdeaf47437760e19496f5a9c   24e76fcec8c0   3 months ago    457MB
redis                                      7.4.10-alpine         sha256:e7723ff73d963f5cc6d9c4643ea3d989527a402a319239054e9472a7fb9219a2   e7723ff73d96   3 months ago    57.8MB
prom/node-exporter                         latest                sha256:1b4e4438faca4dd7e001dd445d161a4a2091b0fededa84093b3a8dfeae1f1be0   1b4e4438faca   4 months ago    41MB
getmeili/meilisearch                       <none>                sha256:c1a52f17c759c2cd6349eede3d5108b8dac07b97e10665b1d64a2d4961c2fd29   c1a52f17c759   4 months ago    252MB
alpine                                     <none>                sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b   28bd5fe8b56d   5 months ago    13MB
grafana/grafana-oss                        <none>                sha256:5dad0df181cb644a14e13617b913b261a54f7d4fd4510721dba420929f35bea2   5dad0df181cb   5 months ago    1.47GB
crazymax/diun                              <none>                sha256:e324b793eb32dfb7f74d3a39421ebf090141caaadee69b8f78da63112408ee25   e324b793eb32   5 months ago    86.5MB
ghcr.io/karakeep-app/karakeep              <none>                sha256:64d6a9bbf2d37b5c808cf06b5d87f1f1c7846fdd3844724145a9741aeb06fd31   64d6a9bbf2d3   6 months ago    2.33GB
mysql                                      <none>                sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b   7dcddc01f13b   6 months ago    1.1GB
node                                       <none>                sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293   fb4cd12c85ee   7 months ago    194MB
nginx                                      <none>                sha256:0c8a74b863b202a8e9ce8b2f97cc8bf96bc573206d46c2c469d507095dd2c77e   0c8a74b863b2   8 months ago    92.4MB
gcr.io/cadvisor/cadvisor                   latest                sha256:3de2bd5203120b866d74a9b283b2ffb8ec382fbf9dc321814700c6ea6f44ec57   3de2bd520312   11 months ago   107MB
louislam/uptime-kuma                       <none>                sha256:3d632903e6af34139a37f18055c4f1bfd9b7205ae1138f1e5e8940ddc1d176f9   3d632903e6af   13 months ago   724MB
bitnamilegacy/minio                        latest                sha256:451fe6858cb770cc9d0e77ba811ce287420f781c7c1b806a386f6896471a349c   451fe6858cb7   17 months ago   398MB
influxdb                                   <none>                sha256:299ebda2c7e308dbef42e26ac9b8fd1d9b3bcb8a0aee80c6509aa0219c1d0290   299ebda2c7e3   2 years ago     458MB
couchdb                                    <none>                sha256:ee75c9a737e7c48af0170142689959f2d70f93700162fef40818c799dfeecb8e   ee75c9a737e7   6 years ago     313MB
exit=0
$ bash -c docker ps -a | grep memlab
shell-init: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory
exit=1
$ bash -c ss -ltnp | grep 391
shell-init: error retrieving current directory: getcwd: cannot access parent directories: No such file or directory
LISTEN 0      4096                                127.0.0.1:39109      0.0.0.0:*                                                 
exit=0
$ df -h /var/tmp
Filesystem      Size  Used Avail Use% Mounted on
/dev/nvme0n1p2  915G  684G  185G  79% /
exit=0
$ df -B1 /var/tmp
Filesystem        1B-blocks         Used    Available Use% Mounted on
/dev/nvme0n1p2 982240026624 734227939328 198041571328  79% /
exit=0
Filesystem available bytes increased by 15775375360 (14.692 GiB). Shared filesystem delta includes concurrent work.
Lab exists after cleanup: False
No named volumes were created; only bind mounts were used.
```


Docker images before the test:

```text
REPOSITORY                                 TAG                   DIGEST                                                                    IMAGE ID       CREATED         SIZE
ubuntu                                     24.04                 sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8   73b999393d07   10 days ago     119MB
redis                                      7                     sha256:2e3eb11462c4e3759e6972678dd051d150ff54b1e60714b3c33b701260172a90   2e3eb11462c4   2 weeks ago     170MB
nginx                                      stable                sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   42c68eab6f7e   2 weeks ago     242MB
mariadb                                    <none>                sha256:c4124d1afa875e47f2892edf26b482fa54f796e2f342d3717a04ca091a22a9bd   c4124d1afa87   3 weeks ago     458MB
redis                                      <none>                sha256:6ba19c50b56777f5c11c58eff8ddb69d0d5f27ba131cffb63f180ccfd43c66af   6ba19c50b567   3 weeks ago     57.8MB
composer                                   2.10.3                sha256:2cf275428757e5435a667bfc0d038b14520ca02be2b1b70d44a05c8c19e2de48   2cf275428757   4 weeks ago     316MB
node                                       22.23.3-trixie-slim   sha256:28d03803f09ba76560e273af33beb7eda4ed68fa0698bc9bd15e9a6e35693923   28d03803f09b   4 weeks ago     333MB
nginx                                      1.30.5                sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   9bf97bd7714f   6 weeks ago     242MB
grafana/alloy                              <none>                sha256:2aa2099af76c0098d4af7a4d6e48f86cb66dc1a000222ad927a1c67c6542d13f   2aa2099af76c   7 weeks ago     946MB
prom/prometheus                            <none>                sha256:efd719c99d83b060d9daefdcf00360461adf279f45ef5391f8d111892118753e   efd719c99d83   8 weeks ago     381MB
mariadb                                    11.8.8                sha256:24e76fcec8c003a0362d0dd53f4806e7e79458d7fdeaf47437760e19496f5a9c   24e76fcec8c0   3 months ago    457MB
mariadb                                    12.3.2                sha256:a02fe89cb597d4375812b2eac90cf9d0775d4686daa7f7cc750ebbcad7525bbc   a02fe89cb597   3 months ago    464MB
redis                                      7.4.10-alpine         sha256:e7723ff73d963f5cc6d9c4643ea3d989527a402a319239054e9472a7fb9219a2   e7723ff73d96   3 months ago    57.8MB
prom/node-exporter                         latest                sha256:1b4e4438faca4dd7e001dd445d161a4a2091b0fededa84093b3a8dfeae1f1be0   1b4e4438faca   4 months ago    41MB
getmeili/meilisearch                       <none>                sha256:c1a52f17c759c2cd6349eede3d5108b8dac07b97e10665b1d64a2d4961c2fd29   c1a52f17c759   4 months ago    252MB
alpine                                     <none>                sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b   28bd5fe8b56d   5 months ago    13MB
grafana/grafana-oss                        <none>                sha256:5dad0df181cb644a14e13617b913b261a54f7d4fd4510721dba420929f35bea2   5dad0df181cb   5 months ago    1.47GB
crazymax/diun                              <none>                sha256:e324b793eb32dfb7f74d3a39421ebf090141caaadee69b8f78da63112408ee25   e324b793eb32   5 months ago    86.5MB
ghcr.io/karakeep-app/karakeep              <none>                sha256:64d6a9bbf2d37b5c808cf06b5d87f1f1c7846fdd3844724145a9741aeb06fd31   64d6a9bbf2d3   6 months ago    2.33GB
mysql                                      <none>                sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b   7dcddc01f13b   6 months ago    1.1GB
node                                       <none>                sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293   fb4cd12c85ee   7 months ago    194MB
nginx                                      <none>                sha256:0c8a74b863b202a8e9ce8b2f97cc8bf96bc573206d46c2c469d507095dd2c77e   0c8a74b863b2   8 months ago    92.4MB
gcr.io/cadvisor/cadvisor                   latest                sha256:3de2bd5203120b866d74a9b283b2ffb8ec382fbf9dc321814700c6ea6f44ec57   3de2bd520312   11 months ago   107MB
louislam/uptime-kuma                       <none>                sha256:3d632903e6af34139a37f18055c4f1bfd9b7205ae1138f1e5e8940ddc1d176f9   3d632903e6af   13 months ago   724MB
bitnamilegacy/minio                        latest                sha256:451fe6858cb770cc9d0e77ba811ce287420f781c7c1b806a386f6896471a349c   451fe6858cb7   17 months ago   398MB
influxdb                                   <none>                sha256:299ebda2c7e308dbef42e26ac9b8fd1d9b3bcb8a0aee80c6509aa0219c1d0290   299ebda2c7e3   2 years ago     458MB
couchdb                                    <none>                sha256:ee75c9a737e7c48af0170142689959f2d70f93700162fef40818c799dfeecb8e   ee75c9a737e7   6 years ago     313MB
```

GGUF SHA-256 values measured with `sha256sum chat.gguf embed.gguf`:
```text
9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031  chat.gguf
b5ce9d77a3fc4b3b39ccb5643c36777911cc4eb46a66962eadfa3f5f60490d63  embed.gguf
```

Pip cache relocation cleanup used `python3 cache-relocate.py`; exact executed source:
```python
from pathlib import Path
from datetime import datetime
import shutil,json
# Only files created and last modified in our two pip invocation windows.
windows=[(datetime.fromisoformat('2026-11-20T09:18:54-06:00').timestamp(),Path('torch-install.log').stat().st_mtime),(Path('ollama-python-install.log').stat().st_ctime-2,Path('ollama-python-install.log').stat().st_mtime+1)]
# Require birth time via statx exposed by GNU stat: ctime is not birth time.
import subprocess
moved=[]
for f in (Path.home()/'.cache/pip').rglob('*'):
 if not f.is_file():continue
 st=f.stat()
 if not any(a<=st.st_mtime<=b for a,b in windows):continue
 birth=int(subprocess.check_output(['stat','-c','%W',str(f)]))
 if not any(int(a)<=birth<=int(b) for a,b in windows):continue
 rel=f.relative_to('$HOME/.cache/pip');dest=Path('recovered-pip-cache')/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 moved.append({'file':str(f),'bytes':st.st_size});shutil.move(str(f),dest)
Path('cache-relocate-results.json').write_text(json.dumps(moved,indent=2));print('Relocated our pip cache entries:',len(moved),'bytes:',sum(x['bytes'] for x in moved))

```

Additional official docs fetched during troubleshooting: [Ollama Modelfile](https://docs.ollama.com/modelfile). Mem0 provider config, additive extraction implementation, and custom-instructions support were also inspected in the installed 2.2.1 package source.

Cleanup was executed with `python3 cleanup-lab.py` from the lab directory. Its `shutil.rmtree(lab)` removed the complete lab including downloaded models, venv, Qdrant state, recovered pip cache, npm packages and caches. The initial post-removal shell checks emitted a getcwd warning because the working directory had just been deleted; clean rechecks from the project directory follow. The filesystem delta includes concurrent workers cleaning up; the allocated lab directory itself was 5,275,828,224 bytes, and the three removed image identities/sizes are recorded above.

Clean rechecks from existing cwd:
```text
$ docker ps -a | grep memlab
exit=1
$ ss -ltnp | grep 391
LISTEN 0      4096                                127.0.0.1:39109      0.0.0.0:*                                                 
exit=0
$ df -h /var/tmp
Filesystem      Size  Used Avail Use% Mounted on
/dev/nvme0n1p2  915G  684G  185G  79% /
exit=0
```
Port 39109 was present before this test; it is unrelated and was preserved. No memlab containers remained at final check.

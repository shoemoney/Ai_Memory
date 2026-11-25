# Executed store walkthroughs

Test date: 2026-11-20. Ubuntu, Docker; loopback ports 39000–39099. Small deterministic vectors; no embedding model or GPU. Outputs below are from actual execution. Floating tags identify what was pulled on this test date; image digests pin the resolved builds.

## Shared setup and client versions

The following setup commands were executed before the walkthroughs. Save each displayed source block under its stated filename in this lab directory before running its client command. The sample password is a disposable local fixture, used only by the throwaway loopback-bound containers.

```bash
mkdir -p /var/tmp/memguide-lab-stores
python3 -m venv /var/tmp/memguide-lab-stores/venv
/var/tmp/memguide-lab-stores/venv/bin/pip install --no-cache-dir redis pymemcache qdrant-client chromadb lancedb sqlite-vec tantivy > /var/tmp/memguide-lab-stores/pip.log 2>&1
```

```bash
cd /var/tmp/memguide-lab-stores && pwd
```

```text
/var/tmp/memguide-lab-stores
```

```bash
venv/bin/python -c "import importlib.metadata as m; print('\n'.join(p+'=='+m.version(p) for p in ['redis','pymemcache','qdrant-client','chromadb','lancedb','tantivy','sqlite-vec']))"
```

```text
redis==8.1.0
pymemcache==4.0.0
qdrant-client==1.20.0
chromadb==1.5.9
lancedb==0.41.0
tantivy==0.27.0
sqlite-vec==0.1.9
```

```bash
venv/bin/pip freeze > requirements-tested.txt && cat requirements-tested.txt
```

```text
aiohappyeyeballs==2.7.1
aiohttp==3.14.5
aiohttp-retry==2.9.1
aiosignal==1.4.0
annotated-doc==0.0.7
annotated-types==0.8.0
anyio==4.16.0
attrs==26.1.0
bcrypt==5.0.0
build==1.6.1
certifi==2026.10.23
charset-normalizer==3.5.2
chromadb==1.5.9
click==8.5.1
deprecation==2.1.0
durationpy==0.11
filelock==4.2.12
flatbuffers==25.12.19
frozenlist==1.8.0
fsspec==2026.9.0
googleapis-common-protos==1.76.0
grpcio==1.85.3
h11==0.16.0
h2==4.4.1
hf-xet==1.8.0
hpack==4.2.0
httpcore==1.0.9
httpcore2==2.16.2
httptools==0.9.0
httpx==0.28.1
httpx2==2.16.2
huggingface_hub==2.4.0
hyperframe==6.1.0
idna==3.20
importlib_resources==7.1.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
kubernetes==37.0.3
lance-namespace==0.13.0
lance-namespace-urllib3-client==0.13.0
lancedb==0.41.0
markdown-it-py==4.3.0
mdurl==0.1.2
mmh3==5.3.1
multidict==7.2.1
numpy==2.5.5
oauthlib==4.0.1
onnxruntime==1.32.0
opentelemetry-api==1.45.2
opentelemetry-exporter-otlp-common==0.66b2
opentelemetry-exporter-otlp-proto-common==1.45.2
opentelemetry-exporter-otlp-proto-grpc==1.45.2
opentelemetry-proto==1.45.2
opentelemetry-sdk==1.45.2
opentelemetry-semantic-conventions==0.66b2
orjson==3.13.0
overrides==7.7.0
packaging==26.3
portalocker==4.4.2
propcache==0.5.4
protobuf==7.36.2
pyarrow==26.0.1
pybase64==1.5.2
pydantic==2.14.4
pydantic-settings==2.16.3
pydantic_core==2.50.5
Pygments==2.21.0
pymemcache==4.0.0
PyPika==0.51.1
pyproject_hooks==1.3.3
python-dateutil==4.0.0
python-dotenv==1.2.4
PyYAML==6.0.3
qdrant-client==1.20.0
redis==8.1.0
referencing==0.37.0
requests==2.34.2
requests-oauthlib==2.0.0
rich==15.0.0
rpds-py==2026.9.1
shellingham==1.5.4
sqlite-vec==0.1.9
tantivy==0.27.0
tenacity==9.2.1
tokenizers==0.23.3
tqdm==4.70.1
truststore==0.10.5
typer==0.29.2
typing-inspection==0.4.5
typing_extensions==4.16.0
tzdata==2026.6
urllib3==2.8.0
uvicorn==0.54.0
uvloop==0.23.0
watchfiles==1.3.0
websocket-client==1.9.2
websockets==17.4
yarl==1.25.1
```

Installation completed successfully; exact resolved package versions are in the pip freeze output above.


## 1. PostgreSQL + pgvector

Test date: 2026-11-20.

Versions: pgvector/pgvector:pg18; PostgreSQL 18.7; pgvector 0.8.7.

Gotchas: HNSW operator class and ORDER BY distance must agree (cosine here). The SQL forces index selection only to demonstrate use on this tiny fixture.

```bash
docker pull pgvector/pgvector:pg18
```

```text
pg18: Pulling from pgvector/pgvector
Digest: sha256:38681dc6eaf55308e2a4c6de392d131652dcfac70e1263e35cd9b5ea3fe39782
Status: Downloaded newer image for pgvector/pgvector:pg18
docker.io/pgvector/pgvector:pg18
```

```bash
docker image inspect pgvector/pgvector:pg18 --format '{{json .RepoDigests}}'
```

```text
["pgvector/pgvector@sha256:38681dc6eaf55308e2a4c6de392d131652dcfac70e1263e35cd9b5ea3fe39782"]
```

```bash
docker run -d --name memlab-pg -p 127.0.0.1:39001:5432 -e POSTGRES_PASSWORD=memlab-local-only pgvector/pgvector:pg18
```

```text
6f9e52087e45ccc1a080a222f47442f4f8e7e22a6f20e234c5bbf7103a76ac30
```

```bash
until docker exec memlab-pg pg_isready -U postgres; do sleep 1; done
```

```text
/var/run/postgresql:5432 - no response
/var/run/postgresql:5432 - no response
/var/run/postgresql:5432 - accepting connections
```

Executed client/SQL source (`pg.sql`):

```sql
SELECT version();
CREATE EXTENSION vector;
SELECT extversion FROM pg_extension WHERE extname='vector';
CREATE TABLE memories(id bigserial PRIMARY KEY,user_id text,kind text,content text,tsv tsvector GENERATED ALWAYS AS(to_tsvector('english',content)) STORED,embedding vector(384),created_at timestamptz DEFAULT now());
CREATE INDEX memories_hnsw ON memories USING hnsw(embedding vector_cosine_ops) WITH(m=16,ef_construction=64);
CREATE INDEX memories_fts ON memories USING gin(tsv);
SELECT setseed(0.42);
INSERT INTO memories(user_id,kind,content,embedding) SELECT 'alice','fact',CASE WHEN i%2=0 THEN 'agent memory loves databases' ELSE 'travel plans for Paris' END,ARRAY(SELECT (random()+i*0)::real FROM generate_series(1,384))::vector FROM generate_series(1,200) i;
SET hnsw.ef_search=80;
SELECT id,content FROM memories ORDER BY embedding <=> (SELECT embedding FROM memories WHERE id=1) LIMIT 3;
SELECT id,content FROM memories WHERE tsv @@ plainto_tsquery('english','agent memory') LIMIT 3;
WITH v AS(SELECT id,row_number() OVER(ORDER BY embedding <=> (SELECT embedding FROM memories WHERE id=1)) r FROM memories ORDER BY embedding <=> (SELECT embedding FROM memories WHERE id=1) LIMIT 10), f AS(SELECT id,row_number() OVER(ORDER BY ts_rank_cd(tsv,plainto_tsquery('agent memory')) DESC,id) r FROM memories WHERE tsv @@ plainto_tsquery('agent memory') LIMIT 10) SELECT id,coalesce(1.0/(60+v.r),0)+coalesce(1.0/(60+f.r),0) score FROM v FULL JOIN f USING(id) ORDER BY score DESC LIMIT 3;
SET enable_seqscan=off;
EXPLAIN SELECT id FROM memories ORDER BY embedding <=> (SELECT embedding FROM memories WHERE id=1) LIMIT 3;

```

```bash
docker exec -i memlab-pg psql -U postgres -v ON_ERROR_STOP=1 < pg.sql
```

```text
                                                          version                                                           
----------------------------------------------------------------------------------------------------------------------------
 PostgreSQL 18.7 (Debian 18.7-1.pgdg12+2) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14+deb12u1) 12.2.0, 64-bit
(1 row)

CREATE EXTENSION
 extversion 
------------
 0.8.7
(1 row)

CREATE TABLE
CREATE INDEX
CREATE INDEX
 setseed 
---------
 
(1 row)

INSERT 0 200
SET
 id  |           content            
-----+------------------------------
   1 | travel plans for Paris
 174 | agent memory loves databases
 158 | agent memory loves databases
(3 rows)

 id |           content            
----+------------------------------
  2 | agent memory loves databases
  4 | agent memory loves databases
  6 | agent memory loves databases
(3 rows)

 id  |         score          
-----+------------------------
   1 | 0.01639344262295081967
   2 | 0.01639344262295081967
 174 | 0.01612903225806451613
(3 rows)

SET
                                            QUERY PLAN                                            
--------------------------------------------------------------------------------------------------
 Limit  (cost=90.21..90.75 rows=3 width=16)
   InitPlan 1
     ->  Index Scan using memories_pkey on memories memories_1  (cost=0.15..8.17 rows=1 width=32)
           Index Cond: (id = 1)
   ->  Index Scan using memories_hnsw on memories  (cost=82.04..444.00 rows=2000 width=16)
         Order By: (embedding <=> (InitPlan 1).col1)
(6 rows)

```

Status: **TESTED**. For the tiny fixture, enable_seqscan=off demonstrates index eligibility; it is not a production tuning recommendation.


## 2. Redis 8

Test date: 2026-11-20.

Versions: redis:8; server 8.10.3; redis-py 8.1.0.

Gotchas: FLOAT32 hash vectors are binary little-endian bytes. FT.SEARCH uses DIALECT 2. redis-py 8.1.0 returned a structured dictionary for search and VSIM.

```bash
docker pull redis:8
```

```text
8: Pulling from library/redis
Digest: sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53
Status: Downloaded newer image for redis:8
docker.io/library/redis:8
```

```bash
docker image inspect redis:8 --format '{{json .RepoDigests}}'
```

```text
["redis@sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53"]
```

```bash
docker run -d --name memlab-redis -p 127.0.0.1:39002:6379  redis:8
```

```text
fd4f2f29b19519c07211b5c93dca50f054ef0384b5e13d3b6c47d3e48738c46a
```

Executed client/SQL source (`redis_test.py`):

```python
import redis,struct,importlib.metadata
r=redis.Redis(port=39002)
print('redis-py',importlib.metadata.version('redis'),'server',r.info()['redis_version'])
print('session',r.hset('session:alice',mapping={'summary':'likes databases'}),r.expire('session:alice',300),r.hgetall('session:alice'),r.ttl('session:alice'))
print('XADD',r.xadd('history:alice',{'role':'user','content':'remember me'}));print('XRANGE',r.xrange('history:alice'))
print('FT.CREATE',r.execute_command('FT.CREATE','memidx','ON','HASH','PREFIX',1,'memory:','SCHEMA','user_id','TAG','embedding','VECTOR','HNSW',6,'TYPE','FLOAT32','DIM',4,'DISTANCE_METRIC','COSINE'))
r.hset('memory:1',mapping={'user_id':'alice','embedding':struct.pack('<4f',1,0,0,0)})
print('KNN',r.execute_command('FT.SEARCH','memidx','*=>[KNN 2 @embedding $q AS distance]','PARAMS',2,'q',struct.pack('<4f',1,0,0,0),'SORTBY','distance','RETURN',1,'distance','DIALECT',2))
print('VADD',r.execute_command('VADD','memvectors','VALUES',4,1,0,0,0,'fact:1'))
print('VSIM',r.execute_command('VSIM','memvectors','VALUES',4,1,0,0,0,'COUNT',2,'WITHSCORES'))

```

```bash
venv/bin/python redis_test.py
```

```text
redis-py 8.1.0 server 8.10.3
session 1 True {b'summary': b'likes databases'} 300
XADD b'1795187953302-0'
XRANGE [(b'1795187953302-0', {b'role': b'user', b'content': b'remember me'})]
FT.CREATE b'OK'
KNN {b'attributes': [], b'format': b'STRING', b'results': [{b'id': b'memory:1', b'extra_attributes': {b'distance': b'0'}, b'values': []}], b'total_results': 1, b'warning': []}
VADD True
VSIM {b'fact:1': 1.0}
```

Status: **TESTED**. 


## 3. Valkey

Test date: 2026-11-20.

Versions: valkey/valkey:latest; Valkey 9.2.0; redis-py 8.1.0.

Gotchas: INFO redis_version reports compatibility version 7.2.4; INFO valkey_version identifies the actual server. The core image has no search module in MODULE LIST.

```bash
docker pull valkey/valkey:latest
```

```text
latest: Pulling from valkey/valkey
Digest: sha256:1c2b25b09f354c66fe994733acdf12fcfd4bdf6f3bd92b88a93a70378d884056
Status: Downloaded newer image for valkey/valkey:latest
docker.io/valkey/valkey:latest
```

```bash
docker image inspect valkey/valkey:latest --format '{{json .RepoDigests}}'
```

```text
["valkey/valkey@sha256:1c2b25b09f354c66fe994733acdf12fcfd4bdf6f3bd92b88a93a70378d884056"]
```

```bash
docker run -d --name memlab-valkey -p 127.0.0.1:39003:6379  valkey/valkey:latest
```

```text
33538064c39e495e8edccf1b039b1bb64c57e14fdff184899edc899ec400189c
```

Executed client/SQL source (`valkey_test.py`):

```python
import redis
r=redis.Redis(port=39003)
print('server',r.info()['redis_version'],r.info().get('valkey_version'))
print(r.hset('session:alice',mapping={'summary':'likes databases'}),r.expire('session:alice',300),r.hgetall('session:alice'),r.ttl('session:alice'))
print(r.xadd('history:alice',{'role':'user','content':'remember me'}));print(r.xrange('history:alice'))
print('modules',r.execute_command('MODULE','LIST'))

```

```bash
venv/bin/python valkey_test.py
```

```text
server 7.2.4 9.2.0
1 True {b'summary': b'likes databases'} 300
b'1795187960329-0'
[(b'1795187960329-0', {b'role': b'user', b'content': b'remember me'})]
modules [{b'name': b'lua', b'ver': 1, b'path': b'lua', b'args': []}]
```

Status: **TESTED**. Core Valkey session/hash/stream test; search requires a bundle/module.


## 3b. Valkey bundle vector search

Test date: 2026-11-20.

Versions: valkey/valkey-bundle:latest; Valkey 9.2.0; search module numeric version 66304; redis-py 8.1.0.

Gotchas: The bundle loads search; the core image does not. This test waited one second after writing before querying the index.

```bash
docker pull valkey/valkey-bundle:latest
```

```text
latest: Pulling from valkey/valkey-bundle
Digest: sha256:cc210fe648eea982a9b3d76c429859ca150e2b653aa9b3cd81e58c9b49940404
Status: Downloaded newer image for valkey/valkey-bundle:latest
docker.io/valkey/valkey-bundle:latest
```

```bash
docker image inspect valkey/valkey-bundle:latest --format '{{json .RepoDigests}}'
```

```text
["valkey/valkey-bundle@sha256:cc210fe648eea982a9b3d76c429859ca150e2b653aa9b3cd81e58c9b49940404"]
```

```bash
docker run -d --name memlab-valkey-bundle -p 127.0.0.1:39004:6379  valkey/valkey-bundle:latest
```

```text
c5aa74fb1902c61f68bd65ab05aa74e7082b0bd15c5634ae2a8edc92f5307ad0
```

Executed client/SQL source (`valkey_vector.py`):

```python
import redis,struct,time
r=redis.Redis(port=39004)
print('version',r.info());print('modules',r.execute_command('MODULE','LIST'))
print(r.execute_command('FT.CREATE','idx','ON','HASH','PREFIX',1,'memory:','SCHEMA','embedding','VECTOR','HNSW',6,'TYPE','FLOAT32','DIM',4,'DISTANCE_METRIC','COSINE'))
r.hset('memory:1',mapping={'embedding':struct.pack('<4f',1,0,0,0)})
time.sleep(1)
print(r.execute_command('FT.SEARCH','idx','*=>[KNN 2 @embedding $q AS distance]','PARAMS',2,'q',struct.pack('<4f',1,0,0,0),'SORTBY','distance','DIALECT',2))

```

```bash
venv/bin/python valkey_vector.py
```

```text
version {'redis_version': '7.2.4', 'server_name': 'valkey', 'valkey_version': '9.2.0', 'valkey_release_stage': 'ga', …} [unrelated INFO fields trimmed]
modules [{b'name': b'json', b'ver': 10100, b'path': b'/usr/lib/valkey/libjson.so', b'args': []}, {b'name': b'search', b'ver': 66304, b'path': b'/usr/lib/valkey/libsearch.so', b'args': []}, {b'name': b'bf', b'ver': 10001, b'path': b'/usr/lib/valkey/libvalkey_bloom.so', b'args': []}, {b'name': b'ldap', b'ver': 16843263, b'path': b'/usr/lib/valkey/libvalkey_ldap.so', b'args': []}, {b'name': b'lua', b'ver': 1, b'path': b'lua', b'args': []}]
b'OK'
[1, b'memory:1', [b'distance', b'0', b'embedding', b'\x00\x00\x80?\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00']]
```

Status: **TESTED**. 


## 4. Memcached

Test date: 2026-11-20.

Versions: memcached:latest; server 1.6.45; pymemcache 4.0.0.

Gotchas: Use default_noreply=False to receive write errors. -I 2m allowed the tested 1,048,577-byte value; the default rejected it.

```bash
docker pull memcached:latest
```

```text
latest: Pulling from library/memcached
Digest: sha256:a395a1bcf5e0e2b0fa4a0142e12b4e24a2320ba4b7c6ffa8655a1a86e8f29dee
Status: Downloaded newer image for memcached:latest
docker.io/library/memcached:latest
```

```bash
docker image inspect memcached:latest --format '{{json .RepoDigests}}'
```

```text
["memcached@sha256:a395a1bcf5e0e2b0fa4a0142e12b4e24a2320ba4b7c6ffa8655a1a86e8f29dee"]
```

```bash
docker run -d --name memlab-memcache -p 127.0.0.1:39005:11211  memcached:latest
```

```text
779d918d93bdb1619d47888bb893b278461fe012b19bb1fc4b24eb958719ce11
```

```bash
docker exec memlab-memcache memcached --version
```

```text
memcached 1.6.45
```

```bash
docker run -d --name memlab-memcache-large -p 127.0.0.1:39006:11211 memcached:latest memcached -I 2m
```

```text
40add4c875b7eab3751467b310be7ccf8d47e5b59d4a16159c850806d2f3c1da
```

Executed client/SQL source (`memcache.py`):

```python
from pymemcache.client.base import Client
import hashlib,json,importlib.metadata
print('pymemcache',importlib.metadata.version('pymemcache'))
c=Client(('127.0.0.1',39005),default_noreply=False)
print('set/get TTL',c.set('session:alice','summary',expire=60),c.get('session:alice'))
try: c.set('large',b'x'*(1024*1024+1),noreply=False)
except Exception as e: print('default rejection',type(e).__name__,str(e))
c2=Client(('127.0.0.1',39006),default_noreply=False)
print('raised limit',c2.set('large',b'x'*(1024*1024+1)),len(c2.get('large')))
def embedding_cache(model,text,compute):
    key=hashlib.sha256((model+'\0'+text).encode()).hexdigest()
    cached=c.get(key)
    if cached is not None: return json.loads(cached)
    vector=compute(text)
    c.set(key,json.dumps(vector),expire=3600)
    return vector
print('cache miss',embedding_cache('demo-v1','hello',lambda text:[1.,0.,0.,0.]))
print('cache hit',embedding_cache('demo-v1','hello',lambda text:(_ for _ in ()).throw(Exception('must not compute'))))

```

```bash
venv/bin/python memcache.py
```

```text
pymemcache 4.0.0
set/get TTL True b'summary'
default rejection MemcacheServerError b'object too large for cache'
raised limit True 1048577
cache miss [1.0, 0.0, 0.0, 0.0]
cache hit [1.0, 0.0, 0.0, 0.0]
```

Status: **TESTED**. default_noreply=False is necessary to observe server errors on writes.


## 5. Qdrant

Test date: 2026-11-20.

Versions: qdrant/qdrant:latest; server 1.20.2; qdrant-client 1.20.0.

Gotchas: The tested client API is query_points. The payload filter returned only Alice’s point.

```bash
docker pull qdrant/qdrant:latest
```

```text
latest: Pulling from qdrant/qdrant
Digest: sha256:d277592721d2e3b73f9b797b53cf05e6a5bb2134f6d13fdbda4ca51782afbcac
Status: Downloaded newer image for qdrant/qdrant:latest
docker.io/qdrant/qdrant:latest
```

```bash
docker image inspect qdrant/qdrant:latest --format '{{json .RepoDigests}}'
```

```text
["qdrant/qdrant@sha256:d277592721d2e3b73f9b797b53cf05e6a5bb2134f6d13fdbda4ca51782afbcac"]
```

```bash
docker run -d --name memlab-qdrant -p 127.0.0.1:39007:6333  qdrant/qdrant:latest
```

```text
e3045f33efbe72e0287ed83b4a362571d532c4ed4d04d5f92390f95efcc7ecc8
```

Executed client/SQL source (`qdrant_test.py`):

```python
from qdrant_client import QdrantClient,models
import importlib.metadata
c=QdrantClient(url='http://127.0.0.1:39007')
print('client',importlib.metadata.version('qdrant-client'),'server',c.info())
c.create_collection('memories',vectors_config=models.VectorParams(size=4,distance=models.Distance.COSINE))
print(c.upsert('memories',points=[models.PointStruct(id=1,vector=[1.,0.,0.,0.],payload={'user_id':'alice','content':'likes databases'}),models.PointStruct(id=2,vector=[0.,1.,0.,0.],payload={'user_id':'bob'})],wait=True))
print(c.query_points('memories',query=[1.,0.,0.,0.],query_filter=models.Filter(must=[models.FieldCondition(key='user_id',match=models.MatchValue(value='alice'))]),with_payload=True,limit=3))

```

```bash
venv/bin/python qdrant_test.py
```

```text
client 1.20.0 server title='qdrant - vector search engine' version='1.20.2' commit='23065a0bf6857c3e5da45f6c8939cc746cc0580e'
operation_id=1 status=<UpdateStatus.COMPLETED: 'completed'>
points=[ScoredPoint(id=1, version=1, score=1.0, payload={'user_id': 'alice', 'content': 'likes databases'}, vector=None, shard_key=None, order_value=None)]
```

Status: **TESTED**. 

## 6. Chroma

Test date: 2026-11-20.

Versions: chromadb 1.5.9 (embedded PersistentClient).

Gotchas: Pass explicit embeddings on add and query_embeddings on query. embedding_function=None avoids model downloads.

Executed client/SQL source (`chroma_test.py`):

```python
import chromadb,importlib.metadata
print('chromadb',importlib.metadata.version('chromadb'))
c=chromadb.PersistentClient(path='./chroma-data')
t=c.get_or_create_collection('memories',embedding_function=None)
t.add(ids=['1','2'],documents=['likes databases','travel to Paris'],embeddings=[[1.,0.,0.,0.],[0.,1.,0.,0.]],metadatas=[{'user_id':'alice'},{'user_id':'bob'}])
print(t.query(query_embeddings=[[1.,0.,0.,0.]],n_results=2,include=['documents','distances']))

```

```bash
venv/bin/python chroma_test.py
```

```text
chromadb 1.5.9
{'ids': [['1', '2']], 'embeddings': None, 'documents': [['likes databases', 'travel to Paris']], 'uris': None, 'included': ['documents', 'distances'], 'data': None, 'metadatas': None, 'distances': [[0.0, 2.0]]}
```

Status: **TESTED**. 

## 7. LanceDB

Test date: 2026-11-20.

Versions: lancedb 0.41.0; tantivy 0.27.0 installed.

Gotchas: create_fts_index worked but emitted a deprecation warning. The follow-up below tested the recommended create_index with FTS API.

Executed client/SQL source (`lance_test.py`):

```python
import lancedb,importlib.metadata
print('lancedb',importlib.metadata.version('lancedb'),'tantivy',importlib.metadata.version('tantivy'))
c=lancedb.connect('./lance-data')
t=c.create_table('memories',data=[{'id':1,'text':'agent memory databases','vector':[1.,0.,0.,0.]},{'id':2,'text':'Paris travel plans','vector':[0.,1.,0.,0.]}])
print('vector',t.search([1.,0.,0.,0.]).limit(2).to_list())
t.create_fts_index('text')
print('fts',t.search('memory',query_type='fts').limit(2).to_list())

```

```bash
venv/bin/python lance_test.py
```

```text
/var/tmp/memguide-lab-stores/lance_test.py:6: DeprecatedWarning: create_fts_index is deprecated as of 0.25.0. Use create_index() with config=FTS() instead.
  t.create_fts_index('text')
lancedb 0.41.0 tantivy 0.27.0
vector [{'id': 1, 'text': 'agent memory databases', 'vector': [1.0, 0.0, 0.0, 0.0], '_distance': 0.0}, {'id': 2, 'text': 'Paris travel plans', 'vector': [0.0, 1.0, 0.0, 0.0], '_distance': 2.0}]
fts [{'id': 1, 'text': 'agent memory databases', 'vector': [1.0, 0.0, 0.0, 0.0], '_score': 0.6931471824645996}]
```

Status: **TESTED**. 

### LanceDB current FTS API follow-up

The installed official package docstring recommends create_index with FTS; this follow-up was run to avoid the deprecation above.

Executed client/SQL source (`lance_modern.py`):

```python
import lancedb
from lancedb.index import FTS
c=lancedb.connect('./lance-modern-data')
t=c.create_table('memories',data=[{'id':1,'text':'agent memory databases','vector':[1.,0.,0.,0.]},{'id':2,'text':'Paris travel plans','vector':[0.,1.,0.,0.]}])
t.create_index('text',config=FTS())
print('vector',t.search([1.,0.,0.,0.]).limit(2).to_list())
print('fts',t.search('memory',query_type='fts').limit(2).to_list())

```

```bash
venv/bin/python lance_modern.py
```

```text
vector [{'id': 1, 'text': 'agent memory databases', 'vector': [1.0, 0.0, 0.0, 0.0], '_distance': 0.0}, {'id': 2, 'text': 'Paris travel plans', 'vector': [0.0, 1.0, 0.0, 0.0], '_distance': 2.0}]
fts [{'id': 1, 'text': 'agent memory databases', 'vector': [1.0, 0.0, 0.0, 0.0], '_score': 0.6931471824645996}]
```

Status: **TESTED**. Use this current FTS API in new code. The earlier create_fts_index API still worked but emitted a deprecation warning.


## 8. SQLite + sqlite-vec + FTS5

Test date: 2026-11-20.

Versions: SQLite runtime 3.46.1; sqlite-vec package and extension 0.1.9.

Gotchas: The sqlite-vec KNN query needs k=3 here. FTS MATCH has its own query grammar: an unquoted hyphen produces no such column: memory.

Executed client/SQL source (`sqlite_test.py`):

```python
import sqlite3,sqlite_vec,struct,importlib.metadata
c=sqlite3.connect('memories.sqlite')
c.enable_load_extension(True);sqlite_vec.load(c);c.enable_load_extension(False)
print('SQLite',sqlite3.sqlite_version,'sqlite-vec package',importlib.metadata.version('sqlite-vec'),'extension',c.execute('select vec_version()').fetchone())
c.executescript("CREATE VIRTUAL TABLE docs USING fts5(content); CREATE VIRTUAL TABLE vectors USING vec0(embedding float[4]);")
for i,(text,v) in enumerate([('agent memory databases',[1.,0.,0.,0.]),('Paris travel plans',[0.,1.,0.,0.]),('agent-memory tips',[0.9,0.1,0.,0.])],1):
 c.execute('INSERT INTO docs(rowid,content) VALUES(?,?)',(i,text));c.execute('INSERT INTO vectors(rowid,embedding) VALUES(?,?)',(i,struct.pack('<4f',*v)))
c.commit()
v=c.execute('SELECT rowid,distance FROM vectors WHERE embedding MATCH ? AND k=3 ORDER BY distance',(struct.pack('<4f',1,0,0,0),)).fetchall()
f=c.execute("SELECT rowid,bm25(docs) FROM docs WHERE docs MATCH ? ORDER BY bm25(docs)",('memory',)).fetchall()
scores={}
for ranked in (v,f):
 for rank,(id,_) in enumerate(ranked,1):scores[id]=scores.get(id,0)+1/(60+rank)
print('vector',v,'fts',f,'RRF',sorted(scores.items(),key=lambda x:x[1],reverse=True))
try:c.execute('SELECT rowid FROM docs WHERE docs MATCH ?',('agent-memory',)).fetchall()
except sqlite3.OperationalError as e:print('unquoted hyphen error',e)
print('quoted phrase',c.execute('SELECT rowid FROM docs WHERE docs MATCH ?',('"agent-memory"',)).fetchall())

```

```bash
venv/bin/python sqlite_test.py
```

```text
SQLite 3.46.1 sqlite-vec package 0.1.9 extension ('v0.1.9',)
vector [(1, 0.0), (3, 0.141421377658844), (2, 1.4142135381698608)] fts [(1, -1e-06), (3, -1e-06)] RRF [(1, 0.03278688524590164), (3, 0.03225806451612903), (2, 0.015873015873015872)]
unquoted hyphen error no such column: memory
quoted phrase [(1,), (3,)]
```

Status: **TESTED**. Quote hyphenated phrases inside MATCH; SQL parameterization alone does not quote the FTS query language.


## 9. MariaDB vector search

Test date: 2026-11-20.

Versions: mariadb:lts; server 12.3.3-MariaDB-ubu2404.

Gotchas: The vector column is NOT NULL, matching VECTOR INDEX requirements. The cosine distance function is VEC_DISTANCE_COSINE and the index is configured DISTANCE=cosine.

```bash
docker pull mariadb:lts
```

```text
lts: Pulling from library/mariadb
Digest: sha256:4aaf88b3106382c8c18e49f0cec60267be618fc22f858c4503afb2a2555afed3
Status: Downloaded newer image for mariadb:lts
docker.io/library/mariadb:lts
```

```bash
docker image inspect mariadb:lts --format '{{json .RepoDigests}}'
```

```text
["mariadb@sha256:4aaf88b3106382c8c18e49f0cec60267be618fc22f858c4503afb2a2555afed3"]
```

```bash
docker run -d --name memlab-maria -p 127.0.0.1:39008:3306 -e MARIADB_ROOT_PASSWORD=memlab-local-only mariadb:lts
```

```text
c3e5582aca9280544fc73cd899054b19b6bb93e2964cf1c1d27fc9c55d111650
```

```bash
until docker exec memlab-maria mariadb-admin ping -uroot -pmemlab-local-only --silent; do sleep 1; done
```

```text
mysqld is alive
```

Executed client/SQL source (`maria.sql`):

```sql
SELECT VERSION();
CREATE DATABASE memlab;
USE memlab;
CREATE TABLE memories(id INT PRIMARY KEY, content TEXT, embedding VECTOR(4) NOT NULL, VECTOR INDEX(embedding) M=8 DISTANCE=cosine);
INSERT INTO memories VALUES(1,'likes databases',VEC_FromText('[1,0,0,0]')),(2,'Paris travel',VEC_FromText('[0,1,0,0]'));
SELECT id,content,VEC_DISTANCE_COSINE(embedding,VEC_FromText('[1,0,0,0]')) AS distance FROM memories ORDER BY distance LIMIT 2;
EXPLAIN SELECT id FROM memories ORDER BY VEC_DISTANCE_COSINE(embedding,VEC_FromText('[1,0,0,0]')) LIMIT 2;

```

```bash
docker exec -i memlab-maria mariadb -uroot -pmemlab-local-only < maria.sql
```

```text
VERSION()
12.3.3-MariaDB-ubu2404
id	content	distance
1	likes databases	0
2	Paris travel	1
id	select_type	table	type	possible_keys	key	key_len	ref	rows	Extra
1	SIMPLE	memories	index	NULL	embedding	18	NULL	2	
```

Status: **TESTED**. 


## 10. Neo4j Community temporal facts

Test date: 2026-11-20.

Versions: neo4j:community; server 2026.10.2; Community edition.

Gotchas: A missing invalid_at property evaluates to null. The query treats invalid_at as an exclusive upper bound and filters out the expired Travel relationship. Authentication was disabled only for this loopback-bound disposable lab.

```bash
docker pull neo4j:community
```

```text
community: Pulling from library/neo4j
Digest: sha256:4a2fd4f41ce384aa7d6a74b399f22c202e154f3966119c28a18ed9a500904f5e
Status: Downloaded newer image for neo4j:community
docker.io/library/neo4j:community
```

```bash
docker image inspect neo4j:community --format '{{json .RepoDigests}}'
```

```text
["neo4j@sha256:4a2fd4f41ce384aa7d6a74b399f22c202e154f3966119c28a18ed9a500904f5e"]
```

```bash
docker run -d --name memlab-neo4j -p 127.0.0.1:39009:7687 -e NEO4J_AUTH=none -e NEO4J_server_memory_heap_initial__size=128m -e NEO4J_server_memory_heap_max__size=256m -e NEO4J_server_memory_pagecache_size=128m neo4j:community
```

```text
5d8c2471ded586b132982aad363f16f4c27c2f3e31ae82d209dbf88a28d9384f
```

```bash
until docker exec memlab-neo4j cypher-shell "RETURN 1"; do sleep 2; done
```

```text
finishConnect(..) failed with error(-111): Connection refused
finishConnect(..) failed with error(-111): Connection refused
1
1
```

Executed client/SQL source (`neo.cypher`):

```cypher
CALL dbms.components() YIELD name,versions,edition RETURN name,versions,edition;
CREATE (a:Person {name:'Alice'}),(b:Topic {name:'Databases'}),(c:Topic {name:'Travel'}), (a)-[:LIKES {valid_from:datetime('2026-01-01T00:00:00Z')}]->(b), (a)-[:LIKES {valid_from:datetime('2025-01-01T00:00:00Z'),invalid_at:datetime('2026-01-01T00:00:00Z')}]->(c);
MATCH (a:Person)-[r:LIKES]->(b:Topic) WHERE r.valid_from <= datetime() AND (r.invalid_at IS NULL OR r.invalid_at > datetime()) RETURN a.name,b.name,r.valid_from,r.invalid_at;

```

```bash
docker exec -i memlab-neo4j cypher-shell < neo.cypher
```

```text
name, versions, edition
"Neo4j Kernel", ["2026.10.2"], "community"
"Cypher", ["5", "25"], ""
a.name, b.name, r.valid_from, r.invalid_at
"Alice", "Databases", 2026-01-01T00:00Z, NULL
```

Status: **TESTED**. Missing relationship property reads as null; invalid_at is an exclusive validity bound.

## Cleanup and image inventory

Only this lab’s explicit container names and newly pulled image tags were removed. Other workers may have containers named memlab-*; they are excluded from cleanup. No image prune or prefix-based deletion was used.

Before testing, executed `docker images --no-trunc > /var/tmp/memguide-lab-stores/images-before.txt` and `docker image ls -q --no-trunc > /var/tmp/memguide-lab-stores/ids-before.txt`. Full before inventory:

```text
REPOSITORY                                 TAG                   IMAGE ID                                                                  CREATED         SIZE
ubuntu                                     24.04                 sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8   10 days ago     119MB
redis                                      7                     sha256:2e3eb11462c4e3759e6972678dd051d150ff54b1e60714b3c33b701260172a90   2 weeks ago     170MB
nginx                                      stable                sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   2 weeks ago     242MB
mariadb                                    <none>                sha256:c4124d1afa875e47f2892edf26b482fa54f796e2f342d3717a04ca091a22a9bd   3 weeks ago     458MB
redis                                      <none>                sha256:6ba19c50b56777f5c11c58eff8ddb69d0d5f27ba131cffb63f180ccfd43c66af   3 weeks ago     57.8MB
composer                                   2.10.3                sha256:2cf275428757e5435a667bfc0d038b14520ca02be2b1b70d44a05c8c19e2de48   4 weeks ago     316MB
node                                       22.23.3-trixie-slim   sha256:28d03803f09ba76560e273af33beb7eda4ed68fa0698bc9bd15e9a6e35693923   4 weeks ago     333MB
nginx                                      1.30.5                sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   6 weeks ago     242MB
grafana/alloy                              <none>                sha256:2aa2099af76c0098d4af7a4d6e48f86cb66dc1a000222ad927a1c67c6542d13f   7 weeks ago     946MB
prom/prometheus                            <none>                sha256:efd719c99d83b060d9daefdcf00360461adf279f45ef5391f8d111892118753e   8 weeks ago     381MB
mariadb                                    11.8.8                sha256:24e76fcec8c003a0362d0dd53f4806e7e79458d7fdeaf47437760e19496f5a9c   3 months ago    457MB
mariadb                                    12.3.2                sha256:a02fe89cb597d4375812b2eac90cf9d0775d4686daa7f7cc750ebbcad7525bbc   3 months ago    464MB
redis                                      7.4.10-alpine         sha256:e7723ff73d963f5cc6d9c4643ea3d989527a402a319239054e9472a7fb9219a2   3 months ago    57.8MB
prom/node-exporter                         latest                sha256:1b4e4438faca4dd7e001dd445d161a4a2091b0fededa84093b3a8dfeae1f1be0   4 months ago    41MB
getmeili/meilisearch                       <none>                sha256:c1a52f17c759c2cd6349eede3d5108b8dac07b97e10665b1d64a2d4961c2fd29   4 months ago    252MB
alpine                                     <none>                sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b   5 months ago    13MB
grafana/grafana-oss                        <none>                sha256:5dad0df181cb644a14e13617b913b261a54f7d4fd4510721dba420929f35bea2   5 months ago    1.47GB
crazymax/diun                              <none>                sha256:e324b793eb32dfb7f74d3a39421ebf090141caaadee69b8f78da63112408ee25   5 months ago    86.5MB
ghcr.io/karakeep-app/karakeep              <none>                sha256:64d6a9bbf2d37b5c808cf06b5d87f1f1c7846fdd3844724145a9741aeb06fd31   6 months ago    2.33GB
mysql                                      <none>                sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b   6 months ago    1.1GB
node                                       <none>                sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293   7 months ago    194MB
nginx                                      <none>                sha256:0c8a74b863b202a8e9ce8b2f97cc8bf96bc573206d46c2c469d507095dd2c77e   8 months ago    92.4MB
gcr.io/cadvisor/cadvisor                   latest                sha256:3de2bd5203120b866d74a9b283b2ffb8ec382fbf9dc321814700c6ea6f44ec57   11 months ago   107MB
louislam/uptime-kuma                       <none>                sha256:3d632903e6af34139a37f18055c4f1bfd9b7205ae1138f1e5e8940ddc1d176f9   13 months ago   724MB
bitnamilegacy/minio                        latest                sha256:451fe6858cb770cc9d0e77ba811ce287420f781c7c1b806a386f6896471a349c   17 months ago   398MB
influxdb                                   <none>                sha256:299ebda2c7e308dbef42e26ac9b8fd1d9b3bcb8a0aee80c6509aa0219c1d0290   2 years ago     458MB
couchdb                                    <none>                sha256:ee75c9a737e7c48af0170142689959f2d70f93700162fef40818c799dfeecb8e   6 years ago     313MB
```

```bash
docker inspect memlab-pg memlab-redis memlab-valkey memlab-valkey-bundle memlab-memcache memlab-memcache-large memlab-qdrant memlab-maria memlab-neo4j --format '{{.Name}} {{json .Mounts}}'
```

```text
/memlab-pg [{"Type":"volume","Name":"67598b6dc56f5ee10249dfc41a0abf4bfa6792dba9ce09f98e9e97b7c5c60102","Source":"/var/lib/docker/volumes/67598b6dc56f5ee10249dfc41a0abf4bfa6792dba9ce09f98e9e97b7c5c60102/_data","Destination":"/var/lib/postgresql","Driver":"local","Mode":"","RW":true,"Propagation":""}]
/memlab-redis []
/memlab-valkey []
/memlab-valkey-bundle []
/memlab-memcache []
/memlab-memcache-large []
/memlab-qdrant []
/memlab-maria [{"Type":"volume","Name":"b4d0d103d8ed46552af2eb5e0031e0465a65e223a042073f9bf2e984ba587ca9","Source":"/var/lib/docker/volumes/b4d0d103d8ed46552af2eb5e0031e0465a65e223a042073f9bf2e984ba587ca9/_data","Destination":"/var/lib/mysql","Driver":"local","Mode":"","RW":true,"Propagation":""}]
/memlab-neo4j [{"Type":"volume","Name":"19867cd43c440fcb0991c293c13fd2ffdcc592f3e5071014ca2eb83e2606f963","Source":"/var/lib/docker/volumes/19867cd43c440fcb0991c293c13fd2ffdcc592f3e5071014ca2eb83e2606f963/_data","Destination":"/logs","Driver":"local","Mode":"","RW":true,"Propagation":""},{"Type":"volume","Name":"eddb53f2a57abe9d49ccc97ead749c9120191c6d141e7f838e758ead63288473","Source":"/var/lib/docker/volumes/eddb53f2a57abe9d49ccc97ead749c9120191c6d141e7f838e758ead63288473/_data","Destination":"/data","Driver":"local","Mode":"","RW":true,"Propagation":""}]
```

```bash
docker rm -fv memlab-pg memlab-redis memlab-valkey memlab-valkey-bundle memlab-memcache memlab-memcache-large memlab-qdrant memlab-maria memlab-neo4j
```

```text
memlab-pg
memlab-redis
memlab-valkey
memlab-valkey-bundle
memlab-memcache
memlab-memcache-large
memlab-qdrant
memlab-maria
memlab-neo4j
```

```bash
docker image inspect pgvector/pgvector:pg18 --format '{{.Id}}'
```

```text
sha256:38681dc6eaf55308e2a4c6de392d131652dcfac70e1263e35cd9b5ea3fe39782
```

```bash
docker image rm pgvector/pgvector:pg18
```

```text
Untagged: pgvector/pgvector:pg18
Deleted: sha256:38681dc6eaf55308e2a4c6de392d131652dcfac70e1263e35cd9b5ea3fe39782
```

```bash
docker image inspect redis:8 --format '{{.Id}}'
```

```text
sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53
```

```bash
docker image rm redis:8
```

```text
Untagged: redis:8
Deleted: sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53
```

```bash
docker image inspect valkey/valkey:latest --format '{{.Id}}'
```

```text
sha256:1c2b25b09f354c66fe994733acdf12fcfd4bdf6f3bd92b88a93a70378d884056
```

```bash
docker image rm valkey/valkey:latest
```

```text
Untagged: valkey/valkey:latest
Deleted: sha256:1c2b25b09f354c66fe994733acdf12fcfd4bdf6f3bd92b88a93a70378d884056
```

```bash
docker image inspect valkey/valkey-bundle:latest --format '{{.Id}}'
```

```text
sha256:cc210fe648eea982a9b3d76c429859ca150e2b653aa9b3cd81e58c9b49940404
```

```bash
docker image rm valkey/valkey-bundle:latest
```

```text
Untagged: valkey/valkey-bundle:latest
Deleted: sha256:cc210fe648eea982a9b3d76c429859ca150e2b653aa9b3cd81e58c9b49940404
```

```bash
docker image inspect memcached:latest --format '{{.Id}}'
```

```text
sha256:a395a1bcf5e0e2b0fa4a0142e12b4e24a2320ba4b7c6ffa8655a1a86e8f29dee
```

```bash
docker image rm memcached:latest
```

```text
Untagged: memcached:latest
Deleted: sha256:a395a1bcf5e0e2b0fa4a0142e12b4e24a2320ba4b7c6ffa8655a1a86e8f29dee
```

```bash
docker image inspect qdrant/qdrant:latest --format '{{.Id}}'
```

```text
sha256:d277592721d2e3b73f9b797b53cf05e6a5bb2134f6d13fdbda4ca51782afbcac
```

```bash
docker image rm qdrant/qdrant:latest
```

```text
Untagged: qdrant/qdrant:latest
Deleted: sha256:d277592721d2e3b73f9b797b53cf05e6a5bb2134f6d13fdbda4ca51782afbcac
```

```bash
docker image inspect mariadb:lts --format '{{.Id}}'
```

```text
sha256:4aaf88b3106382c8c18e49f0cec60267be618fc22f858c4503afb2a2555afed3
```

```bash
docker image rm mariadb:lts
```

```text
Untagged: mariadb:lts
Deleted: sha256:4aaf88b3106382c8c18e49f0cec60267be618fc22f858c4503afb2a2555afed3
```

```bash
docker image inspect neo4j:community --format '{{.Id}}'
```

```text
sha256:4a2fd4f41ce384aa7d6a74b399f22c202e154f3966119c28a18ed9a500904f5e
```

```bash
docker image rm neo4j:community
```

```text
Untagged: neo4j:community
Deleted: sha256:4a2fd4f41ce384aa7d6a74b399f22c202e154f3966119c28a18ed9a500904f5e
```

```bash
docker images --no-trunc > images-after.txt && cat images-after.txt
```

```text
REPOSITORY                                      TAG                   IMAGE ID                                                                  CREATED         SIZE
ghcr.io/ggml-org/llama.cpp                      server                sha256:5b43086e3ba7ea5794d72904654f6cd41224a9b1c6ac0398f4940ee380d30f23   3 days ago      1.16GB
ubuntu                                          24.04                 sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8   10 days ago     119MB
ollama/ollama                                   latest                sha256:910d0d8107b538fb0894e63163eb195de0cc7aefcbc666dc62d3b18f71124592   10 days ago     8.52GB
redis                                           7                     sha256:2e3eb11462c4e3759e6972678dd051d150ff54b1e60714b3c33b701260172a90   2 weeks ago     170MB
nginx                                           stable                sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703   2 weeks ago     242MB
mariadb                                         <none>                sha256:c4124d1afa875e47f2892edf26b482fa54f796e2f342d3717a04ca091a22a9bd   3 weeks ago     458MB
redis                                           <none>                sha256:6ba19c50b56777f5c11c58eff8ddb69d0d5f27ba131cffb63f180ccfd43c66af   3 weeks ago     57.8MB
composer                                        2.10.3                sha256:2cf275428757e5435a667bfc0d038b14520ca02be2b1b70d44a05c8c19e2de48   4 weeks ago     316MB
node                                            22.23.3-trixie-slim   sha256:28d03803f09ba76560e273af33beb7eda4ed68fa0698bc9bd15e9a6e35693923   4 weeks ago     333MB
nginx                                           1.30.5                sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb   6 weeks ago     242MB
grafana/alloy                                   <none>                sha256:2aa2099af76c0098d4af7a4d6e48f86cb66dc1a000222ad927a1c67c6542d13f   7 weeks ago     946MB
prom/prometheus                                 <none>                sha256:efd719c99d83b060d9daefdcf00360461adf279f45ef5391f8d111892118753e   8 weeks ago     381MB
ghcr.io/huggingface/text-embeddings-inference   cpu-1.9               sha256:2538ea1c9640d3763b15af668039d24172d063b42337b0c27796fc2be180c78d   2 months ago    938MB
mariadb                                         12.3.2                sha256:a02fe89cb597d4375812b2eac90cf9d0775d4686daa7f7cc750ebbcad7525bbc   3 months ago    464MB
mariadb                                         11.8.8                sha256:24e76fcec8c003a0362d0dd53f4806e7e79458d7fdeaf47437760e19496f5a9c   3 months ago    457MB
redis                                           7.4.10-alpine         sha256:e7723ff73d963f5cc6d9c4643ea3d989527a402a319239054e9472a7fb9219a2   3 months ago    57.8MB
prom/node-exporter                              latest                sha256:1b4e4438faca4dd7e001dd445d161a4a2091b0fededa84093b3a8dfeae1f1be0   4 months ago    41MB
getmeili/meilisearch                            <none>                sha256:c1a52f17c759c2cd6349eede3d5108b8dac07b97e10665b1d64a2d4961c2fd29   4 months ago    252MB
alpine                                          <none>                sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b   5 months ago    13MB
grafana/grafana-oss                             <none>                sha256:5dad0df181cb644a14e13617b913b261a54f7d4fd4510721dba420929f35bea2   5 months ago    1.47GB
crazymax/diun                                   <none>                sha256:e324b793eb32dfb7f74d3a39421ebf090141caaadee69b8f78da63112408ee25   5 months ago    86.5MB
ghcr.io/karakeep-app/karakeep                   <none>                sha256:64d6a9bbf2d37b5c808cf06b5d87f1f1c7846fdd3844724145a9741aeb06fd31   6 months ago    2.33GB
mysql                                           <none>                sha256:7dcddc01f13bab2f15cde676d44d01f61fc9f99fe7785e86196dfc07d358ae2b   6 months ago    1.1GB
node                                            <none>                sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293   7 months ago    194MB
nginx                                           <none>                sha256:0c8a74b863b202a8e9ce8b2f97cc8bf96bc573206d46c2c469d507095dd2c77e   8 months ago    92.4MB
gcr.io/cadvisor/cadvisor                        latest                sha256:3de2bd5203120b866d74a9b283b2ffb8ec382fbf9dc321814700c6ea6f44ec57   11 months ago   107MB
louislam/uptime-kuma                            <none>                sha256:3d632903e6af34139a37f18055c4f1bfd9b7205ae1138f1e5e8940ddc1d176f9   13 months ago   724MB
bitnamilegacy/minio                             latest                sha256:451fe6858cb770cc9d0e77ba811ce287420f781c7c1b806a386f6896471a349c   17 months ago   398MB
influxdb                                        <none>                sha256:299ebda2c7e308dbef42e26ac9b8fd1d9b3bcb8a0aee80c6509aa0219c1d0290   2 years ago     458MB
couchdb                                         <none>                sha256:ee75c9a737e7c48af0170142689959f2d70f93700162fef40818c799dfeecb8e   6 years ago     313MB
```

```bash
docker volume inspect 67598b6dc56f5ee10249dfc41a0abf4bfa6792dba9ce09f98e9e97b7c5c60102 b4d0d103d8ed46552af2eb5e0031e0465a65e223a042073f9bf2e984ba587ca9 19867cd43c440fcb0991c293c13fd2ffdcc592f3e5071014ca2eb83e2606f963 eddb53f2a57abe9d49ccc97ead749c9120191c6d141e7f838e758ead63288473
```

```text
[]
Error response from daemon: get 67598b6dc56f5ee10249dfc41a0abf4bfa6792dba9ce09f98e9e97b7c5c60102: no such volume
Error response from daemon: get b4d0d103d8ed46552af2eb5e0031e0465a65e223a042073f9bf2e984ba587ca9: no such volume
Error response from daemon: get 19867cd43c440fcb0991c293c13fd2ffdcc592f3e5071014ca2eb83e2606f963: no such volume
Error response from daemon: get eddb53f2a57abe9d49ccc97ead749c9120191c6d141e7f838e758ead63288473: no such volume
```

```bash
docker ps -a | grep memlab
```

```text
08b852caf58a   ghcr.io/ggml-org/llama.cpp:server                       "/app/llama-server -…"   58 seconds ago       Up 57 seconds (healthy)     127.0.0.1:39113->8080/tcp                     memlab-llama-chat
c0bc83c6e7ec   ghcr.io/ggml-org/llama.cpp:server                       "/app/llama-server -…"   58 seconds ago       Up 58 seconds (healthy)     127.0.0.1:39112->8080/tcp                     memlab-llama-embed
9e30d9eb5069   ollama/ollama:latest                                    "/bin/ollama serve"      About a minute ago   Up About a minute           127.0.0.1:39110->11434/tcp                    memlab-ollama
a822698d8613   ghcr.io/huggingface/text-embeddings-inference:cpu-1.9   "text-embeddings-rou…"   About a minute ago   Up About a minute           127.0.0.1:39111->80/tcp                       memlab-tei
```

```bash
ss -ltnp | grep 390
```

```text
```

The four owned anonymous volume inspections above must return “no such volume”. No matches from a grep command has exit status 1. Any other worker’s memlab containers in the global listing are intentionally retained.


### Final lab removal verification

```bash
rm -rf /var/tmp/memguide-lab-stores
```

```text
```

Exit status: 0.

```bash
test ! -e /var/tmp/memguide-lab-stores && echo "lab directory absent"
```

```text
lab directory absent
```

Exit status: 0.

```bash
docker ps -a | grep memlab
```

```text
08b852caf58a   ghcr.io/ggml-org/llama.cpp:server                       "/app/llama-server -…"   About a minute ago   Up About a minute (healthy)   127.0.0.1:39113->8080/tcp                     memlab-llama-chat
c0bc83c6e7ec   ghcr.io/ggml-org/llama.cpp:server                       "/app/llama-server -…"   About a minute ago   Up About a minute (healthy)   127.0.0.1:39112->8080/tcp                     memlab-llama-embed
9e30d9eb5069   ollama/ollama:latest                                    "/bin/ollama serve"      About a minute ago   Up About a minute             127.0.0.1:39110->11434/tcp                    memlab-ollama
a822698d8613   ghcr.io/huggingface/text-embeddings-inference:cpu-1.9   "text-embeddings-rou…"   2 minutes ago        Up 2 minutes                  127.0.0.1:39111->80/tcp                       memlab-tei
```

Exit status: 0.

```bash
ss -ltnp | grep 390
```

```text
```

Exit status: 1.

Removed: nine owned containers, their four anonymous Docker volumes, eight newly pulled image tags and their unreferenced layers, and the lab directory including its Python venv, package installations, source scripts, downloaded documentation, and test data. All pre-existing images and the other worker’s model containers were retained. No listeners remained in 39000–39099.

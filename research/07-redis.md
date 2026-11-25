# Redis as agent memory (research as of 2026-11-20)

Scope: what Redis is in late 2026 and how it fits agent memory. Every fact carries its source. Anything I could not check against a primary page is marked **UNVERIFIED**.

## How it works

Redis keeps the working dataset in RAM and serves it from one main thread per shard. Core data types map onto memory patterns:

- **Strings / hashes / JSON**: session state, per-user preferences, small memory records. Hashes hold a memory record plus its embedding bytes.
- **Lists and Streams**: ordered message history and event logs. Streams are the append-only option with consumer groups.
- **Sorted sets**: recency ranking (score = timestamp) and "top N most recent memories".
- **TTL (`EXPIRE`)**: the forgetting mechanism. A session key expires on its own.
- **Pub/sub and Streams**: agent-to-agent messaging.
- **Vector search (Query Engine)**: an index over hashes or JSON that holds embeddings, with FLAT or HNSW vector fields and filterable tag/numeric/text fields. The Query Engine was previously the RediSearch module and is now part of Redis 8 and Redis Cloud. [1]
- **Vector Sets**: a native data type (not an index) where elements are added with `VADD`, removed with `VREM`, and queried with `VSIM`. Its HNSW graph is serialized to disk, so a restart does not re-insert every vector. [2]

Durability is a separate knob. RDB snapshots fork the process and write `dump.rdb` on a schedule such as `save 60 1000`. [3] AOF logs every write, with `appendfsync always | everysec | no`; `everysec` can lose about one second of writes after a crash. [4]

## Variants and tools (versions and dates)

**Licence and product line**

- Redis 7.2.4 was the last BSD-licensed Redis release. The Linux Foundation forked it as **Valkey**, which stays BSD-3. [5]
- In May 2025 Redis added **AGPLv3** as a licence option starting with **Redis 8 GA** (RSALv2 and SSPLv1 remain alongside). [6][7]
- Redis 8 absorbed Redis Stack into core: JSON, Time Series, the Query Engine, Vector Sets and the RedisBloom set. [8] (secondary source; primary release notes not checked)
- The redis.io site in Nov 2026 lists "Redis open source framework, Redis 8.8" as current. [9] I did not check the 8.8 release notes; **UNVERIFIED** as to its feature list.

**Forks and alternatives**

- **Valkey**: BSD-3, Linux Foundation, the drop-in path for clients and data files. Valkey 9 is cited by several 2026 comparisons as current; those are secondary sources. [5][10]
- **KeyDB** (Snap Inc.): multithreaded Redis fork. Comparison pages from 2026 say development has slowed. **UNVERIFIED**: I did not read the KeyDB GitHub releases page.
- **DragonflyDB**: its own multithreaded engine with Redis protocol compatibility. Licence is BSL 1.1 per a comparison page. **UNVERIFIED** against the repo's LICENSE file.
- Redis's own March 2026 guide says there are no exact substitutes once you use the newer modules. [11]

**Agent-memory products (Redis-made)**

- **Redis Agent Memory** (the current product, in Redis Iris). Managed on Redis Cloud, or self-managed on Kubernetes. It keeps session memory and extracts durable facts into long-term memory in the background. Python package `redis-iris>=1.0.0`, env vars `IRIS_AGENT_MEMORY_URL`, `IRIS_AGENT_MEMORY_STORE_ID`, `IRIS_AGENT_MEMORY_API_KEY`. It has a REST API and an MCP endpoint. [12]
- **Agent Memory Server (V0)** in `redis/agent-memory-server`. The README says it is **deprecated** and not the supported production path. Last release 0.15.2. It is built on FastAPI, RedisVL and LiteLLM and ships a REST API, a CLI and an MCP server. [12]
- The two are not drop-in compatible. Switching does not copy existing memories. [12]

**Client libraries**

- **RedisVL** (`redisvl`, Python >=3.11, MIT). Latest docs version is 0.32.0 (the Redis docs version list shows it; release notes dated 2026-03-20 per a PDF snippet). Includes `SearchIndex`, `VectorQuery`, `HybridQuery` (needs Redis 8.4.0+), `SemanticCache`, `SemanticMessageHistory`, `SemanticRouter`, `EmbeddingsCache`, and an MCP server extra. [13][14]
- **LangCache**: a managed semantic-cache service for LLM responses, on Redis Cloud or self-managed. RedisVL has an `LLM Cache` implementation that calls the LangCache API. [15][16] Current GA/preview status **UNVERIFIED**: one docs snippet says "public preview" for the Redis Cloud flavour. Check before recommending.
- **langgraph-checkpoint-redis** (LangChain). Python and JS packages. Provides `RedisSaver` (full checkpoints), `ShallowRedisSaver` (only the latest checkpoint per thread) and Redis-backed stores. Initial release announced 2025-03-28. [17][18]

## Strengths

- **Latency and simplicity.** Session reads and writes are in-memory operations. Sub-millisecond is Redis's own marketing claim; I did not measure it. [19]
- **Native structures fit agent state.** TTL, sorted-set recency, streams for history, and pub/sub for coordination all exist without extra services.
- **Vector search in the same process as the cache.** Hybrid filter plus vector queries (`FilterQuery`, `VectorQuery` with a `filter_expression` mixing `Tag`, `Num`, text) run in one round trip. [13]
- **Vector Sets quantization.** Vector Sets use 8-bit quantization by default. Per the author, int8 takes 25% of FP32 memory with near-identical results on typical embedding models. [2][20]
- **Restart cost for vector sets.** Loading the serialized graph avoids rebuilding HNSW on restart. The author says roughly a few seconds per million elements. [2]
- **LangGraph integration** for checkpoints and cross-thread stores. [17]

## Limits and failure modes

- **RAM bound.** Everything you keep is in memory. A vector costs roughly `dims × bytes_per_dim` plus graph overhead. For a 1536-dim FP32 embedding that is 6,144 bytes before HNSW links. (This is my arithmetic, not a sourced figure.) At int8 it is about a quarter of that. Plan capacity from the formula, not from the marketing numbers.
- **Restart data loss.** Default RDB loses everything since the last snapshot. AOF with `everysec` loses up to about a second. `appendfsync no` can lose more. [3][4] An agent that writes a long plan to Redis and crashes before the next snapshot loses the plan.
- **Eviction.** With `maxmemory` set and an eviction policy, Redis silently drops keys. Set the policy on purpose. (General Redis behaviour; the eviction page was not read, so treat this as **UNVERIFIED** on exact policy names.)
- **Licence churn.** BSD (7.2.4) → RSALv2/SSPLv1 dual licence from 2024 [11] → AGPL added with 8.0 (2025). A dependency on any one licence is a business decision, not a technical one. [5][6]
- **Vector Sets status.** Antirez's 2025 post described Vector Sets as beta. [2] Check the current docs before treating them as stable.
- **Product split.** Redis Agent Memory (managed) and Agent Memory Server (V0, deprecated) use different APIs and data models. Starting on V0 means a migration later. [12]
- **Semantic cache correctness.** Semantic caches return a stored answer for a similar question. A similarity threshold that is too loose returns the wrong answer confidently. The LangCache concepts page says semantic caching differs from exact-key caching in correctness terms. [15]

## Exact use cases

**Pick Redis when:**

1. **Short-term / session memory.** Active conversation, scratchpad, tool results. Use a hash or list per session with `EXPIRE` so forgetting is automatic.
2. **Semantic cache of LLM answers.** RedisVL `SemanticCache` (self-hosted) or LangCache (managed). Measure the threshold on your own traffic first.
3. **Rate limits and locks for agent fleets.** `INCR` with `EXPIRE` for token-bucket counters; `SET key value NX PX` for leases. Fast and atomic across workers.
4. **Pub/sub or streams between agents.** Pub/sub for fire-and-forget signals; Streams with consumer groups when a message must be processed by one worker and retried.
5. **Hot recent-memory tier in front of a durable store.** Redis holds the last N days or the top-K recent facts; Postgres or a document store holds the truth. Write-through on save, read-through on miss.

**Avoid Redis when:**

1. **It is the system of record.** A crash window of a second (AOF) or minutes (RDB) is too much for user-facing facts or money. Keep the durable store as truth and rebuild Redis from it.
2. **The corpus does not fit RAM.** Billions of vectors or a multi-terabyte memory store will cost more in RAM than a disk-backed vector index. Use a disk-first store and keep only the hot slice in Redis.
3. **You need strong multi-document transactions or complex relational queries.** Redis transactions are limited and the data model is not relational.
4. **You need a licence the business has not approved.** Check the Redis 8 AGPL/RSAL/SSPL terms or pick Valkey (BSD-3) instead.

## Setup walkthrough

These commands are from primary pages where noted. Anything marked UNVERIFIED should be checked against the command reference before you rely on it.

**1. Run Redis 8 locally** (verified: RedisVL README)

```bash
docker run -d --name redis -p 6379:6379 redis:latest
docker exec -it redis redis-cli PING
```

**2. Session memory with TTL** (plain Redis commands; standard, not from a fetched page)

```bash
redis-cli HSET session:abc123 role user last_msg "book a table for two"
redis-cli EXPIRE session:abc123 1800
redis-cli TTL session:abc123
```

**3. Create a vector index and query it** (FT.CREATE syntax: **UNVERIFIED**, from memory of the RediSearch syntax; confirm against the FT.CREATE page)

```bash
redis-cli FT.CREATE mem_idx ON HASH PREFIX 1 mem: SCHEMA \
  owner TAG user_id TAG \
  text TEXT \
  embedding VECTOR HNSW 6 TYPE FLOAT32 DIM 4 DISTANCE_METRIC COSINE
redis-cli HSET mem:1 owner alice text "prefers vegetarian" embedding "\x00\x00\x80\x3f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
redis-cli FT.SEARCH mem_idx "(@owner:{alice})=>[KNN 3 @embedding \$vec AS score]" \
  PARAMS 2 vec "<binary FLOAT32 blob>" SORTBY score DIALECT 2
```

The `$vec` parameter must be a FLOAT32 blob, not text. Use a client library to build it.

**4. Vector Sets** (command names `VADD`, `VSIM`, `VREM`, `VCARD`, `VDIM`, `VEMB` confirmed by the Redis vector-sets docs page; the argument syntax below is **UNVERIFIED**, confirm with `redis-cli` `HELP VADD`)

```bash
redis-cli VADD topics VALUES 4 0.1 0.9 0.2 0.0 "pizza-notes"
redis-cli VADD topics VALUES 4 0.8 0.1 0.0 0.3 "rust-notes"
redis-cli VSIM topics VALUES 4 0.1 0.8 0.3 0.0 COUNT 3
redis-cli VREM topics "rust-notes"
```

**5. RedisVL quickstart** (installation and API names from the RedisVL README; schema YAML and calls quoted from the README)

```bash
pip install redisvl
```

```python
from redisvl.schema import IndexSchema
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery

schema = IndexSchema.from_dict({
    "index": {"name": "user-idx", "prefix": "user", "storage_type": "json"},
    "fields": [
        {"name": "user", "type": "tag"},
        {"name": "embedding", "type": "vector",
         "attrs": {"algorithm": "flat", "dims": 4,
                   "distance_metric": "cosine", "datatype": "float32"}},
    ],
})
index = SearchIndex(schema, redis_url="redis://localhost:6379")
index.create()
index.load([{"user": "john", "embedding": [0.23, 0.49, -0.18, 0.95]}], id_field="user")
hits = index.query(VectorQuery(vector=[0.16, -0.34, 0.98, 0.23],
                               vector_field_name="embedding", num_results=3))
```

`SemanticCache` is the next step for LLM answers; see the RedisVL "Cache LLM Responses" how-to. **UNVERIFIED** constructor arguments; I did not read the page.

**6. Persistence config** (verified: redis.io persistence page)

```conf
save 60 1000
appendonly yes
appendfsync everysec
```

## Numbers

- Redis 7.2.4: last BSD release. [5]
- Redis 8 GA with AGPLv3 option: May 1, 2025. [6]
- Vector Sets int8 quantization: about 25% of FP32 memory. [20]
- Vector Sets: about 50k–60k VSIM top-10 per second on a 3M-element, 300-dim set on the author's laptop (single run, author-reported, not a published benchmark). [2]
- Vector Sets: loading one million elements takes a few seconds from the serialized graph. [2]
- AOF `everysec`: up to about 1 second of writes lost on a crash. [4]
- RedisVL latest docs version: 0.32.0. [13]
- Agent Memory Server (V0) last release: 0.15.2, deprecated. [12]
- Redis's own marketing sub-millisecond claim: **UNVERIFIED** as a measured number.
- Billion-scale vector benchmark claims in Redis 8 marketing: **UNVERIFIED** (the blog page did not render its body).

## Sources

1. Redis vector search concepts, https://redis.io/docs/latest/develop/ai/search-and-query/vectors/ (page read; body partly nav)
2. Antirez, "Vector Sets are part of Redis", https://antirez.com/news/149 (read, 2025-04)
3. Redis persistence, snapshotting section, https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/ (read)
4. Redis persistence, append-only file section, same URL (read)
5. Redis blog, "What is Valkey?", https://redis.io/blog/what-is-valkey/ (snippet read)
6. Redis blog, "Redis is now available under the AGPLv3", https://redis.io/blog/agplv3/ (snippet; page body did not render)
7. Redis 8 GA, https://redis.io/blog/redis-8-ga/ (snippet)
8. Level-up/dev.to comparison, https://dev.to/jamilxt/valkey-vs-redis-in-2026-the-fork-quietly-won-most-of-the-market (secondary)
9. Redis site navigation (fetched via redis.io/blog/vector-indexes-in-redis/; the nav text lists "Redis open source framework, Redis 8.8")
10. JusDB comparison, https://www.jusdb.com/compare/redis-vs-valkey (secondary)
11. Redis, "Redis alternatives: why there are no exact substitutes", https://redis.io/blog/redis-alternatives-why-there-are-no-exact-substitutes/ (snippet, 2026-03-13)
12. redis/agent-memory-server README, https://raw.githubusercontent.com/redis/agent-memory-server/main/README.md (read)
13. RedisVL docs, installation, https://docs.redisvl.com/en/latest/user_guide/installation.html and RedisVL README, https://raw.githubusercontent.com/redis/redis-vl-python/main/README.md (read)
14. RedisVL API, LLM cache, https://docs.redisvl.com/en/stable/api/cache.html (read, nav only)
15. Redis LangCache docs, https://redis.io/docs/latest/develop/ai/langcache/ (metadata read)
16. RedisVL "LLM Cache" API page (LangCache backend), https://docs.redisvl.com/en/stable/api/cache.html (snippet)
17. LangGraph Redis launch, https://redis.io/blog/langgraph-redis-build-smarter-ai-agents-with-memory-persistence/ (snippet, 2025-03-28)
18. langgraph-checkpoint-redis reference, https://reference.langchain.com/javascript/langchain-langgraph-checkpoint-redis (snippet)
19. Redis caching solution page, https://redis.io/solutions/caching/ (claim only, nav text)
20. Antirez, "Scaling HNSWs", https://antirez.com/news/156 (snippet; the 25% memory claim is in post 149 body, see source 2)

Tool note: Redis.io pages returned mostly navigation text through the fetch tool. Section extraction failed for several pages. The numbers above come from primary posts where I read the body, and are otherwise marked.

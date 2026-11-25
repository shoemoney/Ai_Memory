# Memcached and the cache layer in agent systems

Research date: 2026-11-20. Every fact has its source next to it. Anything I could not verify in this run is marked **UNVERIFIED**.

**Bottom line:** a cache is not memory. It holds disposable copies of answers, embeddings, or prefixes that can be recomputed. Memcached is a fast, RAM-only, TTL-driven key-value cache. It is a good home for exact-match response and embedding caches. It is the wrong home for agent memory, and it must never hold the only copy of anything.

---

## How it works

Memcached is "a high performance multithreaded event-based key/value cache store intended to be used in a distributed system" ([README, master](https://raw.githubusercontent.com/memcached/memcached/master/README.md)). Its project site describes it as "a short-term memory for your applications" ([memcached.org/about](https://memcached.org/about)).

- **Storage is RAM only.** The README says memcached "does non-blocking network I/O, but not disk. (it should never go to disk, or you've lost the whole point of it)" ([README](https://raw.githubusercontent.com/memcached/memcached/master/README.md)). Persistence is not a default feature.
- **Narrow protocol.** Commands are storage (`set`, `add`, `replace`, `append`, `prepend`, `cas`) and retrieval (`get`, `gets`, `gat`, `gats`). Values are opaque bytes. There are no lists, sets, sorted sets, or hashes ([protocol.txt](https://raw.githubusercontent.com/memcached/memcached/master/doc/protocol.txt)).
- **Keys:** up to 250 characters, no control characters or whitespace ([protocol.txt](https://raw.githubusercontent.com/memcached/memcached/master/doc/protocol.txt)). Hash long prompts into keys (`sha256(...)`).
- **Eviction is LRU and TTL-based.** Items expire by TTL or are evicted when memory is full. **UNVERIFIED in this run:** the exact eviction behavior in the current version. Check [docs.memcached.org](https://docs.memcached.org/) before relying on it.
- **Default item size limit is 1 MB.** **UNVERIFIED in this run:** the configuring page body did not render. Confirm with `memcached -h` on the target build.

## Variants and tools

| Item | Status (2026-11-20) | Source |
|---|---|---|
| Memcached latest | **1.6.45**, release notes dated 2026-07-09 | [GitHub wiki ReleaseNotes1645](https://github.com/memcached/memcached/wiki/ReleaseNotes1645); [ReleaseNotes index](https://github.com/memcached/memcached/wiki/ReleaseNotes) |
| Security | **CVE-2026-47783**, timing side channel, published 2026-05-21. Upgrade to 1.6 and restrict network access. Confirm the affected range in the advisory before acting. | [SentinelOne CVE page](https://www.sentinelone.com/vulnerability-database/cve-2026-47783/) |
| Flash-backed storage (extstore) | Documented under "Flash Storage". Page body not read in this run. | [docs.memcached.org/features/flashstorage](https://docs.memcached.org/features/flashstorage) |
| Built-in proxy | Exists in the docs. Build flag `--enable-proxy`. | [README](https://raw.githubusercontent.com/memcached/memcached/master/README.md); [docs.memcached.org](https://docs.memcached.org/) |
| Warm restart | Documented under "Warm Restart". Body not read. | [docs.memcached.org](https://docs.memcached.org/) |
| TrueNAS community app | Memcached 1.6.45, last updated 2026-11-18 | [apps.truenas.com](https://apps.truenas.com/catalog/memcached_community/) |
| LangChain integration | `MemcachedCache`: "Cache that uses Memcached backend through pymemcache client lib" | [LangChain reference, langchain_community.caches](https://reference.langchain.com/python/langchain-community/caches) |

Exact-match and semantic caching are different product families. The rest of this guide covers both.

**Cache family, one line each:**

- **Exact-match LLM response cache:** hash of (model, params, prompt) to answer.
- **Semantic cache:** embed the query, look for a nearby prior query above a similarity threshold. Examples: [GPTCache](https://github.com/zilliztech/GPTCache) (pip package `gptcache`, MIT, "Slash Your LLM API Costs by 10x"), [RedisVL SemanticCache](https://docs.redisvl.com/en/0.4.1/user_guide/03_llmcache.html), [Redis semantic cache](https://redis.io/docs/latest/develop/use-cases/semantic-cache/), [Amazon ElastiCache semantic caching](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/semantic-caching-overview.html).
- **Embedding cache:** store vectors keyed by (embedding model, text hash).
- **Tool-result cache:** store deterministic tool outputs with a TTL.
- **Provider prompt caching:** the provider keeps the KV state of a prefix. You pay less to re-read it. See the numbers section.
- **Inference-level KV reuse:** the local engine saves and restores KV state. Examples: llama.cpp slots, vLLM prefix caching, MLX/oMLX prompt cache.

## Strengths

- Very low latency for small values, multithreaded, and scales across nodes with client-side hashing.
- Simple: one binary, one protocol, `get`/`set` with TTL.
- Restarting it loses only cache contents. Nothing else breaks.
- Fits any language with a client library. Python: `pymemcache` (used by LangChain's `MemcachedCache`).

## Memcached vs Redis/Valkey for agent workloads

| Need | Memcached | Redis / Valkey |
|---|---|---|
| Plain exact-match cache with TTL | Good, the simplest fit | Good |
| Data structures (hashes, sorted sets, streams) for session state, rate limits, queues | No | Yes (docs-verified for Redis: [redis.io](https://redis.io/docs/latest/develop/use-cases/semantic-cache/) mentions the built-in caching and vector search) |
| Vector search for semantic cache | No | Yes, through RedisVL (`SemanticCache` with embedding, distance threshold, TTL, metadata filters) |
| Persistence across restart | No (RAM only) | Available as an option. **UNVERIFIED in this run:** exact RDB/AOF behavior. |
| Metadata filters (per user, per tenant) | Only by key design | Yes, via RedisVL metadata filters |

Honest verdict: for agent systems, Redis/Valkey covers Memcached's use cases plus the semantic and state features agents need. Memcached only wins when you want the smallest possible exact-match cache and already run it.

## Limits and failure modes

1. **Stale answers.** A cache keyed only on the prompt returns yesterday's answer after a tool, document, or policy changed. Include a version of the model, the system prompt, and the tool or data snapshot in the key.
2. **Cross-user leakage.** If the key omits user or tenant, user A gets user B's answer. The key must carry the full authorization scope: `tenant:user:purpose:hash`.
3. **Semantic false hits.** "Cancel my order" and "cancel my subscription" can sit close in embedding space. Set the threshold high, store the query text with the entry, and gate by metadata. Measure hit precision on real logs before turning it on.
4. **Eviction.** LRU eviction under memory pressure silently drops entries. A cache miss must always be correct, just slower. Never rely on a hit.
5. **Prompt-cache silent misses.** Anthropic: a request below the minimum length is processed without caching and no error is returned. Check `cache_creation_input_tokens` and `cache_read_input_tokens` ([Anthropic cache limitations](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)). OpenAI: one character difference in the first 1,024 tokens gives a miss ([Microsoft Foundry docs on OpenAI prompt caching](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/prompt-caching)).
6. **Concurrent requests.** Anthropic: a cache entry only becomes available after the first response starts. Parallel requests on a cold prefix all miss ([Anthropic docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)).
7. **Stampede.** Many workers miss on the same key and all call the LLM. Use a lock or single-flight per key.
8. **Security.** Memcached has no auth by default. Bind it to localhost or a private network. The CVE above is a reminder to patch.
9. **Never the only copy.** If losing the cache costs you data (a conversation, a fact the user told the agent), the cache was being used as memory. Write the source of truth to a durable store (Postgres, a file, an append-only log) first. The cache is derived and rebuildable.

## TTL choices

- **Exact response cache:** minutes to hours, shorter when source data changes often. Invalidate on write.
- **Embedding cache:** long or indefinite, keyed by model name. An embedding is a pure function of (model, text), so it does not go stale unless the model changes.
- **Tool results:** match the tool's freshness requirement. Weather: minutes. Docs: hours. Anything with user state: do not cache, or key by user version.
- **Provider prompt cache:** 5 minutes default, 1 hour available (see numbers). Pick by request gap.

## Exact use cases

**Pick it when:**
- Identical prompts recur (FAQ bots, batch classification with repeated templates).
- Embedding the same text many times (re-indexing, retries, repeated chunks).
- A deterministic tool call is repeated within a short window.
- You need a cheap, shared, disposable cache for many app servers, and you already run Memcached.
- Long, stable system prompt or document prefix reused across many requests (use provider prompt caching, not your own cache).

**Avoid it when:**
- You need agent memory: facts about a user, decisions, task state. Use a durable store with explicit retrieval.
- Answers depend on per-user state and the key cannot carry that scope cleanly.
- You need semantic matching. Memcached has no vector search. Use RedisVL or GPTCache with strict thresholds.
- Correctness matters more than cost and latency, and a stale hit would cause harm (medical, legal, financial actions).
- You need persistence, data structures, or atomic queue semantics.

## Setup walkthrough

These commands are documented patterns. **I did not execute them in this run.** Test on a non-production host first.

**1. Run Memcached (localhost, 256 MB, 1024 connections):**

```bash
sudo apt-get install -y memcached libmemcached-tools
memcached -d -u memcache -m 256 -c 1024 -l 127.0.0.1 -p 11211
printf 'stats\nquit\n' | nc 127.0.0.1 11211 | grep -E 'limit_maxbytes|curr_items|evictions'
```

Flags: `-m` memory in MB, `-c` max connections, `-l` listen address, `-p` port, `-d` daemonize. Verify with `memcached -h` on your version.

**2. Set and get from Python with `pymemcache`:**

```bash
python3 -m pip install pymemcache
```

```python
import json
from pymemcache.client.base import Client

cache = Client(("127.0.0.1", 11211), connect_timeout=1, timeout=1)
cache.set("answer:v1:faq:abc123", json.dumps({"text": "Hello"}).encode(), expire=3600)
raw = cache.get("answer:v1:faq:abc123")
print(json.loads(raw) if raw else None)
```

Always catch connection errors and treat them as a miss. The cache must never break the request path.

**3. Embedding cache wrapper (never embed the same text twice):**

```python
import hashlib, json
from pymemcache.client.base import Client

cache = Client(("127.0.0.1", 11211), connect_timeout=1, timeout=1)

def embed_cached(text: str, model: str, embed_fn) -> list[float]:
    key = "emb:" + hashlib.sha256(f"{model}\x00{text}".encode()).hexdigest()
    try:
        hit = cache.get(key)
        if hit is not None:
            return json.loads(hit)
    except Exception:
        pass  # cache is best effort
    vec = embed_fn(text)
    try:
        cache.set(key, json.dumps(vec).encode(), expire=0)  # no expiry; model name is in the key
    except Exception:
        pass
    return vec
```

The model name is in the key, so changing models never returns a stale vector. Hashing keeps keys under 250 characters and free of whitespace.

**4. LangChain LLM cache with Memcached (UNVERIFIED constructor):**

```python
from langchain_core.globals import set_llm_cache
from langchain_community.cache import MemcachedCache
from pymemcache.client.base import Client

set_llm_cache(MemcachedCache(Client(("127.0.0.1", 11211))))
```

The class exists per the [LangChain reference](https://reference.langchain.com/python/langchain-community/caches). **UNVERIFIED in this run:** the exact import path and constructor signature for the current release. Check the reference before shipping.

**5. Anthropic prompt caching request (Python):**

From the [Anthropic docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), automatic caching adds one top-level `cache_control` field:

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=1024,
    cache_control={"type": "ephemeral"},   # 5-minute default lifetime
    system=LONG_STABLE_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": "Summarise the open tickets."}],
)
print(response.usage.cache_creation_input_tokens, response.usage.cache_read_input_tokens)
```

Check the usage fields on every call. Both at 0 means the prefix was not cached.

**UNVERIFIED in this run:** the exact field for the 1-hour TTL. The docs page says 5-minute or 1-hour TTLs are supported, but I did not read the parameter name. Confirm it in the docs before using it.

## Numbers

Prices per million tokens, from the [Anthropic pricing table](https://platform.claude.com/docs/en/build-with-claude/prompt-caching):

| Model | Base input | 5-min write | 1-hour write | Cache hit or refresh |
|---|---|---|---|---|
| Claude Opus 5.5 | $4 | $5 (1.25x) | $8 (2x) | $0.20 (0.1x) |
| Claude Sonnet 5.5 | $2 | $2.50 | $4 | $0.10 |
| Claude Haiku 5.5 | $0.10 (up to 100K tokens) | $0.125 | $0.20 | $0.01 |

Minimum cacheable prompt lengths (same page): 512 tokens for Opus 5.5, Sonnet 5.5, and Haiku 5.5 (Haiku 4.5 was 4,096). Shorter prompts are processed without caching and no error is returned.

Arithmetic from those prices: a 1-hour write costs 0.75x base more than a 5-minute write. One cache hit saves 0.9x base versus uncached input. So a single later hit within the hour covers the 1-hour premium.

OpenAI ([prompt caching guide](https://developers.openai.com/api/docs/guides/prompt-caching)): automatic, no code change. Minimum cacheable prompt is 1,024 tokens for GPT-5.6 and later models. **UNVERIFIED in this run:** the cached-input discount rate, which is on the pricing page I could not render.

Gemini ([context caching docs](https://aistudio.google.com/docs/caching)): implicit caching is on by default for Gemini 2.5 and newer. Minimum token counts listed: 2,048 for Gemini 2.5 Pro and Flash, 4,096 for Gemini 3.x and 4 models. On Gemini 4, a cache hit needs the new request to add at least 2,050 tokens. Explicit caching prices are **UNVERIFIED** in this run. Google Cloud's Vertex blog states cached tokens cost 10% of standard input for Gemini 2.5+ ([Google Cloud blog, 2025-10-15](https://cloud.google.com/blog/products/ai-machine-learning/vertex-ai-context-caching)). Third-party sources put explicit storage at about $1 per million tokens per hour from 2027-01-01 ([Requesty](https://www.requesty.ai/blog/cache-read-price-comparison-across-providers)). Verify against Google's pricing page.

Local KV reuse:
- llama.cpp server: `--slot-save-path` plus `POST /slots/{id}?action=save|restore` writes the full sequence state to disk ([particula.tech, 2026-07-29](https://particula.tech/blog/prompt-reprocessing-swa-hybrid-models-kv-cache); [llama.cpp discussion #18244](https://github.com/ggml-org/llama.cpp/discussions/18244)). Save files are sensitive data.
- LM Studio MLX engine: loads KV cache from disk for prompt sections it has seen ([LM Studio blog, 2026-06-05](https://lmstudio.ai/blog/mlx-engine-agentic-workloads)).
- oMLX: paged SSD KV caching; vendor claim that agent TTFT drops from 30-90 s to under 5 s ([omlx.ai](https://omlx.ai/)). **Vendor claim, not measured here.**
- vLLM: automatic prefix caching exists ([docs.vllm.ai](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html)). Body not read in this run.

Memcached-specific numbers: 1.6.45 release date 2026-07-09; key limit 250 bytes; default item limit 1 MB (**UNVERIFIED in this run**); default LRU behavior (**UNVERIFIED in this run**).

## Sources

- Memcached README (master): https://raw.githubusercontent.com/memcached/memcached/master/README.md
- Memcached protocol (master): https://raw.githubusercontent.com/memcached/memcached/master/doc/protocol.txt
- Memcached 1.6.45 release notes: https://github.com/memcached/memcached/wiki/ReleaseNotes1645
- Memcached release index: https://github.com/memcached/memcached/wiki/ReleaseNotes
- memcached.org About: https://memcached.org/about
- Memcached docs: https://docs.memcached.org/ (flash storage: https://docs.memcached.org/features/flashstorage)
- CVE-2026-47783: https://www.sentinelone.com/vulnerability-database/cve-2026-47783/
- Anthropic prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- OpenAI prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching
- Gemini context caching: https://aistudio.google.com/docs/caching
- Google Cloud Vertex context caching blog (2025-10-15): https://cloud.google.com/blog/products/ai-machine-learning/vertex-ai-context-caching
- LangChain reference (caches): https://reference.langchain.com/python/langchain-community/caches
- GPTCache: https://github.com/zilliztech/GPTCache
- RedisVL SemanticCache: https://docs.redisvl.com/en/0.4.1/user_guide/03_llmcache.html
- Redis semantic cache: https://redis.io/docs/latest/develop/use-cases/semantic-cache/
- Amazon ElastiCache semantic caching: https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/semantic-caching-overview.html
- llama.cpp server: https://github.com/ggml-org/llama.cpp/discussions/18244
- vLLM automatic prefix caching: https://docs.vllm.ai/en/latest/features/automatic_prefix_caching.html
- LM Studio MLX engine (2026-06-05): https://lmstudio.ai/blog/mlx-engine-agentic-workloads
- oMLX: https://omlx.ai/
- Requesty price comparison (secondary): https://www.requesty.ai/blog/cache-read-price-comparison-across-providers

#!/usr/bin/env python3
"""Fetch primary sources, retaining retrieval hashes rather than republishing pages."""
import concurrent.futures, datetime, hashlib, json, pathlib, urllib.request
SOURCES={
 'cl-bench-release':'https://continual-learning-bench.com/news/cl-bench-1-0/',
 'mongot-memory-estimator':'https://raw.githubusercontent.com/mongodb/mongot/main/src/main/java/com/xgen/mongot/index/definition/VectorMemoryEstimator.java',
 'mongot-disk-stats':'https://raw.githubusercontent.com/mongodb/mongot/main/src/main/java/com/xgen/mongot/index/lucene/backing/DiskStats.java',
 'mongot-vector-metrics':'https://raw.githubusercontent.com/mongodb/mongot/main/src/main/java/com/xgen/mongot/index/lucene/LuceneVectorIndexMetricValuesSupplier.java',
 'pinecone-architecture':'https://docs.pinecone.io/guides/get-started/architecture',
 'redisvl-cache-api':'https://docs.redisvl.com/en/stable/api/cache.html',
 'duckdb-vss-release':'https://github.com/duckdb/duckdb-vss',
 'mongo-quantization-markdown':'https://www.mongodb.com/docs/vector-search/about/vector-quantization.md',
 'mongo-deployment-markdown':'https://www.mongodb.com/docs/vector-search/deployment/deployment-options.md',
 'mongo-local-docker':'https://www.mongodb.com/docs/atlas/cli/current/atlas-cli-deploy-docker.md',
 'mongot-source':'https://raw.githubusercontent.com/mongodb/mongot/main/README.md',
 'llama-api':'https://raw.githubusercontent.com/ggml-org/llama.cpp/b12464/tools/server/README.md',
 'pgvector':'https://raw.githubusercontent.com/pgvector/pgvector/v0.8.7/README.md',
 'redis-vectors':'https://raw.githubusercontent.com/redis/redis/8.10.3/modules/vector-sets/README.md',
 'redis-persistence':'https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/',
 'redis-eviction':'https://redis.io/docs/latest/develop/reference/eviction/',
 'redis-locks':'https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/',
 'memcached-protocol':'https://raw.githubusercontent.com/memcached/memcached/1.6.45/doc/protocol.txt',
 'memcached-restart':'https://docs.memcached.org/features/restart/',
 'memcached-extstore':'https://docs.memcached.org/features/flashstorage/',
 'memcached-eviction':'https://docs.memcached.org/serverguide/maintenance/',
 'sqlite-wal':'https://sqlite.org/wal.html',
 'sqlite-fts5':'https://sqlite.org/fts5.html',
 'sqlite-vec':'https://raw.githubusercontent.com/asg017/sqlite-vec/v0.1.9/README.md',
 'sqlite-vec-source':'https://raw.githubusercontent.com/asg017/sqlite-vec/v0.1.9/sqlite-vec.c',
 'duckdb-vss':'https://raw.githubusercontent.com/duckdb/duckdb-vss/main/README.md',
 'mariadb-vectors':'https://mariadb.com/docs/server/reference/sql-structure/vectors/vector-overview',
 'mongo-quantization':'https://www.mongodb.com/docs/vector-search/about/vector-quantization/',
 'mongo-deployment':'https://www.mongodb.com/docs/vector-search/deployment/deployment-options/',
 'turbopuffer-architecture':'https://turbopuffer.com/docs/architecture',
 'turbopuffer-tradeoffs':'https://turbopuffer.com/docs/tradeoffs',
 'vectorize-limits':'https://developers.cloudflare.com/vectorize/platform/limits/',
 's3-vectors':'https://aws.amazon.com/blogs/aws/amazon-s3-vectors-now-generally-available-with-increased-scale-and-performance/',
 'claude-memory':'https://code.claude.com/docs/en/memory',
 'cursor-rules':'https://cursor.com/docs/rules',
 'copilot-memory':'https://docs.github.com/en/copilot/concepts/agents/copilot-memory',
 'copilot-measurement':'https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/',
 'anthropic-memory-measurement':'https://www.anthropic.com/research/components-of-agent-memory',
 'anthropic-cache':'https://platform.claude.com/docs/en/build-with-claude/prompt-caching',
 'anthropic-pricing':'https://platform.claude.com/docs/en/about-claude/pricing',
 'openai-cache':'https://developers.openai.com/api/docs/guides/prompt-caching',
 'openai-pricing':'https://developers.openai.com/api/docs/pricing',
 'gemini-cache':'https://aistudio.google.com/docs/caching',
 'gemini-pricing':'https://ai.google.dev/gemini-api/docs/pricing',
 'wa-sqlite':'https://raw.githubusercontent.com/rhashimoto/wa-sqlite/205eed588e60ac43401292df6583dbdc7c7fe966/README.md',
 'wa-sqlite-vfs':'https://raw.githubusercontent.com/rhashimoto/wa-sqlite/205eed588e60ac43401292df6583dbdc7c7fe966/src/examples/README.md',
 'browser-storage':'https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria',
}
def fetch(kv):
 k,u=kv;r={'id':k,'url':u,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Storage-reproduction-audit/1.0'}),timeout=45) as resp:
   b=resp.read();r.update(status=resp.status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),final_url=resp.url)
 except Exception as e:r.update(error=str(e))
 return r
if __name__=='__main__':
 out=pathlib.Path(__file__).resolve().parent/'results';out.mkdir(exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,SOURCES.items()))
 (out/'sources.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps({'fetched':sum('sha256' in r for r in results),'errors':[r for r in results if 'error' in r]},indent=2))

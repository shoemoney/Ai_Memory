# PostgreSQL as agent memory ("just use Postgres")

Research snapshot: 2026-11-20. Items marked **UNVERIFIED** could not be checked against a primary source in this pass.

## How it works

Postgres stores agent memory as ordinary rows. The pieces that matter for agents:

- **Relational facts and episodes** in normal tables, with transactions (a memory write and its audit row commit together).
- **Vectors** via the pgvector extension, which adds `vector`, `halfvec`, `bit` and `sparsevec` types and distance operators (`<->` L2, `<#>` negative inner product, `<=>` cosine, `<+>` L1, `<~>` Hamming, `<%>` Jaccard). By default pgvector does exact nearest-neighbour search with perfect recall; an HNSW or IVFFlat index makes it approximate ([pgvector README](https://raw.githubusercontent.com/pgvector/pgvector/master/README.md), read 2026-11-20).
- **Full text** via `tsvector`/GIN and `ts_rank_cd`, plus `pg_trgm` for fuzzy matching (built-in; docs URL in Sources, mechanism not re-read this pass).
- **Hybrid ranking** in one SQL statement, usually Reciprocal Rank Fusion (RRF) over a vector ranking and a keyword ranking.
- **Row-level security** (RLS) for per-tenant or per-user isolation, **LISTEN/NOTIFY** for change signals, and **JSONB** for flexible metadata.

The classic miss: a `vector` column with no ANN index. `ORDER BY embedding <=> $1 LIMIT 10` then computes distance against every row and sorts. It is correct, recall is 100 %, and latency grows linearly with table size. Teams often ship this, pass their tests on 5,000 rows, and discover the problem at 5 million. Check with `EXPLAIN`: a plan showing `Seq Scan` on the memory table with a `Sort` above it means no index is being used.

Approximate indexes trade recall for speed and change results: the README notes that with an approximate index, "you will see different results for queries after adding" it. Filtering is applied after the index scan, so a `WHERE tenant_id = ...` on an HNSW query can return fewer rows than `LIMIT` asks for. Iterative index scans (pgvector 0.8.0+) fix this by continuing the scan.

## Variants and tools

| Tool | Latest verified version / date | What it is | Source |
|---|---|---|---|
| PostgreSQL | **19**, released 2026-11-19. Latest 18.x minor is **18.7** (2026-11-12, with 17.12, 16.16, 15.20, 14.25 and the final PG14 release) | Core database | [PG 19 news](https://www.postgresql.org/about/news/postgresql-19-released-3449/), [18.7 news](https://www.postgresql.org/about/news/postgresql-187-1712-1616-1520-1425-and-19-rc-2-released-3442/) |
| pgvector | **0.8.7** (2026-10-01) is the latest tagged release; 0.9.0 is in master, unreleased | Vector types and HNSW/IVFFlat | [CHANGELOG](https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md), [README](https://raw.githubusercontent.com/pgvector/pgvector/master/README.md) |
| pgvectorscale (Timescale / Tiger Data) | Release number **UNVERIFIED** (GitHub tag page did not render) | StreamingDiskANN index, Statistical Binary Quantization, label-filtered search; Rust/pgrx; requires pgvector | [README](https://raw.githubusercontent.com/timescale/pgvectorscale/main/README.md) |
| pgai (Timescale / Tiger Data) | **UNVERIFIED** this pass | Embedding and retrieval helpers in SQL | Not fetched |
| VectorChord (tensorchord) | **1.1.1** (Docker tag `pg18-v1.1.1` in README); 1.0 released 2025-11-11 | `vchordrq` index: IVF + RaBitQ with reranking; RaBitQ4/8 storage types; pgvector-compatible types | [README](https://raw.githubusercontent.com/tensorchord/VectorChord/main/README.md), [releases snippet](https://github.com/tensorchord/VectorChord/releases) |
| ParadeDB `pg_search` | Docs at **v0.27.0**; BM25 index renamed to the `paradedb` index access method in **0.25.0** | BM25 ranked full text as a custom index, plus hybrid search and RRF docs | [create-index docs](https://docs.paradedb.com/documentation/indexing/create-index) |
| Built-in `tsvector` + `pg_trgm` | Ships with Postgres | Keyword ranking, fuzzy match | Postgres docs |
| Apache AGE | **v1.8.0** (for PG18, around Jul 2026) | openCypher graph queries inside Postgres | [AGE README](https://raw.githubusercontent.com/apache/age/master/README.md), [SourceForge snippet](https://sourceforge.net/projects/apache-age.mirror/) |
| LangGraph checkpointers | `langgraph-checkpoint-postgres`, version **UNVERIFIED** | `PostgresSaver` (thread checkpoints) and `PostgresStore` (JSON documents by namespace and key, with optional semantic search) | [checkpoint-postgres README](https://raw.githubusercontent.com/langchain-ai/langgraph/main/libs/checkpoint-postgres/README.md), [LangChain memory docs](https://docs.langchain.com/oss/python/langgraph/add-memory) |
| mem0 | Current version **UNVERIFIED** | Has a `pgvector` vector-store provider; TypeScript config can enable `diskann` (pgvectorscale) or `hnsw` | [mem0 pgvector docs](https://raw.githubusercontent.com/mem0ai/mem0/main/docs/components/vectordbs/dbs/pgvector.mdx) |
| Hindsight (vectorize-io) | Docs at 1.2; 0.10.2 cited by third party | Agent memory. **PostgreSQL with pgvector is the primary storage backend**; Oracle 23ai is an alternative; Alembic migrations | [Storage docs](https://hindsight.vectorize.io/developer/storage), [repo CLAUDE.md snippet](https://github.com/vectorize-io/hindsight/blob/main/CLAUDE.md) |
| Zep / Graphiti | Graphiti is a temporal knowledge-graph framework | Graph storage is **not** Postgres-first. A third-party comparison lists Neo4j 5.26, FalkorDB and Neptune. Exact backend matrix **UNVERIFIED** from a primary page | [Graphiti README](https://raw.githubusercontent.com/getzep/graphiti/main/README.md), [comparison snippet](https://infranodus.com/docs/llm-memory-tools-comparison) |
| Letta | Current code lives in `letta-code`; the V1 API server is retired to an `archive` branch | Stateful agents. Whether it requires Postgres **UNVERIFIED** | [Letta README](https://raw.githubusercontent.com/letta-ai/letta/main/README.md) |

Managed options (versions and limits partly from search snippets, not full pages):

- **Neon**: lists Postgres 19 as available on its Free plan. Its pgvector docs state HNSW supports up to 2,000 dimensions for `vector` and 4,000 for `halfvec`, and a search snippet from 2026-11-06 says the latest supported pgvector was 0.8.0 at that time ([Neon pgvector docs](https://neon.com/docs/extensions/pgvector), snippet only). Treat the pgvector version as provider-dependent and check it.
- **Supabase**: same dimension limits in its HNSW docs (snippet from [Supabase HNSW docs](https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes)).
- **AWS RDS, AlloyDB**: pgvector and ScaNN-related claims **UNVERIFIED** this pass.

## Strengths

- **One transactional store.** A memory write, its audit row, its embedding and its NOTIFY can commit together or roll back together. Most vector databases cannot do this.
- **Joins.** Facts join to episodes, users, tenants and permissions in the same query. The filter and the similarity search happen in one plan.
- **Hybrid search is plain SQL.** RRF is a few lines of CTE (see the setup section).
- **Index choice is per column and per operator.** Partial indexes, expression indexes (`binary_quantize`, `halfvec` casts, `subvector`) and list partitioning all work.
- **Operational maturity.** Backups, PITR, replicas, and every managed provider (Neon, Supabase, RDS, AlloyDB and others) already run it.
- **Frameworks already target it.** LangGraph (`PostgresSaver`, `PostgresStore`), Hindsight and mem0 all have Postgres paths.

## Limits and failure modes

- **No index means a full scan.** See above. Verify with `EXPLAIN (ANALYZE, BUFFERS)`.
- **Filtered ANN returns short result sets.** pgvector's README example: with a filter matching 10 % of rows and `hnsw.ef_search` at its default of 40, only about 4 rows survive on average. Use `hnsw.iterative_scan` (`strict_order` or `relaxed_order`) and tune `hnsw.max_scan_tuples` (default 20000) and `hnsw.scan_mem_multiplier` (default 1).
- **Dimension limits on indexes.** `vector` indexes cap at 2,000 dimensions, `halfvec` at 4,000, `bit` at 64,000, `sparsevec` at 1,000 non-zero elements (README). A 3,072-dim embedding cannot be HNSW-indexed as `vector`; use `halfvec` or reduce dimensions.
- **HNSW build cost.** Build is slower and uses more memory than IVFFlat. Graphs that do not fit `maintenance_work_mem` build much slower; pgvector prints `hnsw graph no longer fits into maintenance_work_mem after 100000 tuples`. Default parallel workers are 2.
- **Tenant sharing of one index.** Sharing an approximate index across tenants lets one tenant's vectors affect recall and speed for others. The README recommends list partitioning or separate tables for isolation.
- **Recall is a setting, not a guarantee.** `ef_search` defaults to 40. Recall must be measured against exact search on your own data.
- **Vacuum and churn.** Memory tables are update-heavy (decay, supersession). HNSW vacuuming had several index-corruption and "graph not repaired" fixes in 0.8.3 to 0.8.4 and an unreleased fix in 0.9.0. Keep pgvector current.
- **Version drift between docs.** The pgvector README says "Postgres 13+", but the unreleased 0.9.0 changelog says it dropped 13 and 14. Pin your version and read the changelog.
- **pgvectorscale** does not build on Intel macOS (README warning). Its README points new users to `pg_vectorsearch`, which is in early alpha and "isn't yet production-ready."
- **Scale ceiling.** Vendor benchmarks (Timescale, VectorChord, Pinecone comparisons) show pgvector falling behind at tens to hundreds of millions of vectors and tight latency targets. Those are vendor numbers; reproduce on your own corpus.
- **NOTIFY is not a queue.** Payloads are size-limited and listeners that are offline miss notifications. Use a real queue or an outbox table for guaranteed delivery (PG docs).

## Exact use cases

**Pick Postgres when:**
- You already run Postgres, and agent memory is one of several tables in the app.
- Memory writes must be transactional with the business data (a booking plus its memory, an audit row with each fact change).
- You need one query that mixes SQL predicates (tenant, user, `valid_to IS NULL`, time window), keyword rank and vector rank.
- You need per-tenant isolation enforced in the database with RLS.
- Your corpus is under roughly tens of millions of vectors per index, and you can meet latency with HNSW plus tuned `ef_search`.
- You want an audit trail that is just tables and triggers.

**Avoid Postgres (or add a second system) when:**
- You need very large corpora (hundreds of millions to billions of vectors) with a hard p99 latency budget. Consider VectorChord or pgvectorscale on dedicated hardware, or a dedicated vector store, and measure.
- Your core need is multi-hop relationship reasoning over a graph. Use Apache AGE (fine for moderate graphs) or a dedicated graph store such as Graphiti's backends.
- You need sub-millisecond write-heavy streaming ingestion with no tuning budget.
- Your team cannot operate Postgres (vacuum, connections, upgrades). Managed Postgres removes most of that but not all.

## Setup walkthrough

Install pgvector from source (command set from the pgvector README, tag v0.8.7):

```bash
cd /tmp
git clone --branch v0.8.7 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

Enable it and set build memory for the session:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
SET maintenance_work_mem = '2GB';            -- size to your graph; do not exhaust RAM
SET max_parallel_maintenance_workers = 3;    -- plus leader
```

Schema for episodic, semantic and embedding memory. Dimension 1536 is an example; match your embedding model:

```sql
CREATE TABLE episodes (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id   uuid NOT NULL,
  user_id     uuid NOT NULL,
  session_id  uuid NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  role        text NOT NULL CHECK (role IN ('user','assistant','tool','system')),
  content     text NOT NULL,
  metadata    jsonb NOT NULL DEFAULT '{}',
  embedding   vector(1536),
  embedding_model text,
  tsv         tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

CREATE TABLE facts (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id         uuid NOT NULL,
  user_id           uuid NOT NULL,
  subject           text NOT NULL,
  predicate         text NOT NULL,
  object            text NOT NULL,
  valid_from        timestamptz NOT NULL DEFAULT now(),
  valid_to          timestamptz,              -- NULL = currently believed
  source_episode_id bigint REFERENCES episodes(id),
  metadata          jsonb NOT NULL DEFAULT '{}',
  embedding         vector(1536),
  embedding_model   text,
  tsv               tsvector GENERATED ALWAYS AS (
                      to_tsvector('english', subject || ' ' || predicate || ' ' || object)) STORED
);

CREATE TABLE memory_audit (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tenant_id  uuid NOT NULL,
  actor      text NOT NULL,
  op         text NOT NULL,
  table_name text NOT NULL,
  row_id     bigint,
  before     jsonb,
  after      jsonb,
  at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX episodes_tenant_user_time ON episodes (tenant_id, user_id, occurred_at DESC);
CREATE INDEX episodes_tsv_gin          ON episodes USING GIN (tsv);
CREATE INDEX facts_tenant_user_current ON facts (tenant_id, user_id) WHERE valid_to IS NULL;
CREATE INDEX facts_tsv_gin             ON facts USING GIN (tsv);

-- Approximate vector indexes (defaults m=16, ef_construction=64 from the README)
CREATE INDEX episodes_embedding_hnsw ON episodes USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
CREATE INDEX facts_embedding_hnsw ON facts USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

Tenant isolation with RLS, using a non-owner application role (table owners bypass RLS unless forced):

```sql
ALTER TABLE facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE facts FORCE ROW LEVEL SECURITY;
CREATE POLICY facts_tenant ON facts
  USING (tenant_id = current_setting('app.tenant_id')::uuid)
  WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
-- repeat for episodes; the app sets it per transaction:
-- SET LOCAL app.tenant_id = '6f1c...';
```

Change notification and audit in one transaction, from a trigger:

```sql
CREATE OR REPLACE FUNCTION facts_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO memory_audit (tenant_id, actor, op, table_name, row_id, before, after)
  VALUES (COALESCE(NEW.tenant_id, OLD.tenant_id), current_user, TG_OP, TG_TABLE_NAME,
          COALESCE(NEW.id, OLD.id), to_jsonb(OLD), to_jsonb(NEW));
  PERFORM pg_notify('facts_changed', COALESCE(NEW.id, OLD.id)::text);
  RETURN COALESCE(NEW, OLD);
END $$;

CREATE TRIGGER facts_audit_trg AFTER INSERT OR UPDATE OR DELETE ON facts
  FOR EACH ROW EXECUTE FUNCTION facts_audit();
```

Hybrid query with RRF (k = 60, following the RRF pattern in the pgvector-python example). Bind `$1` tenant, `$2` user, `$3` query text, `$4` query embedding:

```sql
BEGIN;
SET LOCAL app.tenant_id = '...';           -- RLS
SET LOCAL hnsw.iterative_scan = relaxed_order;  -- filters need a deeper ANN scan
SET LOCAL hnsw.ef_search = 100;

WITH semantic AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY dist) AS rnk
  FROM (
    SELECT id, embedding <=> $4 AS dist
    FROM facts
    WHERE tenant_id = $1 AND user_id = $2 AND valid_to IS NULL
    ORDER BY embedding <=> $4
    LIMIT 50
  ) s
),
keyword AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY score DESC) AS rnk
  FROM (
    SELECT id, ts_rank_cd(tsv, q) AS score
    FROM facts, plainto_tsquery('english', $3) q
    WHERE tenant_id = $1 AND user_id = $2 AND valid_to IS NULL AND tsv @@ q
    ORDER BY score DESC
    LIMIT 50
  ) k
)
SELECT f.id, f.subject, f.predicate, f.object,
       COALESCE(1.0 / (60 + s.rnk), 0) + COALESCE(1.0 / (60 + k.rnk), 0) AS rrf
FROM semantic s
FULL OUTER JOIN keyword k ON k.id = s.id
JOIN facts f ON f.id = COALESCE(s.id, k.id)
ORDER BY rrf DESC
LIMIT 10;
COMMIT;
```

Tune recall against exact search. Disable index scans to get ground truth, then compare:

```sql
BEGIN;
SET LOCAL enable_indexscan = off;
SET LOCAL enable_bitmapscan = off;
-- run the same ORDER BY embedding <=> $4 LIMIT 10 and save the ids
COMMIT;

BEGIN;
SET LOCAL hnsw.ef_search = 100;  -- try 40, 100, 200 and measure recall and latency
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM facts WHERE tenant_id = $1 AND user_id = $2 AND valid_to IS NULL
ORDER BY embedding <=> $4 LIMIT 10;
COMMIT;
```

Check the plan actually uses `facts_embedding_hnsw`. If it shows `Seq Scan`, the filter, operator class or ORDER BY does not match the index.

Binary quantization for large tables (expression index plus re-rank), from the README:

```sql
CREATE INDEX facts_bq_hnsw ON facts
  USING hnsw ((binary_quantize(embedding)::bit(1536)) bit_hamming_ops);
-- query: ORDER BY binary_quantize(embedding)::bit(1536) <~> binary_quantize($4) LIMIT 20,
-- then re-rank the 20 by embedding <=> $4 in an outer query.
```

## Numbers

- pgvector defaults: `m` = 16, `ef_construction` = 64, `hnsw.ef_search` = 40, `ivfflat.probes` = 1, `max_parallel_maintenance_workers` = 2, `hnsw.max_scan_tuples` = 20000, `hnsw.scan_mem_multiplier` = 1 (README).
- IVFFlat list sizing rule from the README: `rows / 1000` lists up to 1M rows, `sqrt(rows)` above that; probes about `sqrt(lists)`.
- Dimension caps for indexing: 2,000 (`vector`), 4,000 (`halfvec`), 64,000 (`bit`), 1,000 non-zero (`sparsevec`) (README).
- Filter example: 10 % selectivity with `ef_search` 40 gives about 4 matching rows on average (README).
- VectorChord claims 100M vectors indexed in about 20 minutes and 400,000 vectors stored for $1 (vendor claims, README).
- pgvectorscale claims 28x lower p95 and 16x higher throughput than Pinecone s1 at 99 % recall on 50M 768-dim Cohere embeddings (vendor benchmark, README). **UNVERIFIED** independently.
- RRF constant k = 60 (pgvector-python RRF example).
- Postgres: 19 released 2026-11-19; 18.7 released 2026-11-12; PG14 final release was 14.25.

## Sources

- pgvector README (read 2026-11-20): https://raw.githubusercontent.com/pgvector/pgvector/master/README.md
- pgvector CHANGELOG: https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md
- pgvector-python RRF example: https://raw.githubusercontent.com/pgvector/pgvector-python/master/examples/hybrid_search/rrf.py
- PostgreSQL 19 release: https://www.postgresql.org/about/news/postgresql-19-released-3449/
- PostgreSQL 18.7 / 17.12 / 16.16 / 15.20 / 14.25 release: https://www.postgresql.org/about/news/postgresql-187-1712-1616-1520-1425-and-19-rc-2-released-3442/
- PostgreSQL versioning policy: https://www.postgresql.org/support/versioning/
- PostgreSQL row security (docs URL, not re-read): https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- PostgreSQL NOTIFY (docs URL, not re-read): https://www.postgresql.org/docs/current/sql-notify.html
- pgvectorscale README: https://raw.githubusercontent.com/timescale/pgvectorscale/main/README.md
- VectorChord README: https://raw.githubusercontent.com/tensorchord/VectorChord/main/README.md
- VectorChord releases (snippet): https://github.com/tensorchord/VectorChord/releases
- ParadeDB create-index docs: https://docs.paradedb.com/documentation/indexing/create-index
- ParadeDB RRF docs: **UNVERIFIED** (the URL I tried returned 404)
- LangGraph checkpoint-postgres README: https://raw.githubusercontent.com/langchain-ai/langgraph/main/libs/checkpoint-postgres/README.md
- LangChain memory docs (PostgresStore, semantic search): https://docs.langchain.com/oss/python/langgraph/add-memory
- mem0 pgvector docs: https://raw.githubusercontent.com/mem0ai/mem0/main/docs/components/vectordbs/dbs/pgvector.mdx
- Hindsight storage: https://hindsight.vectorize.io/developer/storage
- Hindsight CLAUDE.md (snippet): https://github.com/vectorize-io/hindsight/blob/main/CLAUDE.md
- Graphiti README: https://raw.githubusercontent.com/getzep/graphiti/main/README.md
- Zep/Graphiti backend comparison (third party, snippet): https://infranodus.com/docs/llm-memory-tools-comparison
- Letta README: https://raw.githubusercontent.com/letta-ai/letta/main/README.md
- Apache AGE README: https://raw.githubusercontent.com/apache/age/master/README.md
- Apache AGE 1.8.0 (SourceForge snippet): https://sourceforge.net/projects/apache-age.mirror/
- Neon pgvector docs (snippet for limits and version): https://neon.com/docs/extensions/pgvector
- Neon vector search optimization: https://neon.com/docs/ai/ai-vector-search-optimization (not read in full)
- Supabase HNSW docs (snippet): https://supabase.com/docs/guides/ai/vector-indexes/hnsw-indexes
- Timescale pgvector vs Pinecone benchmark (cited from pgvectorscale README): http://www.timescale.com/blog/pgvector-vs-pinecone

**Not verified this pass:** pgai current version; pgvectorscale release tag; mem0 current version; LangGraph package version; Letta's Postgres requirement; Zep's exact storage backends; RDS and AlloyDB pgvector versions and ScaNN claims; ParadeDB RRF page; search engines degraded (brave, duckduckgo, startpage suspended or CAPTCHA, google cse timeouts), so broad web coverage is thin.

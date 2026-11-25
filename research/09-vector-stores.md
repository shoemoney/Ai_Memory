# 09. Dedicated vector stores as agent memory

Research date: 2026-11-20. Versions and licences come from the GitHub Releases and repo APIs unless noted. Vendor performance numbers are vendor claims. Anything not confirmed from a primary source is marked **UNVERIFIED**.

## How it works

A vector store keeps embeddings plus metadata and returns the k nearest vectors to a query. Four design axes matter for agent memory:

- **Index family.** Flat (brute force) is exact and linear in corpus size. IVF partitions vectors into clusters and scans a few. HNSW is a layered proximity graph held mostly in RAM. DiskANN/Vamana is a graph designed to sit on SSD. Milvus lists DiskANN and HNSW among its index options (github.com/milvus-io/milvus topics). FAISS documents HNSW and NSG graphs alongside compact quantization codes that can run without the raw vectors (github.com/facebookresearch/faiss README).
- **Quantization.** Scalar (SQ), product (PQ) and binary (BQ) shrink vectors and trade recall for memory. MongoDB reports RAM for vectors on its search node drops 3.75x with scalar and 24x with binary quantization, and it keeps full-precision vectors on disk for rescoring (mongodb.com/docs/vector-search/about/vector-quantization/ and deployment-options; vendor claim).
- **Filtering.** Pre-filtering applies the metadata predicate before the ANN search. Post-filtering searches first and then drops non-matches, so a selective filter can return fewer than k rows. pgvector's docs make this concrete: with HNSW and the default `hnsw.ef_search` of 40, a condition matching 10% of rows yields about 4 matches on average, and `hnsw.iterative_scan` exists to scan further (github.com/pgvector/pgvector README).
- **Storage tier.** RAM-resident graphs are fastest. NVMe-cached or object-storage-backed designs trade cold latency for cost. turbopuffer's docs state the first query to a namespace reads object storage directly (p50 874 ms at 1M documents) and cached queries take p50 14 ms (turbopuffer.com/docs/architecture; vendor claim).

Hybrid search combines dense vectors with BM25 or sparse vectors. Qdrant 1.20 advertises BM25 hybrid search without sparse vectors (qdrant.tech/benchmarks/ page header, read 2026-11-20).

## Stores table

| Store | Latest release (date) | Licence | Architecture | Best at |
|---|---|---|---|---|
| Qdrant | v1.20.2 (2026-11-16) | Apache-2.0 | Rust server; local in-process mode via `QdrantClient(":memory:")` or `path=` | Payload filtering with indexes, self-hosted server |
| Milvus | v3.0.6 (2026-11-11) | Apache-2.0 | Go, distributed; Milvus Lite is a local Python backend | Very large scale, many index types |
| Milvus Lite | pymilvus 3.0.2 + milvus-lite 3.2.2 (docs) | Per package, UNVERIFIED | Embedded, local `.db` directory | Notebook/laptop prototypes that later move to a server |
| Weaviate | v1.40.7 (2026-11-20) | GitHub reports NOASSERTION ("Other"); read LICENSE before relying | Go; stores objects and vectors | Vector plus structured filtering in one DB |
| Chroma | 1.5.9 (2026-05-05) | Apache-2.0 | Rust core; in-process or `chroma run` server | Simplest developer API |
| LanceDB | v0.41.0 (2026-10-29) | Apache-2.0 | Embedded, Lance columnar format on local disk or object storage | Embedded multimodal tables, versioned data |
| sqlite-vec | v0.1.9 (2026-03-31) | Apache-2.0 (GitHub) | Pure C SQLite extension, `vec0` virtual tables | Single-file local memory; pre-v1, expect breaking changes |
| FAISS | v1.16.0 (2026-11-10) | MIT | C++/Python library, not a database | Index research, GPU batch search, in-process ANN |
| hnswlib | v0.9.0 (2026-03-28) | Apache-2.0 | Header-only C++ HNSW | Minimal in-memory HNSW |
| usearch | v2.26.6 (2026-10-25) | Apache-2.0 | C++ HNSW with bindings | Small footprint, quantized indexes |
| pgvector | v0.8.7 | UNVERIFIED (PostgreSQL-style licence expected) | Postgres extension; exact by default, HNSW and IVFFlat | Vectors next to relational data |
| Elasticsearch | v9.5.6 (2026-10-28) | Triple: AGPLv3 / SSPL / Elastic License 2.0 (LICENSE.txt) | JVM search engine with kNN | Existing Elastic estates, BM25 plus kNN |
| OpenSearch | 3.10.0 (tag) | UNVERIFIED (Apache-2.0 expected) | Fork of Elasticsearch | AWS-hosted search with vectors |
| Vespa | CLI 8.788.13 (2026-11-16); engine version UNVERIFIED | UNVERIFIED | C++ engine with ranking expressions | Large-scale ranking and hybrid queries |
| DuckDB VSS | UNVERIFIED (GitHub API 403) | MIT (LICENSE text) | DuckDB extension, HNSW index | Analytics plus vectors in one embedded file |
| Marqo | UNVERIFIED version | Apache-2.0 (LICENSE) | Vector search engine with built-in embedding | Turnkey text/image search |
| Vald | UNVERIFIED (API 403) | UNVERIFIED | Kubernetes-native distributed ANN | Cloud-native scale-out |
| Pinecone | Managed, no release tags | Proprietary | Serverless, object-storage backed, namespaces | Zero-ops hosted index |
| turbopuffer | Managed | Proprietary (no public OSS repo located) | Object storage as WAL and index store, NVMe cache, stateless query nodes | Cheap huge multi-tenant corpora |
| S3 Vectors | GA 2025-12-02 | AWS managed | Vector buckets and indexes on S3 | Cheap cold vectors, long tail |
| Cloudflare Vectorize | Managed, docs updated 2026-10-30 | Managed | Edge-adjacent managed index | Workers-native apps |
| MongoDB Atlas Vector Search | Managed | Managed | `mongot` search nodes beside the database | Vectors plus documents in Mongo |

Sources: GitHub releases and repo APIs (api.github.com/repos/OWNER/REPO/releases/latest; LICENSE files via raw.githubusercontent.com). Pinecone architecture: docs.pinecone.io/guides/get-started/architecture. S3 Vectors GA: aws.amazon.com/about-aws/whats-new/2025/12/amazon-s3-vectors-generally-available/. Cloudflare limits: developers.cloudflare.com/vectorize/platform/limits/.

## Strengths

- **Qdrant:** filtering is a first-class clause system with nested AND/OR/NOT; payload indexes are advised before ingest (qdrant.tech/documentation/search/filtering/). Runs in-process for tests.
- **Chroma:** core API is four calls (`create_collection`, `add`, `query`, `get`). Apache-2.0 (github.com/chroma-core/chroma README).
- **LanceDB:** embedded, runs in the app process, data on local disk or object storage; Lance format gives versioning (github.com/lancedb/lancedb README).
- **sqlite-vec:** pure C, no dependencies, runs on Linux, macOS, Windows, WASM and Raspberry Pi; stores float, int8 and binary vectors in `vec0` tables (github.com/asg017/sqlite-vec README).
- **pgvector:** exact search by default with perfect recall, ACID, joins with relational data; supports half-precision, binary and sparse vectors (github.com/pgvector/pgvector README).
- **FAISS, hnswlib, usearch:** libraries with no server; FAISS adds GPU search and compressed codes that scale past RAM with quantization.
- **Managed (Pinecone, turbopuffer, S3 Vectors, Vectorize):** no index tuning; storage is billed separately from compute.

## Limits and failure modes

- **Post-filter starvation.** Selective metadata filters on approximate indexes return fewer than k rows (pgvector example above). Fix with iterative scans, partial indexes per tenant, or partitioning.
- **Object-storage cold starts.** turbopuffer's 874 ms cold p50 at 1M documents is fine for batch agents and bad for interactive turns; use its warm-cache pre-flight query.
- **Write latency.** turbopuffer states writes take up to 200 ms to commit (turbopuffer.com/docs/tradeoffs).
- **Hard limits.** Cloudflare Vectorize caps vectors at 1536 dimensions of float32, 10 KiB metadata per vector, topK 50 with values or metadata, 100 without, and upsert batches of 1000 (Workers) or 5000 (HTTP API) (developers.cloudflare.com/vectorize/platform/limits/). Elsewhere the limits differ, so read each store's page.
- **Format migrations.** Milvus Lite 3.x cannot open a 2.x `.db` file in place (milvus.io/docs/milvus_lite.md).
- **Pre-v1 churn.** sqlite-vec says "expect breaking changes" (its README). Its docs site labels v0.1.10-alpha.4 while the latest GitHub release is v0.1.9, so pin one.
- **Quantization recall.** Binary quantization needs full-precision rescoring; without it recall drops (MongoDB docs describe the rescoring design).
- **Licence traps.** Elasticsearch is no longer plain Apache-2.0. Weaviate's licence is not machine-readable on GitHub.

## Exact use cases

| Use case | Pick | Avoid |
|---|---|---|
| **Embedded single-file memory for a desktop/CLI agent** | sqlite-vec (one `.db` file, no server), or LanceDB for multimodal tables | Any server store: an extra daemon for one user's notes |
| **Millions of memories, multi-tenant SaaS** | Qdrant or Weaviate with per-tenant payload filters, or Pinecone namespaces, or turbopuffer namespaces (one namespace per tenant maps cleanly) | Post-filter-only designs where tenants are small and filters are selective |
| **Billion-scale** | Milvus (distributed), Vespa, or S3 Vectors for cold tiers. S3 Vectors reports 40 billion vectors ingested during preview (AWS blog) | Single-node RAM HNSW |
| **Multimodal multi-vector (ColPali-style late interaction)** | Qdrant (multivector support), LanceDB (multimodal tables). Verify multi-vector support per store before committing | Stores with only single-vector indexes; flatten late-interaction embeddings at your own risk |
| **Edge / offline** | sqlite-vec (WASM, Raspberry Pi), Milvus Lite (laptops, edge devices with Python), usearch for a tiny index | Managed-only stores (no offline mode) |

## Setup walkthrough

**Qdrant (Docker server + Python client)**

```bash
docker run -p 6333:6333 qdrant/qdrant:latest
pip install qdrant-client
```

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")  # or QdrantClient(path="./qdrant_local")
client.create_collection(
    "memories",
    vectors_config=models.VectorParams(size=4, distance=models.Distance.COSINE),
)
client.upsert(
    collection_name="memories",
    points=[models.PointStruct(id=1, vector=[0.1, 0.2, 0.3, 0.4], payload={"user": "u1", "kind": "fact"})],
)
hits = client.query_points(
    collection_name="memories",
    query=[0.1, 0.2, 0.3, 0.4],
    limit=3,
).points
```

Commands and `create_collection`/`query_points` shapes come from the qdrant-client README. The `upsert` and `PointStruct` names are the standard client API and were not in the fetched text; **verify on first run.**

**Chroma (persistent)**

```bash
pip install chromadb
chroma run --path ./chroma_db        # optional client-server mode
```

```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")  # PersistentClient: UNVERIFIED, docs page 404 at fetch time
col = client.get_or_create_collection("memories")
col.add(ids=["m1"], documents=["User prefers dark mode"], metadatas=[{"user": "u1"}])
res = col.query(query_texts=["UI preference"], n_results=2, where={"user": "u1"})
```

`add`, `query` and `where` are from the chroma-core README. `chroma run --path` is in the same README.

**LanceDB (embedded)**

```bash
pip install lancedb
```

LanceDB's README confirms the install; the `connect`/`create_table`/`search` calls below are **UNVERIFIED** against the current SDK. Check them against lancedb.github.io/lancedb/python before use.

```python
import lancedb
db = lancedb.connect("./agent_memory.lancedb")
tbl = db.create_table("memories", data=[{"id": "m1", "vector": [0.1, 0.2, 0.3, 0.4], "text": "prefers dark mode"}])
rows = tbl.search([0.1, 0.2, 0.3, 0.4]).limit(3).to_list()
```

**sqlite-vec (single file)**

```bash
pip install sqlite-vec
```

The installation line is from the sqlite-vec README. The Python snippet below follows its documented pattern but the Python page did not render, so **verify before use.**

```python
import sqlite3, sqlite_vec
db = sqlite3.connect("memory.db")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories USING vec0(embedding float[4])")
db.execute("INSERT INTO vec_memories(rowid, embedding) VALUES (1, ?)", [sqlite_vec.serialize_float32([0.1, 0.2, 0.3, 0.4])])
rows = db.execute("SELECT rowid, distance FROM vec_memories WHERE embedding MATCH ? ORDER BY distance LIMIT 3",
                  [sqlite_vec.serialize_float32([0.1, 0.2, 0.3, 0.4])]).fetchall()
```

**Milvus Lite (local)**

```bash
python -m pip install "pymilvus[milvus-lite]==3.0.2" "milvus-lite==3.2.2"
```

```python
from pymilvus import MilvusClient
client = MilvusClient("./milvus_demo.db")  # creates a directory, not one file
```

Source: milvus.io/docs/milvus_lite.md.

## Numbers

Only vendor claims or docs values, all stated as such:

- turbopuffer: cold p50 874 ms and cached p50 14 ms at 1M documents; writes commit within 200 ms (turbopuffer.com/docs/architecture, /docs/tradeoffs). Vendor claim.
- MongoDB: RAM for vectors on `mongot` down 3.75x (scalar) and 24x (binary); disk down 66% with binData (mongodb.com deployment-options). Vendor claim.
- S3 Vectors: GA on 2025-12-02; 40 billion vectors ingested during preview (aws.amazon.com/blogs/aws/amazon-s3-vectors-now-generally-available-with-increased-scale-and-performance/, search snippet). AWS says it can cut vector costs by up to 90% (aws.amazon.com/s3/features/vectors/). Vendor claim.
- Cloudflare Vectorize: limits as listed above.
- ANN-Benchmarks (ann-benchmarks.com) publishes recall-versus-QPS plots per dataset (glove, fashion-mnist, sift, gist). I could not extract plotted values, so **no numbers taken from it**.
- VectorDBBench (github.com/zilliztech/vectordbbench) is the Zilliz open benchmark. I could not read its README, and the third-party numbers I found (Endee blog: Vespa 860 QPS at 95.01% recall; Medium: 6-DB RAG benchmark) are **secondary and UNVERIFIED**.
- Do-you-need-a-vector-DB sizes: pgvector's README says to start with exact search and only add an ANN index when needed (exact search gives perfect recall). It gives no row-count threshold. I found **no primary source with a size threshold**, so the commonly cited "pgvector is enough up to N million vectors" numbers are **UNVERIFIED**.

## Sources

- Qdrant: github.com/qdrant/qdrant (API), github.com/qdrant/qdrant-client README, qdrant.tech/documentation/search/filtering/, qdrant.tech/benchmarks/
- Milvus: github.com/milvus-io/milvus (API), milvus.io/docs/milvus_lite.md
- Weaviate: github.com/weaviate/weaviate (API)
- Chroma: github.com/chroma-core/chroma (API and README)
- LanceDB: github.com/lancedb/lancedb (API and README), github.com/lancedb/lancedb/python/README.md
- sqlite-vec: github.com/asg017/sqlite-vec (API and README), alexgarcia.xyz/sqlite-vec/
- FAISS: github.com/facebookresearch/faiss (API, README, LICENSE)
- hnswlib: github.com/nmslib/hnswlib (API); usearch: github.com/unum-cloud/usearch (API, LICENSE)
- pgvector: github.com/pgvector/pgvector README
- Elasticsearch: github.com/elastic/elasticsearch (API, LICENSE.txt)
- Marqo: github.com/marqo-ai/marqo LICENSE
- DuckDB VSS: github.com/duckdb/duckdb-vss LICENSE
- Vespa: github.com/vespa-engine/vespa (CLI release)
- Pinecone: docs.pinecone.io/guides/get-started/architecture; pinecone.io/pricing/; docs.pinecone.io/guides/cost/understand-cost
- turbopuffer: turbopuffer.com/docs/architecture, /docs/tradeoffs, /docs/limits
- S3 Vectors: aws.amazon.com/about-aws/whats-new/2025/12/amazon-s3-vectors-generally-available/; aws.amazon.com/blogs/aws/amazon-s3-vectors-now-generally-available-with-increased-scale-and-performance/; aws.amazon.com/s3/features/vectors/
- Cloudflare Vectorize: developers.cloudflare.com/vectorize/platform/limits/
- MongoDB: mongodb.com/docs/vector-search/about/vector-quantization/; mongodb.com/docs/vector-search/deployment/deployment-options/
- Benchmarks: ann-benchmarks.com; github.com/zilliztech/vectordbbench (README not readable)

**Not verified:** Vespa engine version and licence; OpenSearch and pgvector licence text; Vald and DuckDB VSS versions; Marqo version; Chroma `PersistentClient` and LanceDB Python call signatures; sqlite-vec Python snippet; all vendor benchmark numbers beyond those listed.

# Agent memory on stores other than Redis, Postgres and vector DBs

Research date: 2026-11-20. Every fact carries its source. Anything not checked is marked UNVERIFIED.

## How it works

Most agent memory is text plus an index. The store decides three things: where the bytes live, how they are found (exact key, full-text, vector, graph, time order), and what survives a crash.

Three patterns cover most of the non-standard stores:

1. **Single-file relational store with extensions.** SQLite (plus FTS5 and sqlite-vec), libSQL/Turso, DuckDB. One file, SQL, no server. Vectors and keywords sit next to the rows they describe, so there is no sync step.
2. **Server relational store with a native vector type.** MariaDB 11.7+ and MySQL 9.x. The vector is a column type and the index is built in. Good when the app already runs a SQL server.
3. **Append-only log, derived everything else.** JSONL or an event table is the source of truth. Summaries, embeddings, FTS indexes and graphs are rebuilt from it. Losing a derived index costs time, not memory.

Checkpointers are a separate pattern. LangGraph saves a snapshot of graph state per step, keyed by thread and checkpoint ID, so a run can pause, resume or fork. This is thread state, not long-term memory, and it is easy to confuse with memory.

## Stores table

| Store | Current version / date (source) | What it is good for in agent memory | Notes |
|---|---|---|---|
| SQLite FTS5 | Ships with SQLite; docs at sqlite.org/fts5.html | Keyword and phrase recall, BM25 ranking, trigram substring search (sqlite.org/fts5.html §4.3.4) | FTS5 tokens capped at 32768 bytes (sqlite.org/fts5.html) |
| sqlite-vec | PyPI 0.1.9, released 2026-03-31 (pypi.org/project/sqlite-vec/); README says "pre-v1, so expect breaking changes" (github.com/asg017/sqlite-vec) | `vec0` virtual table, float/int8/binary vectors, KNN with `MATCH` and `k` | Brute-force style KNN per the README; ANN status UNVERIFIED for 0.1.9 |
| sqlite.org vec1 | Separate SQLite-team project, "current release version 0.8" (sqlite.org/vec1.html, page dated Oct 2026) | IVFADC + OPQ approximate search, L2 and cosine | Different project from sqlite-vec. Build from source; not a pip package (UNVERIFIED whether it is packaged) |
| LangGraph SqliteSaver | langgraph-checkpoint-sqlite 3.1.3 on PyPI (pypi.org/project/langgraph-checkpoint-sqlite/); sync and aiosqlite async | Thread checkpoints for pause, resume, time travel | Has a 2026 security chain, see Limits |
| libSQL / Turso | Native `F32_BLOB(N)` columns, `libsql_vector_idx`, `vector_top_k()` (turso.tech/vector) | Vectors in the same file with no extension | Falls back to an exact linear scan without the index (turso.tech blog, 2026-07-15). Turso announced it is joining Supabase (banner on turso.tech/vector, date UNVERIFIED) |
| DuckDB | Docs at duckdb.org/docs/2.0/ (2.0 LTS) | Analytics over traces; `vss` (HNSW) and `fts` extensions | `vss` is marked experimental. HNSW on disk needs `SET hnsw_enable_experimental_persistence = true` and the docs warn against production use (duckdb.org/docs/2.0/core_extensions/vss.html) |
| MariaDB VECTOR | Community 11.7 (rolling), GA in 11.8 LTS; Enterprise 11.4.5-3 (mariadb.com/docs/server/reference/sql-structure/vectors/vector-overview) | `VECTOR(N)` up to 16383 dims; `VECTOR INDEX` with M 3 to 200 and `DISTANCE=euclidean|cosine`; HNSW-based | Concurrent reads and writes and all isolation levels supported (same page) |
| MySQL VECTOR | Introduced in 9.0.0, 2024-07-01 (dev.mysql.com/doc/relnotes/mysql/9.0/en/news-9-0-0.html); manual at 9.7 (dev.mysql.com/doc/refman/9.7/en/vector.html) | Native column; `VECTOR` cannot be a key (9.0 release notes) | Distance metrics COSINE, DOT, EUCLIDEAN (9.0 manual, vector-functions.html). Index support in 9.7 UNVERIFIED |
| ClickHouse | Used for agent traces via ClickStack and OpenTelemetry; OTel GenAI spans `invoke_agent` and `execute_tool` (clickhouse.com/resources/engineering/what-is-ai-agent-observability, 2026-07-29) | Append-heavy trace store, fast aggregation | Not a memory recall store. Use for observing memory, not for retrieving it |
| OpenSearch | 3.5 released Feb 2026 with agentic conversation memory (en.wikipedia.org/wiki/OpenSearch_(software), secondary; docs.opensearch.org/latest/version-history/) | k-NN plus BM25 in one index | Wikipedia is a secondary source for the 3.5 claim |
| MongoDB | Atlas Vector Search (mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/) | Document memory with vector search | Vector search on self-managed Community Edition: UNVERIFIED |
| LMDB | Python `lmdb` 3.0.1 docs (lmdb.readthedocs.io) | Memory-mapped, single-machine, ordered key-value | Docs say to use it for fast local persistence on one machine |
| RocksDB | Latest tag v11.13.2 (github.com/meta/rocksdb/releases/tag/v11.13.2) | LSM key-value for write-heavy logs and indexes | MyRocks was archived 2026-03-01 (artem.krylysov.com blog, 2026-07-23, secondary) |
| Parquet on object storage | Parquet and DuckDB/Arrow readers | Cold archive of episodes, batch analysis | No recall path by itself; pair with a hot index |
| Browser: IndexedDB / OPFS | wa-sqlite (github.com/rhashimoto/wa-sqlite) runs SQLite on an OPFS VFS | In-browser agents with local state | OPFS is browser-managed, not durable storage (tinyjoin.org/guides/caveats/, secondary) |
| Git | Not sourced | Versioned notes, diffable memory files | Judgment, not a sourced claim: good audit trail, poor concurrent writes |
| OpenAI Responses / Conversations | Responses API, `previous_response_id` (developers.openai.com/api/docs/guides/conversation-state) | Server-side thread state | Retention window and per-account limits UNVERIFIED (the page did not render the details) |
| Anthropic memory tool | `memory_20250818`, client-side file directory (platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool) | Agent writes and reads its own memory files in your storage | The tool is client-side: your app executes the file operations |

## Memory-type taxonomy mapping

CoALA (Sumers, Yao, Narasimhan, Griffiths, arXiv:2309.02427) splits language-agent memory into working, episodic, semantic and procedural. The store mapping below is this guide's synthesis, not part of CoALA.

- **Working / short-term:** the live context window plus the checkpointer. Best store: LangGraph checkpoints or OpenAI/Anthropic server-side thread state. Expires with the thread.
- **Episodic (what happened):** append-only JSONL or an event table, with traces in ClickHouse. This is the source of truth.
- **Semantic (facts):** SQLite FTS5 plus sqlite-vec, libSQL, MariaDB VECTOR, or OpenSearch when the facts must be shared across services.
- **Procedural (how to do things):** versioned files in git or a skills directory, plus the memory tool for agent-written notes. Procedures change rarely and need review, so files beat a database here.

## Strengths

- **SQLite:** one file, zero servers, transactional, WAL gives concurrent readers with one writer. FTS5 and sqlite-vec run in the same connection, so a hybrid query is one SQL statement.
- **libSQL/Turso:** same file model, vectors as a column type, no extension to load (turso.tech/vector).
- **DuckDB:** fast scans over large episode tables; joins and aggregations over memory logs.
- **MariaDB / MySQL:** vector search where the app already has transactions, ACLs and backups.
- **JSONL:** human-readable, greppable, trivially replayable. Easy to rebuild every derived index.
- **Checkpointers:** pause, resume and fork a run without writing any memory logic.

## Limits and failure modes

- **sqlite-vec is pre-v1** (README). Pin the version and expect breaking changes.
- **Single writer:** SQLite WAL allows one writer. Many agents writing at once queue or fail with SQLITE_BUSY. Set `busy_timeout` and batch writes.
- **Sharing:** a SQLite file on a network filesystem is unsafe for concurrent writers. Keep it on local disk.
- **DuckDB HNSW persistence** is experimental and can lose or corrupt an index after a crash with uncommitted changes (duckdb.org vss page). Keep the vector index rebuildable from the source table.
- **Turso exact fallback:** without `libsql_vector_idx`, search is an exact scan (turso.tech blog). Fine for thousands of rows, slow beyond that.
- **LangGraph SqliteSaver security:** CVE-2025-67644 is a SQL injection in the SQLite checkpointer's metadata filter (NVD: nvd.nist.gov/vuln/detail/CVE-2025-67644; CVSS 7.3 per the CSA note). Check Point reports it chains with an msgpack deserialization flaw, CVE-2025-64439, to code execution (research.checkpoint.com/2026/from-sqli-to-rce-exploiting-langgraphs-checkpointer/, 2026-06-11). The CSA note says the fix is in langgraph-checkpoint-sqlite 3.0.1 (labs.cloudsecurityalliance.org, secondary). Current PyPI is 3.1.3. Never let end users control checkpoint history filters.
- **Browser storage** can be evicted. Do not treat OPFS as the only copy.
- **Derived-index drift:** an embedding model change silently makes old vectors incomparable. Store the model name and dimension with every vector.
- **Logs grow without bound** unless rotated (see walkthrough).

## Exact use cases

- **SQLite + FTS5 + sqlite-vec:** pick it when one agent or one desktop app needs personal memory on local disk, under roughly a few hundred thousand chunks (sizing UNVERIFIED). Avoid it when several hosts write to the same memory.
- **libSQL/Turso:** pick it when the memory must sync or ship with an edge or mobile app. Avoid it when you need the exact sqlite-vec extension behavior, or when the vendor direction (Supabase acquisition) matters to your risk.
- **DuckDB:** pick it for analysis over episodes and traces (cohort queries, eval scoring). Avoid it as the live write store for memory updates from many clients.
- **MariaDB VECTOR / MySQL VECTOR:** pick it when the SQL server already holds the tenant data and you want ACLs in the same query. Avoid it if you need graph traversal or very high recall targets.
- **JSONL episodic log:** pick it always, as the first write. Avoid it as the only retrieval path; it has no index.
- **LMDB / RocksDB:** pick LMDB for a fast single-machine key-value cache of computed memory. Pick RocksDB for write-heavy event ingestion. Avoid both when you need SQL or full-text search.
- **OpenSearch / MongoDB:** pick them when the team already runs them. Avoid adding them only for agent memory.
- **ClickHouse:** pick it for trace analytics on memory use. Avoid it for per-turn recall.
- **Object storage + Parquet:** pick it for cold archive and batch re-embedding. Avoid it for interactive recall.
- **Browser IndexedDB/OPFS (wa-sqlite):** pick it for in-browser agents that must work offline. Avoid it as the only copy of user memory.
- **Git:** pick it for procedural memory and reviewable notes. Avoid it for high-frequency writes.
- **LangGraph checkpointer:** pick it for run state and resumption. Avoid it as long-term memory; checkpoints are per thread and grow with every step.
- **Server-side thread state (OpenAI, Anthropic):** pick it when you accept vendor retention for simplicity. Avoid it when memory must be portable or deletable on your terms.

## Setup walkthrough

### 1. Single-file SQLite memory with FTS5 and sqlite-vec hybrid search

```bash
pip install sqlite-vec==0.1.9
```

```python
# memory_store.py
import json, math, sqlite3, struct
import sqlite_vec

DIM = 4  # use your embedding model's size, for example 384

SPACE = dict(model="toy-4d", revision="fixture-v1", dimensions=DIM,
             preprocessing="identity")

def identity(space):
    if set(space) != {"model", "revision", "dimensions", "preprocessing"}:
        raise ValueError("invalid embedding identity")
    if type(space["dimensions"]) is not int or space["dimensions"] != DIM:
        raise ValueError("invalid embedding dimensions")
    if any(type(space[k]) is not str or not space[k].strip()
           for k in ("model", "revision", "preprocessing")):
        raise ValueError("invalid embedding identity")
    return json.dumps(space, sort_keys=True)

def check(db, space, vector=None):
    saved = db.execute("SELECT identity FROM collection WHERE id=1").fetchone()
    if saved != (identity(space),):
        raise ValueError("embedding space mismatch")
    if vector is not None:
        if len(vector) != DIM or not all(math.isfinite(x) for x in vector):
            raise ValueError("invalid embedding vector")

def connect(path, space):
    wanted = identity(space)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    try:
        with db:
            db.execute("CREATE TABLE IF NOT EXISTS collection "
                       "(id INTEGER PRIMARY KEY CHECK(id=1), identity TEXT)")
            saved = db.execute("SELECT identity FROM collection").fetchone()
            if saved is None:
                if db.execute("SELECT 1 FROM sqlite_master "
                              "WHERE name='memories'").fetchone():
                    raise ValueError("collection identity missing; rebuild")
                db.execute("INSERT INTO collection VALUES (1, ?)", (wanted,))
            check(db, space)
    except Exception:
        db.close()
        raise
    db.executescript(f"""
    CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY, kind TEXT,
      content TEXT, embed_model TEXT,
      created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
      content, content='memories', content_rowid='id');
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec USING vec0(
      embedding float[{DIM}]);
    """)
    return db

def vec(v):
    return struct.pack(f"<{len(v)}f", *v)

def add(db, kind, content, vector, space):
    with db:
        check(db, space, vector)
        cur = db.execute(
            "INSERT INTO memories(kind, content, embed_model) VALUES (?,?,?)",
            (kind, content, space["model"]))
        rid = cur.lastrowid
        db.execute("INSERT INTO memories_fts(rowid, content) VALUES (?,?)",
                   (rid, content))
        db.execute("INSERT INTO memories_vec(rowid, embedding) VALUES (?,?)",
                   (rid, vec(vector)))

def quote(text):
    return " OR ".join('"' + w.replace('"', '""') + '"' for w in text.split())

def hybrid(db, text, vector, space, k=3, pool=20, rrf_k=60):
    own = not db.in_transaction
    if own:
        db.execute("BEGIN")  # one snapshot for both rankings and the lookups
    try:
        check(db, space, vector)
        if not text.strip():
            return []  # no search at all, including no dense branch
        fts = db.execute(
            "SELECT rowid FROM memories_fts WHERE memories_fts MATCH ? "
            "ORDER BY rank LIMIT ?", (quote(text), pool)).fetchall()
        knn = db.execute(
            "SELECT rowid FROM memories_vec WHERE embedding MATCH ? AND k = ? "
            "ORDER BY distance", (vec(vector), pool)).fetchall()
        score = {}
        for ranked in (fts, knn):
            for i, (rid,) in enumerate(ranked):
                score[rid] = score.get(rid, 0) + 1 / (rrf_k + i + 1)
        top = sorted(score, key=score.get, reverse=True)[:k]
        return [(r, round(score[r], 4)) + db.execute(
            "SELECT kind, content FROM memories WHERE id = ?", (r,)).fetchone()
            for r in top]
    finally:
        if own:
            db.rollback()

def remove_indexed_row(db, rid):
    if db.in_transaction:
        raise ValueError("removal requires its own write transaction")
    db.execute("BEGIN IMMEDIATE")  # lock before reading the old FTS text
    try:
        row = db.execute("SELECT content FROM memories WHERE id = ?",
                         (rid,)).fetchone()
        if row:
            db.execute("INSERT INTO memories_fts(memories_fts, rowid, content) "
                       "VALUES('delete', ?, ?)", (rid, row[0]))
            db.execute("DELETE FROM memories_vec WHERE rowid = ?", (rid,))
            db.execute("DELETE FROM memories WHERE id = ?", (rid,))
        db.commit()
    except BaseException:
        db.rollback()
        raise
```

Notes: this copy matches Chapter 12. `remove_indexed_row()` locks before reading old text and removes the FTS5 entry, vector and memory row in one transaction. It rejects an existing transaction without ending it. `rank` is FTS5's BM25 ordering. The RRF constant 60 is a common default, not a sourced number.

Check the install: `python -c "import sqlite_vec, sqlite3; c=sqlite3.connect(':memory:'); c.enable_load_extension(True); sqlite_vec.load(c); print(c.execute('select vec_version()').fetchone())"`. The `vec_version()` call is the README's check; confirm it on your machine.

### 2. MariaDB VECTOR index

Requires MariaDB 11.7+ (11.8 LTS for GA).

```sql
CREATE TABLE memories (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  kind VARCHAR(16) NOT NULL,
  content TEXT NOT NULL,
  embed_model VARCHAR(64) NOT NULL,
  embedding VECTOR(384) NOT NULL,
  VECTOR INDEX (embedding) M=8 DISTANCE=cosine
);

INSERT INTO memories (kind, content, embed_model, embedding)
VALUES ('semantic', 'User prefers metric units', 'bge-small-en-v1.5',
        VEC_FromText('[0.012, -0.031, ...]'));  -- 384 floats

SELECT id, content
FROM memories
WHERE kind = 'semantic'
ORDER BY VEC_DISTANCE(embedding, VEC_FromText('[0.010, -0.029, ...]'))
LIMIT 10;
```

Source: MariaDB Vector overview and VECTOR pages (mariadb.com/docs/server/reference/sql-structure/vectors/vector-overview, .../vector). The planner condition for using the index (ORDER BY distance with LIMIT, matching the index's DISTANCE) is UNVERIFIED here; run `EXPLAIN` before trusting it.

### 3. JSONL episodic log with rotation

```python
# episodic_log.py
import json, os, shutil
from pathlib import Path

class Log:
    # One writer; stop readers/sync while recovering or rotating.
    def __init__(self, folder):
        self.root = Path(folder)
        self.root.mkdir(exist_ok=True)
        self.current = self.root / "current.jsonl"
        self.syncdir(self.root.parent)

    def syncdir(self, path=None):
        fd = os.open(path or self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def events(self):
        seen = {}
        paths = sorted(self.root.glob("part-*.jsonl")) + [self.current]
        for path in paths:
            if not path.exists():
                continue
            with path.open("r+b" if path == self.current else "rb") as f:
                line_no = 0
                while True:
                    start = f.tell()
                    raw = f.readline()
                    if not raw:
                        break
                    line_no += 1
                    if path == self.current and not raw.endswith(b"\n"):
                        f.truncate(start)  # only an uncommitted final record
                        f.flush()
                        os.fsync(f.fileno())
                        break
                    try:
                        if not raw.endswith(b"\n"):
                            raise ValueError("unterminated archived record")
                        e = json.loads(raw)
                        validate(e)
                        if e["id"] in seen and seen[e["id"]] != e:
                            raise ValueError("event id reused with different data")
                    except (ValueError, TypeError, KeyError) as exc:
                        raise ValueError(f"{path}:{line_no}: {exc}") from exc
                    seen[e["id"]] = e
        events = list(seen.values())
        state(events)  # reject invalid dependencies during replay too
        return events

    def append(self, e):
        validate(e)
        old = {v["id"]: v for v in self.events()}  # recover before append
        if e["id"] in old:
            if old[e["id"]] != e:
                raise ValueError("event id reused with different data")
            if self.current.exists():
                with self.current.open("rb") as f:
                    os.fsync(f.fileno())
            self.syncdir()  # retry must finish any failed durability barrier
            return  # retry after lost acknowledgement
        state([*old.values(), e])  # validate before writing any bytes
        raw = (json.dumps(e, sort_keys=True, allow_nan=False) + "\n").encode()
        with self.current.open("ab") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        self.syncdir()  # also makes first creation durable

    def rotate(self):
        self.events()  # validate all history; repair only active tail
        if not self.current.exists() or not self.current.stat().st_size:
            return
        parts = sorted(self.root.glob("part-*.jsonl"))
        n = int(parts[-1].stem.split("-")[1]) + 1 if parts else 1
        target = self.root / f"part-{n:08d}.jsonl"
        temp = self.root / "rotation.tmp"
        with self.current.open("rb") as src, temp.open("wb") as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(temp, target)  # same filesystem, atomic publication
        self.syncdir()  # archive durable before touching current
        with self.current.open("wb") as f:
            f.flush()
            os.fsync(f.fileno())
        # Crash before truncation leaves duplicates, removed by event id.

def validate(e):
    fields = ("id", "key", "device", "clock", "op", "text")
    if not isinstance(e, dict) or any(type(e.get(k)) is not str for k in fields):
        raise ValueError("event string fields required")
    if not all(e[k] for k in ("id", "key", "device", "clock")):
        raise ValueError("empty identity or provenance")
    if e["op"] not in ("put", "supersede", "delete"):
        raise ValueError("unknown operation")
    if type(e.get("parents")) is not list:
        raise ValueError("parents must be a list")
    if any(type(p) is not str or not p or p == e["id"] for p in e["parents"]):
        raise ValueError("invalid parent")
    if e["op"] == "supersede" and not e["parents"]:
        raise ValueError("supersede needs parents")
    if e["op"] != "supersede" and e["parents"]:
        raise ValueError("only supersede accepts parents")

def state(events):
    by_id = {}
    for e in events:
        validate(e)
        if e["id"] in by_id and by_id[e["id"]] != e:
            raise ValueError("event id reused with different data")
        by_id[e["id"]] = e
    visiting, ready = set(), {}

    for root in by_id:
        stack = [(root, False)]
        while stack:
            eid, done = stack.pop()
            if eid in ready:
                continue
            e = by_id[eid]
            if done:
                visiting.remove(eid)
                ready[eid] = all(ready.get(pid, False) for pid in e["parents"])
                continue
            if eid in visiting:
                raise ValueError("dependency cycle")
            visiting.add(eid)
            stack.append((eid, True))
            for pid in reversed(e["parents"]):
                if pid not in by_id:
                    continue  # pending, but validate every available edge
                parent = by_id[pid]
                if parent["key"] != e["key"]:
                    raise ValueError("parent key mismatch")
                if parent["op"] not in ("put", "supersede"):
                    raise ValueError("parent must be put or supersede")
                stack.append((pid, False))
    active = [e for eid, e in by_id.items() if ready[eid]]
    dead = {e["key"] for e in active if e["op"] == "delete"}
    replaced = {p for e in active for p in e["parents"]}
    live = {}
    for e in active:
        if e["key"] not in dead and e["id"] not in replaced:
            live.setdefault(e["key"], []).append(e)
    return {k: sorted(v, key=lambda e: e["id"]) for k, v in live.items()}
```

This copy matches Chapter 12. Replay with `Log.events()` repairs only an unfinished active tail and rejects malformed complete records; `state()` validates dependencies and excludes pending, superseded and deleted values. Rotation publishes a synced copy before truncation, and replay deduplicates event IDs. Preserve tombstones and event history through the supported restore and offline-device period.

## Numbers

- MariaDB `VECTOR(N)`: up to 16383 dimensions; `VECTOR INDEX` M from 3 to 200 (MariaDB vector docs).
- MariaDB stores index values as int16 (15 bits) rather than float16's 10 bits (MariaDB vector overview).
- FTS5 token limit: 32768 bytes (sqlite.org/fts5.html).
- sqlite-vec latest on PyPI: 0.1.9, 2026-03-31 (pypi.org).
- vec1 (sqlite.org): release 0.8.
- LangGraph checkpoint CVEs: CVE-2025-67644, CVSS 7.3; CVE-2025-64439, CVSS 7.4 (CSA note, secondary).
- rocksdb latest tag: v11.13.2 (GitHub redirect in fetch).
- MySQL VECTOR introduced in 9.0.0, 2024-07-01.
- Turso joined by Supabase per banner; date UNVERIFIED.

## Sources

Primary:
- SQLite FTS5: https://sqlite.org/fts5.html
- SQLite vec1 (separate project): https://sqlite.org/vec1.html
- sqlite-vec repo and README: https://github.com/asg017/sqlite-vec ; releases page not readable in fetch
- sqlite-vec on PyPI: https://pypi.org/project/sqlite-vec/
- langgraph-checkpoint-sqlite on PyPI: https://pypi.org/project/langgraph-checkpoint-sqlite/
- LangGraph SqliteSaver reference: https://reference.langchain.com/python/langgraph.checkpoint.sqlite/SqliteSaver
- NVD CVE-2025-67644: https://nvd.nist.gov/vuln/detail/CVE-2025-67644
- Check Point research on LangGraph checkpointer: https://research.checkpoint.com/2026/from-sqli-to-rce-exploiting-langgraphs-checkpointer/
- Turso native vectors: https://turso.tech/vector ; blog: https://turso.tech/blog/turso-brings-native-vector-search-to-sqlite
- DuckDB VSS: https://duckdb.org/docs/2.0/core_extensions/vss.html
- MariaDB Vector overview: https://mariadb.com/docs/server/reference/sql-structure/vectors/vector-overview
- MariaDB VECTOR type: https://mariadb.com/docs/server/reference/sql-structure/vectors/vector
- MySQL 9.0 release notes: https://dev.mysql.com/doc/relnotes/mysql/9.0/en/news-9-0-0.html
- MySQL 9.7 VECTOR type: https://dev.mysql.com/doc/refman/9.7/en/vector.html
- MongoDB Atlas Vector Search: https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/
- ClickHouse agent observability: https://clickhouse.com/resources/engineering/what-is-ai-agent-observability
- OpenSearch version history: https://docs.opensearch.org/latest/version-history/
- RocksDB v11.13.2: https://github.com/meta/rocksdb/releases/tag/v11.13.2
- LMDB Python docs: https://lmdb.readthedocs.io/
- OpenAI conversation state: https://developers.openai.com/api/docs/guides/conversation-state
- Anthropic memory tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- CoALA: https://arxiv.org/abs/2309.02427

Secondary (used only where no primary was readable):
- CSA research note on LangGraph chain: https://labs.cloudsecurityalliance.org/research/csa-research-note-langgraph-rce-chain-cve-20260612-csa-style/
- OpenSearch 3.5 agentic memory (Wikipedia): https://en.wikipedia.org/wiki/OpenSearch_(software)
- TinyJoin browser storage caveats: https://tinyjoin.org/guides/caveats/
- wa-sqlite: https://github.com/rhashimoto/wa-sqlite
- MyRocks archive note: https://artem.krylysov.com/blog/2026/07/23/how-mvcc-and-transactions-work-in-rocksdb/

UNVERIFIED (not confirmed in this pass): OpenAI server-side retention window; sqlite-vec 0.1.9 ANN support; MariaDB planner rule for vector index use; MySQL 9.7 vector index support; MongoDB vector search on self-managed Community; Git and Parquet numbers; RRF constant 60 as best default; Turso/Supabase deal date; fennecdb's claim that sqlite-vec ANN arrived in v0.1.10-alpha.1 (single vendor claim, not checked against the repo).

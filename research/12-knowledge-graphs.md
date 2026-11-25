# Knowledge-graph memory and graph-based retrieval

Research snapshot: 2026-11-20. Every fact carries its source URL. Anything not checked against a primary source is marked **UNVERIFIED**.

## How it works

A knowledge-graph memory system does three things on top of plain RAG:

1. **Extract.** An LLM reads each chunk or episode and emits entities (people, companies, products) and relations or facts between them. Some systems also attach summaries to nodes.
2. **Store.** Nodes and edges go into a graph store (a property graph such as Neo4j, FalkorDB or Kuzu, or a plain file as in the MCP reference server).
3. **Retrieve.** Queries either walk the graph from matched entities (local search), read precomputed summaries of clusters (global search), or spread relevance over the graph with an algorithm such as personalized PageRank.

Microsoft's GraphRAG pipeline builds entities, relationships and hierarchical community summaries, then answers "global" questions over those summaries and "local" questions over entity neighbourhoods. The paper frames vector RAG as good for local "who/what/when/where" questions and weak for corpus-wide questions such as "what are the main themes?" ([arXiv 2404.16130](https://arxiv.org/abs/2404.16130)).

Temporal graphs add a validity window to every edge. Graphiti states the rule directly: "facts have validity windows. When information changes, old facts are invalidated, not deleted" ([getzep/graphiti README](https://github.com/getzep/graphiti)).

## Variants and tools

| Tool | Status (2026-11-20) | Core idea | Source |
|---|---|---|---|
| **Microsoft GraphRAG** | MIT, 36.7k stars, 499 commits. README says the project is "largely in maintenance mode" and will not take new features | Entity/relation extraction, Leiden communities, community summaries; global, local and DRIFT search | [microsoft/graphrag](https://github.com/microsoft/graphrag), [arXiv 2404.16130](https://arxiv.org/abs/2404.16130) |
| **LazyGraphRAG** | Released Nov 2024, folded into Microsoft Discovery and Azure Local (per editor's note, June 2025) | Defers LLM work to query time; indexing costs the same as vector RAG | [MS Research blog, 25 Nov 2024](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/) |
| **LightRAG** | EMNLP 2025, active (News entries through 2026-07). Dual-level keyword retrieval (local + global) over an extracted graph; supports Neo4j, PostgreSQL, MongoDB and OpenSearch storage | Cheap indexing, graph plus vector retrieval | [HKUDS/LightRAG README](https://raw.githubusercontent.com/HKUDS/LightRAG/main/README.md), [arXiv 2410.05779](https://arxiv.org/abs/2410.05779) |
| **HippoRAG / HippoRAG 2** | ICML 2025. Code at OSU-NLP-Group/HippoRAG | Extracts a KG, then runs Personalized PageRank from query entities over the graph | [arXiv 2502.14802](https://arxiv.org/abs/2502.14802) |
| **RAPTOR** | Paper from Jan 2024. Tree of summaries, not a true entity graph | Recursively embed, cluster and summarise chunks; retrieve across levels | [arXiv 2401.18059](https://arxiv.org/abs/2401.18059) |
| **Graphiti (Zep)** | Apache-2.0, 33k stars, 1,080 commits. Reference MCP and REST servers, not production deployments | Bi-temporal context graph: episodes, entities, facts with validity windows, communities; hybrid semantic + BM25 + graph retrieval | [getzep/graphiti](https://github.com/getzep/graphiti), [arXiv 2501.13956](https://arxiv.org/abs/2501.13956) |
| **mem0 graph memory** | Open-source plus hosted platform. Graph variant is "mem0g" in the paper | Extracts entities and links them to memories; docs say it "does not assign typed, labeled relationships" | [arXiv 2504.19413](https://arxiv.org/abs/2504.19413), [docs.mem0.ai graph memory](https://docs.mem0.ai/platform/features/graph-memory) |
| **Cognee** | Open-source memory platform, Apache-2.0 (per third-party review; UNVERIFIED against LICENSE). Ships a local GLiNER extractor and local embeddings when no LLM key is set | Ingest, extract graph, query; embedded Ladybug/Kuzu engine in recent changelog | [github.com/topoteretes/cognee](https://github.com/topoteretes/cognee), [docs.cognee.ai changelog](https://docs.cognee.ai/changelog) |
| **MCP reference memory server** | Published as `@modelcontextprotocol/server-memory`. Needs Node 24+. Stores a JSONL file | Entities, relations, observations; read/search tools | [modelcontextprotocol/servers src/memory](https://raw.githubusercontent.com/modelcontextprotocol/servers/main/src/memory/README.md) |

**Graph stores.**
- **Kuzu is archived.** Its README says the project is being archived, that releases stay usable, and that 0.11.3 is the last release bundling most extensions ([kuzudb/kuzu README](https://raw.githubusercontent.com/kuzudb/kuzu/master/README.md)). The Hacker News thread from Oct 2025 announces the end of active support ([news.ycombinator.com/item?id=45560036](https://news.ycombinator.com/item?id=45560036)). Secondary sources say a fork continues as Ladybug (UNVERIFIED beyond those posts). Do not start new work on Kuzu.
- **FalkorDB** is a Redis-protocol property graph with OpenCypher. An embedded `falkordblite` package exists (blog, 26 Nov 2025), and Graphiti added an extra for it (requires Python 3.12+) ([falkordb.com blog](https://www.falkordb.com/blog/falkordblite-embedded-python-graph-database/), [Graphiti README](https://raw.githubusercontent.com/getzep/graphiti/main/README.md)).
- **Apache AGE** is a PostgreSQL extension. Latest release on the project page is v1.7.0, dated 21 Jan 2026, with PG18 builds and row-level security ([age.apache.org release notes](https://age.apache.org/release-notes/)). It is the pick if you already run Postgres.
- **Neo4j and Memgraph:** UNVERIFIED in this pass. Graphiti officially supports Neo4j 5.26 and FalkorDB 1.1.2 (see Setup).
- **RDF/triple stores** (Virtuoso, Blazegraph, GraphDB): not researched in this pass; UNVERIFIED for this guide.

## Strengths

- **Corpus-wide questions.** GraphRAG's global search answers theme questions that vector top-k cannot. This is the paper's central claim ([arXiv 2404.16130](https://arxiv.org/abs/2404.16130)).
- **Multi-hop and associative recall.** HippoRAG 2 reports a 7% improvement on associative memory tasks over the best embedding model, and says it outperforms standard RAG on factual, sense-making and associative tasks ([arXiv 2502.14802](https://arxiv.org/abs/2502.14802)).
- **Changing facts.** Graphiti keeps history: superseded facts are invalidated, not deleted, and queries can ask what was true at a point in time ([getzep/graphiti README](https://github.com/getzep/graphiti)). Zep reports DMR 94.8% vs MemGPT 93.4%, and LongMemEval accuracy gains up to 18.5% with 90% lower latency versus baselines ([arXiv 2501.13956](https://arxiv.org/abs/2501.13956)). These are the authors' numbers.
- **Relationship-heavy personal memory.** Named entities with typed edges (who works at what, who introduced whom) are natural in a graph and awkward in flat vectors.
- **Provenance.** Graphiti ties every derived fact to its source episode.

## Limits and failure modes

- **Extraction errors compound.** One bad entity merge or wrong relation feeds every later query that walks through it. Graphiti's own README says structured-output-capable LLMs work best and that smaller models can produce wrong schemas and failed ingestion ([getzep/graphiti README](https://github.com/getzep/graphiti)).
- **Build cost.** Full GraphRAG indexing is expensive. Its README warns explicitly: "indexing can be an expensive operation... start small" ([microsoft/graphrag README](https://github.com/microsoft/graphrag)). Graphiti's default `SEMAPHORE_LIMIT` is 10 to avoid 429s, which means ingestion is rate-limit-bound ([getzep/graphiti README](https://github.com/getzep/graphiti)).
- **Schema drift.** Free-form extraction produces `works_at`, `employed_by` and `job` for the same fact. Graphiti's prescribed ontology (Pydantic types) and mem0's untyped graph are two answers to the same problem.
- **Entity resolution.** Merging "Bob Smith", "Robert Smith" and "bob@corp" is a separate, error-prone step. UNVERIFIED how each product handles it beyond the docs above.
- **Hard to debug.** A wrong answer may come from a wrong edge written months ago. Provenance links help only if you read them.
- **Deployment safety.** The Graphiti reference servers have no authentication or prompt-injection filter and must not face an untrusted network ([Graphiti README](https://github.com/getzep/graphiti)). The LightRAG server binds `0.0.0.0` with auth off by default ([LightRAG README](https://raw.githubusercontent.com/HKUDS/LightRAG/main/README.md)). Both are easy to expose by accident.
- **Project health.** GraphRAG is in maintenance mode; Kuzu is archived. Pin versions and plan a migration path.

## Exact use cases

**Pick a knowledge graph when:**
- The data is about **people, companies and who-knows-who**, and you ask about connections (multi-hop).
- **Facts change over time** and you need "was true until" answers. Use Graphiti-style validity windows.
- You need **"summarise the whole corpus"** answers. Use GraphRAG global search or LazyGraphRAG to avoid the full indexing bill.
- **Multi-hop research** across many documents where the answer needs bridging entities. Use HippoRAG 2-style PPR.

**Avoid it when:**
- The questions are **local lookups** ("what did I say about X on Tuesday?"). Vector search or plain files win on cost and on debuggability.
- The corpus is **small** (tens of notes). Read the files.
- You cannot afford **LLM extraction on every write** or cannot tolerate wrong edges silently persisting.
- You only need **preferences and short facts** about one user. A keyed profile or an MCP memory file is enough.
- Your **data changes faster than you can re-extract**. Plain vectors with timestamps are simpler.

## Setup walkthrough

All commands below are copied from the cited READMEs. Items marked UNVERIFIED were not run.

### A. Graphiti with FalkorDB (fastest local start)

Source: [getzep/graphiti README](https://github.com/getzep/graphiti)

```bash
# 1. Graph database (FalkorDB 1.1.2+ is the tested floor)
docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest

# 2. Python package with the FalkorDB extra
pip install "graphiti-core[falkordb]"
#    or the embedded variant (Python 3.12+):
#    pip install "graphiti-core[falkordblite]"

# 3. LLM key (Graphiti defaults to OpenAI; Anthropic and Gemini are extras)
export OPENAI_API_KEY=sk-...
export SEMAPHORE_LIMIT=5   # lower it if you see 429s
```

Then copy the quickstart from `examples/quickstart/` in the Graphiti repo. Its README covers connecting, building indices, adding episodes, and hybrid search. The exact Python class names are UNVERIFIED here; take them from the example, not from memory.

For Neo4j instead, the README says `docker compose up` in the repo starts Neo4j, and Graphiti needs **Neo4j 5.26**.

### B. Microsoft GraphRAG CLI: index and query

Sources: [get_started](https://microsoft.github.io/graphrag/get_started/), [CLI reference](https://microsoft.github.io/graphrag/cli/)

```bash
mkdir graphrag_quickstart && cd graphrag_quickstart
python -m venv .venv && source .venv/bin/activate
python -m pip install graphrag

graphrag init                      # writes .env, settings.yaml, input/
curl https://www.gutenberg.org/cache/epub/24022/pg24022.txt -o ./input/book.txt
# set GRAPHRAG_API_KEY in .env

graphrag index --root . --dry-run  # validate config, no LLM calls
graphrag index --root . --method standard
```

`--dry-run`, `--method standard|fast|standard-update|fast-update` and `--no-cache` are listed in the CLI reference. Query flags are UNVERIFIED in this pass: the docs have Global, Local and DRIFT search pages, so run `graphrag query --help` and use the method name it lists. The quickstart says to start with the tutorial text and a cheap model.

### C. LightRAG server quickstart

Source: [HKUDS/LightRAG README](https://raw.githubusercontent.com/HKUDS/LightRAG/main/README.md)

```bash
uv tool install "lightrag-hku[api]"
curl -O https://raw.githubusercontent.com/HKUDS/LightRAG/main/env.example
cp env.example .env
# in .env, before first start:
#   HOST=127.0.0.1
#   LIGHTRAG_API_KEY=$(openssl rand -hex 32)
lightrag-server
```

The README's warning is explicit: the server binds all interfaces by default with auth off. Bind to localhost or set a key first.

### D. MCP knowledge-graph memory server

Source: [modelcontextprotocol/servers src/memory](https://raw.githubusercontent.com/modelcontextprotocol/servers/main/src/memory/README.md). Requires Node 24+.

Claude Desktop or Claude Code MCP config:

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": {
        "MEMORY_FILE_PATH": "/home/you/.local/share/mcp-memory/memory.jsonl"
      }
    }
  }
}
```

Use an absolute path you own. Optional caps `MEMORY_MAX_ENTITIES`, `MEMORY_MAX_RELATIONS` and `MEMORY_MAX_FILE_BYTES` are opt-in. Over HTTP, run `npx -y @modelcontextprotocol/server-memory --transport streamable-http`, which listens on `127.0.0.1:3001`.

## Numbers

Only figures from papers or official docs are listed.

| Claim | Value | Source |
|---|---|---|
| LazyGraphRAG indexing cost vs full GraphRAG | 0.1% (same as vector RAG) | [MS Research blog, 25 Nov 2024](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/) |
| Zep on DMR | 94.8% vs MemGPT 93.4% | [arXiv 2501.13956](https://arxiv.org/abs/2501.13956) |
| Zep on LongMemEval | up to +18.5% accuracy, up to -90% latency vs baselines | [arXiv 2501.13956](https://arxiv.org/abs/2501.13956) |
| HippoRAG 2 on associative memory | +7% vs the best embedding model | [arXiv 2502.14802](https://arxiv.org/abs/2502.14802) |
| RAPTOR on QuALITY (with GPT-4) | +20% absolute accuracy vs prior best | [arXiv 2401.18059](https://arxiv.org/abs/2401.18059) |
| Graphiti default concurrency | SEMAPHORE_LIMIT = 10 | [getzep/graphiti README](https://github.com/getzep/graphiti) |
| Graphiti minimum backends | Neo4j 5.26, FalkorDB 1.1.2 | [getzep/graphiti README](https://github.com/getzep/graphiti) |
| Apache AGE latest | v1.7.0, 21 Jan 2026 | [age.apache.org](https://age.apache.org/release-notes/) |

**UNVERIFIED:** absolute GraphRAG indexing cost in dollars or tokens per corpus, LightRAG's cost and quality versus GraphRAG in its own paper table, and mem0g's LOCOMO scores beyond the paper abstract. Get these from the papers' tables before publishing any number.

## Sources

- Microsoft GraphRAG repo and docs: https://github.com/microsoft/graphrag , https://microsoft.github.io/graphrag/get_started/ , https://microsoft.github.io/graphrag/cli/
- GraphRAG paper: https://arxiv.org/abs/2404.16130
- LazyGraphRAG blog: https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/
- LightRAG: https://github.com/HKUDS/LightRAG , https://arxiv.org/abs/2410.05779
- HippoRAG 2: https://arxiv.org/abs/2502.14802
- RAPTOR: https://arxiv.org/abs/2401.18059
- Zep / Graphiti: https://arxiv.org/abs/2501.13956 , https://github.com/getzep/graphiti
- mem0: https://arxiv.org/abs/2504.19413 , https://docs.mem0.ai/platform/features/graph-memory
- Cognee: https://github.com/topoteretes/cognee , https://docs.cognee.ai/changelog
- MCP memory server: https://raw.githubusercontent.com/modelcontextprotocol/servers/main/src/memory/README.md
- Kuzu archive notice: https://raw.githubusercontent.com/kuzudb/kuzu/master/README.md , https://news.ycombinator.com/item?id=45560036
- FalkorDBLite: https://www.falkordb.com/blog/falkordblite-embedded-python-graph-database/
- Apache AGE: https://age.apache.org/release-notes/

# Verified setup sheet: agent memory stack (researched 2026-11-20)

Method: official README or docs page fetched through the SearXNG `web_url_read` tool on 2026-11-20. Where a fetch returned only site navigation, the item is marked UNVERIFIED. Release dates were not verified for any item, so they are UNVERIFIED throughout. Commands are copied from the cited page, not written from memory.

---

## 1. pgvector (PostgreSQL extension)

- **Version:** v0.8.7 (README clone example and Docker tags). Supports Postgres 13+ per README. Release date: UNVERIFIED.
- **Install (Docker):** `docker pull pgvector/pgvector:pg19-trixie` (tags `pg15` to `pg19`, bookworm and trixie variants listed).
- **Install (APT):** `sudo apt install postgresql-19-pgvector` (replace 19 with your server major version; needs the PostgreSQL APT repo).
- **Install (source):** `git clone --branch v0.8.7 https://github.com/pgvector/pgvector.git && cd pgvector && make && make install`
- **Quickstart:**
  ```sql
  CREATE EXTENSION vector;
  CREATE TABLE items (id bigserial PRIMARY KEY, embedding vector(3));
  INSERT INTO items (embedding) VALUES ('[1,2,3]'), ('[4,5,6]');
  SELECT * FROM items ORDER BY embedding <-> '[3,1,2]' LIMIT 5;
  ```
- **HNSW index:** `CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops);` Defaults `m = 16`, `ef_construction = 64`. Query-time `SET hnsw.ef_search = 100;` (default 40).
- **Default port:** 5432 (standard Postgres default, not stated in the pgvector README).
- **Gotchas (from README):**
  1. `vector` HNSW supports up to 2,000 dimensions. `halfvec` goes to 4,000.
  2. Approximate indexes change query results. Recall is lower than exact search.
  3. `<#>` returns the **negative** inner product. Multiply by -1 to read the score.
  4. Parallel HNSW builds need `--shm-size` at least as large as `maintenance_work_mem` in Docker.
- **Source:** https://github.com/pgvector/pgvector (raw README: https://raw.githubusercontent.com/pgvector/pgvector/master/README.md)

## 2. Redis 8 / Redis Stack (vector index)

- **Version:** Redis Open Source 8.6 release notes page exists (search snippet). Exact GA date: UNVERIFIED.
- **Docker install:** UNVERIFIED. The docs page at https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/docker/ fetched only navigation. Do not use a command from this sheet until checked.
- **Vector index:** Redis docs say the index is created with `FT.CREATE` and a `VECTOR` field, queried with `FT.SEARCH` KNN, and combined with keywords via `FT.HYBRID`. The exact `FT.CREATE` syntax was not captured, so it is UNVERIFIED here.
- **Source:** https://redis.io/docs/latest/develop/get-started/search-tutorial/vector-search/ and https://redis.io/docs/latest/develop/ai/search-and-query/vectors/
- **Gotchas:** UNVERIFIED (not captured).

## 3. Valkey

- **Version:** UNVERIFIED (the repo README does not state a release number).
- **Build from source:** `make` (TLS: `make BUILD_TLS=yes`, needs libssl-dev). Tests: `make test`.
- **Docker (bundle with search, JSON, bloom):**
  ```bash
  docker run --name my-valkey-bundle -d -p 6379:6379 valkey/valkey-bundle
  ```
- **Default port:** 6379.
- **Gotchas:**
  1. Valkey Bundle ships Valkey Search, which is the vector path. Plain `valkey/valkey` has no vector index.
  2. Pin a tag such as `8.1-bookworm` for reproducible builds (the Valkey Bundle page recommends this).
  3. Valkey forked from Redis before the license change (README).
- **Source:** https://github.com/valkey-io/valkey and https://valkey.io/topics/valkey-bundle/

## 4. Memcached

- **Version:** UNVERIFIED.
- **Install (from tarball):**
  ```bash
  ./configure
  make
  make test   # optional
  make install
  ```
  Needs libevent (`libevent-dev` on Debian/Ubuntu). TLS: `./configure --enable-tls`.
- **Run and check:** `./memcached`, then `telnet 127.0.0.1 11211` and `stats`.
- **Default port:** 11211 (from README telnet example).
- **Gotchas:**
  1. Memcached is a cache with no disk persistence. It is not a memory store of record.
  2. The `-k` (mlockall) option can be dangerous with a large cache, per README.
  3. Docker image: UNVERIFIED.
- **Source:** https://github.com/memcached/memcached (raw README: https://raw.githubusercontent.com/memcached/memcached/master/README.md)

## 5. Qdrant (Docker)

- **Version:** UNVERIFIED (README does not state one).
- **Run:**
  ```bash
  docker run -p 6333:6333 qdrant/qdrant
  ```
- **Client:**
  ```python
  from qdrant_client import QdrantClient
  client = QdrantClient(url="http://localhost:6333")
  ```
- **Default port:** 6333 (REST, from the run command).
- **Gotchas (README):**
  1. The docker command starts an **insecure** deployment with no authentication, open on all interfaces. Read the security guide before exposing it.
  2. Read the installation guide before production.
- **Source:** https://github.com/qdrant/qdrant ; docs: https://qdrant.tech/documentation/installation/

## 6. Chroma

- **Version:** UNVERIFIED. The README says Python and npm packages release on Mondays, with hotfixes at any time.
- **Install:** `pip install chromadb` (Python). `npm install chromadb` (JavaScript).
- **Client-server mode:** `chroma run --path /chroma_db_path`
- **Minimal example (README):**
  ```python
  import chromadb
  client = chromadb.Client()
  collection = client.create_collection("all-my-documents")
  collection.add(documents=["This is document1", "This is document2"],
                 metadatas=[{"source": "notion"}, {"source": "google-docs"}],
                 ids=["doc1", "doc2"])
  results = collection.query(query_texts=["This is a query document"], n_results=2)
  ```
- **Default port for `chroma run`:** UNVERIFIED (the CLI docs page fetched only navigation).
- **Gotchas:**
  1. `chromadb.Client()` is in-memory. Use a persistent client or `chroma run --path` to keep data (README says persistence is "easy to add").
  2. The client embeds documents by default. Pass your own embeddings to skip the default embedder.
- **Source:** https://github.com/chroma-core/chroma ; docs: https://docs.trychroma.com/docs/cli/run (navigation only)

## 7. LanceDB

- **Version:** UNVERIFIED.
- **Install:** UNVERIFIED. The README sends you to the Quickstart and does not show a pip line. Docs: https://docs.lancedb.com (Quickstart at https://docs.lancedb.com/quickstart).
- **SDKs (README table):** Python https://lancedb.github.io/lancedb/python/python/ ; TypeScript https://lancedb.github.io/lancedb/js/globals/ ; Rust https://docs.rs/lancedb/latest/lancedb/index.html
- **Gotchas:**
  1. Embedded LanceDB runs in your process. Data can sit on local disk or object storage (README).
  2. "LanceDB Enterprise" is a separate paid product. The open-source embedded build is what this guide covers.
- **Source:** https://github.com/lancedb/lancedb

## 8. sqlite-vec

- **Version:** UNVERIFIED (README says pre-v1).
- **Install:** `pip install sqlite-vec` (Python). `npm install sqlite-vec` (Node.js). `cargo add sqlite-vec` (Rust).
- **Minimal example:** UNVERIFIED (the README points to https://alexgarcia.xyz/sqlite-vec/python.html, which was not fetched). The README confirms vectors live in `vec0` virtual tables.
- **Gotchas (README):**
  1. Pre-v1: "expect breaking changes." Pin the version.
  2. Stores float, int8 and binary vectors. Non-vector data goes in metadata, auxiliary or partition-key columns.
- **Source:** https://github.com/asg017/sqlite-vec

## 9. Ollama: embedding model pull and call

- **Version:** UNVERIFIED.
- **Install (Linux and macOS):** `curl -fsSL https://ollama.com/install.sh | sh`. Windows: `irm https://ollama.com/install.ps1 | iex`. Docker: `ollama/ollama`.
- **Qwen3 embedding tags (confirmed on the Ollama library page):**
  - `qwen3-embedding:0.6b` (639 MB, 32K context)
  - `qwen3-embedding:4b` (2.5 GB, 40K context)
  - `qwen3-embedding:8b` (4.7 GB, 40K context). Also tagged `latest`.
  - `qwen3-embedding` (no tag) resolves to `latest`, which is the 8b model.
- **Pull and call:**
  ```bash
  ollama pull qwen3-embedding:0.6b
  curl http://localhost:11434/api/embed \
    -d '{"model": "qwen3-embedding:0.6b", "input": "Why is the sky blue?"}'
  ```
  Python: `ollama.embed(model='qwen3-embedding:0.6b', input='...')` then `response.embeddings`.
- **Default port:** 11434.
- **Gotchas:**
  1. The README's own examples use `gemma4` for chat. Embedding calls use `/api/embed`, not `/api/chat`.
  2. Pick the tag on purpose. `qwen3-embedding` with no tag pulls 8b, which is 4.7 GB.
- **Source:** https://github.com/ollama/ollama ; https://ollama.com/library/qwen3-embedding

## 10. Hugging Face text-embeddings-inference (TEI), CPU

- **Version:** the docs example uses image tag `cuda-1.9`. CPU tag: UNVERIFIED (the CPU tag was not in the fetched text).
- **Docker (GPU, verified text):**
  ```bash
  model=Qwen/Qwen3-Embedding-0.6B
  volume=$PWD/data
  docker run --gpus all -p 8080:80 -v $volume:/data --pull always \
    ghcr.io/huggingface/text-embeddings-inference:cuda-1.9 --model-id $model
  ```
  For CPU, drop `--gpus all` and use the CPU image tag, which is UNVERIFIED. Confirm the tag at https://github.com/huggingface/text-embeddings-inference before use.
- **Call:**
  ```bash
  curl 127.0.0.1:8080/embed -X POST -d '{"inputs":"What is Deep Learning?"}' -H 'Content-Type: application/json'
  ```
- **Port:** host 8080 maps to container 80 in the example.
- **Gotchas (README):**
  1. Qwen3 embedding models are listed as supported (Qwen3-Embedding-0.6B is the small one).
  2. The `--gpus all` flag needs the NVIDIA Container Toolkit, and drivers need CUDA 12.2 or newer. Neither applies to CPU.
  3. Weights download on first run. Share a volume (`-v $PWD/data:/data`) to avoid re-downloading.
- **Source:** https://github.com/huggingface/text-embeddings-inference

## 11. llama.cpp `llama-server` (embedding mode and chat with JSON schema)

- **Version:** UNVERIFIED (no release number captured).
- **Run (README quick start):**
  ```bash
  ./llama-server -m models/7B/ggml-model.gguf -c 2048
  ```
  The README says it listens on `127.0.0.1:9931` by default. Docker example: `docker run -p 8080:8080 -v /path/to/models:/models ghcr.io/ggml-org/llama.cpp:server -m models/7B/ggml-model.gguf -c 512 --host 0.0.0.0 --port 8080`
- **Embedding mode:** the README lists `POST /v1/embeddings` (OpenAI-compatible) and `POST /embedding`. The server flag that enables embeddings (`--embedding`) was NOT captured. UNVERIFIED.
- **Chat with JSON schema output:** the README feature list includes "Schema-constrained JSON response format" and the OpenAI-compatible `POST /v1/chat/completions`. The exact flag or request field for the schema was NOT captured. UNVERIFIED.
- **Other endpoints (README):** `/v1/responses`, `/v1/messages` (Anthropic-compatible), `/health`, `/models`.
- **Gotchas (README):**
  1. The README's own default listen address (`127.0.0.1:9931`) and the Docker example (`8080`) differ. Pass `--host` and `--port` explicitly.
  2. Grammar errors on `/completion` return HTTP 400 "Failed to parse grammar".
- **Source:** https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

## 12. MLX-LM server on Apple Silicon

- **Version:** UNVERIFIED.
- **Install:** `pip install mlx-lm` (or `conda install -c conda-forge mlx-lm`).
- **Minimal commands (README):**
  ```bash
  mlx_lm.generate --model mistralai/Mistral-7B-Instruct-v0.3 --prompt "hello"
  mlx_lm.chat
  ```
  The README mentions `mlx_lm.server` as a command that accepts `--prefill-step-size`. Its start command and default port were NOT captured. UNVERIFIED.
- **Gotchas (README):**
  1. Default generation model is `mlx-community/Llama-3.2-3B-Instruct-4bit`.
  2. Use `--max-kv-size` to cap RAM for long contexts. Smaller values use less RAM and reduce quality.
  3. `--prefill-step-size` defaults to 2048. Lower it to cut peak memory.
- **Source:** https://github.com/ml-explore/mlx-lm

## 13. mem0 open-source with a local OpenAI-compatible LLM and local embedder

- **Version:** UNVERIFIED.
- **Install:** `pip install mem0ai` (Python 3.10+).
- **Default (README/quickstart):** `Memory()` uses OpenAI `gpt-5-mini` for extraction, `text-embedding-3-small` (1536 dims), a Qdrant store at `/tmp/qdrant`, and SQLite history at `~/.mem0/history.db`.
- **Minimal call:**
  ```python
  from mem0 import Memory
  m = Memory()
  m.add([{"role": "user", "content": "Hi, I'm Alex. I love basketball and gaming."}], user_id="alex")
  m.search("What do you know about me?", filters={"user_id": "alex"})
  ```
- **Local config:** the docs say Ollama works as the LLM and as the embedder. Pages: https://docs.mem0.ai/components/llms/models/ollama and https://docs.mem0.ai/components/embedders/models/ollama. Those pages returned only navigation, so the config keys (`llm`, `embedder`, `provider`, `config`) are UNVERIFIED here.
- **Gotchas:**
  1. The default `Memory()` calls OpenAI and needs `OPENAI_API_KEY`. A local setup must override the config.
  2. The default vector store is on-disk Qdrant under `/tmp`, which is not durable.
  3. The docs say the OSS path changed in v3 ("migrating to the new memory algorithm"). Read that page before copying old examples.
- **Source:** https://docs.mem0.ai/open-source/python-quickstart ; https://docs.mem0.ai/open-source/setup (self-hosted bundle, not fetched)

## 14. Graphiti (getzep/graphiti)

- **Version:** UNVERIFIED. Requirements in README: Python 3.10+, Neo4j 5.26 (or FalkorDB 1.1.2, or Neptune).
- **Install:** `pip install graphiti-core` or `uv add graphiti-core`. FalkorDB extra: `pip install graphiti-core[falkordb]`.
- **Graph DB via Docker:** README says use `docker compose up` from the examples (Neo4j) or `docker compose --profile falkordb up`. FalkorDB single container: `docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest`
- **Minimal example:** the README points to `examples/quickstart/README.md` (connect to Neo4j, build indices, add episodes, hybrid search). The code was not fetched, so UNVERIFIED here.
- **Gotchas (README):**
  1. Defaults to OpenAI for LLM and embeddings. `OPENAI_API_KEY` must be set.
  2. Works best with LLMs that support structured output (OpenAI, Anthropic, Gemini). Smaller or other models can produce bad schemas and failed ingestion.
  3. Graphiti is a framework, not a finished memory service. You supply the DB, LLM and embedder, and build ingestion and access control yourself.
- **Source:** https://github.com/getzep/graphiti

## 15. Hindsight (vectorize-io/hindsight), local and embedded

- **Version:** docs site shows 1.2 as current. Release date: UNVERIFIED.
- **Docker server (README, verified):**
  ```bash
  export OPENAI_API_KEY=sk-xxx
  docker run -it --pull always --name hindsight --restart unless-stopped -p 8888:8888 -p 9999:9999 \
    -e HINDSIGHT_API_LLM_API_KEY=$OPENAI_API_KEY \
    -v hindsight-data:/home/hindsight/.pg0 \
    ghcr.io/vectorize-io/hindsight:latest
  ```
  API on port 8888, UI on port 9999.
- **Fully local LLM:** README says `HINDSIGHT_API_LLM_PROVIDER` accepts `ollama`, `lmstudio` and `llamacpp`, plus any OpenAI-compatible endpoint.
- **Embedded Python (no server):** the docs say `pip install hindsight-all` bundles `hindsight-api-slim`, `hindsight-client` and `hindsight-embed`. Exact install line and code: UNVERIFIED (the README section heading was not found when fetched; the page https://hindsight.vectorize.io/sdks/hindsight-all returned navigation only).
- **Gotchas:**
  1. Docker command pulls `ghcr.io/vectorize-io/hindsight:latest` with `--pull always`. Pin a version for reproducible setups.
  2. Subscription logins (`openai-codex`, `claude-code`, `cursor`, `github-copilot`) need no API key, per README.
  3. A docs install note says the full `hindsight-api` and `hindsight-all` packages need a newer Python than some systems ship. The exact version is UNVERIFIED.
- **Source:** https://github.com/vectorize-io/hindsight ; https://hindsight.vectorize.io/sdks/python

## 16. Letta

- **Version:** UNVERIFIED.
- **Current state (README):** the active source moved to `letta-ai/letta-code`. The old Letta V1 API server lives on the `archive` branch and is retired.
- **Install and run (README):**
  ```bash
  npm install -g @letta-ai/letta-code
  letta            # interactive terminal UI
  letta server     # App Server for local or self-hosted agents
  ```
- **Port:** UNVERIFIED.
- **Gotchas:**
  1. Old Python-server tutorials (`pip install letta`, `letta server` from the V1 API) point at the archived branch. Do not copy them.
  2. Letta Cloud keeps agent memory across machines. Local self-hosted is the path for this guide.
- **Source:** https://github.com/letta-ai/letta

## 17. MCP reference memory server (config JSON)

- **Package:** `@modelcontextprotocol/server-memory` (npm). Knowledge-graph memory (entities, relations, observations).
- **Config (verbatim from the README, NPX):**
  ```json
  {
    "mcpServers": {
      "memory": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"]
      }
    }
  }
  ```
- **Custom storage file:**
  ```json
  {
    "mcpServers": {
      "memory": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": { "MEMORY_FILE_PATH": "/path/to/custom/memory.jsonl" }
      }
    }
  }
  ```
  Default file is `memory.jsonl` in the server directory. A leading `~` expands to your home directory.
- **Windows:** use `"command": "cmd", "args": ["/c", "npx", "-y", "@modelcontextprotocol/server-memory"]`.
- **Docker variant (README):** `docker run -i -v claude-memory:/app/dist --rm mcp/memory`
- **Version:** UNVERIFIED.
- **Gotchas (README):**
  1. Write tools are strict. `create_entities` skips names that already exist. `create_relations` fails if either entity is missing. Use `add_observations` to extend an entity.
  2. `delete_entities` cascades to every relation touching that entity.
  3. The default JSONL file lives in the server's install directory, so set `MEMORY_FILE_PATH` to keep it somewhere durable.
- **Source:** https://github.com/modelcontextprotocol/servers/tree/main/src/memory

## 18. Anthropic memory tool

- **Tool type string:** `memory_20250818`, with `name` set to `memory`. Verified from the docs.
- **Minimal tools entry (verbatim from docs):**
  ```json
  {"type": "memory_20250818", "name": "memory"}
  ```
  The docs say this entry is the whole configuration. No input schema is defined for an Anthropic-provided tool.
- **Full request body:** the messages request shape around that entry was NOT captured. UNVERIFIED. Read the Messages API page and https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool before writing code.
- **Availability:** "all Claude 4 and later models" (docs).
- **Client-side handler:** Claude sends `tool_use` with `name: "memory"` and commands such as `view` with `path: "/memories"`. Your app runs the operation and returns a `tool_result`. The docs say memory lives entirely in your app.
- **Gotchas (docs):**
  1. The handler must reject any path outside `/memories` (path traversal protection, documented in the same page).
  2. Memory persists only if the same `tools` entry is sent and your handler serves the same store.
  3. The docs call the tool client-side. Anthropic does not host the memory store.
- **Source:** https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool

## 19. Neo4j (Docker)

- **Version:** UNVERIFIED.
- **Docker command:** UNVERIFIED. The official page https://neo4j.com/docs/operations-manual/current/docker/ returned navigation only.
- **Graph-memory note:** Neo4j docs list "Agent Memory" (https://neo4j.com/labs/agent-memory/getting-started/) and a vector-index guide (https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/). Graphiti's README uses Neo4j 5.26 as its minimum.
- **Gotchas:** UNVERIFIED.
- **Source:** https://neo4j.com/docs/operations-manual/current/docker/

## 20. Microsoft GraphRAG CLI

- **Version:** UNVERIFIED.
- **Install and init (README and getting-started page):** install per https://microsoft.github.io/graphrag/get_started/ (Python venv, then `pip install graphrag`). The README verifies `graphrag init --root [path] --force`.
- **Commands:** `graphrag init` is verified. `graphrag index` and `graphrag query` were NOT verified in the captured text. UNVERIFIED.
- **Gotchas (README):**
  1. The project is in **maintenance mode**. The README says it will not accept new PRs or features, only bug fixes and CVE updates. Treat it as a reference, not a base for new work.
  2. Indexing is expensive. The README says start small with the tutorial dataset.
  3. After a minor version bump, run `graphrag init --root [path] --force` to refresh the config. This overwrites config and prompts, so back them up first.
- **Source:** https://github.com/microsoft/graphrag ; https://microsoft.github.io/graphrag/get_started/

---

## Items not verified (summary)

- Redis Stack docker command and `FT.CREATE` syntax (items 2)
- Valkey version and core Docker image (item 3)
- Memcached Docker image and version (item 4)
- Qdrant version and Python client install line (item 5)
- Chroma `chroma run` default port (item 6)
- LanceDB install line and code (item 7)
- sqlite-vec Python minimal query (item 8)
- TEI CPU image tag (item 10)
- llama.cpp `--embedding` flag and JSON-schema request field (item 11)
- MLX-LM server start command and port (item 12)
- mem0 local LLM and embedder config keys (item 13)
- Graphiti quickstart code (item 14)
- Hindsight embedded install line and code (item 15)
- Letta port and Python path (item 16)
- Anthropic memory tool full request body (item 18)
- Neo4j Docker command (item 19)
- GraphRAG `index` and `query` commands (item 20)
- Release dates for every item

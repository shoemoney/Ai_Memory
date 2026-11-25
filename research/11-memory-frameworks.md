# Agent memory frameworks and services: state as of 2026-11-20

Scope: the layer that wraps an LLM, an embedder and a store into a memory service. Versions and star counts come from the GitHub and PyPI APIs on 2026-11-20. Every figure carries its source. Anything not checked against a primary source is marked **UNVERIFIED**.

## How it works

Most frameworks in this space do the same three things with different trade-offs.

1. **Write path.** Raw turns or documents go in. Some frameworks call an LLM to extract facts (mem0, Graphiti, Hindsight). Some let the agent decide what to save through tool calls (Letta, the MCP memory server, basic-memory). Some store raw text and never call an LLM (filesystem and grep setups).
2. **Store.** Vectors (Qdrant, Chroma, pgvector), a temporal knowledge graph (Graphiti on Neo4j, FalkorDB or Neptune), editable in-context blocks (Letta), or plain Markdown files (basic-memory, Claude's memory tool).
3. **Read path.** Hybrid retrieval (semantic plus BM25 plus entity or graph) returns snippets that get injected into the prompt. Some frameworks add an LLM reasoning step on top (Hindsight `reflect`, Letta's agent loop).

The dispute in this area is mostly about step 3. Retrieval recall and end-to-end answer accuracy are different numbers, and the benchmarks do not always separate them (see Numbers).

## Frameworks table

Star counts are GitHub stargazers on 2026-11-20. "Latest" is the newest GitHub release or the PyPI version, whichever the source gives.

| Framework | Latest (date) | Licence | Architecture | Write-path LLM calls | Read-path LLM calls | Storage | Source |
|---|---|---|---|---|---|---|---|
| **mem0** (OSS SDK, OpenMemory, Platform) | GitHub tag `ts-v3.3.1` (2026-09-25); PyPI `mem0ai` 2.2.1 (2026-09-25). Version mismatch unresolved, see Limits | Apache-2.0, 69,279 stars | Vector store plus LLM fact extraction. README says the April 2026 algorithm is single-pass ADD-only extraction with entity linking and multi-signal retrieval | One extraction call per add (README). Earlier versions also ran UPDATE/DELETE calls (UNVERIFIED for the current version) | Hybrid retrieval (semantic, BM25, entity). No LLM call in the retrieval step per README. Entity extraction may use an LLM (UNVERIFIED) | Qdrant and others; default embedder `text-embedding-3-small`, default LLM `gpt-5-mini` (README) | github.com/mem0ai/mem0 README |
| **Graphiti** (Zep's OSS engine) | `graphiti-core` 0.31.2 on PyPI (2026-10-20) | Apache-2.0, 32,959 stars | Temporal context graph. Facts carry validity windows and are invalidated, not deleted, when superseded. Every fact links to its source episode | Several per episode: entity and edge extraction, dedup, invalidation (details UNVERIFIED). Needs a model with structured output (README) | No LLM call on the default search path ("without reliance on LLM summarization", README) | Neo4j 5.26, FalkorDB 1.1.2, or Neptune plus OpenSearch (README) | github.com/getzep/graphiti README |
| **Zep** (managed service) | Service, no version | Closed service. Graphiti is the open part | Enterprise context graph (Konig graph DB) built on Graphiti | Managed | Managed | Konig (managed) or BYOC | github.com/getzep/graphiti README |
| **Letta** (formerly MemGPT) | Active code is `letta-code`, npm `@letta-ai/letta-code`. Last `letta` tag 0.16.8 (2026-05-14). `letta-client` on PyPI 1.12.1 (2026-06-02) | Apache-2.0, 25,503 stars for `letta` | OS-style tiers: core memory blocks in context, recall and archival memory outside context, agent edits its own memory with tools. Sleep-time agents edit blocks asynchronously | Agent's own tool calls (core_memory_replace, archival_memory_insert). Sleep-time agent adds background calls | The agent's loop: blocks always in context, archival via search tool | Postgres for the server (UNVERIFIED). Local filesystem for letta-code context repositories | github.com/letta-ai/letta, letta.com/blog/context-repositories |
| **Hindsight** (Vectorize) | `hindsight-api` 1.2.3 on PyPI (2026-11-19); GitHub `v1.2.3` (2026-11-19) | MIT, 62,201 stars | Four logical networks (world facts, agent experiences, entity summaries, beliefs). Operations: retain, recall, reflect. Biomimetic framing per the paper | `retain` extracts facts and entities with an LLM. `reflect` is an LLM reasoning call. Whether `recall` calls an LLM is UNVERIFIED | `recall` is multi-strategy retrieval. `reflect` calls the LLM | PostgreSQL, or embedded pg0 for local. 25+ LLM providers including `ollama`, `lmstudio`, `llamacpp` | github.com/vectorize-io/hindsight README; arxiv.org/abs/2512.12818 |
| **LangMem / LangGraph Store** | LangMem launched Feb 2025 (blog). Current version UNVERIFIED | LangMem MIT (UNVERIFIED) | LangGraph stores long-term memory as JSON documents in a store with namespaces. LangMem adds extraction and consolidation tools on top | LangMem extraction calls the LLM you pass in (UNVERIFIED in detail) | Store search, plus LangMem's search tools | Any LangGraph store backend | docs.langchain.com/oss/python/concepts/memory; langchain.com/blog/langmem-sdk-launch |
| **Cognee** | v1.6.10 (2026-11-18), PyPI same | Apache-2.0, 33,432 stars | Knowledge-graph memory with vector and graph stores | LLM extraction into graph (UNVERIFIED detail) | Graph plus vector search | Graph DB plus vector DB | github.com/topoteretes/cognee |
| **MemOS** (MemTensor) | v2.0.36 (2026-11-09) | Apache-2.0, 12,465 stars | "Memory operating system" with MemCube units | UNVERIFIED | UNVERIFIED | UNVERIFIED | github.com/MemTensor/MemOS; arxiv.org/html/2610.26825v1 |
| **Memobase** (memodb-io) | UNVERIFIED | UNVERIFIED | User-profile-based memory: profiles per user rather than per-turn facts | UNVERIFIED | UNVERIFIED | UNVERIFIED | github.com/memodb-io/memobase |
| **supermemory** | server-v0.0.9 (2026-10-12) | MIT, 31,677 stars | Hosted memory engine plus OSS repo, with its own MemoryBench harness | UNVERIFIED | UNVERIFIED | Hosted | github.com/supermemoryai/supermemory; supermemory.ai/blog |
| **A-MEM** | Research code, NeurIPS 2025 | UNVERIFIED | Zettelkasten-style notes: each memory is written with keywords and links, and linked memories evolve | LLM writes the note and links | LLM-assisted retrieval (UNVERIFIED) | Local | arxiv.org/abs/2502.12110; github.com/WujiangXu/A-mem |
| **Memary** | UNVERIFIED | UNVERIFIED | Not checked in this pass | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| **OpenMemory MCP** (mem0) | Part of the mem0 product; version UNVERIFIED | Apache-2.0 per mem0 repo (UNVERIFIED for this component) | Local MCP server wrapping mem0 with a local vector store | Same as mem0 OSS | Same as mem0 OSS | Local vector store (Qdrant) | github.com/mem0ai/mem0 README |
| **MCP reference memory server** (`@modelcontextprotocol/server-memory`) | Part of `modelcontextprotocol/servers` v2.5.0 (2026-11-18). Package version UNVERIFIED | MIT per a directory listing (secondary, UNVERIFIED against LICENSE) | Knowledge graph of entities, typed relations and atomic observations, stored as local JSON | None. The client model decides what to write through tools | None. Read tools return graph slices to the client model | Local JSON file | github.com/modelcontextprotocol/servers/tree/main/src/memory |
| **basic-memory** | v1.0.0 (2026-10-29), PyPI same | AGPL-3.0-or-later, 4,647 stars | Markdown files as memory with observations and wikilinks, plus MCP server | None on the server. The client writes via tools | Search over files (index details UNVERIFIED) | Plain Markdown on disk; optional cloud sync | github.com/basicmachines-co/basic-memory README |
| **OpenAI ChatGPT memory** | Product feature, not versioned | Closed | Two layers: "saved memories" (things you asked it to remember) and "reference chat history" (draws on past chats). Turning off reference chat history does not delete saved memories | Managed, details UNVERIFIED | Managed | Managed | help.openai.com/en/articles/8590148-memory-in-chatgpt; openai.com/index/chatgpt-memory-dreaming/ (June 2026 post on consolidation, details UNVERIFIED) |
| **Claude memory** | Product feature (app), plus Claude Code auto memory and the Claude Platform memory tool | Closed (product), docs public | Platform memory tool: Claude writes files under `/memories` and reads them in later conversations. Claude Code: CLAUDE.md (human-written) plus auto memory (Claude-written notes) | Managed for the app | Managed for the app | Files | platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool (fetched 2026-11-20, page text partial); code.claude.com/docs/en/memory |

## Strengths

- **mem0**: simplest API (`add`, `search`), widest integration list, self-hostable with Qdrant and Ollama. Its README now publishes benchmark numbers from a reproducible repo (`mem0ai/memory-benchmarks`).
- **Graphiti**: the only option here that tracks when a fact became true and when it was superseded, and keeps every fact tied to its source episode. Retrieval does not need an LLM on the default path, which keeps reads fast and cheap.
- **Letta**: the agent manages its own memory with tools, so memory is visible and editable. Core blocks are always in context, which suits persona and preference state. Its own LoCoMo result (74.0%) uses plain files, so it also works as a baseline (see Numbers).
- **Hindsight**: three-verb API (retain, recall, reflect), 25+ LLM providers including Ollama and llama.cpp, and an embedded mode (`pip install hindsight-all`). MIT.
- **MCP reference server and basic-memory**: no LLM dependency on the server, auditable files or JSON, and they drop into any MCP client.
- **Claude and ChatGPT memory**: zero setup for end users, with user controls for what is saved.

## Limits and failure modes

- **Extraction loses information.** Any framework that stores LLM-extracted facts can drop details at write time. Mem0's own pitch (README) is that memories are "ADD-only", which avoids overwrites but makes contradictions accumulate unless retrieval handles them.
- **Graph frameworks need a strong model.** The Graphiti README warns that smaller models can produce bad output schemas and failed ingestion. Local 7B to 8B models are a known weak point (UNVERIFIED for Graphiti specifically; the warning is in the README).
- **Graph retrieval can be incomplete.** A 2026 independent testbed (arXiv 2601.07978, KTH) measured mem0, RAG and full context at 77 to 81% on LoCoMo, and Graphiti and cognee at 55 to 56%. It attributes the gap to retrieval incompleteness, not reasoning failure. This is one group's measurement, not a vendor claim.
- **Agent-driven memory depends on the agent.** Letta and the MCP server only save what the model chooses to save. A weak model under-writes.
- **Version drift.** mem0's README says OSS users should expect "directionally similar" results to the managed numbers. Letta's docs deprecate the Python client, though `letta-client` is still published.
- **Benchmark inflation.** See Numbers. Several headline scores fell apart on inspection.

## Exact use cases

**Personal assistant (one user, long-lived preferences).**
- Pick: **mem0 OSS** for the quickest path, or **Hindsight** if you want reflection and a local-first embedded mode.
- Avoid: a graph framework unless you need "what was true last March" queries. The overhead is not worth it for preferences.

**Customer-support bot (many users, facts change, audit matters).**
- Pick: **Graphiti** (or Zep if you do not want to run the graph DB). Its validity windows answer "what did we tell this customer and when" and keep the source episode for each fact.
- Avoid: a bot that only needs per-customer profile fields. A keyed profile store does that without an LLM on every write.

**Coding agent (repo knowledge, decisions, session continuity).**
- Pick: **plain files** (CLAUDE.md, Claude Code auto memory, or basic-memory over MCP), with grep. Letta's filesystem result (74.0% LoCoMo with gpt-4o-mini) suggests this is competitive for retrieval-style tasks.
- Avoid: a vector or graph memory service for repo facts. Git history and files are a better audit trail.

**Multi-agent team (shared state between agents with different roles).**
- Pick: **Graphiti** for shared, time-stamped facts with provenance, or **LangGraph Store** if you already run LangGraph and want namespaces per agent.
- Avoid: letting each agent keep its own private Letta blocks with no shared store. They will drift.

**Fully local / offline.**
- Pick: **Hindsight embedded with `ollama` or `llamacpp`**, or **mem0 OSS with Ollama and Qdrant** (cookbook below). **basic-memory** or the **MCP reference server** if you want no LLM on the memory side at all.
- Avoid: Graphiti unless your local model reliably returns structured output. Test it first.

## Setup walkthrough

These are the commands from each project's own docs or README. Items marked UNVERIFIED are not confirmed in the page text I read.

**mem0 OSS, fully local (Ollama LLM and embedder, Qdrant store).** From the mem0 Ollama cookbook (docs.mem0.ai/cookbooks/companions/local-companion-ollama):

```bash
pip install mem0ai
docker run -d -p 6333:6333 qdrant/qdrant
ollama pull llama3.1
ollama pull nomic-embed-text      # UNVERIFIED model name for the embedder
```

```python
from mem0 import Memory

config = {
    "vector_store": {"provider": "qdrant",
        "config": {"collection_name": "test", "host": "localhost", "port": 6333,
                   "embedding_model_dims": 768}},   # must match the embedder output size
    "llm": {"provider": "ollama",
        "config": {"model": "llama3.1:latest", "temperature": 0, "max_tokens": 2000,
                   "ollama_base_url": "http://localhost:11434"}},
    "embedder": {"provider": "ollama",             # UNVERIFIED key shape, check the docs
        "config": {"model": "nomic-embed-text", "ollama_base_url": "http://localhost:11434"}},
}
m = Memory.from_config(config)
m.add("I prefer dark mode and vim keys", user_id="alice")
print(m.search("What does Alice prefer?", filters={"user_id": "alice"}, top_k=3))
```

The embedding dimension must match the model. The cookbook uses 768. Mem0's README recommends a stronger embedder than the default for hybrid search.

**Graphiti quickstart (FalkorDB, OpenAI).** From `examples/quickstart/README.md` in the Graphiti repo:

```bash
docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest
pip install graphiti-core          # the README mentions a FalkorDB extra; exact extra name UNVERIFIED
export OPENAI_API_KEY=your_key
python quickstart_falkordb.py
```

Neo4j and Neptune variants use `quickstart_neo4j.py` and `quickstart_neptune.py`. Graphiti's default LLM and embedder are OpenAI. Local models need a provider change in code, which I did not verify.

**Hindsight quickstart (server in Docker, Python client).** From the Hindsight README:

```bash
export OPENAI_API_KEY=sk-xxx
docker run -it --pull always --name hindsight --restart unless-stopped \
  -p 8888:8888 -p 9999:9999 \
  -e HINDSIGHT_API_LLM_API_KEY=$OPENAI_API_KEY \
  -v hindsight-data:/home/hindsight/.pg0 \
  ghcr.io/vectorize-io/hindsight:latest
pip install hindsight-client -U
```

```python
from hindsight_client import Hindsight
client = Hindsight(base_url="http://localhost:8888")
client.retain(bank_id="my-bank", content="Alice works at Google as a software engineer")
client.recall(bank_id="my-bank", query="What does Alice do?")
client.reflect(bank_id="my-bank", query="Tell me about Alice")
```

Local LLM: the README names `HINDSIGHT_API_LLM_PROVIDER` with values `ollama`, `lmstudio` and `llamacpp`. The model variable name is UNVERIFIED. Embedded, no server: `pip install hindsight-all`, then `HindsightServer(llm_provider="openai", llm_model="gpt-5-mini", llm_api_key=...)` as a context manager.

**Letta quickstart.** From the letta-ai/letta README and the Letta docs:

```bash
npm install -g @letta-ai/letta-code
letta            # interactive terminal UI
letta server     # local App Server for self-hosted agents
```

For code, the docs point to the TypeScript SDK (`@letta-ai/letta-client`, `new Letta({ apiKey })`) and the Agent SDK. The Python `letta-client` page says it is deprecated, so do not start a new project on it.

**MCP reference memory server (for comparison).**

```bash
npx -y @modelcontextprotocol/server-memory
```

Point an MCP client at it. The memory file location is set through an environment variable (UNVERIFIED name, read the package README).

## Numbers

**Vendor-reported (not independently reproduced):**
- mem0, April 2026 algorithm, managed platform, from mem0 README: LoCoMo 92.5 (old 71.4), LongMemEval 94.4 (old 67.8), BEAM 1M 64.1, BEAM 10M 48.6. The README says these use managed-platform optimizations not in the OSS SDK.
- Hindsight (arXiv 2512.12818, Latimer et al.): open 20B backbone lifts LongMemEval and LoCoMo from 39% to 83.6% over full context with the same backbone; scaled backbone reaches 91.4% on LongMemEval and 89.61% on LoCoMo, against 75.78% for the strongest prior open system. The README says Virginia Tech and The Washington Post reproduced the Hindsight numbers, and that other scores are vendor-reported.
- supermemory: 95% overall on LongMemEval-S with a GPT-4o setup (vendor blog, supermemory.ai/blog/supermemory-vs-mem0, secondary snippet).
- MemOS: a third-party field guide reports self-run July 2026 scores of LoCoMo 88.83 and LongMemEval 89.20 (theagentfieldguide.com, UNVERIFIED against MemOS's own record).
- Zep, DMR (Deep Memory Retrieval): 94.8% vs MemGPT 93.4% (arXiv 2501.13956 abstract). Zep reports LongMemEval gains, but the abstract gives no number.

**Disputed:**
- **Zep vs mem0 on LoCoMo.** Zep's paper-era claim was 84% on LoCoMo. A mem0 CTO reply on Zep's own issue tracker (github.com/getzep/zep-papers/issues/5, titled "Revisiting Zep's 84% LoCoMo Claim: Corrected Evaluation & 58.44% Accuracy") argues the corrected figure is 58.44%. I could not read the issue body (GitHub returned navigation chrome only), so this rests on the title and secondary summaries. Zep's counter-evaluation, as cited by arXiv 2601.07978, reports Graphiti at 75.14%. The dispute is unresolved. Each side's evaluation harness differs.
- **Mem0 on MemGPT/LoCoMo (2025).** Letta says mem0's MemGPT numbers could not be reproduced, and that mem0 did not answer its questions (letta.com/blog/benchmarking-ai-agent-memory, a vendor claim about a competitor).
- **Filesystem vs memory products.** Letta's Aug 2025 post: Letta Filesystem with gpt-4o-mini and grep, search_files, open and close tools scores 74.0% on LoCoMo. Letta says this challenges the need for specialised memory tools. A later independent write-up (medium.com/@mrsandelin, Mar 2026) and a Towards AI post (Oct 2026) reuse the figure and cite it as a baseline. Neither reproduces it. Note that Letta is itself a memory vendor. The result is about the agent loop as much as the store.
- **MemPalace (Apr 2026).** Claimed 100% on LongMemEval and LoCoMo. A teardown by Vectorize (the Hindsight vendor, so treat as an interested party) says the 100% came from tuning on the test questions, the held-out score was 98.4%, and the 96.6% raw score measures ChromaDB's default embedder, not the palace. An independent reproduction (GitHub issue #39 in the MemPalace repo, cited in that teardown) shows rooms reduce R@5 by 7.2 points and AAAK compression by 12.4.
- **Benchmark definitions.** LongMemEval-S has about 115k tokens per history, M about 1.5M (arXiv 2410.10813). Retrieval recall and QA accuracy are different metrics, and a high S score does not establish a high M score (Supermemory's own blog says so).
- **Independent comparison.** The arXiv 2601.07978 testbed (KTH, IEEE COMPSAC 2026) puts mem0, RAG and full context at 77 to 81% on LoCoMo, and Graphiti and cognee at 55 to 56%. Its RAG baseline matched mem0 at 8.4 times lower total cost of ownership. This is the most controlled head-to-head I found, and it disagrees with the vendor numbers for Graphiti.

## Sources

- Repos and READMEs: github.com/mem0ai/mem0, getzep/graphiti, letta-ai/letta, letta-ai/letta-code, vectorize-io/hindsight, modelcontextprotocol/servers (memory), basicmachines-co/basic-memory. Versions from the GitHub and PyPI APIs.
- Papers: arxiv.org/abs/2501.13956 (Zep), 2512.12818 (Hindsight), 2410.10813 (LongMemEval), 2601.07978 (KTH testbed), 2502.12110 (A-MEM).
- Vendor and dispute pages: mem0.ai/research; letta.com/blog/benchmarking-ai-agent-memory; github.com/getzep/zep-papers/issues/5; vectorize.io/articles/mempalace-benchmarks (interested party).
- Docs: docs.mem0.ai/cookbooks/companions/local-companion-ollama; docs.letta.com/quickstart/; docs.langchain.com/oss/python/concepts/memory; help.openai.com/en/articles/8590148; platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool.

## Could not verify

- Zep's rebuttal post ("Lies, damn lies, and statistics"): 404 in my fetch, so Zep's side rests on secondary summaries.
- The bodies of mem0 issue #3004 and zep-papers issue #5.
- Current versions and internals of LangMem, Memobase, Memary, MemOS, OpenMemory MCP and A-MEM's licence.
- Whether Graphiti or Hindsight run end to end on a local 7B to 8B model; the mem0 embedder config key and the Hindsight model variable name.
- Internals of Claude app memory and ChatGPT's "Dreaming" consolidation.

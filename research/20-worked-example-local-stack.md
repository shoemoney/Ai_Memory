# Worked example: one real local memory stack

The operator's home lab runs five memory layers at once: flat-file memory for coding agents, a shared LLM wiki, Hindsight memory for two local assistants, a pgvector knowledge store in one product, and cache or store layers around them. Every fact below is from the local wiki or the support-desk project docs, and each cites its source. Machines are described generically. Assistants are "assistant A" and "assistant B".

## 1. Flat-file memory for coding agents

- **What it is.** Each project has a memory folder of plain Markdown files, with a `MEMORY.md` index that lists one line per file. Global instructions sit in a `CLAUDE.md` file that imports smaller rule files (`wiki/AGENTS.md` describes the layers: hard rules in `CLAUDE.md`, procedures as skills, facts as wiki pages).
- **Why.** Nothing to run, no service to keep alive, and the agent loads it as plain context. Hard rules that must always apply stay in `CLAUDE.md`.
- **Lesson: the inbox backs up.** Native memory files are treated as the inbox, a source that the wiki compiles and never edits (`wiki/AGENTS.md`, "Layout"). At the time of this read, `bin/wiki-inbox --count` reported 1,177 pending of 1,424 files, while `raw/memory-manifest.tsv` records 257 compiled entries. Flat files are cheap to write and expensive to curate.

## 2. The shared LLM wiki at /data/wiki

- **What it is.** A Git-tracked Markdown knowledge base, maintained by agents under a written schema (`wiki/AGENTS.md`). `index.md` lists one line per page, `log.md` is an append-only history, and each page has frontmatter with `title`, `type`, `updated`, `volatile` and `sources`.
- **How memory gets compiled.** `bin/wiki-inbox` lists memory files that are new or changed since they were last compiled. An agent reads each file, merges it into the right page, then records it with `bin/wiki-inbox mark <file> <slug>`. A file that is out of scope is marked with `-` (`wiki/AGENTS.md`, "Ingest"). `bin/wiki-lint` checks frontmatter, broken links, pages missing from the index, and secret-shaped strings. It exits 1 on errors (`bin/wiki-lint`).
- **Rules that matter for memory.** One answer per fact, merged rather than appended. Every drifting fact carries its date. No secrets anywhere, and the lint script enforces it (`wiki/AGENTS.md`, "Hard rules" and "Resolving conflicts").
- **Lesson.** Compiling is a manual-ish, agent-driven step, not a pipeline. The 1,177-file backlog shows the cost. A schema plus a linter keeps the pages honest, but it does not keep up with volume on its own.

## 3. Hindsight memory for two local assistants

**Setup.** Both assistants use Hindsight for long-term memory, running on a small local model: `Qwen38-9B-Mem`, an uncensored 9B Qwen 3.8 build, about 5 GB, with thinking off. It is served by oMLX on an Apple Silicon Mac. Assistant A runs it on one Mac Studio. Assistant B runs it on another. Each assistant has its own Hindsight profile, bank and embedded Postgres instance (internal infrastructure notes). Assistant A's larger 27B model still serves its voice app, since the 9B model was chosen for memory work only. The 9B model passed a clean uncensored JSON fact-extraction test. The wiki does not say whether its recall sits inside the voice loop's 1.3 to 1.6 s budget.

**Measured timings** (all from internal infrastructure notes, 2026-11-19 to 2026-11-20):

| Operation | Measured |
|---|---|
| Recall, assistant A | about 2 s |
| Retain, assistant A, warm | about 25 s |
| Cold daemon start, assistant A | about 2 min |
| `memory reflect`, assistant B | 40 to 50 s, returned prose with memory IDs |
| `about` (wide high-budget recall), assistant B | 0.2 s |

Assistant B's daemon has no idle timeout (`HINDSIGHT_EMBED_DAEMON_IDLE_TIMEOUT=0`), so the cold start is paid once.

**Traps found and fixed:**

1. **Doc-id collisions.** Hindsight's default document ID is the clock second. Parallel saves in the same second overwrote each other. Fix: `remember` runs async with a unique `--doc-id` per save.
2. **Slow reflect.** `reflect` was too slow for a live assistant and returned database-report prose. Fix: `about` is a wide recall instead. The wiki does not record the fix for assistant A, which still calls recall before answering and retain after.
3. **A proxy dropped system messages.** Assistant B's proxy removed every system message, so the memory instructions in its agent file never reached the model. Fix: the rules moved to a separate proxy note. The wiki says this was live-tested: facts were saved unprompted, recalled in a fresh session, and the persona held.
4. **Memory guard restarts.** On the Mac that runs oMLX, a memory guard restarts the server at a resident-memory threshold, and the restart looks like a crash to clients (internal infrastructure notes). Unload models between tests, or the guard fires.

**Persona-cache note.** oMLX reuses prefixes across turns. A cold prefix took 0.776 s to first token and a repeat took 0.165 to 0.232 s, with cached tokens reused on the next turn. The voice app keeps one byte-identical system message first to make this work (internal infrastructure notes).

## 4. The support-desk project knowledge store (PostgreSQL 17 + pgvector)

**What it is.** A product's retrieval layer over a corpus of six book EPUBs and a blog export. The production box runs PostgreSQL 17.11 with pgvector 0.8.6 on loopback, with `jit = off` set host-locally. That setting cut an inbox query from 519 to 708 ms down to 201 to 285 ms (internal infrastructure notes).

**Corpus and embeddings.** Embeddings are `openai/text-embedding-3-small` at 1,536 dimensions, called through OpenRouter. The batch cap is 9 texts per request. The project's own docs say the model string must never change, because all existing vectors came from it and a change would silently corrupt similarity search (internal project notes (codex-removal-plan)).

**Counts disagree.** An earlier summary cited about 7,730 passages from 3,252 documents. Those figures are not in the docs. The corpus verifier on 2026-09-26 reported 3,245 active documents and 7,668 passages (project notes). A later count cites 1,982 active passages for a different predicate (project notes). Use the verifier's numbers and note the date.

**Retrieval.** `KnowledgeStore.search` runs one SQL statement. It scopes by model, dimensions and kind. It takes the top 40 semantic hits by cosine distance (`<=>`). It runs a lexical branch with `ts_rank_cd`, with a fallback when fewer than 5 full matches exist. It fuses the two lists with Reciprocal Rank Fusion, using the constant 60. The final top-k defaults to 6 and is bounded to 1 to 20 (internal project notes (rag-implementation-audit), section on retrieval).

**The audit finding.** On 2026-09-26 the audit rated the missing ANN index as "Severe." The embedding columns were bare `vector` types with no HNSW or IVFFlat index in three tables, so every kNN query was an exact scan (`rag-implementation-audit.md`, lines 15 and 78). The audit file was not edited afterwards. Later docs record the fix. A partial HNSW expression index on `knowledge_chunks` and `conversation_memory` uses `vector_cosine_ops` with `m=16` and `ef_construction=64`, restricted to `dimensions=1536`. `evidence` was left unindexed on purpose. The production migration script existed but was not run as of that entry (internal project notes (support-desk-architecture), the 27 September entry).

**Other audit findings and their status:**

- **Cache lineage.** The embedding cache keyed on `sha256(text)` and validated only the model string. A silent provider change could poison it. Fix: 8,152 old entries are marked `legacy`, and new entries carry lineage (internal methodology notes, fix 4).
- **Reranker rejected.** A failing case was ranked 159th of 1,905 lexically and 1,063rd of 7,668 semantically. Widening top-k 30x still left it 240th. A reranker reorders only the pool, so the target was never in reach. The fix was a reserved structural slot for unique front-matter headings (`rag-implementation-audit.md`, reranking section).

**Lesson.** The pattern is common and easy to miss. Exact scans look fine at 7,700 rows and degrade with no error. Measure the plan with `EXPLAIN` before you trust the index.

## 5. Caches and stores around the stack

- **Redis as a queue.** A Laravel product stores its queue prefix in `APP_NAME`. Changing the name silently repoints the prefix. Horizon workers keep the boot-time prefix, and jobs strand with no error. Restart workers in the same change (internal infrastructure notes).
- **Atomic counters.** Read-then-write across 50 workers recorded 2.0% of the true total. Atomic increments recorded 100%. Set expiry with `EXPIREAT` to the window end, never a refreshed `EXPIRE` (`wiki/lessons/gates-counters-and-feedback-loops.md`).
- **KeyDB and MariaDB Galera on Raspberry Pis.** Retired on purpose on 2026-11-14. A benchmark had shown the cluster losing to the product's write pattern by 282x (`wiki/lessons/fleet-galera-cluster-and-s3-dr.md`). A separate single-instance NAS MariaDB was hit by ransomware with no snapshot, so no restore was possible.
- **Exposed Redis.** Redis listened on all interfaces on one host, and an empty container published its port too. The posture note lists this as a real exposure, not a trusted-LAN non-issue (`wiki/lessons/fleet-trusted-lab-security-posture.md`).

## 6. Lessons for the guide

1. Flat files are the cheapest layer and the first to back up. Measure the inbox backlog.
2. A schema and a linter keep a shared wiki honest. Neither replaces compiling.
3. Memory daemons have cold-start and idle behaviour that matters more than the recall number. Record both.
4. Default IDs (clock second) and proxies that drop system messages break memory silently. Test with a fresh session.
5. Vector indexes are an audit item, not a default. Check the plan. Keep the embedding model string fixed.
6. Counters need atomic writes and exact expiry, not read-then-write.

## Sources

- `wiki/index.md`, `wiki/AGENTS.md`, `bin/wiki-lint`, `bin/wiki-inbox`, `raw/memory-manifest.tsv`
- internal infrastructure notes, internal infrastructure notes, `wiki/hardware/hardware-macs.md`
- internal infrastructure notes, internal infrastructure notes
- internal infrastructure notes, `wiki/lessons/gates-counters-and-feedback-loops.md`, `wiki/lessons/fleet-galera-cluster-and-s3-dr.md`, `wiki/lessons/fleet-trusted-lab-security-posture.md`
- internal project notes (rag-implementation-audit), internal architecture notes, internal methodology notes, `codex-removal-plan.md`

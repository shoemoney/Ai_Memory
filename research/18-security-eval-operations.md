# 18. Operating agent memory safely and measuring it

Research date: 2026-11-20. Items marked UNVERIFIED were not confirmed against a primary source in this pass.

## Threats

**Memory poisoning via queries alone.** MINJA (Dong et al.) injects malicious records into an agent's memory bank by interacting only through normal queries and observed outputs, with no direct write access. Its bridging-step and indication-prompt design links victim queries to attacker reasoning steps. Source: https://arxiv.org/abs/2503.03704 (v5 revised 12 Feb 2026). A follow-up (arXiv 2601.05504) reports MINJA at over 95% injection success and 70% attack success under idealized conditions, and finds that realistic deployments with pre-existing legitimate memories dramatically reduce it. Source: https://arxiv.org/abs/2601.05504

**Backdoor triggers in memory or RAG stores.** AgentPoison (NeurIPS 2024) optimizes a trigger so that poisoned memory or knowledge-base entries are retrieved for trigger queries. It reports an average attack success rate of at least 80% with at most about 1% benign-performance impact, at a low poison rate. Sources: https://arxiv.org/abs/2407.12784 and https://dl.acm.org/doi/10.5555/3737916.3742052. Implication: clean benchmark recall does not show that a store is safe.

**Persistent prompt injection into assistant memory.** Rehberger's SpAIware research (Sep 2024) showed that untrusted content could insert long-term spyware into ChatGPT's memory on the macOS app, giving continuous exfiltration across later sessions. OpenAI shipped a fix. Source: https://embracethered.com/blog/posts/2024/chatgpt-macos-app-persistent-data-exfiltration/ . Cisco's MemoryTrap case (disclosed April 2026) showed the same class in Claude Code: a payload from a cloned repo reached persistent memory, global hooks and the system-prompt layer. Anthropic remediated it. Sources: https://blogs.cisco.com/ai/identifying-and-remediating-a-persistent-memory-compromise-in-claude-code and https://genai.owasp.org/2026/05/13/memory-is-a-feature-it-is-also-an-attack-surface/

**OWASP mappings.**
- LLM08:2025 Vector and Embedding Weaknesses covers context leakage between users in shared vector databases, and poisoned knowledge sources. Its mitigations are permission-aware stores, strict logical partitioning, source validation, tagging and classification of data, and immutable retrieval logs. Source: https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/
- OWASP Top 10 for Agentic Applications (published 9 Dec 2025) has ASI06: Memory & Context Poisoning. Its co-lead's framing is that memory, hooks and config are part of the trusted operating environment. Sources: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ and https://genai.owasp.org/2026/05/13/memory-is-a-feature-it-is-also-an-attack-surface/
- A 2026 LLM Top 10 edition exists and reorders the 2025 list (per a secondary summary, UNVERIFIED on exact order): https://www.honeyhive.ai/learn/owasp-llm-top-10

**Embedding inversion.** Morris et al. show that dense text embeddings can be inverted. A multi-step correct-and-re-embed method recovers 92% of 32-token inputs exactly, for two state-of-the-art encoders. Source: https://arxiv.org/abs/2310.06816. Consequence: a vector store is not an anonymized store. Treat embeddings as personal data at the same classification as their source text, and access-control the vector index like the text.

## Privacy and deletion

**Tenant isolation.** Vector databases generally lack a native per-user access model. Isolation is usually a metadata filter applied in application code, or a namespace or collection per tenant. A filter bug is a leak. Sources: https://arxiv.org/pdf/2605.03275 (states the filter-after-retrieval pattern). Recommendation: one collection or namespace per tenant for hard isolation, plus a filter as defense in depth, plus a test that queries as user A never return user B's IDs.

**PII and secrets.** Write-side filtering is cheaper than deletion later. Do not let raw tool outputs, logs or pasted credentials reach the extraction step. Store secrets outside memory and reference them by ID.

**Deletion by store type** (engineering reasoning, UNVERIFIED against specific vendor docs in this pass):
- Files (markdown, JSON): delete the record or line and rewrite; keep no shadow copies in git history without a scrub plan.
- Vector index: deleting a row is usually a soft delete or tombstone until compaction or rebuild, so the vector may still exist on disk and in backups. pgvector's VACUUM and HNSW rebuild semantics should be checked against the pgvector README before relying on them (https://github.com/pgvector/pgvector; the fetch failed in this pass).
- Graph: deleting a node may not remove derived edges, summaries or community nodes that were built from it. Track provenance to find derived artifacts.
- Model weights: fine-tuning on user memory cannot be undone by deletion. Machine unlearning is research-grade. Keep user data out of weights unless you can retrain.
- Derived caches (embeddings of summaries, KV caches, indexes): invalidate them with the source.

**Encryption at rest.** Encrypt the store volume and the backups. For per-user erasure, use per-tenant keys (crypto-shredding): destroying the key makes the stored copies, including backups, unreadable. This is a standard pattern; no specific published study was checked here.

**Right-to-delete scope.** Regulators such as EU GDPR Art. 17 apply to derived data. Practitioner write-ups argue vector embeddings count as personal data (UNVERIFIED, secondary source: https://sota.io/blog). Get legal advice before relying on that.

## Evaluation

**Public benchmarks.**
- LoCoMo (Maharana et al., 2024): ten very long conversations with question answering, event summarization and dialogue tasks. Sources: https://arxiv.org/abs/2402.17753 and https://github.com/snap-research/locomo
- LongMemEval (Wu et al., ICLR 2025): 500 questions over freely scalable chat histories testing information extraction, multi-session reasoning, temporal reasoning, knowledge updates and abstention. Source: https://arxiv.org/abs/2410.10813 ; code https://github.com/xiaowu0162/longmemeval
- MemoryAgentBench (Hu, Wang, McAuley, 2025, v4 revised 28 Jun 2026): incremental multi-turn evaluation of four competencies: accurate retrieval, test-time learning, long-range understanding and selective forgetting. Source: https://arxiv.org/abs/2507.05257

Known caveat: LoCoMo and LongMemEval are chat-QA style and do not cover poisoning or deletion. MemoryAgentBench is the only one of the three that tests forgetting.

**Published reference numbers.** Mem0 reports on LoCoMo a single-hop J score of 67.13 and a multi-hop J of 51.15, and says it cuts p95 latency by 91% and token cost by more than 90% against the compared full-context baseline. Source: https://arxiv.org/abs/2504.19413 (numbers in the body text at https://arxiv.org/html/2504.19413v1). Zep scores higher on open-domain J (76.60 vs Mem0's 72.93). Independent cost study (Pollertlam et al., March 2026): long-context GPT-5-mini beats the Mem0-style memory system on LongMemEval and LoCoMo accuracy, the memory system is competitive on PersonaMem v2, and at 100k context the memory system becomes cheaper after about ten turns with prompt caching. Source: https://arxiv.org/abs/2603.04814 . Vendor and independent results disagree on accuracy; run your own.

**Building a small private golden set.**
1. Take 100 to 300 real interaction fragments (scrubbed of PII) and label the facts that should be stored.
2. Write probes in three types: direct recall, update (a later fact supersedes an earlier one), and should-forget or should-abstain.
3. Add adversarial cases: a poisoned tool output, a user claim that contradicts stored facts, and cross-tenant probes.
4. Pin the embedding model, extraction prompt and judge model version in the eval manifest.
5. Run each change against the set before deploy; keep failing cases as regression tests.

**Metrics.**
- recall@k: fraction of gold memories in the top k retrieved.
- answer accuracy: judge-graded, with the judge model fixed and spot-checked by a human.
- staleness: fraction of answers that use a superseded fact.
- contradiction rate: fraction of memory-store states holding two live facts that conflict.
- write precision: fraction of written memories that are correct, durable and in scope. Track it separately from recall, because a store that writes everything scores high on recall and poorly on precision.
- poisoning success rate and cross-tenant leak rate: must be zero in tests and watched in production.

## Cost and latency model

Per turn, define: W = writes, R = reads, E = embedding calls, L = LLM calls, T = tokens.

- **Files (retrieve by path or full load):** write is one tool call and a file edit, no LLM by default; read is zero LLM calls if the file is injected whole, with T scaling with file size every turn. Cheapest to build, most expensive per read at scale.
- **Embedding store (vector RAG):** write is one embedding call per memory (E = 1 per item), read is one query embedding plus one vector search, then T for the injected top k. Latency is dominated by the network round trips to the embedding API and the DB.
- **LLM-extraction frameworks (Mem0-style):** write uses one or more LLM calls to extract and to decide add, update or delete against similar existing memories (L >= 1, with tokens proportional to the candidate memories), plus embeddings. Reads are usually embedding plus search. Writes are the expensive path; reads are cheap. Mem0's published figures reflect this profile (sources above).
- **Graph memory:** writes add entity and relation extraction (more L calls per write) and graph updates; reads add graph traversal and extra tokens for subgraph serialization. Reported gains are small on single-hop questions (Mem0 paper: the graph variant does not beat the text variant on single-hop or multi-hop).
- **Full context (no memory):** zero write cost, but per-turn read cost grows with context length, even with caching (Pollertlam et al.).

Published numbers in this pass are limited to Mem0's relative latency and token savings and the Pollertlam break-even. Per-call token counts for each family were not verified and should be measured on your own traces.

## Operations

- **Backups:** back up the source-of-truth records (text, metadata, provenance, key IDs), not only the vector index. Vectors can be rebuilt from text with the pinned model. Test a restore into a clean instance once a month.
- **Re-embedding on model change:** store the embedding model ID and dimension on every vector. A model change needs a new index (shadow build): embed all source texts with the new model, run the eval set on both, cut over by alias or collection swap, and keep the old index until the eval passes. Never mix vectors from two models in one index.
- **Schema versioning:** version the memory record format (for example `schema_version`, `embed_model`, `extractor_prompt_hash`). Migrations are scripts with dry-run output and a rollback.
- **Growth and forgetting:** set a TTL per memory type, merge duplicates, summarize old episodic records into fewer semantic facts, and expire superseded facts instead of keeping both. Log each compaction so deletions are auditable.
- **Observability:** log every read and write with tenant ID, memory ID, source, retrieval score, the injected text hash and the agent step that used it. OWASP LLM08 recommends immutable retrieval logs. Alert on writes from untrusted sources, on high write rates per tenant, and on cross-tenant ID hits.

## Checklist

1. Scope: one collection or namespace per tenant; filters are a second layer, and a cross-tenant test runs in CI.
2. Trust labels: every memory carries `source`, `trust_level` (user-stated, tool-derived, web, model-inferred), `created_at`, `tenant_id`, and `supersedes`.
3. Untrusted by default: retrieved memory is injected as quoted data, never as system instructions; memory cannot write to hooks, config, system prompts or tool allowlists.
4. Write gating: tool outputs and web content do not write directly to long-term memory; a separate step with a review rule does.
5. PII: redact or tokenize before extraction; secrets never stored.
6. Encryption: volume encryption plus per-tenant keys so deletion can be done by key destruction.
7. Deletion: a delete request removes the source record, the vectors, graph nodes and derived summaries, and schedules backup expiry; test it end to end.
8. Embeddings are personal data: same access control as the text.
9. Eval: golden set with recall, accuracy, staleness, contradiction, write precision, poisoning and leak metrics; run on every change.
10. Model change: shadow index, eval on both, alias cut-over, keep the old index until passing.
11. Backups: source records first; monthly restore test.
12. Growth: TTLs, dedupe, supersession, logged compaction.
13. Observability: immutable read and write logs with tenant and source IDs; alerts on untrusted writes and cross-tenant hits.
14. Review: an adversarial test pass (MINJA-style query injection, AgentPoison-style trigger) before launch and after each prompt or extractor change.

## Sources

- MINJA, arXiv 2503.03704: https://arxiv.org/abs/2503.03704
- Memory Poisoning Attack and Defense, arXiv 2601.05504: https://arxiv.org/abs/2601.05504
- AgentPoison, arXiv 2407.12784: https://arxiv.org/abs/2407.12784 ; ACM: https://dl.acm.org/doi/10.5555/3737916.3742052
- SpAIware (Rehberger): https://embracethered.com/blog/posts/2024/chatgpt-macos-app-persistent-data-exfiltration/
- Cisco MemoryTrap: https://blogs.cisco.com/ai/identifying-and-remediating-a-persistent-memory-compromise-in-claude-code
- OWASP LLM08:2025: https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/
- OWASP Agentic Top 10 (ASI06): https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ ; https://genai.owasp.org/2026/05/13/memory-is-a-feature-it-is-also-an-attack-surface/
- Text Embeddings Reveal (Almost) As Much As Text, arXiv 2310.06816: https://arxiv.org/abs/2310.06816
- Vector DB tenant isolation, arXiv 2605.03275: https://arxiv.org/pdf/2605.03275
- LoCoMo, arXiv 2402.17753: https://arxiv.org/abs/2402.17753 ; https://github.com/snap-research/locomo
- LongMemEval, arXiv 2410.10813: https://arxiv.org/abs/2410.10813
- MemoryAgentBench, arXiv 2507.05257: https://arxiv.org/abs/2507.05257
- Mem0, arXiv 2504.19413: https://arxiv.org/abs/2504.19413
- Beyond the Context Window (cost analysis), arXiv 2603.04814: https://arxiv.org/abs/2603.04814
- pgvector: https://github.com/pgvector/pgvector (fetch failed; not read)

**Not verified in this pass:** the exact per-call token and latency counts for each architecture family beyond Mem0's relative figures; vendor deletion semantics (HNSW tombstones, backup expiry) for pgvector, Qdrant, Milvus, Pinecone; GDPR applicability to embeddings (secondary source only); the OWASP 2026 LLM Top 10 ordering; the MINJA numbers were taken from a secondary paper's restatement; the Claude Code fix version number.

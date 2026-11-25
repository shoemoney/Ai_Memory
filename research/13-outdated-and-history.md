# Agent memory: history, and the approaches that were superseded

Research state as of 2026-11-20. Every fact carries its source. Anything not checked against a fetched primary page is marked **UNVERIFIED**.

Verification note: the SearXNG search engines were degraded during this run (brave and duckduckgo rate-limited, startpage and google CSE intermittently failing). Most sources below were therefore read directly. OpenAI pages, the Nature DNC page and the LangChain reference body returned 403 or navigation only; those claims rest on search snippets or secondary blogs and are flagged.

---

## Timeline

| Date | Event | Source |
|---|---|---|
| 2014-10 | Memory Networks (Weston, Chopra, Bordes): learned read/write long-term memory for QA | https://arxiv.org/abs/1410.3916 |
| 2014-10 | Neural Turing Machines (Graves et al.): differentiable read/write to external memory | https://arxiv.org/abs/1410.5401 |
| 2016-10 | Differentiable Neural Computer (DeepMind), Nature | https://www.nature.com/articles/nature20101 (date from search snippet; body not readable) |
| 2019-11 | kNN-LM: interpolate an LM with a nearest-neighbour datastore | https://arxiv.org/abs/1911.00172 |
| 2020-05 | RAG (Lewis et al.): parametric seq2seq + dense Wikipedia index | https://arxiv.org/abs/2005.11401 |
| 2021-12 | RETRO: retrieval from a 2T-token database during pretraining | https://arxiv.org/abs/2112.04426 |
| 2022-12 | text-embedding-ada-002 becomes the default embedding for most "long-term memory" recipes | **UNVERIFIED** date from memory; not fetched |
| 2023-03 | ChatGPT retrieval plugin (open-source, vector-DB backed) | https://github.com/openai/chatgpt-retrieval-plugin |
| 2023-04 | Generative Agents: memory stream, recency/importance/relevance, reflection | https://arxiv.org/abs/2304.03442 (v1 7 Apr 2023) |
| 2023-03 to 2023-06 | AutoGPT and BabyAGI popularise task lists plus vector-store "memory" | repos fetched but only nav chrome; dates **UNVERIFIED** |
| 2023-07 | "Lost in the Middle": accuracy drops for facts placed mid-context | https://arxiv.org/abs/2307.03172 |
| 2023-10 | MemGPT: virtual context paging between tiers | https://arxiv.org/abs/2310.08560 |
| 2024-01 | text-embedding-3-small/large replace ada-002 | https://openai.com/index/new-embedding-models-and-api-updates/ (snippet-verified; page 403) |
| 2025-04 | Mem0: extract, consolidate and retrieve salient facts | https://arxiv.org/abs/2504.19413 |
| 2025-09 | Anthropic publishes "context engineering" as the successor to prompt engineering | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| 2025-2026 | LangChain memory classes moved to `langchain-classic`; agents use checkpointers and a Store | https://docs.langchain.com/oss/python/migrate/langchain-v1 (via secondary quote) |
| 2026-11 | Letta's docs now show Agent SDK as current and the MemGPT-era API as "V1 SDK (legacy)" | https://docs.letta.com/concepts/memgpt |

---

## Each approach

### 1. Pre-LLM roots: memory networks, NTM/DNC, kNN-LM, RETRO

- **What:** learned external memory that a network reads and writes. Memory Networks used an explicit long-term store with inference components. NTMs and DNCs made the read/write addressing differentiable so gradient descent could train it end to end. kNN-LM kept a datastore of (context, next-token) pairs and interpolated its nearest-neighbour distribution with the LM. RETRO conditioned the model on chunks retrieved from a large database.
- **Why used:** to give a network more capacity than its weights or hidden state could hold, and to make knowledge updatable without retraining.
- **Why superseded:** these were trained, not run. A DNC needs training on the task, and its memory is tied to that model. They never became a practical store for a user's own data. Retrieval moved into the prompt, where any frozen model can use it.
- **Still valid when:** you are doing research on learned memory, or you need a memory that is differentiable inside the model. kNN-LM and RETRO remain the reference for retrieval at pretraining time.

### 2. RNN/LSTM hidden state as memory

- **What:** the recurrent state carried across tokens or turns was the only memory.
- **Why used:** it was the default sequence model before transformers.
- **Why superseded:** the state is a fixed-size vector, so long histories are compressed lossily. Transformers attend over the raw tokens, which is why they replaced RNNs for dialogue. The LSTM citation (Hochreiter and Schmidhuber, 1997) is **UNVERIFIED** here; it was not fetched.
- **Still valid when:** constant memory per step matters, for example on-device streaming or very long sequences where attention cost is the constraint.

### 3. Chatbot-era buffers and LangChain memory classes

- **What:** `ConversationBufferMemory` kept every message. `ConversationBufferWindowMemory` and `ConversationTokenBufferMemory` kept the last N messages or tokens. `ConversationSummaryMemory` and `ConversationSummaryBufferMemory` kept a rolling summary. `VectorStoreRetrieverMemory` and `ConversationEntityMemory` recalled snippets or entity facts.
- **Why used:** they were the simplest way to give a chain a conversation history.
- **Why superseded:** LangChain's reference marks these as deprecated and due for removal in 2.0. A secondary write-up, which quotes the reference, gives the deprecation date as LangChain 0.3.1. Another blog gives 5 May 2026 for `langchain-core` 1.3.3. **These dates conflict, and I could not read the reference body to settle it.** The replacement is listed in the v1 migration guide (https://docs.langchain.com/oss/python/migrate/langchain-v1):
  - buffer → checkpointer on `create_agent`, keyed by `thread_id`
  - window or token buffer → checkpointer plus trimming middleware
  - summary → checkpointer plus `SummarizationMiddleware`
  - vector or entity memory → a Store passed to `create_agent`, or an external memory service
  
  Source for the table: https://supermemory.ai/blog/how-to-add-conversational-memory-to-llms-using-langchain/ (secondary; it quotes the reference).
- **Still valid when:** you are maintaining a pre-1.0 chain, or a short single-session bot where a plain list of messages is enough.

### 4. Naive RAG: fixed-size chunks, one top-k cosine search, no rerank

- **What:** split documents into fixed-size chunks, embed them, and return the top-k by cosine similarity into the prompt.
- **Why used:** it is the RAG paper's pattern with off-the-shelf parts. The 2020 RAG paper combined a generator with a dense retriever and a Wikipedia index (https://arxiv.org/abs/2005.11401).
- **Why superseded:** the RAG paper itself lists the open problems of provenance and updating knowledge. The fixed chunks cut through meaning, and a single similarity pass misses exact names and keywords. The ChatGPT retrieval plugin's own README says embeddings "may not always be effective at capturing exact keyword matches" and recommends hybrid search (https://github.com/openai/chatgpt-retrieval-plugin, Limitations section).
- **Still valid when:** the corpus is small, the questions are paraphrases of the text, and a quick prototype is the goal. Add hybrid search and a reranker before calling it production.

### 5. Early Pinecone plus ada-002 "long-term memory" recipes

- **What:** embed each message or fact with `text-embedding-ada-002`, store it in a vector index, and retrieve by similarity.
- **Why used:** ada-002 was cheap and good enough, and the recipe was a few lines.
- **Why superseded:** OpenAI announced `text-embedding-3-small` and `-large` on 25 January 2024 as successors to the ada line (https://openai.com/index/new-embedding-models-and-api-updates/, snippet-verified). The bigger problem is that similarity alone does not decide what to remember, what to update, or what to forget. Mem0's paper argues for extracting and consolidating facts instead of storing raw messages (https://arxiv.org/abs/2504.19413).
- **Still valid when:** you need a semantic search over documents, not a memory of a user. Pick the current embedding model for new work.

### 6. AutoGPT and BabyAGI memory (2023)

- **What:** an autonomous loop with a task list, and a vector store as "long-term memory" that the agent queries each cycle.
- **Why used:** it was the first viral demonstration of agents that run for many steps.
- **Why superseded:** the loops drifted and repeated work, and the vector store held everything with no consolidation. Later frameworks moved to explicit state (LangGraph checkpoints) and to curated memory. Repo dates and star counts were not verifiable in this run (**UNVERIFIED**).
- **Still valid when:** you want a quick autonomous-task toy to study the failure modes.

### 7. Generative Agents memory stream (Park et al., 2023)

- **What:** every observation goes into a natural-language stream. Retrieval scores each memory by recency, importance and relevance. Periodic reflections synthesise higher-level memories from the stream. The paper evaluates a 25-agent sandbox (https://arxiv.org/abs/2304.03442).
- **Why used:** it was the best published account of believable long-run agent memory, and the scoring formula became a template.
- **Why superseded:** the importance score is itself a model call on every observation, which is expensive at scale. Reflection piles summaries on summaries, and the paper's own ablations show the components matter in combination. Newer systems use explicit extraction and update operations instead of a stream that is re-scored on every read (Mem0, 2025).
- **Still valid when:** you are simulating characters or need the recency-plus-importance-plus-relevance idea as a baseline. It is still the clearest statement of the design problem.

### 8. MemGPT (2023): virtual context paging, now Letta

- **What:** treat the context window as RAM and external storage as disk. The model pages data between tiers with explicit function calls, and interrupts manage control flow between the agent and the user (https://arxiv.org/abs/2310.08560).
- **Why used:** it was the first clear design where the model itself decides what to keep in its working context.
- **Why superseded:** the paper's framing was a workaround for 4k to 16k windows. The Letta docs now present the Agent SDK as the current product, and the MemGPT-era API appears under "V1 SDK (legacy)" (https://docs.letta.com/concepts/memgpt). The idea lives on in memory blocks and archival memory, but the paging is no longer the centre of the design.
- **Still valid when:** the agent must manage its own memory explicitly and you want the memory writes visible as tool calls.

### 9. Fine-tuning on user data as memory

- **What:** train or continue-train the model on a user's history so the knowledge sits in the weights.
- **Why used:** it looked like the only route to durable personal knowledge.
- **Why superseded:** RAG's own authors list "updating their world knowledge" as an open problem (https://arxiv.org/abs/2005.11401). Weights cannot be deleted for one user, cannot show provenance, and go stale. Retrieval and explicit stores beat them on those three counts.
- **Still valid when:** you need a style, a behaviour or a domain skill, not a list of facts. Facts belong in a store.

### 10. Giant context window as the memory

- **What:** put the whole history or corpus into the prompt.
- **Why used:** it is zero engineering, and long windows became common.
- **Why superseded:** "Lost in the Middle" found that accuracy degrades when relevant information sits in the middle of a long context, even for explicitly long-context models (https://arxiv.org/abs/2307.03172, TACL 2023). Cost and latency scale with the window. Anthropic's context-engineering post frames the task as curating the smallest high-signal set of tokens, not filling the window (https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).
- **Still valid when:** the whole artefact fits comfortably and is read once, for example a single contract or a repo snapshot under a few hundred thousand tokens. Test position sensitivity before trusting it.

### 11. Summary-of-summaries

- **What:** each turn or day is summarised, and summaries are summarised again.
- **Why used:** it bounds size with no retrieval index.
- **Why superseded:** every compression step drops detail, and the drops compound. Names, numbers and dates go first. This is the failure the summary memory classes above exhibit in long sessions.
- **Still valid when:** the goal is a rough sense of direction over a long session, and the raw log is kept elsewhere so details can be recovered.

### 12. ChatGPT plugins and retrieval

- **What:** the open-source retrieval plugin stored chunks in a chosen vector database and served them to ChatGPT through an API (https://github.com/openai/chatgpt-retrieval-plugin).
- **Why used:** it was the first standard way for a hosted model to search a user's documents.
- **Why superseded:** the README's own limitations list keyword weakness, no sensitive-data filtering and scale variance. Native retrieval inside the platform and MCP-style tool access replaced the plugin pattern. A search snippet reports that OpenAI plans to retire custom GPTs in favour of plugins, with a date of 11 December 2026 (edtechinnovationhub, 1 Oct 2026). **UNVERIFIED:** the OpenAI Help Center article returned 403, and I did not confirm this against a primary source.
- **Still valid when:** you are maintaining an existing plugin, or you need a self-hosted retrieval API with a clear contract.

---

## Lessons that carried forward

1. **Storage is cheap; selection is the problem.** Every replaced approach stored too much and selected badly (buffers, stream scoring, top-k over fixed chunks). Current designs spend effort on extraction, update and deletion (Mem0; Anthropic context engineering).
2. **Position matters.** A fact is not "in context" just because it fits (Lost in the Middle).
3. **Keep the raw log, compress the view.** Summaries decay. Keep the source and derive views from it.
4. **Retrieval beats weights for facts.** RAG's authors flagged provenance and updates as open in 2020, and weights still fail both (RAG paper).
5. **Explicit state beats hidden state.** LangChain moved from memory objects to checkpointers and stores; MemGPT moved from paging to memory blocks. Named, inspectable state is easier to test.
6. **Hybrid retrieval.** Pure cosine search misses exact terms (ChatGPT retrieval plugin README).

## Still the right simple answer

- Short, single-session chat: a message list, bounded by a window or token budget.
- Small corpus, paraphrased questions: one embedding index, chunked by structure rather than fixed size, with a reranker before a launch.
- Long-running agents: explicit state with a checkpointer, plus a store for facts you choose to keep.
- Style or skill: fine-tuning. Facts: a store.

---

## Sources

Primary (fetched and read):
- https://arxiv.org/abs/1410.3916 Memory Networks
- https://arxiv.org/abs/1410.5401 Neural Turing Machines
- https://arxiv.org/abs/1911.00172 kNN-LM
- https://arxiv.org/abs/2005.11401 RAG
- https://arxiv.org/abs/2112.04426 RETRO
- https://arxiv.org/abs/2304.03442 Generative Agents
- https://arxiv.org/abs/2307.03172 Lost in the Middle
- https://arxiv.org/abs/2310.08560 MemGPT
- https://arxiv.org/abs/2504.19413 Mem0
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents (published 29 Sep 2025)
- https://docs.letta.com/concepts/memgpt (Letta docs navigation; legacy SDK labelling)
- https://github.com/openai/chatgpt-retrieval-plugin (Limitations section)
- https://docs.langchain.com/oss/python/migrate/langchain-v1 (cited via secondary source; the migration page was not read directly for the memory section)

Partially verified (snippet or secondary only):
- https://www.nature.com/articles/nature20101 DNC (title and date from search snippet; body unreadable)
- https://openai.com/index/new-embedding-models-and-api-updates/ (25 Jan 2024; snippet only, page 403)
- https://reference.langchain.com/python/langchain-classic/memory/buffer/ConversationBufferMemory (body not readable; deprecation dates conflict across sources)
- https://supermemory.ai/blog/how-to-add-conversational-memory-to-llms-using-langchain/ (secondary table)
- https://www.edtechinnovationhub.com/news/openai-to-retire-custom-gpts-in-december-as-creators-move-to-plugins (secondary, unverified)

Not verified in this run:
- LSTM (Hochreiter and Schmidhuber, 1997)
- text-embedding-ada-002 launch date (Dec 2022)
- AutoGPT and BabyAGI first-release and popularity dates
- Pinecone "long-term memory" recipe specifics
- Plugin deprecation date and the custom-GPT retirement claim (primary OpenAI pages blocked)
- Conflicting LangChain deprecation version: 0.3.1 (reference, via secondary) versus langchain-core 1.3.3 on 5 May 2026 (maximem.ai blog)

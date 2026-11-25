# 15. Retrieval techniques on top of any memory store

Research date: 2026-11-20. Everything marked UNVERIFIED was not confirmed from a primary source in this pass.

## How it works

A memory store only holds rows. Retrieval is the layer that turns a query into a short, ranked list the model can read. The usual stack is:

1. **Candidate generation**: keyword (BM25/FTS), dense vectors, or both, each returning a top-N list (Anthropic's post uses top-150 for the reranker input).
2. **Fusion**: merge the lists with Reciprocal Rank Fusion (RRF), which needs no score calibration.
3. **Reranking**: a cross-encoder rescores the top-N pairs (query, chunk) and keeps top-K (Anthropic used top-20 out).
4. **Filtering and diversity**: metadata/time filters before or after, MMR to avoid near-duplicates.
5. **Evaluation**: measure recall@k and MRR on a golden set, not vibes.

The failure that dominates memory systems is that the correct item never reaches step 1. Rerankers cannot recover it.

## Techniques table

| Technique | What it does | Key number or fact | Source |
|---|---|---|---|
| BM25 | Lexical scoring, k1=1.2, b=0.75 in SQLite FTS5 | FTS5 hard-codes k1=1.2, b=0.75; bm25() is negated so `ORDER BY bm25(t)` is best-first | https://sqlite.org/fts5.html |
| Postgres tsvector | Lexeme index, GIN for search | GIN index stores lexemes; `ts_rank`/`ts_rank_cd` for scoring | https://www.postgresql.org/docs/current/textsearch-indexes.html |
| Tantivy | Rust full-text search library (Lucene-style) | Repo exists; benchmark numbers UNVERIFIED | https://github.com/quickwit-oss/tantivy |
| Dense retrieval | Embedding cosine/dot | Anthropic's baseline: 5.7% top-20 failure with embeddings alone | https://www.anthropic.com/research/contextual-retrieval |
| RRF | Sum of 1/(k+rank) over lists | k=60 "fixed during a pilot investigation"; beat Condorcet and best single system by 4-5% average | https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf |
| SPLADE | Learned sparse (expanded lexical) vectors | Introduced arXiv:2109.10086 (Sep 2021) | https://arxiv.org/abs/2109.10086 |
| BGE-M3 | One model: dense + sparse + multi-vector (ColBERT-style), 8192 tokens | Three retrieval modes in one checkpoint | https://huggingface.co/BAAI/bge-m3 |
| ColBERTv2 | Late interaction (MaxSim over token vectors), residual compression | Abstract: late interaction "inflates the space footprint... by an order of magnitude"; compression addresses this | https://arxiv.org/abs/2112.01488 |
| PLAID | Efficient engine for ColBERTv2 retrieval | Engine paper, May 2022 | https://arxiv.org/abs/2205.09707 |
| answerai-colbert-small-v1 | Small ColBERT-style model | Listed in HF multi-vector blog (Aug 2026); benchmark numbers UNVERIFIED | https://huggingface.co/blog/multi-vector-encoder |
| Jina ColBERT v2 | Multilingual late interaction, ~303.5M params | Param count from third-party table (mLateOn blog) | https://arxiv.org/html/2408.16672v1 , https://huggingface.co/blog/hotchpotch/mlateon-multilingual-colbert-hakari-bench |
| Qwen3-Reranker | Cross-encoder family, Apache-2.0 | 0.6B card confirmed; 4B and 8B sizes in release family; arXiv 2506.05176 | https://huggingface.co/Qwen/Qwen3-Reranker-0.6B , https://github.com/QwenLM/Qwen3-Embedding |
| bge-reranker-v2-m3 | Multilingual cross-encoder | Model exists; BEIR/MTEB scores UNVERIFIED | https://huggingface.co/BAAI/bge-reranker-base (family page) |
| Cohere Rerank 5 | Managed reranker, current generation | Cohere's own page: "Rerank 5 is here... Context Focus." Pro/Fast split UNVERIFIED (one secondary source) | https://cohere.com/models-overview |
| Jina reranker v3.5 | Listwise reranker, 0.6B, 131K input | Released 2026-07-27; **CC-BY-NC-4.0 (non-commercial)** | https://jina.ai/models/jina-reranker-v3.5/ |
| Voyage rerank, mxbai rerank | Managed/OSS rerankers | Not verified in this pass | UNVERIFIED |
| HyDE | Generate a hypothetical answer, embed it, search | Gao et al., arXiv:2212.10496 (Dec 2022) | https://arxiv.org/abs/2212.10496 |
| MMR | Pick items balancing relevance and novelty | Carbonell & Goldstein, SIGIR 1998 | https://dl.acm.org/doi/10.1145/290941.291025 |
| Generative Agents scoring | Memory score = recency + importance + relevance, each normalized | arXiv:2304.03442; default weights UNVERIFIED | https://arxiv.org/abs/2304.03442 |
| Late chunking | Embed whole document, then pool per chunk | arXiv:2409.04701 v3 (Jul 2025); numbers UNVERIFIED (abstract truncated) | https://arxiv.org/abs/2409.04701 |
| Contextual Retrieval | Prepend LLM-written context (50-100 tokens) to each chunk before embedding and BM25 | 35% / 49% / 67% fewer top-20 failures (below) | https://www.anthropic.com/research/contextual-retrieval |

## Strengths

- **BM25/FTS5**: zero infrastructure, exact-match on IDs, error codes, file names. Anthropic's example: "TS-999" is missed by embeddings and found by BM25.
- **Dense**: handles paraphrase and vocabulary mismatch. Needs an embedding model and an index refresh on write.
- **Hybrid + RRF**: no score normalization, one parameter (k), robust across scales. It is the default that rarely loses.
- **Late interaction**: finer token matching than a single vector, at a storage cost.
- **Reranker**: largest precision gain per line of code, and it works on any candidate list.
- **Agentic search (grep/find/read)**: no index to go stale; the model iterates on its own queries.

## Limits and failure modes

- **Pool miss**: a reranker cannot rank a chunk that was never retrieved. Recall@N is the ceiling for everything after it.
- **Chunk context loss**: "The company's revenue grew by 3%" retrieves nothing useful without the company name (Anthropic's example). Fix by contextualizing or late chunking.
- **Contextual Retrieval cost**: about $1.02 per million document tokens one-time with prompt caching, per Anthropic.
- **Reranker latency**: scores every candidate; Anthropic says the trade-off is candidate count vs latency.
- **RRF is rank-only**: it throws away score magnitude, so a very confident single-list hit can be diluted.
- **Stale vectors**: Boris Cherny (Claude Code creator), as relayed by a secondary article quoting an HN thread, said early Claude Code's RAG plus local vector DB had "security, privacy, staleness, and reliability" issues and agentic search "generally works better" (https://vadim.blog/claude-code-no-indexing/ quoting https://news.ycombinator.com/item?id=43164253; HN page itself not fetched).
- **Agentic search cost**: each grep/read is a tool turn and tokens. Viable for a repo of code; slower for a 10k-document corpus.
- **Licenses**: Jina reranker v3.5 is non-commercial. Check before shipping.
- **Memory-specific**: duplicates, contradictions and stale facts are not retrieval problems; retrieval just surfaces them. They need write-time handling (dedup, supersede, provenance).

## Exact use cases

**Small personal corpus (under about 10k notes, mixed prose and IDs)**
- Pick: FTS5 BM25 + small dense model (BGE-M3 or Qwen3-Embedding-0.6B) + RRF. Rerank only if precision matters.
- Avoid: a vector DB server. A single SQLite file does both.

**Code**
- Pick: agentic search (ripgrep, glob, read), which is what Claude Code and similar tools do. Add FTS5 over symbols and paths only if the repo is very large.
- Avoid: pure dense retrieval over code chunks (identifiers are exact-match).

**Chat history**
- Pick: FTS5 for exact recall ("what did I say about X"), plus a time filter, plus dense for paraphrase. Score with recency weighting. Add contextualized chunks (one turn with the previous turn).
- Avoid: fixed-size chunking across turn boundaries.

**Long documents**
- Pick: structure-aware chunking (headings), contextual chunks or late chunking with a long-context embedder, hybrid + RRF, reranker top-150 to top-20.
- Avoid: fixed 512-token chunks with no context; if the whole corpus fits under about 200K tokens, just put it in the prompt with caching (Anthropic's own advice).

## Setup walkthrough

### 1. Hybrid BM25 + vector with RRF (SQLite FTS5 side verified here)

```bash
python3 -m pip install sentence-transformers sqlite-utils   # UNVERIFIED: not run in this pass
```

FTS5 table and BM25 query (executed in this pass, SQLite 3.46.1):

```python
import sqlite3
db = sqlite3.connect("memory.db")
db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS mem USING fts5(id UNINDEXED, body)")
# Quote phrases with hyphens or dots: unquoted TS-999 is read as column "999" and errors.
rows = db.execute(
    "SELECT id FROM mem WHERE mem MATCH ? ORDER BY bm25(mem) LIMIT 50",
    ('"TS-999"',),
).fetchall()
```

RRF (executed in this pass; output on the toy corpus ranked the doc containing both terms first):

```python
def rrf(rankings, rrf_c=60):
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_c + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

fused = rrf([bm25_ids, dense_ids])[:50]
```

Dense side (UNVERIFIED in this pass): BGE-M3 via sentence-transformers, `SentenceTransformer("BAAI/bge-m3")`, `encode(texts, normalize_embeddings=True)`, cosine = dot product.

### 2. Local reranker

From the Qwen3-Reranker-0.6B card (CrossEncoder usage shown there):

```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder("Qwen/Qwen3-Reranker-0.6B")
pairs = [(query, doc) for doc in fused_docs]
scores = reranker.predict(pairs)
top20 = [d for _, d in sorted(zip(scores, fused_docs), reverse=True)][:20]
```

Swap in `BAAI/bge-reranker-v2-m3` with the same CrossEncoder call (UNVERIFIED in this pass). Qwen3-Reranker is an LLM-style reranker; check its GPU memory on your box first.

### 3. Golden-set eval (20 questions)

Write `golden.jsonl`, one line per question: `{"q": "...", "relevant_ids": ["id1", "id7"]}`. Use real questions your memory must answer, including ID and paraphrase cases.

```python
import json
def recall_at_k(ranked, relevant, k):
    return len(set(ranked[:k]) & set(relevant)) / len(relevant)
def mrr(ranked, relevant):
    for i, d in enumerate(ranked, 1):
        if d in relevant:
            return 1.0 / i
    return 0.0
rows = [json.loads(l) for l in open("golden.jsonl")]
for name, fn in [("bm25", run_bm25), ("hybrid_rrf", run_hybrid), ("hybrid_rerank", run_rerank)]:
    rs = [fn(r["q"]) for r in rows]
    print(name,
          "R@10=%.2f" % (sum(recall_at_k(x, r["relevant_ids"], 10) for x, r in zip(rs, rows)) / len(rows)),
          "MRR=%.2f" % (sum(mrr(x, r["relevant_ids"]) for x, r in zip(rs, rows)) / len(rows)))
```

Run the three arms on the same 20 questions. Recall@N for the candidate pool tells you whether the reranker is even worth running.

## Numbers

- Anthropic Contextual Retrieval, top-20 failure rate (1 minus recall@20, average across domains, Gemini text-004 embeddings):
  - Baseline embeddings: 5.7%
  - Contextual embeddings: 3.7% (-35%)
  - Contextual embeddings + contextual BM25: 2.9% (-49%)
  - Plus reranking: 1.9% (-67%)
  - Source: https://www.anthropic.com/research/contextual-retrieval
- RRF: k=60; beats Condorcet all 7 pilot/TREC comparisons (sign-test p approx 0.008); average 4-5% over best single system (Cormack et al. 2009).
- FTS5 BM25: k1=1.2, b=0.75 hard-coded (https://sqlite.org/fts5.html).
- Contextual Retrieval one-time cost: $1.02 per million document tokens with prompt caching, per Anthropic.
- Anthropic reranker input top-150, output top-20; they found 20 beats 5 and 10 as context size.
- Jina reranker v3.5: 0.6B params, 131K input tokens (https://jina.ai/models/jina-reranker-v3.5/).
- Qwen3-Reranker-0.6B: Apache-2.0, arXiv 2506.05176 (https://huggingface.co/Qwen/Qwen3-Reranker-0.6B).

## Sources

- Anthropic, Contextual Retrieval (Sep 19 2024): https://www.anthropic.com/research/contextual-retrieval
- Cormack, Clarke, Büttcher, RRF (SIGIR 2009): https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf
- SQLite FTS5 documentation: https://sqlite.org/fts5.html
- PostgreSQL text search indexes: https://www.postgresql.org/docs/current/textsearch-indexes.html
- Qwen3-Reranker-0.6B model card: https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
- Qwen3 Embedding repo: https://github.com/QwenLM/Qwen3-Embedding
- BGE-M3 model card: https://huggingface.co/BAAI/bge-m3
- SPLADE (arXiv:2109.10086): https://arxiv.org/abs/2109.10086
- ColBERTv2 (arXiv:2112.01488): https://arxiv.org/abs/2112.01488
- PLAID (arXiv:2205.09707): https://arxiv.org/abs/2205.09707
- Multi-vector encoders blog (answerai-colbert-small, Aug 2026): https://huggingface.co/blog/multi-vector-encoder
- Jina ColBERT v2 (arXiv:2408.16672): https://arxiv.org/html/2408.16672v1
- Jina reranker v3.5: https://jina.ai/models/jina-reranker-v3.5/
- Cohere models overview (Rerank 5): https://cohere.com/models-overview
- Late chunking (arXiv:2409.04701): https://arxiv.org/abs/2409.04701
- HyDE (arXiv:2212.10496): https://arxiv.org/abs/2212.10496
- MMR, Carbonell & Goldstein 1998: https://dl.acm.org/doi/10.1145/290941.291025
- Generative Agents (arXiv:2304.03442): https://arxiv.org/abs/2304.03442
- Claude Code agentic search, secondary: https://vadim.blog/claude-code-no-indexing/ (quotes https://news.ycombinator.com/item?id=43164253)
- Tantivy: https://github.com/quickwit-oss/tantivy

## Could not verify

- Numbers for Voyage rerank, mxbai rerank, bge-reranker-v2-m3 benchmarks, answerai-colbert-small, late chunking gains, Generative Agents default weights.
- Cohere Rerank Pro/Fast variant names (one secondary source; Cohere's own page only says "Rerank 5").
- Direct HN text (only a secondary quote).
- Tantivy benchmark figures.
- The dense half of the setup walkthrough and the CrossEncoder bge-reranker call were not executed.

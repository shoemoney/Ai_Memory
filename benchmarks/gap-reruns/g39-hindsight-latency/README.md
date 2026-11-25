# G39: Hindsight decision-model latency (167 ms median)

Chapter sentence: `build/chapters/06-small-memory-models.html:159` and the table row at line 292 ("167 ms vs 1 to 7 s").

## What the published figure times

The figure comes from the vendor blog post "Introducing Hindsight Models" (2026-11-03,
https://hindsight.vectorize.io/blog/2026/11/03/hindsight-models). It says: "A decision-model request takes 167 ms at the
median (350 ms at p90) and answers every question about a fact or a memory at once; the LLM call it replaces takes 1 to 7
seconds at the median." The vendor's evaluation ran Hindsight 1.2.0 operations (retain, consolidation, reflect, knowledge
pages) against seven hosted LLMs, with `hs-decide-1-flash` (0.8B parameters, Apache 2.0, built on Qwen3.5-0.8B) answering
the small judgments. The post does not say which hardware served the decision model or how many requests the median covers.
The weights serve on vLLM (a GPU path); the vendor's Transformers server is the path for CPUs and Apple Silicon.

## What this folder measures

One decision-model request, timed on the server around the model's forward pass (`compute_s`) and around the whole HTTP
handler (`wall_s`), for the requests a task-owned Hindsight 1.2.3 container sends while it answers 199 recall queries
(LoCoMo conversation 0, CC BY-NC 4.0, fetched by script, never stored here) with `rerank: {prune: true, dedup: true}`.

Setup:

- Hindsight 1.2.3 in a new container (memory limit 4 GB, 4 CPUs, localhost-only port), its own database volume. The service
  that was already running on this machine was not touched.
- Retain extraction by a local Qwen2.5-7B-Instruct (Q4_K_M, llama.cpp) on an Apple M1 Ultra (20-core CPU, 64 GB) reached
  through an SSH tunnel; embeddings and reranker are the vendor's `hs-embed-1` (revision 5c38ec7c) and `hs-rerank-1` (revision 233902d2) on CPU.
- Decision model: `hs-decide-1-flash` (Hugging Face revision e2c78902, Apache 2.0),
  vendor Transformers server (`hindsight_decision` 0.4.0) on the Apple M1 Ultra GPU (MPS, bfloat16), reached by Hindsight
  through an SSH tunnel to localhost. `run_decider.py` adds the per-request timing.
- Six LoCoMo sessions retained (`raw/retain.jsonl`), then 199 sequential recalls (`raw/recall.jsonl`, client seconds per
  recall). Decision-model timings: `raw/decider-timing.jsonl` (246 lines; the first 4 are retain-time warm-up and are
  excluded, leaving N=242).

One command after the stack is up: `drive.py retain --sessions 6 && drive.py recall --n 199 && analyze.py` (stack start:
`start_stack.sh`, model host: `../serve.sh`).

## Results

| Subset | N | Median compute (95% bootstrap CI) | p90 | p95 | Median input tokens |
|---|---|---|---|---|---|
| All decision-model requests | 242 | 2,105 ms (2,103 to 2,108) | 2,301 ms | 2,380 ms | 5,680 |
| Requests under 1,000 input tokens (dedup questions) | 36 | 132 ms (128 to 163) | 294 ms | 367 ms | 241 |
| Requests of 1,000 tokens or more (recall ranking) | 206 | 2,109 ms (2,107 to 2,111) | 2,331 ms | 2,389 ms | 5,681 |

Server wall time differs from compute time by about 1 ms. Client-side, a whole recall (embedding, search, rerank, prune,
dedup, two or more decision requests) took a median of 2.15 s (p95 2.58 s, N=199).

Published: 167 ms median, 350 ms p90. The intervals are bootstrap intervals over requests, which are not independent
(nearly all ranking requests have the same size), so they are narrow because the workload is nearly constant, not because
the figure is precise for other workloads.

## How this differs from the source

1. Hardware and serving stack: Transformers on Apple M1 Ultra MPS, not vLLM on whatever the vendor used.
2. Workload: recall ranking (prune) and dedup. The vendor's median covers consolidation, reflect and knowledge-page
   judgments; recall pruning is an optional feature the vendor's own evaluation does not list. Ranking requests here carry
   a median of 5,680 input tokens, about 24 times the dedup requests.
3. Sequential single-client traffic, small bank (six sessions), one conversation.
4. Time inside the decision model, as the vendor says its time is "spent in model calls" from traces; network and queueing
   are excluded for compute and nearly equal for wall.
5. Decision-model requests were not made by consolidation, reflect or page refresh: consolidation did not run to completion
   in this setup (a stale job from the killed earlier container held the claim), and a reflect pass failed when the model
   host server stopped under memory pressure. No reflect traffic is in the numbers.

## Verdict

The local median for the requests Hindsight sends during recall pruning is 2,105 ms on this hardware, not 167 ms. The
132 ms median for the short dedup requests is in the same range as the published figure, which fits latency growing with
request size, but that subset is a different workload from the vendor's. This run cannot confirm or refute the 167 ms
median for the vendor's workload on the vendor's hardware.

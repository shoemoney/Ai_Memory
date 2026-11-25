# Cost and latency accounting from saved local runs

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

Run from the repository root, without models, network access or new dependencies:

```bash
python3 benchmarks/cost/analyze.py
python3 benchmarks/cost/verify.py
```

Executed with CPython 3.14.4, standard library only (the exact observed version is in an unpublished raw log; no third-party packages are used). Analysis runs on a 32-thread x86 CPU. It does not contact a Mac or use a GPU. Existing LoCoMo calls used Qwen2.5-14B-Instruct Q4_K_M on Apple M3 Ultra, 96 GB; existing LongMemEval calls used Gemma 2 9B 4-bit on Apple M1 Ultra, 64 GB. Both used CPU all-MiniLM-L6-v2 embeddings. No generation or judge is run by this analysis.

The generated [results table](results/TABLE.md) prints published claims beside local accounting, per-question input/output tokens, ingestion LLM tokens and recorded elapsed time per history. [summary.json](results/summary.json) holds per-history results, cost parameters, latency/token ratios and assignment uncertainty. [queries.jsonl](results/queries.jsonl) is the original five-system/LongMemEval per-item ledger, and [queries-four-system.jsonl](results/queries-four-system.jsonl) holds the larger matched cohort; raw prompts and responses remain in the upstream benchmark directories. [source-hashes.json](results/source-hashes.json) pins every consumed JSON artifact by SHA256. Exact claim locations and editor replacements are in [REPORT.md](REPORT.md).

## What the numbers mean

The primary four-system analysis uses every saved-answer question shared by full context, RAG, Mem0 and Graphiti in histories with finalized ingestion timers and all expected Mem0 chunk/Graphiti session checkpoints. It finds **123 matched questions per system across four histories**: c00 (34), c01 (24), c02 (32), c03 (33). This matches the upstream `four-system-matched.json` coverage without requiring accuracy or judge completion. Average full-context prompt lengths are 29,617, 23,625, 44,682 and 39,550 tokens respectively. No history matches the published 100,000-token setting.

The original five-system analysis, including Cognee, remains unchanged: 58 matched questions per system in c00/c01. Its original summary keys and `queries.jsonl` retain their previous meaning. The added `summary.json` → `four_system_locomo` and `queries-four-system.jsonl` hold the larger cohort separately, so neither Cognee coverage nor LongMemEval coverage is widened by implication.

Question-level token reductions and p95 times pool the 123 paired answer calls per lane. Cost crossovers model an equal-weight average of the four histories, not the mean of their integer crossovers; the Mem0/RAG ratio is the equal-weight mean of four per-history ratios. Each history pays ingestion once at its observed question count. A fixed stored history and stationary mean query cost are extrapolated beyond those counts, rather than measured at the crossover; history growth and incremental writes are absent.

A 95% percentile cluster bootstrap resamples four whole histories with replacement, keeping every question and paired lane together, for 10,000 replicates with seed 20261122. It recomputes pooled token reductions and p95, the mean per-history cost ratio and the crossover of mean history costs. The intervals rest on **only four independent histories** and are descriptive and unstable. They do not establish broad population precision or 123 independent cases. No interval is reported for the two-history Cognee cohort; its per-history bounds remain in the results. With fewer than four admissible histories the added analysis reports per-history ranges and explains why no interval is given.

Answer records match saved raw calls by exact prompt, exact output and successful finish. Four-system ingestion attribution excludes system examples and user EXAMPLE blocks, prioritizes CURRENT_MESSAGE and actual speaker labels, maps anonymized aliases from source histories, and intersects ownership with backend ingestion intervals. This matters because framework examples contain aliases from other histories and one rewritten alias has a different numeric prefix from its actual history. Every Mem0/Graphiti four-system call has a unique owner under this rule. The five-system attribution remains unchanged, including four anonymous Cognee calls bounded per history and counted once in its pooled total.

Earlier superseded ingestion/preflight attempts and evaluation judges are excluded. This models finalized ingestion, not complete experimental recovery effort. The proxy deduplicates identical requests, so the ledger measures distinct saved generations, not an API invoice or complete invocation trace. Truncated generations inside the selected ingestion interval are included. CPU embedding token counts were not logged and remain unavailable.

## Parameterized dollars

Default dollars per million tokens: uncached input $0.15, cached input $0.075, output $0.60, from the [official GPT-4o mini model price list](https://developers.openai.com/api/docs/models/gpt-4o-mini), checked November 22, 2026. These are illustrative list rates applied to local tokenizer counts, not actual API spend, a GPT-4o mini performance test, or total ownership cost. No provider is called. The source page currently labels the model deprecated; choose current rates for a deployment.

```bash
python3 benchmarks/cost/analyze.py --input-price 0.15 --cached-price 0.015 --output-price 0.60 --cache-fraction 1 --out benchmarks/cost/results/custom
```

For input I, output O, uncached rate U and cached rate K, cost is `(I*U + O*output_rate)/1e6`. Ingestion and memory answer calls use uncached input rates. Full context uses uncached input for Q=1 and `I*((1-f)*U+f*K)` thereafter, where f is `--cache-fraction`, default 1. This idealizes the entire stable full-history prompt as cacheable, including the small question/template overhead; memory prompts are conservatively uncached. Real cache eligibility, eviction, prefix layouts and write fees are not simulated. Recorded local cache-hit counts remain in the ledger but are not treated as paid cache billing.

The first integer Q satisfying `write + Q*memory_query < full_first + (Q-1)*full_repeat` is printed. This compares an equal-weight average history, not an average of individual crossover Q values. Storage, embedding, retrieval, network, maintenance, reranker infrastructure and idle-server costs are excluded, so the dollar model is explicitly LLM-token-only. For RAG, zero generation ingestion tokens make Q=1 in this model; this does not establish free indexing or a Q=1 total-cost crossover.

Original five-system cohort including Cognee: price sensitivity at N=58 questions per lane in two histories, keeping saved tokens fixed:

| Cached input / million | Full-input cache fraction | RAG Q | Mem0 Q | Graphiti Q | Cognee Q |
|---|---:|---:|---:|---:|---:|
| $0.075 | 1 | 1 | 49 | 60 | 132 |
| $0.075 | 0 | 1 | 25 | 30 | 16 |
| $0.015 | 1 | 1 | 306 | 478 | Never |

## Four-system results and recorded seconds

At the default prices and full cache fraction, the four-system cohort gives:

| History | Questions per lane | Mem0 crossover Q | Graphiti crossover Q | Mem0/RAG token-only total-dollar ratio |
|---|---:|---:|---:|---:|
| c00 | 34 | 47 | 71 | 11.622 |
| c01 | 24 | 52 | 46 | 13.980 |
| c02 | 32 | 49 | 46 | 20.764 |
| c03 | 33 | 50 | 44 | 17.951 |
| Equal-weight history model/mean ratio | 123 total, 4 histories | 49 | 51 | 16.079 |
| 95% history-bootstrap interval | 4 histories | 48 to 51 | 45 to 63 | 12.801 to 19.358 |

Mem0/RAG ratios range from 11.622 to 20.764 across the four histories. These count generation tokens only and cannot reproduce a total ownership-cost ratio.

For N=123 matched answer calls per lane across four histories, full-context p95 is 5.824 seconds (95% history-bootstrap interval 5.473 to 9.707), and Mem0 p95 is 11.407 seconds (6.901 to 13.509). This is a 95.85% increase at the point estimate, not a 91% end-to-end saving. Mem0 uses 97.80% fewer answer-call input plus output tokens (97.25% to 98.15%); including ingestion once per history at the observed 34/24/32/33 query counts reduces the saving to 27.19% (14.78% to 33.84%). Every interval in this paragraph resamples the same four independent histories; see `results/TABLE.md` for per-history ranges and latency-ratio uncertainty.

A separate conditional model substitutes recorded ingestion elapsed seconds and mean answer-call elapsed seconds into the same inequality. On N=123 paired questions across four histories, it gives Mem0 Q=5,698 and Graphiti Q=195,261; RAG is unavailable because indexing time is missing. The preserved five-system analysis including Cognee (N=58 questions per lane, two histories) gives Mem0 Q=7,000, Graphiti Q=15,904 and no eventual Cognee saving. These are partial-cost scenarios, not end-to-end latency crossovers or pure CPU compute. Timers include initialization, contention and recovery; answer calls have uncontrolled prefix reuse/serving load and exclude retrieval. Warm full-context calls can be faster than short memory calls. Concurrent elapsed time is not additive hardware utilization. No monetary electricity estimate or unobserved cold-cache seconds model is invented.

## LongMemEval and unreproduced items

All 300 full-standard histories overflow the native 8,192-token model window. The analysis reports available RAG/Mem0 answer tokens and seconds, but cannot compute a measured crossover against full standard context. The 212 oracle-context answers are labeled separately. Mem0 uses `infer=False`; its LLM extraction tokens are zero, not a fact-extraction replication. Its preparation timer includes retrieval and reuses dense-lane embeddings. Per-history isolated ingestion wall time and embedding token counts cannot be recovered from these logs. Graphiti and Cognee were not run on LongMemEval.

Sleep-time consolidation is absent from both runs, so the [2.5x Multi-Query GSM-Symbolic cost claim](https://arxiv.org/abs/2504.13171) is not reproduced. Hindsight's [167 ms decision-request median](https://hindsight.vectorize.io/blog/2026/11/03/hindsight-models) is not reproduced. There is no retained local Hindsight image/container; a fresh server, model downloads and task-matched decision fixtures would be a separate experiment. Running ordinary retain/recall would not reproduce decision-model latency.

## Data and versions

LoCoMo: [official dataset](https://github.com/snap-research/locomo), revision `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`, CC BY-NC 4.0. LongMemEval: [official dataset](https://github.com/xiaowu0162/LongMemEval), revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`, MIT. No datasets or models are copied here. Exact model/framework/dependency pins remain in `benchmarks/locomo/requirements-full-lock.txt`, `requirements-graph-lock.txt`, `results/full/manifest.json`, and `benchmarks/longmemeval/requirements.txt`, `results/full/manifest.json`. LoCoMo uses Mem0 2.2.1 and Graphiti 0.31.2; LongMemEval uses Mem0 0.1.118. These configurations differ from the published hosted-model experiments.

Published primary sources: [memory/full-context crossover](https://arxiv.org/html/2603.04814v1), [independent framework ownership-cost comparison](https://arxiv.org/html/2601.07978v5), [Mem0 paper](https://arxiv.org/abs/2504.19413). No claim here treats those published figures as measurements from this analysis.

Cleanup: no services, tunnels, containers, images, volumes, model downloads or scratch directory were created. Before/after disk and task-process proofs are retained in an unpublished raw log and an unpublished raw log. Only `benchmarks/cost/` is written; no commits are made.

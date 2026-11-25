# Offline cost results

## Five-system matched cohort, including Cognee

LoCoMo: 58 matched questions in two complete histories. Token means below are question-weighted. Cost scenarios average histories equally.

| System | Input/query | Output/query | Answer seconds/query | LLM ingest input/history | LLM ingest output/history | Ingest elapsed seconds/history | Cached dollar crossover Q | Recorded-seconds scenario Q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full-context | 27,137.4 | 63.0 | 4.7 | 0.0 | 0.0 | 0.0 | baseline | unavailable |
| rag | 1,531.7 | 63.5 | 7.7 | 0.0 | 0.0 | unavailable | 1 | unavailable |
| mem0 | 681.7 | 63.3 | 4.2 | 560,668.5 | 16,196.5 | 1,655.4 | 49 | 7000 |
| graphiti | 1,131.6 | 69.1 | 4.4 | 462,942.0 | 69,429.0 | 5,590.5 | 60 | 15904 |
| cognee | 11,392.8 | 57.3 | 32.0 | 105,609.0 to 107,931.0 | 32,033.0 to 32,548.0 | 2,841.0 | 132 | never |

Dollar Q excludes CPU embeddings/storage/maintenance. RAG write LLM tokens are zero; indexing time is unrecorded. Seconds Q excludes retrieval and is not an end-to-end latency result. Cognee ingestion ranges allocate ambiguous calls to neither/either history.

| Published figure | Local accounting |
|---|---|
| Mem0 cheaper after about 10 questions at 100K cached tokens | 49 questions; N=123 matched questions/system across 4 shorter histories, different prices and tokenizer |
| RAG 8.4x lower total ownership cost | Token-only ratio below; ownership cost not reproduced |
| Mem0 91% lower p95 latency, >90% token reduction | Answer-call-only p95 and token ratios below; ingestion separately counted |
| Sleep-time 2.5x lower cost/query | Not reproduced: neither reused run executes sleep-time consolidation |
| Hindsight decision request median 167 ms | Not reproduced; no retained local decision-model install |

LongMemEval: all 300 full-standard histories exceed 8,192-token native window; no measured full-standard baseline or crossover. Oracle rows use shorter supplied evidence and cannot replace it.

| Lane | Answer N | Input/query | Output/query | Answer seconds/query | Preparation seconds (shared cache, includes retrieval) |
|---|---:|---:|---:|---:|---:|
| bm25-standard | 300 | 1,972.1 | 27.9 | 4.00 | 0.041 |
| dense-standard | 300 | 2,054.6 | 31.5 | 4.44 | 15.636 |
| full-oracle | 212 | 4,850.2 | 74.4 | 10.85 | 0.000 |
| mem0-raw-standard | 300 | 2,054.6 | 31.5 | 4.23 | 0.190 |

## Four-system matched LoCoMo analysis (without Cognee)

N=123 matched questions per system across 4 histories.

| System | Answer N | Input/query | Output/query | Answer seconds/query | LLM ingest input/history | LLM ingest output/history | Ingest seconds/history | Dollar crossover Q | Recorded-seconds scenario Q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full-context | 123 | 35,032.1 | 61.2 | 5.262 | 0.0 | 0.0 | 0.000 | baseline | unavailable |
| rag | 123 | 1,478.0 | 62.6 | 6.344 | 0.0 | 0.0 | unavailable | 1 | unavailable |
| mem0 | 123 | 709.6 | 61.0 | 4.811 | 741,350.2 | 20,607.5 | 1,970.306 | 49 | 5698 |
| graphiti | 123 | 1,147.3 | 64.0 | 5.270 | 554,028.8 | 67,950.2 | 5,772.450 | 51 | 195261 |

| History | Matched questions/system | Mem0 dollar crossover Q | Graphiti dollar crossover Q | Mem0/RAG token-only dollar ratio | Mem0 answer-token reduction | Reduction including ingestion | Full-context answer p95 (s) | Mem0 answer p95 (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| c00 | 34 | 47 | 71 | 11.622 | 97.56% | 36.12% | 4.518 | 4.791 |
| c01 | 24 | 52 | 46 | 13.980 | 96.73% | 2.84% | 5.221 | 13.146 |
| c02 | 32 | 49 | 46 | 20.764 | 98.29% | 29.00% | 8.866 | 8.747 |
| c03 | 33 | 50 | 44 | 17.951 | 97.93% | 28.91% | 5.387 | 12.583 |

| Statistic | Estimate | Per-history range | 95% history-bootstrap interval |
|---|---:|---:|---:|
| mem0_over_rag_cost_ratio_mean | 16.079 | 11.622 to 20.764 | 12.801 to 19.358 |
| token_reduction | 97.80% | 96.73% to 98.29% | 97.25% to 98.15% |
| token_reduction_including_ingestion_at_observed_counts | 27.19% | 2.84% to 36.12% | 14.78% to 33.84% |
| full_p95_seconds | 5.824 | 4.518 to 8.866 | 5.473 to 9.707 |
| mem0_p95_seconds | 11.407 | 4.791 to 13.146 | 6.901 to 13.509 |
| p95_latency_reduction | -95.85% | -151.80% to 1.35% | -144.87% to 15.17% |
| mem0_macro_crossover_questions | 49.000 | 47.000 to 52.000 | 48.000 to 51.000 |
| graphiti_macro_crossover_questions | 51.000 | 44.000 to 71.000 | 45.000 to 63.000 |

Crossover estimates price an equal-weight average history, rather than averaging crossover integers. Ratios average histories equally; token reductions and p95 pool the matched answer calls. Ingestion is counted once per history at its observed question count. All intervals resample whole histories, retain paired lanes, and rest on N=4 independent histories, with 10,000 resamples and seed 20261122; four histories give unstable, descriptive intervals. No question-level independence is assumed.

This analysis uses the same token prices, idealized full-prefix caching and partial recorded-seconds model as the five-system cohort. Complete Mem0 chunk and Graphiti session checkpoints plus finalized ingestion intervals are required; RAG has no LLM writes, but its embedding tokens/indexing time remain unavailable. Retrieval, embeddings, storage and maintenance are excluded. Answer p95 is not end-to-end latency.

Per-query token/time ledgers: `queries-four-system.jsonl`; ingestion ledgers, conditional recorded-seconds crossovers, admission checks and interval metadata: `summary.json` → `four_system_locomo`.

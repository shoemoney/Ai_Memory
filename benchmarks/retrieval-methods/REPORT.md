# Retrieval claim inventory and local evaluation

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

All six required retrieval configurations were completed on SciFact (300 queries), NFCorpus (323), and LoCoMo (150), with additional contextual RRF and reranking comparisons. Four supplementary LongMemEval baselines add 150 questions: 28 complete method/dataset cells, 923 distinct queries, and 18,619 generated prefixes. This measures evidence retrieval with public labels, not answer quality.

RRF improved AP@150 over the better single retriever on both BEIR sets and reduced it on LoCoMo. Against uncontextualized dense retrieval, the full contextual pipeline had an inconclusive top-20 recall change on SciFact and NFCorpus; it improved LoCoMo retrieval within its small original conversation haystacks. These local measurements use different models, corpora, and relevance units from the published claims.

## Chapter 05: Contextual Retrieval

Chapter file: `build/chapters/05-retrieval-techniques.html`.

Printed sentences:

> 5.7% Anthropic vendor measurement: queries with no correct chunk in the top 20, using embeddings alone.

> 3.7%, 2.9%, 1.9% The same failure rate with contextual embeddings, then contextual BM25 added, then reranking added. These are 35%, 49% and 67% fewer failures.

The primary source explicitly defines its failure metric as 1 minus recall@20, whereas the chapter calls it queries with no correct chunk. Those definitions differ when several items are relevant. The published-versus-local comparison therefore uses macro 1 minus document/session recall@20; complete misses are reported separately. Paired bootstrap relative reductions compare contextual dense, contextual BM25 plus dense via RRF, and contextual RRF plus cross-encoder to the same uncontextualized dense baseline on the same queries. Contextual BM25 alone is also measured. Deduplicated document/session labels differ from the original top-20-chunk evaluation, and Qwen3.5-4B, MiniLM embeddings, and the open reranker differ from Claude, Gemini, and Cohere. These measurements test the local pipeline direction but cannot confirm or refute the published magnitude on a different benchmark.

NFCorpus has a median of 16 positive documents per query and 144 of 323 queries have more than 20 positives. Its macro recall@20 ceiling is 76.83% even under an oracle ranking, so its 1 minus recall@20 has a 23.17% floor; raw miss percentages should not be compared across corpora. Evidence: `results/data-label-audit.json`.

Printed sentence:

> 150 in, 20 out Candidates sent to the reranker and chunks passed to the model.

Local matching setup: at most 150 fused unique documents are reranked and the first 20 are scored; no reader is used. This is a configured candidate budget, not a quality result. Each first-stage leg is capped at 150 unique documents before fusion; candidate recall limits the reranker. Evidence: `run.py`, per-query `*.rankings.jsonl` and `*.rerank.jsonl`.

Suggested replacement: "This book reranks at most 150 fused documents and scores the first 20. Memory candidate pools contain 19 to 32 LoCoMo sessions or 38 to 62 LongMemEval sessions, so their candidate budget is smaller."

## Chapter 05: Reciprocal Rank Fusion

Printed sentence:

> 4 to 5% Average gain of RRF over the best single system in the RRF paper.

The primary paper describes MAP gains across its pilot and TREC experiments, not a universal gain for BM25 plus modern embeddings. The local evaluation measures RRF versus both constituent systems, plus the better single system, for nDCG@10 and AP@150. Best-baseline bootstrap ratios reselect the best of the two baselines in each paired resample. AP@150 truncates the BEIR rankings and covers the full original memory haystacks. The two-system fusion, public biomedical corpora, and conversational-memory session labels differ from the paper. Evidence: `results/summary.json`, `summarize.py`, and `results/sources.json`.

The chapter's k=60 is reproduced as an algorithm setting. Its sample RRF scores, 0.03226 for rank two in both lists and 0.01639 for rank one in one list, are arithmetic rounded from 2/62 and 1/61; they are not benchmark gains.

Suggested replacement: "This book uses RRF with k=60. A document ranked second by both retrievers scores 2/62, about 0.03226, while a first-place hit in only one retriever scores 1/61, about 0.01639."

## Chapter 05: Existing local figures and tutorial

Printed local result: BM25 191/300 (63.7%, interval 58.1 to 68.9) versus dense 165/300 (55.0%, interval 49.3 to 60.5); paired difference 8.7 points (interval 2.7 to 14.7; exact p=.006). These are reader answer accuracies, measured with a local Gemma 2 9B reader in `benchmarks/longmemeval`, not retrieval relevance metrics. This task does not rerun answer generation; a retrieval difference must not replace those answer-accuracy figures. The supplementary LongMemEval arm uses 150 answerable standard-s questions and session labels, with no answer reader. A separate LoCoMo arm compares all required methods on 150 questions using author-supplied turn evidence mapped to sessions; it uses raw dialogs and provided image captions, not generated observations or summaries.

Suggested replacement: "This book separately reported reader answer accuracy of 191 out of 300 questions for BM25 and 165 out of 300 for dense retrieval. The public-data retrieval metrics here measure evidence retrieval and cannot replace those answer-accuracy figures."

LoCoMo source mapping and exclusions are recorded in `results/locomo-label-audit.json`, `results/manifest.json`, and `prepare_locomo.py`. Query-bootstrap intervals condition on ten supplied conversations; top-20 recall has a ceiling effect in the small original candidate pools.

The tutorial's 20-question, 24-note figures are BM25 recall@3=.90/MRR=.86, dense 1.00/.97, hybrid .95/.93, and hybrid plus reranking .95/.96. The resulting tutorial reranker MRR difference is +.03, with no recall@3 improvement. This task does not recreate the synthetic tutorial or claim it as public-data evidence; the accompanying public-data table provides separate retrieval measurements. Suggested replacement: "The tutorial illustrates the calculation on 20 questions and cannot rank pipelines. This book also reports a separate public-data comparison with paired query intervals."

## Chapter 14: LazyGraphRAG indexing cost

Chapter file: `build/chapters/14-knowledge-graphs.html`.

Printed sentence:

> 0.1% LazyGraphRAG indexing cost relative to full GraphRAG, which Microsoft says matches vector RAG.

Local figure: **cannot be reproduced locally from an identified official implementation**. The cited maintainer page's June 2025 update directs users to Microsoft Discovery and Azure Local integrations. The official GraphRAG repository tree inspected at the commit in `results/graph-availability.json` has no LazyGraphRAG-labelled implementation. FastGraphRAG exists in that repository but is a distinct method; substituting it would not test this claim. Neither a 200-document paired indexing run nor model-call/token ratios were measured. No model-call count is presented as a dollar-cost reproduction.

Suggested replacement: "Microsoft reports LazyGraphRAG indexing at 0.1% of full GraphRAG's cost. This book could not reproduce that ratio locally because the cited release points to Azure integrations and an official runnable local LazyGraphRAG implementation was not identified."

Evidence: cited primary blog URL and SHA256 in `results/sources.json`; official repository commit and matching paths in `results/graph-availability.json`. The conclusion concerns the identified official release, not a proof that no third-party reimplementation exists.

## Chapter 14: Related graph-retrieval gain

Printed sentence: "+7% HippoRAG 2 on associative memory tasks against the best embedding model." The six required configurations in this task do not include HippoRAG 2's graph extraction and associative retrieval algorithm, so this harness cannot speak to that percentage. Plain RRF results must not be labeled a HippoRAG 2 reproduction.

Suggested replacement: "HippoRAG 2 reports a 7% improvement on its associative memory tasks. This book's BM25, dense, and RRF evaluation does not reproduce that graph algorithm or its benchmark."

## Execution and unresolved work

See `results/operations.json` for the unreachable original BEIR archive host, scratch-disk relocation, and preparation-memory correction. The GPU is shared; the harness waits for other wave models and required memory headroom, allows authorized resident and graphics processes, and never stops them. The generated results below contain completed local figures, replacement sentences, and model output audits; cleanup proof is recorded separately.

<!-- GENERATED RESULTS -->
## Completed public-data results

All values below are percentages, with query-bootstrap 95% intervals in brackets. Paired changes are percentage points unless marked relative. Each row uses all selected queries; partial cells are not printed.

| Dataset | Method | N | Recall@5 | Recall@20 | nDCG@10 | Complete miss@20 |
|---|---|---:|---:|---:|---:|---:|
| scifact | bm25 | 300 | 70.96 [65.76, 75.86] | 81.48 [77.14, 85.61] | 64.19 [59.53, 68.62] | 16.67 [12.67, 21.00] |
| scifact | dense | 300 | 71.71 [66.52, 76.58] | 85.47 [81.37, 89.27] | 64.27 [59.72, 68.59] | 14.00 [10.33, 18.00] |
| scifact | hybrid_rrf | 300 | 74.74 [69.80, 79.36] | 86.64 [82.80, 90.25] | 67.04 [62.45, 71.39] | 12.00 [8.33, 16.00] |
| scifact | hybrid_rerank | 300 | 75.42 [70.48, 80.08] | 87.19 [83.29, 90.69] | 69.24 [64.62, 73.64] | 11.67 [8.33, 15.34] |
| scifact | context_bm25 | 300 | 71.96 [66.94, 76.78] | 82.71 [78.42, 86.78] | 65.29 [60.67, 69.70] | 15.33 [11.33, 19.67] |
| scifact | context_dense | 300 | 74.29 [69.32, 79.02] | 86.80 [82.83, 90.37] | 66.98 [62.54, 71.19] | 12.67 [9.00, 16.67] |
| scifact | context_hybrid_rrf | 300 | 76.29 [71.44, 80.89] | 87.27 [83.39, 90.82] | 68.77 [64.28, 73.09] | 11.67 [8.00, 15.67] |
| scifact | context_hybrid_rerank | 300 | 76.29 [71.43, 80.76] | 86.24 [82.28, 89.89] | 70.44 [65.98, 74.68] | 12.67 [9.00, 16.67] |
| nfcorpus | bm25 | 323 | 11.96 [9.66, 14.41] | 17.39 [14.72, 20.26] | 29.80 [26.50, 33.22] | 28.48 [23.53, 33.44] |
| nfcorpus | dense | 323 | 11.80 [9.44, 14.33] | 18.66 [16.00, 21.40] | 30.24 [27.04, 33.58] | 25.70 [21.05, 30.65] |
| nfcorpus | hybrid_rrf | 323 | 12.42 [10.02, 14.99] | 19.70 [16.92, 22.59] | 32.57 [29.23, 36.02] | 23.53 [18.89, 28.17] |
| nfcorpus | hybrid_rerank | 323 | 13.61 [11.16, 16.21] | 19.49 [16.80, 22.33] | 35.46 [32.03, 39.02] | 23.84 [19.20, 28.48] |
| nfcorpus | context_bm25 | 323 | 12.38 [9.98, 14.92] | 17.58 [14.95, 20.38] | 31.49 [28.15, 34.95] | 28.17 [23.22, 33.13] |
| nfcorpus | context_dense | 323 | 12.68 [10.32, 15.19] | 20.61 [17.83, 23.53] | 33.37 [30.01, 36.85] | 23.84 [19.20, 28.48] |
| nfcorpus | context_hybrid_rrf | 323 | 13.49 [10.99, 16.15] | 20.12 [17.39, 22.95] | 34.38 [30.99, 37.98] | 23.84 [19.20, 28.48] |
| nfcorpus | context_hybrid_rerank | 323 | 13.67 [11.22, 16.28] | 20.14 [17.36, 23.08] | 34.69 [31.34, 38.09] | 24.46 [19.81, 29.10] |
| longmemeval | bm25 | 150 | 88.20 [83.83, 92.04] | 97.96 [95.69, 99.64] | 87.77 [83.83, 91.36] | 1.33 [0.00, 3.33] |
| longmemeval | dense | 150 | 94.61 [91.62, 97.18] | 98.67 [97.00, 100.00] | 92.06 [89.07, 94.75] | 0.67 [0.00, 2.00] |
| longmemeval | hybrid_rrf | 150 | 93.66 [90.32, 96.56] | 99.44 [98.56, 100.00] | 92.89 [89.75, 95.58] | 0.00 [0.00, 0.00] |
| longmemeval | hybrid_rerank | 150 | 95.14 [92.34, 97.54] | 98.12 [96.31, 99.51] | 93.56 [90.58, 96.16] | 0.67 [0.00, 2.00] |
| locomo | bm25 | 150 | 84.23 [78.79, 89.24] | 97.89 [96.00, 99.39] | 79.21 [74.53, 83.80] | 0.00 [0.00, 0.00] |
| locomo | dense | 150 | 65.51 [57.92, 72.58] | 94.04 [90.31, 97.22] | 57.18 [51.27, 62.87] | 4.67 [1.33, 8.00] |
| locomo | hybrid_rrf | 150 | 79.51 [73.22, 85.36] | 98.64 [97.40, 99.67] | 74.43 [69.18, 79.40] | 0.00 [0.00, 0.00] |
| locomo | hybrid_rerank | 150 | 84.72 [79.28, 89.65] | 99.28 [98.33, 100.00] | 81.16 [76.19, 85.81] | 0.00 [0.00, 0.00] |
| locomo | context_bm25 | 150 | 86.38 [81.47, 90.87] | 98.33 [96.67, 99.67] | 79.84 [75.30, 84.17] | 0.00 [0.00, 0.00] |
| locomo | context_dense | 150 | 65.42 [58.01, 72.41] | 93.98 [90.25, 97.25] | 62.23 [56.20, 68.01] | 4.67 [1.33, 8.00] |
| locomo | context_hybrid_rrf | 150 | 82.97 [77.25, 88.12] | 98.70 [97.37, 99.70] | 75.59 [70.80, 80.17] | 0.00 [0.00, 0.00] |
| locomo | context_hybrid_rerank | 150 | 85.44 [80.09, 90.20] | 99.37 [98.43, 100.00] | 80.95 [76.26, 85.39] | 0.00 [0.00, 0.00] |

### Published figures beside the local counterpart

| Claim | Dataset | N | Published | Local measurement, 95% interval | Interpretation |
|---|---|---:|---|---|---|
| Embedding 1 − recall@20 | scifact | 300 | 5.7% | 14.53 [10.73, 18.63] | Cannot speak to the published percentage on a different benchmark |
| Contextual dense 1 − recall@20 | scifact | 300 | 3.7%; 35% reduction | 13.20 [9.63, 17.17] | Cannot speak to the published percentage on a different benchmark; local change inconclusive |
| Contextual hybrid 1 − recall@20 | scifact | 300 | 2.9%; 49% reduction | 12.73 [9.18, 16.61] | Cannot speak to the published percentage on a different benchmark; local change inconclusive |
| Contextual hybrid plus reranker 1 − recall@20 | scifact | 300 | 1.9%; 67% reduction | 13.76 [10.11, 17.72] | Cannot speak to the published percentage on a different benchmark; local change inconclusive |
| Relative failure reduction, context_dense vs dense | scifact | 300 | 35% | 9.17 [-7.79, 24.01] | Paired absolute error change -1.33 [-3.67, 1.00] points |
| Relative failure reduction, context_hybrid_rrf vs dense | scifact | 300 | 49% | 12.42 [-14.31, 33.90] | Paired absolute error change -1.81 [-5.56, 1.78] points |
| Relative failure reduction, context_hybrid_rerank vs dense | scifact | 300 | 67% | 5.35 [-24.03, 27.78] | Paired absolute error change -0.78 [-4.50, 3.00] points |
| RRF relative nDCG@10 gain over best single | scifact | 300 | 4 to 5%, reported MAP | 4.32 [-0.52, 6.54] | local direction inconclusive; cannot validate original magnitude with different metric/corpus; baseline dense |
| RRF relative AP@150 gain over best single | scifact | 300 | 4 to 5%, reported MAP | 5.31 [0.22, 8.60] | supports a positive local gain; cannot validate original magnitude with different metric/corpus; baseline bm25 |
| Embedding 1 − recall@20 | nfcorpus | 323 | 5.7% | 81.34 [78.60, 84.00] | Cannot speak to the published percentage on a different benchmark |
| Contextual dense 1 − recall@20 | nfcorpus | 323 | 3.7%; 35% reduction | 79.39 [76.47, 82.17] | Cannot speak to the published percentage on a different benchmark; supports higher recall locally |
| Contextual hybrid 1 − recall@20 | nfcorpus | 323 | 2.9%; 49% reduction | 79.88 [77.05, 82.61] | Cannot speak to the published percentage on a different benchmark; supports higher recall locally |
| Contextual hybrid plus reranker 1 − recall@20 | nfcorpus | 323 | 1.9%; 67% reduction | 79.86 [76.92, 82.64] | Cannot speak to the published percentage on a different benchmark; local change inconclusive |
| Relative failure reduction, context_dense vs dense | nfcorpus | 323 | 35% | 2.40 [1.29, 3.69] | Paired absolute error change -1.96 [-3.01, -1.05] points |
| Relative failure reduction, context_hybrid_rrf vs dense | nfcorpus | 323 | 49% | 1.79 [0.21, 3.35] | Paired absolute error change -1.46 [-2.74, -0.16] points |
| Relative failure reduction, context_hybrid_rerank vs dense | nfcorpus | 323 | 67% | 1.82 [-0.16, 3.80] | Paired absolute error change -1.48 [-3.11, 0.13] points |
| RRF relative nDCG@10 gain over best single | nfcorpus | 323 | 4 to 5%, reported MAP | 7.68 [2.45, 10.66] | supports a positive local gain; cannot validate original magnitude with different metric/corpus; baseline dense |
| RRF relative AP@150 gain over best single | nfcorpus | 323 | 4 to 5%, reported MAP | 7.88 [1.33, 12.87] | supports a positive local gain; cannot validate original magnitude with different metric/corpus; baseline dense |
| Embedding 1 − recall@20 | longmemeval | 150 | 5.7% | 1.33 [0.00, 3.00] | Cannot speak to the published percentage on a different benchmark |
| Contextual dense 1 − recall@20 | longmemeval | 150 | 3.7%; 35% reduction | not measured | No completed local cell |
| Contextual hybrid 1 − recall@20 | longmemeval | 150 | 2.9%; 49% reduction | not measured | No completed local cell |
| Contextual hybrid plus reranker 1 − recall@20 | longmemeval | 150 | 1.9%; 67% reduction | not measured | No completed local cell |
| RRF relative nDCG@10 gain over best single | longmemeval | 150 | 4 to 5%, reported MAP | 0.91 [-1.77, 3.42] | local direction inconclusive; cannot validate original magnitude with different metric/corpus; baseline dense |
| RRF relative AP@150 gain over best single | longmemeval | 150 | 4 to 5%, reported MAP | 1.64 [-1.59, 4.79] | local direction inconclusive; cannot validate original magnitude with different metric/corpus; baseline dense |
| Embedding 1 − recall@20 | locomo | 150 | 5.7% | 5.96 [2.78, 9.69] | Cannot speak to the published percentage on a different benchmark |
| Contextual dense 1 − recall@20 | locomo | 150 | 3.7%; 35% reduction | 6.02 [2.75, 9.75] | Cannot speak to the published percentage on a different benchmark; local change inconclusive |
| Contextual hybrid 1 − recall@20 | locomo | 150 | 2.9%; 49% reduction | 1.30 [0.30, 2.63] | Cannot speak to the published percentage on a different benchmark; supports higher recall locally |
| Contextual hybrid plus reranker 1 − recall@20 | locomo | 150 | 1.9%; 67% reduction | 0.63 [0.00, 1.57] | Cannot speak to the published percentage on a different benchmark; supports higher recall locally |
| Relative failure reduction, context_dense vs dense | locomo | 150 | 35% | -1.03 (interval undefined) | Paired absolute error change 0.06 [-2.74, 2.84] points; 1/10000 ratio draws undefined because baseline error is zero |
| Relative failure reduction, context_hybrid_rrf vs dense | locomo | 150 | 49% | 78.17 (interval undefined) | Paired absolute error change -4.66 [-8.48, -1.32] points; 1/10000 ratio draws undefined because baseline error is zero |
| Relative failure reduction, context_hybrid_rerank vs dense | locomo | 150 | 67% | 89.37 (interval undefined) | Paired absolute error change -5.32 [-9.10, -2.04] points; 1/10000 ratio draws undefined because baseline error is zero |
| RRF relative nDCG@10 gain over best single | locomo | 150 | 4 to 5%, reported MAP | -6.03 [-11.22, -0.96] | contradicts a positive local gain; cannot validate original magnitude with different metric/corpus; baseline bm25 |
| RRF relative AP@150 gain over best single | locomo | 150 | 4 to 5%, reported MAP | -7.34 [-14.07, -0.74] | contradicts a positive local gain; cannot validate original magnitude with different metric/corpus; baseline bm25 |
| LazyGraphRAG indexing/full GraphRAG | none | 0 | 0.1% | cannot be reproduced locally from an identified official implementation | No paired indexing run or call/token ratio |

### Paired changes

| Dataset | Comparison | Recall@5 change | Recall@20 change | nDCG@10 change | Complete miss@20 change |
|---|---|---:|---:|---:|---:|
| scifact | hybrid_rrf minus bm25 | 3.78 [0.37, 7.33] | 5.16 [2.06, 8.39] | 2.86 [0.29, 5.36] | -4.67 [-8.00, -1.67] |
| scifact | hybrid_rrf minus dense | 3.03 [-0.94, 7.03] | 1.17 [-2.22, 4.67] | 2.78 [-0.13, 5.58] | -2.00 [-5.67, 1.33] |
| scifact | hybrid_rerank minus hybrid_rrf | 0.68 [-3.31, 4.62] | 0.55 [-2.42, 3.40] | 2.20 [-1.04, 5.44] | -0.33 [-3.00, 2.67] |
| scifact | context_bm25 minus bm25 | 1.00 [-0.67, 2.83] | 1.23 [-0.70, 3.23] | 1.10 [-0.29, 2.49] | -1.33 [-3.33, 0.67] |
| scifact | context_dense minus dense | 2.58 [-0.77, 6.10] | 1.33 [-1.00, 3.67] | 2.71 [0.62, 4.91] | -1.33 [-3.67, 1.00] |
| scifact | context_hybrid_rrf minus dense | 4.58 [0.11, 9.08] | 1.81 [-1.78, 5.56] | 4.50 [1.44, 7.56] | -2.33 [-6.00, 1.33] |
| scifact | context_hybrid_rerank minus dense | 4.58 [0.39, 8.79] | 0.78 [-3.00, 4.50] | 6.17 [2.90, 9.48] | -1.33 [-5.33, 2.67] |
| scifact | context_hybrid_rrf minus context_dense | 2.00 [-2.02, 5.91] | 0.47 [-2.78, 3.83] | 1.79 [-0.97, 4.53] | -1.00 [-4.33, 2.33] |
| scifact | context_hybrid_rerank minus context_hybrid_rrf | -0.01 [-3.27, 3.19] | -1.03 [-4.08, 1.97] | 1.67 [-1.00, 4.32] | 1.00 [-2.00, 4.00] |
| nfcorpus | hybrid_rrf minus bm25 | 0.46 [-0.50, 1.53] | 2.31 [1.31, 3.42] | 2.77 [1.51, 4.03] | -4.95 [-8.05, -1.86] |
| nfcorpus | hybrid_rrf minus dense | 0.62 [-0.50, 1.67] | 1.05 [-0.22, 2.25] | 2.32 [0.77, 3.93] | -2.17 [-5.26, 0.93] |
| nfcorpus | hybrid_rerank minus hybrid_rrf | 1.19 [0.41, 2.02] | -0.21 [-1.23, 0.69] | 2.89 [1.73, 4.05] | 0.31 [-2.48, 3.10] |
| nfcorpus | context_bm25 minus bm25 | 0.42 [-0.17, 0.98] | 0.19 [-0.27, 0.59] | 1.69 [1.05, 2.34] | -0.31 [-1.86, 1.24] |
| nfcorpus | context_dense minus dense | 0.87 [-0.28, 2.02] | 1.96 [1.05, 3.01] | 3.12 [1.85, 4.42] | -1.86 [-4.33, 0.62] |
| nfcorpus | context_hybrid_rrf minus dense | 1.69 [0.72, 2.71] | 1.46 [0.16, 2.74] | 4.14 [2.43, 5.91] | -1.86 [-5.26, 1.55] |
| nfcorpus | context_hybrid_rerank minus dense | 1.87 [0.58, 3.16] | 1.48 [-0.13, 3.11] | 4.44 [2.58, 6.34] | -1.24 [-5.26, 2.48] |
| nfcorpus | context_hybrid_rrf minus context_dense | 0.82 [-0.40, 2.10] | -0.50 [-1.92, 0.85] | 1.01 [-0.49, 2.52] | 0.00 [-3.41, 3.41] |
| nfcorpus | context_hybrid_rerank minus context_hybrid_rrf | 0.17 [-0.86, 1.14] | 0.02 [-1.14, 1.19] | 0.31 [-1.00, 1.64] | 0.62 [-2.48, 3.72] |
| longmemeval | hybrid_rrf minus bm25 | 5.46 [3.07, 8.16] | 1.49 [-0.13, 3.53] | 5.12 [2.94, 7.43] | -1.33 [-3.33, 0.00] |
| longmemeval | hybrid_rrf minus dense | -0.96 [-3.96, 2.04] | 0.78 [-0.44, 2.56] | 0.83 [-1.64, 3.19] | -0.67 [-2.00, 0.00] |
| longmemeval | hybrid_rerank minus hybrid_rrf | 1.49 [-1.84, 4.96] | -1.32 [-2.97, -0.22] | 0.67 [-2.06, 3.32] | 0.67 [0.00, 2.00] |
| locomo | hybrid_rrf minus bm25 | -4.72 [-9.72, 0.11] | 0.76 [-0.13, 1.89] | -4.78 [-9.04, -0.74] | 0.00 [0.00, 0.00] |
| locomo | hybrid_rrf minus dense | 14.00 [8.17, 20.33] | 4.60 [1.33, 8.38] | 17.25 [13.47, 21.07] | -4.67 [-8.00, -1.33] |
| locomo | hybrid_rerank minus hybrid_rrf | 5.21 [-0.97, 11.46] | 0.63 [-0.17, 1.63] | 6.73 [2.10, 11.31] | 0.00 [0.00, 0.00] |
| locomo | context_bm25 minus bm25 | 2.16 [-2.33, 6.83] | 0.44 [-0.67, 1.78] | 0.64 [-1.80, 3.12] | 0.00 [0.00, 0.00] |
| locomo | context_dense minus dense | -0.08 [-6.56, 6.36] | -0.06 [-2.84, 2.74] | 5.05 [0.46, 9.69] | 0.00 [-2.67, 2.67] |
| locomo | context_hybrid_rrf minus dense | 17.47 [11.27, 23.93] | 4.66 [1.32, 8.48] | 18.41 [13.80, 23.01] | -4.67 [-8.00, -1.33] |
| locomo | context_hybrid_rerank minus dense | 19.93 [12.68, 27.54] | 5.32 [2.04, 9.10] | 23.78 [17.85, 29.61] | -4.67 [-8.00, -1.33] |
| locomo | context_hybrid_rrf minus context_dense | 17.55 [11.67, 23.85] | 4.72 [1.42, 8.47] | 13.36 [9.98, 16.81] | -4.67 [-8.00, -1.33] |
| locomo | context_hybrid_rerank minus context_hybrid_rrf | 2.47 [-2.78, 7.80] | 0.67 [-0.67, 2.00] | 5.37 [1.27, 9.71] | 0.00 [0.00, 0.00] |

### Suggested replacement sentences

Contextual Retrieval:
In this book, replacing uncontextualized dense retrieval with local contextual hybrid retrieval and reranking changed the share of relevant documents or sessions missing from the top 20 from 14.5% to 13.8% on SciFact (300 queries), and 81.3% to 79.9% on NFCorpus (323 queries), and 6.0% to 0.6% on LoCoMo (150 queries). Different corpora, document or session labels, and open models make this a local comparison, not a reproduction of Anthropic's percentages.

RRF:
This book measured relative AP@150 changes with RRF of +5.3% on SciFact (300 queries), and +7.9% on NFCorpus (323 queries), and +1.6% on LongMemEval (150 queries), and -7.3% on LoCoMo (150 queries) against the better single retriever. These public-data measurements differ from the original paper's MAP benchmark and do not establish a universal 4 to 5% gain.

### Limits and incomplete cells

The contextual LongMemEval arm was not run: its 82,605 additional chunk-prefix calls could not fit the fixed ten-hour budget after completing the two full BEIR corpora and the compact LoCoMo arm. LoCoMo supplies the full contextual conversational-memory comparison. All four baseline memory methods use the same 150 questions; no thin contextual subset is compared to them.

No answer generation or LLM judge was used, so the requirement to hand-check generated judgments does not apply. Session-level LongMemEval relevance cannot establish precise evidence-turn retrieval or answer correctness. No original vendor evaluation corpus or RRF TREC run bundle was replaced with generated relevance labels.

- longmemeval: unrun or incomplete: context_bm25, context_dense, context_hybrid_rrf, context_hybrid_rerank.

### Binary-rate boundary check

A percentile query bootstrap is degenerate when every observed failure indicator is zero or one. The additional Wilson interval is supplied for the failure rate, without replacing the requested paired-bootstrap differences.

| Dataset | Method | Misses / N | Complete miss@20 Wilson 95% interval |
|---|---|---:|---:|
| scifact | bm25 | 50 / 300 | 16.67 [12.88, 21.30] |
| scifact | dense | 42 / 300 | 14.00 [10.53, 18.38] |
| scifact | hybrid_rrf | 36 / 300 | 12.00 [8.80, 16.17] |
| scifact | hybrid_rerank | 35 / 300 | 11.67 [8.51, 15.79] |
| scifact | context_bm25 | 46 / 300 | 15.33 [11.70, 19.85] |
| scifact | context_dense | 38 / 300 | 12.67 [9.37, 16.91] |
| scifact | context_hybrid_rrf | 35 / 300 | 11.67 [8.51, 15.79] |
| scifact | context_hybrid_rerank | 38 / 300 | 12.67 [9.37, 16.91] |
| nfcorpus | bm25 | 92 / 323 | 28.48 [23.84, 33.64] |
| nfcorpus | dense | 83 / 323 | 25.70 [21.24, 30.73] |
| nfcorpus | hybrid_rrf | 76 / 323 | 23.53 [19.23, 28.45] |
| nfcorpus | hybrid_rerank | 77 / 323 | 23.84 [19.52, 28.78] |
| nfcorpus | context_bm25 | 91 / 323 | 28.17 [23.55, 33.31] |
| nfcorpus | context_dense | 77 / 323 | 23.84 [19.52, 28.78] |
| nfcorpus | context_hybrid_rrf | 77 / 323 | 23.84 [19.52, 28.78] |
| nfcorpus | context_hybrid_rerank | 79 / 323 | 24.46 [20.09, 29.43] |
| longmemeval | bm25 | 2 / 150 | 1.33 [0.37, 4.73] |
| longmemeval | dense | 1 / 150 | 0.67 [0.12, 3.68] |
| longmemeval | hybrid_rrf | 0 / 150 | 0.00 [0.00, 2.50] |
| longmemeval | hybrid_rerank | 1 / 150 | 0.67 [0.12, 3.68] |
| locomo | bm25 | 0 / 150 | 0.00 [0.00, 2.50] |
| locomo | dense | 7 / 150 | 4.67 [2.28, 9.32] |
| locomo | hybrid_rrf | 0 / 150 | 0.00 [0.00, 2.50] |
| locomo | hybrid_rerank | 0 / 150 | 0.00 [0.00, 2.50] |
| locomo | context_bm25 | 0 / 150 | 0.00 [0.00, 2.50] |
| locomo | context_dense | 7 / 150 | 4.67 [2.28, 9.32] |
| locomo | context_hybrid_rrf | 0 / 150 | 0.00 [0.00, 2.50] |
| locomo | context_hybrid_rerank | 0 / 150 | 0.00 [0.00, 2.50] |

### Prefix output audit

```json
{
  "scifact": {
    "hardware_classes": {
      "Apple M1 Ultra, 64 GB": 460,
      "Apple M3 Ultra, 96 GB": 779,
      "8 GB NVIDIA RTX 3070 Ti GPU": 8822,
      "8 GB NVIDIA RTX 3070 Ti GPU with CPU offload": 5
    },
    "parallel_request_counts": {
      "4": 1150,
      "8": 89,
      "2": 2472,
      "1": 6355
    },
    "context_limit_recording_note": "Early Mac rows lack a per-row token limit; deployment history records four 8192-token slots for those initial phases. All fixed prompts fit 2976 tokens.",
    "context_token_limits": {
      "None": 1139,
      "4096": 89,
      "3072": 4583,
      "3008": 1589,
      "2976": 2666
    },
    "gpu_layer_counts": {
      "runtime default": 7400,
      "28": 5,
      "99": 2661
    },
    "prefill_batch_tokens": {
      "runtime default": 7459,
      "128": 2607
    },
    "physical_prefill_batch_tokens": {
      "runtime default": 7459,
      "64": 2607
    },
    "n": 10066,
    "completion_tokens": 789916,
    "median_completion_tokens": 78.0,
    "outside_requested_50_100_tokens": 2313,
    "finish_reasons": {
      "stop": 9711,
      "length": 355
    },
    "interpretation": "Request timings remain raw operational records and are not compared across hardware. Context text is generated, not a relevance judgment."
  },
  "nfcorpus": {
    "hardware_classes": {
      "8 GB NVIDIA RTX 3070 Ti GPU": 7349
    },
    "parallel_request_counts": {
      "1": 7349
    },
    "context_limit_recording_note": "Per-row context limits are complete; every fixed prompt fits 2976 tokens.",
    "context_token_limits": {
      "2976": 7349
    },
    "gpu_layer_counts": {
      "99": 7349
    },
    "prefill_batch_tokens": {
      "128": 7349
    },
    "physical_prefill_batch_tokens": {
      "64": 7349
    },
    "n": 7349,
    "completion_tokens": 543467,
    "median_completion_tokens": 73,
    "outside_requested_50_100_tokens": 1674,
    "finish_reasons": {
      "stop": 7189,
      "length": 160
    },
    "interpretation": "Request timings remain raw operational records and are not compared across hardware. Context text is generated, not a relevance judgment."
  },
  "locomo": {
    "hardware_classes": {
      "8 GB NVIDIA RTX 3070 Ti GPU": 1204
    },
    "parallel_request_counts": {
      "1": 1204
    },
    "context_limit_recording_note": "Per-row context limits are complete; every fixed prompt fits 2976 tokens.",
    "context_token_limits": {
      "2976": 1204
    },
    "gpu_layer_counts": {
      "99": 1204
    },
    "prefill_batch_tokens": {
      "128": 1204
    },
    "physical_prefill_batch_tokens": {
      "64": 1204
    },
    "n": 1204,
    "completion_tokens": 90712,
    "median_completion_tokens": 75.0,
    "outside_requested_50_100_tokens": 94,
    "finish_reasons": {
      "stop": 1199,
      "length": 5
    },
    "interpretation": "Request timings remain raw operational records and are not compared across hardware. Context text is generated, not a relevance judgment."
  }
}
```

Model output lengths outside 50 to 100 tokens are retained and counted, not silently excluded. Prefixes are deterministic-temperature generations; floating-point batching can still vary across hardware.


<!-- CLEANUP PROOF -->
Cleanup confirmed: all benchmark scratch directories and the compatibility alias are absent, and no owned inference process remains. No containers were started. The owned tunnel was closed, and no other task process was stopped. See an unpublished raw log for before/after disk and process listings.

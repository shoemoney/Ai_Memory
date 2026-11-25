# Embedding follow-up report

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

Partial, run finished: 7/12 new text-task cells and 3/3 visual-subset cells are retained. The 2B visual result belongs to the initial GPU phase. Missing cells have no local score. Qwen3-VL-Embedding-8B text NFCorpus and ArguAna, and all three Harrier-27B text tasks, were deferred on elapsed-time forecasts alone (never on scores) so that the visual models could finish; every retained cell keeps its full query split and corpus.

The run stopped mid-way and was resumed: the live Qwen3-VL-Embedding-8B text run was kept, the dropped SSH tunnel was recreated (the worker on the Mac had stayed healthy; one text invocation had died with a connection error and the controller retried it from checkpoints), and after the first session deadline the run resumed with a new deadline and the `--visual-first` option so the Nomic and Qwen3-VL-8B visual cells ran before any more text work. No finished cell, prompt, model, sample or scoring rule was changed.

The initial assigned Mac entered warning pressure and was not used after reassignment. The replacement machine is the same hardware class, Apple M3 Ultra with 96 GB memory, shared with other benchmark servers. The follow-up uses no dev GPU. Earlier small-model rows and the initial 2B visual row remain explicitly identified reused evidence.

## Published text-task scores against local scores

Scores are percentage points, with 95% query-bootstrap intervals. Every completed cell uses its full test split and full corpus: SciFact N=300/5,183 documents, NFCorpus N=323/3,633, ArguAna N=1,406/8,674. “Within CI” describes consistency on that task, not verification of a full-suite average or proof that quantization, backend and version changes have no effect.

| Model | Task | Published | Local [95% CI] | N | Hardware and precision | Interpretation / evidence |
|---|---|---:|---|---:|---|---|
| Qwen/Qwen3-Embedding-0.6B | SciFact | 69.72 | 69.99 [65.62, 74.23] | 300 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/Qwen__Qwen3-Embedding-0.6B/SciFact.json` |
| Qwen/Qwen3-Embedding-0.6B | NFCorpus | 36.71 | 36.17 [32.64, 39.69] | 323 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/Qwen__Qwen3-Embedding-0.6B/NFCorpus.json` |
| Qwen/Qwen3-Embedding-0.6B | ArguAna | 70.97 | 69.15 [67.52, 70.82] | 1406 | Earlier 8 GB NVIDIA GPU; BF16 | Outside local CI; `../mteb/results/local/Qwen__Qwen3-Embedding-0.6B/ArguAna.json` |
| Qwen/Qwen3-Embedding-4B | SciFact | 78.33 | 78.38 [74.71, 81.89] | 300 | Apple M3 Ultra, 96 GB; MLX; 8-bit weights, BF16 compute | Within local CI; `results/local/Qwen__Qwen3-Embedding-4B/SciFact.json` |
| Qwen/Qwen3-Embedding-4B | NFCorpus | 41.10 | 40.99 [37.41, 44.54] | 323 | Apple M3 Ultra, 96 GB; MLX; 8-bit weights, BF16 compute | Within local CI; `results/local/Qwen__Qwen3-Embedding-4B/NFCorpus.json` |
| Qwen/Qwen3-Embedding-4B | ArguAna | 75.64 | 74.74 [73.20, 76.26] | 1406 | Apple M3 Ultra, 96 GB; MLX; 8-bit weights, BF16 compute | Within local CI; `results/local/Qwen__Qwen3-Embedding-4B/ArguAna.json` |
| Qwen/Qwen3-Embedding-8B | SciFact | 78.46 | 78.04 [74.34, 81.66] | 300 | Apple M3 Ultra, 96 GB; MLX; 4-bit weights, BF16 compute | Within local CI; `results/local/Qwen__Qwen3-Embedding-8B/SciFact.json` |
| Qwen/Qwen3-Embedding-8B | NFCorpus | 41.45 | 41.14 [37.48, 44.80] | 323 | Apple M3 Ultra, 96 GB; MLX; 4-bit weights, BF16 compute | Within local CI; `results/local/Qwen__Qwen3-Embedding-8B/NFCorpus.json` |
| Qwen/Qwen3-Embedding-8B | ArguAna | 76.85 | 74.37 [72.89, 75.88] | 1406 | Apple M3 Ultra, 96 GB; MLX; 4-bit weights, BF16 compute | Outside local CI; `results/local/Qwen__Qwen3-Embedding-8B/ArguAna.json` |
| BAAI/bge-small-en-v1.5 | SciFact | 71.27 | 71.41 [67.02, 75.62] | 300 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/BAAI__bge-small-en-v1.5/SciFact.json` |
| BAAI/bge-small-en-v1.5 | NFCorpus | 34.26 | 34.27 [30.77, 37.81] | 323 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/BAAI__bge-small-en-v1.5/NFCorpus.json` |
| BAAI/bge-small-en-v1.5 | ArguAna | 60.35 | 60.43 [58.54, 62.28] | 1406 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/BAAI__bge-small-en-v1.5/ArguAna.json` |
| BAAI/bge-m3 | SciFact | 64.37 | 64.55 [59.89, 68.94] | 300 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/BAAI__bge-m3/SciFact.json` |
| BAAI/bge-m3 | NFCorpus | 31.41 | 31.53 [28.21, 34.92] | 323 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/BAAI__bge-m3/NFCorpus.json` |
| BAAI/bge-m3 | ArguAna | 54.04 | 54.05 [52.23, 55.89] | 1406 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/BAAI__bge-m3/ArguAna.json` |
| google/embeddinggemma-2 | SciFact | Unavailable | 85.32 [81.82, 88.62] | 300 | Earlier 8 GB NVIDIA GPU; BF16 | No matching published task score; `../mteb/results/local/google__embeddinggemma-2/SciFact.json` |
| google/embeddinggemma-2 | NFCorpus | Unavailable | 36.85 [33.45, 40.33] | 323 | Earlier 8 GB NVIDIA GPU; BF16 | No matching published task score; `../mteb/results/local/google__embeddinggemma-2/NFCorpus.json` |
| google/embeddinggemma-2 | ArguAna | 59.83 | 60.01 [58.11, 61.86] | 1406 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/google__embeddinggemma-2/ArguAna.json` |
| jinaai/jina-embeddings-v5-text-small | SciFact | 76.53 | 76.36 [72.45, 80.20] | 300 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/jinaai__jina-embeddings-v5-text-small/SciFact.json` |
| jinaai/jina-embeddings-v5-text-small | NFCorpus | 39.81 | 39.82 [36.30, 43.38] | 323 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/jinaai__jina-embeddings-v5-text-small/NFCorpus.json` |
| jinaai/jina-embeddings-v5-text-small | ArguAna | 65.07 | 64.75 [63.05, 66.43] | 1406 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/jinaai__jina-embeddings-v5-text-small/ArguAna.json` |
| microsoft/harrier-oss-v1-270m | SciFact | 75.40 | 75.30 [71.21, 79.29] | 300 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/microsoft__harrier-oss-v1-270m/SciFact.json` |
| microsoft/harrier-oss-v1-270m | NFCorpus | 36.15 | 36.01 [32.49, 39.54] | 323 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/microsoft__harrier-oss-v1-270m/NFCorpus.json` |
| microsoft/harrier-oss-v1-270m | ArguAna | 63.63 | 64.23 [62.44, 65.96] | 1406 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/microsoft__harrier-oss-v1-270m/ArguAna.json` |
| microsoft/harrier-oss-v1-0.6b | SciFact | 76.26 | 75.95 [71.99, 79.82] | 300 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/microsoft__harrier-oss-v1-0.6b/SciFact.json` |
| microsoft/harrier-oss-v1-0.6b | NFCorpus | 37.23 | 37.08 [33.55, 40.62] | 323 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/microsoft__harrier-oss-v1-0.6b/NFCorpus.json` |
| microsoft/harrier-oss-v1-0.6b | ArguAna | 64.99 | 65.20 [63.49, 66.92] | 1406 | Earlier 8 GB NVIDIA GPU; BF16 | Within local CI; `../mteb/results/local/microsoft__harrier-oss-v1-0.6b/ArguAna.json` |
| microsoft/harrier-oss-v1-27b | SciFact | Unavailable | Not evaluated | 0 | Deferred (timing estimate) | Cannot assess; first-task forecast exceeded the remaining session time; `results/followup-events.jsonl` |
| microsoft/harrier-oss-v1-27b | NFCorpus | Unavailable | Not evaluated | 0 | Deferred (timing estimate) | Cannot assess; first-task forecast exceeded the remaining session time; `results/followup-events.jsonl` |
| microsoft/harrier-oss-v1-27b | ArguAna | 67.76 | Not evaluated | 0 | Deferred (timing estimate) | Cannot assess; first-task forecast exceeded the remaining session time; `results/followup-events.jsonl` |
| Qwen/Qwen3-VL-Embedding-2B | SciFact | Unavailable | 74.78 [70.75, 78.70] | 300 | Earlier 8 GB NVIDIA GPU; BF16 | No matching published task score; `../mteb/results/local/Qwen__Qwen3-VL-Embedding-2B/SciFact.json` |
| Qwen/Qwen3-VL-Embedding-2B | NFCorpus | Unavailable | 37.34 [33.76, 41.01] | 323 | Earlier 8 GB NVIDIA GPU; BF16 | No matching published task score; `../mteb/results/local/Qwen__Qwen3-VL-Embedding-2B/NFCorpus.json` |
| Qwen/Qwen3-VL-Embedding-2B | ArguAna | Unavailable | 58.64 [56.89, 60.36] | 1406 | Earlier 8 GB NVIDIA GPU; BF16 | No matching published task score; `../mteb/results/local/Qwen__Qwen3-VL-Embedding-2B/ArguAna.json` |
| Qwen/Qwen3-VL-Embedding-8B | SciFact | Unavailable | 78.75 [75.06, 82.33] | 300 | Apple M3 Ultra, 96 GB; MLX; 4-bit weights, BF16 compute | No matching published task score; `results/local/Qwen__Qwen3-VL-Embedding-8B/SciFact.json` |
| Qwen/Qwen3-VL-Embedding-8B | NFCorpus | Unavailable | Not evaluated | 0 | Deferred (timing estimate) | Cannot assess; deferred on elapsed-time forecast only, no score used; `results/local/Qwen__Qwen3-VL-Embedding-8B/deferred.json` |
| Qwen/Qwen3-VL-Embedding-8B | ArguAna | Unavailable | Not evaluated | 0 | Deferred (timing estimate) | Cannot assess; deferred on elapsed-time forecast only, no score used; `results/local/Qwen__Qwen3-VL-Embedding-8B/deferred.json` |

## Published visual figures against the local subset

The local subset is ViDoRe V3 HR English, all 318 queries against all 1,110 pages. All models use the same items and graded qrels. This is different from MMEB-V2’s 78-task mean and the ViDoRe-v2 multi-dataset mean; these local results cannot support or contradict either published aggregate.

| Model | Published figure and benchmark | Local HR nDCG@5 [95% CI] | Local HR nDCG@10 [95% CI] | N | Hardware and precision |
|---|---|---|---|---:|---|
| Qwen/Qwen3-VL-Embedding-2B | 73.2; MMEB-V2, 78 tasks | 54.98 [51.36, 58.55] | 58.51 [55.26, 61.77] | 318 | 8 GB NVIDIA GPU; PyTorch; BF16 weights/compute |
| Qwen/Qwen3-VL-Embedding-8B | 77.8; MMEB-V2, 78 tasks | 58.77 [55.39, 62.20] | 62.07 [58.95, 65.20] | 318 | Apple M3 Ultra, 96 GB; MLX; 4-bit weights, BF16 compute |
| nomic-ai/nomic-embed-multimodal-7b | 58.8; ViDoRe-v2 nDCG@5 | 55.17 [51.64, 58.74] | 57.19 [53.84, 60.54] | 318 | Apple M3 Ultra, 96 GB; PyTorch MPS; 4-bit weights, BF16 compute |

Raw visual evidence: `results/vidore/<model>/queries.jsonl.gz` and `summary.json`. Dataset revision `bc7d43d64815ed30f664168c8052106484aba7fd`, CC BY 4.0, is recorded in `results/vidore-data.json`. The qrels configuration contains 8,655 rows for query IDs outside the English query file; only judgments for the provided English IDs are used, and all 318 English queries retain judgments.

## Printed figures and editor replacements

Exact chapter sentences, source citations and chapter content hashes are in `claims.json`. `inventory.json` lists every printed embedding quality score in chapters 03, 04 and 18. Hosted models have dimensions/prices but no printed quality score there; MiniLM, Jina v4, ColQwen2, ColPali and ImageBind have no printed numeric quality score.

### Qwen/Qwen3-Embedding-0.6B

Published: 64.33 on MMTEB. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 64.33 on MMTEB. This book scored 69.99 on SciFact (N=300), 36.17 on NFCorpus (N=323), 69.15 on ArguAna (N=1406), a narrower test that cannot verify the full-suite average.

### Qwen/Qwen3-Embedding-4B

Published: 69.45 on MMTEB. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 69.45 on MMTEB. This book scored 78.38 on SciFact (N=300), 40.99 on NFCorpus (N=323), 74.74 on ArguAna (N=1406) with 8-bit weights, a narrower test that cannot verify the full-suite average.

### Qwen/Qwen3-Embedding-8B

Published: 70.58 on MMTEB. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 70.58 on MMTEB. This book scored 78.04 on SciFact (N=300), 41.14 on NFCorpus (N=323), 74.37 on ArguAna (N=1406) with 4-bit weights, a narrower test that cannot verify the full-suite average.

### jinaai/jina-embeddings-v5-text-small

Published: 71.7 on MTEB English v2; 67.7 on MMTEB. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 71.7 on MTEB English v2; 67.7 on MMTEB. This book scored 76.36 on SciFact (N=300), 39.82 on NFCorpus (N=323), 64.75 on ArguAna (N=1406), a narrower test that cannot verify the full-suite average.

### microsoft/harrier-oss-v1-270m

Published: 66.5 on MTEB multilingual v2. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 66.5 on MTEB multilingual v2. This book scored 75.30 on SciFact (N=300), 36.01 on NFCorpus (N=323), 64.23 on ArguAna (N=1406), a narrower test that cannot verify the full-suite average.

### microsoft/harrier-oss-v1-0.6b

Published: 69.0 on MTEB multilingual v2. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 69.0 on MTEB multilingual v2. This book scored 75.95 on SciFact (N=300), 37.08 on NFCorpus (N=323), 65.20 on ArguAna (N=1406), a narrower test that cannot verify the full-suite average.

### microsoft/harrier-oss-v1-27b

Published: 74.3 on MTEB multilingual v2. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 74.3 on MTEB multilingual v2. The figure cannot be reproduced locally in this session under the available capacity and time constraints, so this book reports no local score.

### google/embeddinggemma-2

Published: 61.36 on MTEB multilingual v2 at 768; 68.46 on MTEB English 768; 67.78 on MTEB English 256; 65.68 on MTEB English 128. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 61.36 on MTEB multilingual v2 at 768; 68.46 on MTEB English 768; 67.78 on MTEB English 256; 65.68 on MTEB English 128. This book scored 85.32 on SciFact (N=300), 36.85 on NFCorpus (N=323), 60.01 on ArguAna (N=1406), a narrower test that cannot verify the full-suite average.

### BAAI/bge-m3

Published: 59.56 on MTEB multilingual, secondary guide. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 59.56 on MTEB multilingual, secondary guide. This book scored 64.55 on SciFact (N=300), 31.53 on NFCorpus (N=323), 54.05 on ArguAna (N=1406), a narrower test that cannot verify the full-suite average.

### BAAI/bge-small-en-v1.5

Published: 62.17 on MTEB English mean. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 62.17 on MTEB English mean. This book scored 71.41 on SciFact (N=300), 34.27 on NFCorpus (N=323), 60.43 on ArguAna (N=1406), a narrower test that cannot verify the full-suite average.

### Qwen/Qwen3-VL-Embedding-2B

Published: 63.87 on MMTEB text only. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 63.87 on MMTEB text only. This book scored 74.78 on SciFact (N=300), 37.34 on NFCorpus (N=323), 58.64 on ArguAna (N=1406), a narrower test that cannot verify the full-suite average.

### Qwen/Qwen3-VL-Embedding-8B

Published: 67.88 on MMTEB text only. The chapter file, exact source sentence and chapter hash are recorded in `claims.json`.

Local figures, N, intervals, precision and evidence are in the per-task table. These three English retrieval tasks cannot verify the cited full English/multilingual suite means.

**Suggested replacement:** The card reports 67.88 on MMTEB text only. This book scored 78.75 on SciFact (N=300) with 4-bit weights, a narrower test that cannot verify the full-suite average.

### Chapter 04: Qwen MMEB-V2 77.8 and 73.2

Published: 77.8 and 73.2 for the 8B and 2B models over 78 MMEB-V2 tasks. Local: the HR table above; this subset cannot verify that mean or the 8B versus 2B full-suite gap.

**Suggested replacement:** Qwen reports MMEB-V2 means of 77.8 and 73.2 for its 8B and 2B models. This book’s 2B model scored 58.51 nDCG@10 on 318 English ViDoRe V3 HR queries, a different benchmark.

### Chapter 04: Nomic 58.8 nDCG@5

The pinned 7B card is internally inconsistent: its introduction states 58.8, while its table gives 59.7 for 7B and 58.8 for 3B. Content hashes and source URLs are in `results/sources.json`. A V3 HR subset cannot resolve a V2 multi-dataset average.

**Suggested replacement:** Nomic’s 7B card says 58.8 nDCG@5 in its introduction but 59.7 in its table. This book treats the source figure as unresolved and reports its local ViDoRe V3 HR test separately.

### Other printed behavior figures

EmbeddingGemma’s published 768/256/128-dimensional English-suite scores, 68.46/67.78/65.68, are separate from the earlier local retrieval cuts retained in `../mteb/REPORT.md`. The published Qwen instruction gain of 1 to 5 points is an ablation not established by these instructed-only runs. No OCR control or agent screenshot-task evaluation was run, so this test cannot establish visual-over-OCR superiority or screenshot-agent usefulness.

**Suggested replacement:** The cards report full-suite dimension and instruction results, while this book’s earlier dimension tests cover three English retrieval tasks. This follow-up uses the official instructions and does not measure the gain from adding them.

## Setup differences and limits

The data/scoring harness uses MTEB 2.27.20, pinned original model/dataset revisions, the 512-token text cap, exact cosine search, pytrec_eval, and 10,000 query-bootstrap samples with seed 20261121. Transport batches sort by character length and restore the original order. The VL worker omits the unused language-model output head absent from its embedding checkpoint, strictly loads every backbone parameter, and resets position state for each independent request. Six synthetic embeddings passed its padding/order/repeated-request check with minimum cosine 0.99858 (results/vl-batch-invariance.json); this is not a full-precision backend check. Native Qwen text cells use batch size 32; all actual execution settings are in neighboring model config/worker-identity files. A paired 32-input, label-free numerical check gave a minimum full-precision embedding cosine of 0.99977 between the original 4B PyTorch wrapper and MLX; see `results/backend-equivalence.json`. It validates the adapter before quantization, not retrieval accuracy after quantization.

Configuration descriptions for unrun workers describe the shipped harness, not completed measurements. Full-precision 4B trials crossed the reserve; the measured 4B configuration therefore uses 8-bit MLX affine weights, group size 64. Larger Qwen models use 4-bit MLX affine weights with bfloat16 compute and an unquantized VL vision tower. Harrier uses its native causal Gemma3 text backbone, strict weight loading without a language-model output head, original local/global attention settings, right padding, last-nonpadding-token pooling including the instruction, and L2 normalization. Its linear and embedding modules use 4-bit MLX affine weights. Conversion streams one matrix at a time on the CPU, without calibration.

Nomic uses the official ColPali fork at the pinned archive commit with Transformers 4.49.0 and PEFT 0.14.0. Its large linear matrices use symmetric round-to-nearest 4-bit weights, group size 64; embeddings, normalization, biases and smaller matrices keep their original precision. Active LoRA deltas are merged per matrix before quantization. Its base and adapter revisions are pinned separately. The Nomic worker includes a CPU-product check for its MPS 3D attention path; if native 3D SDPA fails, the worker promotes it to an equivalent 4D batch and records that path, following the [upstream shape issue](https://github.com/huggingface/transformers/issues/36413). Its official processor defaults and cosine output are retained. Qwen VL image processing uses at most 1,800 image tokens and an 8,192-token image sequence cap; its text/query cap is 512. Different processor policies remain a model-specific difference.

Quantization, native inference, input caps and the source/local software or dataset versions prevent an exact full-precision reproduction claim. Hardware and resource sharing prevent timing comparisons. Cache-only/resumed elapsed times are not end-to-end inference timings. The intervals describe test-query variability, not historical reproducibility. SciFact/NFCorpus are registered among Harrier training datasets; no training/test overlap audit was performed. NFCorpus’s data license is unspecified, and no dataset copy is committed.

## Failures, validation, and cleanup

Historical failures are retained, not converted into scores: the initial Mac’s warning-pressure stop, the early GPU worker’s exit code 120 during disk pressure (exact cause unproven), the qrels-ID loader correction, and package compatibility corrections. After reassignment, full-precision 4B workers also reached the reserve and were stopped before a task score completed. Quantized cells use a fresh precision-specific cache namespace. The numerical backend and quantizer checks are separate from the retrieval-quality data. A small synthetic Q4 matrix probe did not show a float16 speed advantage, so bfloat16 compute was retained; this was not a model benchmark and used no quality data (results/dtype-performance-probe.json).

The first quantized conversion encountered a read-only copied tokenizer file; writable permissions on only the task-owned converted metadata fixed serialization. The VL load also required the missing mlx-lm dependency, an explicit repository argument in the streaming loader, and omission of an unused output head absent from the embedding checkpoint. An independent-request position-cache bug failed before a task score completed; the worker now resets that cache and passed the synthetic batch check. These failed attempts are archived as VL load/position logs. No existing service or its files were changed. Admission, retry, configuration, deadline and completion events are in `results/followup-events.jsonl`; worker logs retain other failed attempts. The initial cleanup is preserved as an unpublished raw log. Later text cells are deferred when a timing-only forecast exceeds the session time remaining; the same-host 8B task durations are the reference, scaled by completed current-model wall times when available and a 15% contingency, with a stated 3.6 starting parameter-scale factor for Harrier. The budget wall clocks include resumption and pauses and are not inference measurements. No quality score enters that choice, and retained cells use complete datasets. Per-model deferred files and the event log preserve the estimates and reasons.

Validation evidence: `results/verification.json`, `results/visual-verification.json`, `results/earlier-verification.json`, the two quantizer check files, and the numerical backend check. A verifier can pass only when its complete raw outputs exist. The earlier source hashes remain in `results/inherited-hashes.json`.

Final cleanup: an unpublished raw log; disk/process evidence: `results/resources-before-cleanup.json` and `results/resources-after.json`.

```json
{
  "local_scratch_removed": true,
  "removed_paths": [
    "/data/scratch/membench/mteb-large"
  ],
  "model_host_scratch_removed": true,
  "owned_processes_stopped_during_cleanup": [
    368057
  ],
  "containers_started": 0,
  "images_pulled": 0,
  "volumes_created": 0,
  "shared_model_service_changed": false,
  "cache_scope": "Task model, dataset, embedding and dedicated package caches removed. Shared package-manager caches were not pruned.",
  "utc": "2026-11-22T19:34:01Z"
}
```

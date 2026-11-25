# Local MTEB retrieval check

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

This is a **partial reproduction**, not a reproduction of a full MTEB or MMTEB leaderboard average. It evaluates open-weight embedding models on three fixed English retrieval tasks with the official `mteb` package. Each query searches the full task corpus. Scores measure how highly the model ranks documents with human relevance labels; no answer model, hosted inference service, or LLM judge is used.

The book's aggregate scores are inventoried in [claims.json](claims.json), with chapter locations and source URLs. [REPORT.md](REPORT.md) gives editorial replacements and unresolved claims. The historical multilingual scores, English suite scores, and this three-task retrieval average have different denominators and must not be substituted for one another.

## Run

From the repository root, on Linux with an NVIDIA GPU, a compatible driver, Python, and `uv` on PATH:

```bash
bash benchmarks/mteb/run.sh
```

The command creates an isolated Python 3.12.16 environment, installs the exact versions in [requirements.txt](requirements.txt), downloads pinned weights and datasets, runs models sequentially, verifies retained query scores, and removes its scratch environment and model caches on exit. It refuses an existing `/var/tmp/membench-mteb` path. Existing result files for each selected model are cleared and recomputed by default, so a failed load cannot leave old scores looking like a new run. To select models, append `--models BAAI/bge-small-en-v1.5 Qwen/Qwen3-Embedding-0.6B`. There is no model endpoint: inference runs in the evaluation process.

`run.py` performs the official evaluation and writes raw evidence, `suite.py` isolates each model in its own process, and `verify.py` independently re-scores the saved rankings with `pytrec_eval`. The optional `--resume` flag on `run.py` explicitly reuses completed task files only when the recorded revision, versions, and settings match. `summarize.py` regenerates the comparison table from evidence; `inventory.py` reads the three chapter files without changing them. `provenance.py` records source availability and checksums. These maintenance scripts are separate from model inference.

## Fixed method and data

Task selection was fixed before model scoring: scientific claim verification, medical information retrieval, and counterargument retrieval. This is a purposive subset of retrieval tasks, not a random sample of the full benchmark. All test queries and all candidate documents are retained; no corpus negatives are removed to make the task easier. Random seed is 20261121. There is no decoding temperature because nothing is generated.

| Task | Test queries | Corpus documents | Dataset revision | Dataset license in MTEB metadata |
|---|---:|---:|---|---|
| SciFact | 300 | 5,183 | `d56462d0e63a25450459c4f213e49ffdb866f7f9` | CC-BY-NC-4.0 |
| NFCorpus | 323 | 3,633 | `ec0fa4fe99da2ff19ca1214b7966684033a58814` | Not specified |
| ArguAna | 1,406 | 8,674 | `c22ab2a51041ffd869aaddef7af8d8215647e41a` | CC-BY-SA-4.0 |

Dataset cards: [SciFact](https://huggingface.co/datasets/mteb/scifact), [NFCorpus](https://huggingface.co/datasets/mteb/nfcorpus), [ArguAna](https://huggingface.co/datasets/mteb/arguana). The [NFCorpus project page](https://www.cl.uni-heidelberg.de/statnlpgroup/nfcorpus/) does not establish a dataset license; a website theme license must not be treated as a data license. Corpus and query text are downloaded at runtime and are not redistributed here. Retained outputs contain document IDs, relevance labels, scores, and ranks.

The public method comes from [MTEB](https://github.com/embeddings-benchmark/mteb), its [paper](https://arxiv.org/abs/2210.07316), the [MMTEB paper](https://arxiv.org/abs/2502.13595), and the pinned [official retrieval scorer](https://github.com/embeddings-benchmark/mteb/blob/2.27.20/mteb/_evaluators/retrieval_metrics.py). `mteb` is Apache-2.0; dataset licenses are separate.

The main metric is mean nDCG@10, displayed on a 0 to 100 scale. It discounts relevant documents at lower ranks and normalizes by the ideal ranking. It is not accuracy or a percentage of correct answers. ArguAna removes a query's identical document ID before scoring, following the official task implementation. Exact dense cosine search is used; BGE-M3 is evaluated as a single dense vector, without sparse or multi-vector scores. Only ranks through 10 are requested, since deeper ranks do not affect nDCG@10.

Models use their official MTEB encoder wrappers and task instructions. The task query instructions are also retained in [prompts.json](results/prompts.json). Query and document processing follow those wrappers: Qwen and Harrier use instructed queries and unprefixed documents; BGE-small uses its retrieval query instruction; BGE-M3 uses no query instruction; Jina uses its retrieval adapter and Query/Document prefixes; EmbeddingGemma 2 uses its task-specific query instructions and titled document format. EmbeddingGemma 2 loads text towers only, in bfloat16, without float16. Matryoshka dimensions use the official wrapper's truncation and normalization.

All inputs are capped at **512 tokens**, with batch size 8; the VL 2B run uses batch size 1 to fit shared GPU memory. Long-input-capable models therefore differ from their original evaluations. Model weights are unquantized bfloat16 on the GPU. Four CPU threads support one active model at a time. Versions include MTEB 2.27.20, sentence-transformers 6.3.0, transformers 5.24.0, torch 2.15.0+cu132, datasets 5.2.0, and pytrec-eval-terrier 0.5.11. The complete environment is pinned in the requirements file, and each run records its versions and dtype.

Hardware class: shared 8 GB NVIDIA GeForce RTX 3070 Ti, 32-thread x86 CPU, 28 GiB physical memory. Approximately 5 GB of GPU memory and 12 GiB of host memory were available initially. Existing GPU processes were left running. Timings include shared-load variation and are not throughput benchmarks.

## Published comparison

Published per-task files come from the official [MTEB results repository](https://github.com/embeddings-benchmark/results/tree/3acc22b2ee9ec7966b92c48a6afffcdede591689), pinned at commit `3acc22b2ee9ec7966b92c48a6afffcdede591689`. [published.json](published.json) records exact model revisions and source URLs. Every available original JSON file is retained under `results/published/`.

Jina's English task results are at revision `46ed7da5b47e4bca710b756313fafaf4110c6bd1`; the registry defaults to a newer revision that lacks these task files. The harness explicitly loads the published revision with the official Jina wrapper. Its historical custom module duplicates `cache_dir` with sentence-transformers 6.3.0 and ignores revisions in nested weight, adapter, and tokenizer loads. The loading-only shim in `compat.py` removes duplicate cache arguments and makes those loaders read a complete local snapshot of the published revision, without changing forward computation, pooling, retrieval-adapter selection, or prompts. An interrupted attempt using unpinned nested loads produced no retained scores. Audio/video packages are pinned because the official Gemma/VL dependency checks require them even for this text-only evaluation. Several other models have no published record for one or more selected tasks at this results commit. Missing published scores are shown as unavailable, never zero.

The results table is generated from [comparison.json](results/comparison.json). Confidence intervals are 10,000 percentile bootstrap resamples of test queries, seed 20261121. They describe query variability on one task, not uncertainty across languages or the whole suite, and are not a paired significance test against the published run. The hit count separately reports queries with at least one relevant document in their top 10.

<!-- RESULTS -->

| Model | Task (test queries) | Published nDCG@10 | Local nDCG@10 [95% CI] | Queries with a relevant top-10 result |
|---|---|---:|---:|---:|
| Qwen/Qwen3-Embedding-0.6B | SciFact (300) | 69.72 | 69.99 [65.62, 74.23] | 254/300 |
| Qwen/Qwen3-Embedding-0.6B | NFCorpus (323) | 36.71 | 36.17 [32.64, 39.69] | 240/323 |
| Qwen/Qwen3-Embedding-0.6B | ArguAna (1406) | 70.97 | 69.15 [67.52, 70.82] | 1320/1406 |
| Qwen/Qwen3-Embedding-4B | SciFact (300) | 78.33 | Not run | 0 evaluated |
| Qwen/Qwen3-Embedding-4B | NFCorpus (323) | 41.10 | Not run | 0 evaluated |
| Qwen/Qwen3-Embedding-4B | ArguAna (1406) | 75.64 | Not run | 0 evaluated |
| Qwen/Qwen3-Embedding-8B | SciFact (300) | 78.46 | Not run | 0 evaluated |
| Qwen/Qwen3-Embedding-8B | NFCorpus (323) | 41.45 | Not run | 0 evaluated |
| Qwen/Qwen3-Embedding-8B | ArguAna (1406) | 76.85 | Not run | 0 evaluated |
| BAAI/bge-small-en-v1.5 | SciFact (300) | 71.27 | 71.41 [67.02, 75.62] | 255/300 |
| BAAI/bge-small-en-v1.5 | NFCorpus (323) | 34.26 | 34.27 [30.77, 37.81] | 224/323 |
| BAAI/bge-small-en-v1.5 | ArguAna (1406) | 60.35 | 60.43 [58.54, 62.28] | 1208/1406 |
| BAAI/bge-m3 | SciFact (300) | 64.37 | 64.55 [59.89, 68.94] | 239/300 |
| BAAI/bge-m3 | NFCorpus (323) | 31.41 | 31.53 [28.21, 34.92] | 221/323 |
| BAAI/bge-m3 | ArguAna (1406) | 54.04 | 54.05 [52.23, 55.89] | 1155/1406 |
| google/embeddinggemma-2 | SciFact (300) | Not available | 85.32 [81.82, 88.62] | 281/300 |
| google/embeddinggemma-2 | NFCorpus (323) | Not available | 36.85 [33.45, 40.33] | 243/323 |
| google/embeddinggemma-2 | ArguAna (1406) | 59.83 | 60.01 [58.11, 61.86] | 1180/1406 |
| jinaai/jina-embeddings-v5-text-small | SciFact (300) | 76.53 | 76.36 [72.45, 80.20] | 272/300 |
| jinaai/jina-embeddings-v5-text-small | NFCorpus (323) | 39.81 | 39.82 [36.30, 43.38] | 246/323 |
| jinaai/jina-embeddings-v5-text-small | ArguAna (1406) | 65.07 | 64.75 [63.05, 66.43] | 1295/1406 |
| microsoft/harrier-oss-v1-270m | SciFact (300) | 75.40 | 75.30 [71.21, 79.29] | 265/300 |
| microsoft/harrier-oss-v1-270m | NFCorpus (323) | 36.15 | 36.01 [32.49, 39.54] | 242/323 |
| microsoft/harrier-oss-v1-270m | ArguAna (1406) | 63.63 | 64.23 [62.44, 65.96] | 1268/1406 |
| microsoft/harrier-oss-v1-0.6b | SciFact (300) | 76.26 | 75.95 [71.99, 79.82] | 267/300 |
| microsoft/harrier-oss-v1-0.6b | NFCorpus (323) | 37.23 | 37.08 [33.55, 40.62] | 240/323 |
| microsoft/harrier-oss-v1-0.6b | ArguAna (1406) | 64.99 | 65.20 [63.49, 66.92] | 1290/1406 |
| microsoft/harrier-oss-v1-27b | SciFact (300) | Not available | Not run | 0 evaluated |
| microsoft/harrier-oss-v1-27b | NFCorpus (323) | Not available | Not run | 0 evaluated |
| microsoft/harrier-oss-v1-27b | ArguAna (1406) | 67.76 | Not run | 0 evaluated |
| Qwen/Qwen3-VL-Embedding-2B | SciFact (300) | Not available | 74.78 [70.75, 78.70] | 265/300 |
| Qwen/Qwen3-VL-Embedding-2B | NFCorpus (323) | Not available | 37.34 [33.76, 41.01] | 244/323 |
| Qwen/Qwen3-VL-Embedding-2B | ArguAna (1406) | Not available | 58.64 [56.89, 60.36] | 1239/1406 |
| Qwen/Qwen3-VL-Embedding-8B | SciFact (300) | Not available | Not run | 0 evaluated |
| Qwen/Qwen3-VL-Embedding-8B | NFCorpus (323) | Not available | Not run | 0 evaluated |
| Qwen/Qwen3-VL-Embedding-8B | ArguAna (1406) | Not available | Not run | 0 evaluated |

### EmbeddingGemma dimensions on the same retrieval subset

| Dimensions | SciFact (N=300) | NFCorpus (N=323) | ArguAna (N=1,406) | Three-task mean | Change vs. 768 [paired 95% CI] |
|---:|---:|---:|---:|---:|---:|
| 768 | 85.32 | 36.85 | 60.01 | 60.73 | Reference |
| 256 | 82.19 | 35.02 | 57.89 | 58.37 | -2.36 [-2.97, -1.78] |
| 128 | 80.89 | 30.39 | 51.16 | 54.15 | -6.58 [-7.54, -5.66] |

Changes are paired within tasks and macro-averaged across tasks; the card's full English MTEB scores are separate figures in REPORT.md.

<!-- /RESULTS -->

## Limits and evidence

The published and local dataset revisions and MTEB releases often differ, even when the model revision matches. [comparison.json](results/comparison.json) preserves those historical versions. The 512-token cap, bfloat16 arithmetic, newer libraries, and historical instruction implementation may also change rankings. The MTEB registry lists SciFact and NFCorpus among Harrier training datasets; this run does not audit training/test overlap or establish zero-shot performance. The disclosure check is recorded in [training_overlap.json](results/training_overlap.json); an empty listed intersection is not proof of absent overlap. No setting was tuned toward a published number. Scores on three English retrieval tasks cannot verify multilingual coverage, overall benchmark means, historical leaderboard ranks, or a model card's claimed instruction gain without an ablation.

Large variants that exceed the available unquantized GPU/host memory are explicitly untested in [scope.json](results/scope.json); CPU offload or quantized replacements are not silently substituted. This leaves part of the requested model coverage unresolved.

For each evaluated model and task, `results/local/<model>/<task>.jsonl.gz` keeps every query ID, full relevance labels, top-10 document scores, per-query nDCG, and a hit indicator. The neighboring JSON records counts, confidence intervals, exact revisions, and elapsed time; `config.json` records model settings. [verification.json](results/verification.json) records independent score checks and output hashes. [sources.json](results/sources.json) records fetched primary-source checksums. The first pre-model snapshot is retained in an unpublished raw log; before/after evidence for the final clean-command validation lives in an unpublished raw log and an unpublished raw log. The cold-start command test is recorded in [command-proof.json](results/command-proof.json), and the overwrite guard in [guard-proof.json](results/guard-proof.json). Cleanup status is reported in REPORT.md.

# Editorial report: MTEB/MMTEB

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

Status: partial reproduction. The evaluated models use local open weights and the official MTEB scorer, with full test splits on three English retrieval tasks. The full multilingual or English benchmark aggregates in the chapters were not reproduced, and larger model coverage remains incomplete.

## Source claims and replacements

Original wording below comes from the chapter HTML; exact source citations and chapter hashes are in `claims.json`. Each suggested replacement is at most two sentences. Local task means give equal weight to SciFact, NFCorpus, and ArguAna, not to individual queries and not to the full MTEB suite. Chapter 05 has no MTEB/MMTEB score; its toy-corpus recall and MRR are outside this benchmark. Chapter 04 MMEB-V2 and ViDoRe figures are different benchmarks and are outside this run.

### 03-text-embeddings.html: Qwen3-Embedding

Original: Qwen3-Embedding 0.6B, 4B, 8B 64.33, 69.45, 70.58 MTEB multilingual. The 8B was No. 1 in the 5 June 2025 snapshot.

Source: [source citation](https://huggingface.co/Qwen/Qwen3-Embedding-8B)

Corresponding local evidence: SciFact 69.99 (N=300), NFCorpus 36.17 (N=323), ArguAna 69.15 (N=1406); 4B and 8B untested.

**Suggested replacement:** The model card reports multilingual MTEB scores of 64.33, 69.45, and 70.58 for the 0.6B, 4B, and 8B variants. Our 0.6B model averaged 58.44 nDCG@10 across three English retrieval tasks, which cannot verify those full-suite averages or the historical number-one rank.

### 03-text-embeddings.html: jina

Original: jina v5 text small 71.7 and 67.7 MTEB English v2 and MMTEB.

Source: [source citation](https://huggingface.co/jinaai/jina-embeddings-v5-text-small)

Corresponding local evidence: SciFact 76.36 (N=300), NFCorpus 39.82 (N=323), ArguAna 64.75 (N=1406)

**Suggested replacement:** Jina reports 71.7 on English MTEB v2 and 67.7 on MMTEB for its v5 text small model. Our three English retrieval tasks averaged 60.31 nDCG@10, a different task set that cannot verify either aggregate.

### 03-text-embeddings.html: Harrier

Original: Harrier 270m, 0.6b, 27b 66.5, 69.0, 74.3 MTEB v2 multilingual. The 27B is too large for CPU.

Source: [source citation](https://huggingface.co/microsoft/harrier-oss-v1-270m)

Corresponding local evidence: 270M: SciFact 75.30 (N=300), NFCorpus 36.01 (N=323), ArguAna 64.23 (N=1406); 0.6B: SciFact 75.95 (N=300), NFCorpus 37.08 (N=323), ArguAna 65.20 (N=1406); 27B untested.

**Suggested replacement:** Microsoft reports multilingual MTEB v2 scores of 66.5, 69.0, and 74.3 for Harrier 270M, 0.6B, and 27B. Our three English retrieval tasks averaged 58.51 and 59.41 nDCG@10 for the two smaller models; the 27B model was not run.

### 03-text-embeddings.html: EmbeddingGemma

Original: EmbeddingGemma 2 61.36 MTEB multilingual v2 at 768 dimensions.

Source: [source citation](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2)

Corresponding local evidence: SciFact 85.32 (N=300), NFCorpus 36.85 (N=323), ArguAna 60.01 (N=1406)

**Suggested replacement:** The EmbeddingGemma 2 card reports 61.36 on multilingual MTEB v2 at 768 dimensions. Our text-only run averaged 60.73 nDCG@10 on three English retrieval tasks, which cannot verify that multilingual mean.

### 03-text-embeddings.html: BGE-M3

Original: BGE-M3 59.56 MTEB multilingual, from a secondary guide.

Source: [source citation](https://superlinked.com/blog/qwen3-embedding-reranker-guide)

Corresponding local evidence: SciFact 64.55 (N=300), NFCorpus 31.53 (N=323), ArguAna 54.05 (N=1406)

**Suggested replacement:** The cited secondary guide reports 59.56 on multilingual MTEB for BGE-M3. Our dense-vector run averaged 50.04 nDCG@10 on three English retrieval tasks, so it does not reproduce that multilingual score.

### 03-text-embeddings.html: bge-small-en-v1.5

Original: bge-small-en-v1.5 62.17 Mean of the English MTEB tasks in its card.

Source: [source citation](https://huggingface.co/BAAI/bge-small-en-v1.5)

Corresponding local evidence: SciFact 71.41 (N=300), NFCorpus 34.27 (N=323), ArguAna 60.43 (N=1406)

**Suggested replacement:** The bge-small-en-v1.5 card reports a 62.17 mean across its English MTEB tasks. Our three-task English retrieval mean was 55.37 nDCG@10, with task scores reported separately because the aggregates cover different tasks.

### 03-text-embeddings.html: all-MiniLM-L6-v2

Original: all-MiniLM-L6-v2 None Its card gives no score. A small baseline.

Corresponding local evidence: No printed benchmark score and no local run in this reproduction.

**Suggested replacement:** The MiniLM card is used here to describe a small baseline, without a cited MTEB score.

### 03-text-embeddings.html: A

Original: A Matryoshka model is trained so that the first k numbers of its vector work as an embedding by themselves. You can store 256 numbers of a 1024-number vector and give up a little quality. Jina v5 lists every size from 32 to 1024 as supported. The EmbeddingGemma 2 card reports its MTEB English score falling from 68.46 at 768 dimensions to 67.78 at 256, a loss of 0.68 points for a vector one third the size, and to 65.68 at 128.

Source: [source citation](https://huggingface.co/jinaai/jina-embeddings-v5-text-small), [source citation](https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2)

Corresponding local evidence: Three-task retrieval means at 768, 256, and 128 dimensions: 60.73, 58.37, 54.15. At 256 dimensions the paired three-task change is -2.36 points, with a 95% interval [-2.97, -1.78]. At 128 dimensions the paired three-task change is -6.58 points, with a 95% interval [-7.54, -5.66].

**Suggested replacement:** The EmbeddingGemma 2 card reports English MTEB scores of 68.46, 67.78, and 65.68 at 768, 256, and 128 dimensions, including a 0.68-point drop from 768 to 256. Our three English retrieval tasks averaged 60.73, 58.37, and 54.15 nDCG@10 at those dimensions; these task means cannot verify the full-suite loss.

### 03-text-embeddings.html: Qwen3-Embedding

Original: Qwen3-Embedding expects a task instruction on the query side. Its card says instructions typically add 1 to 5 points and recommends writing them in English.

Source: [source citation](https://huggingface.co/Qwen/Qwen3-Embedding-8B)

Corresponding local evidence: No instruction/no-instruction ablation was run; all runs used the official instructed wrapper.

**Suggested replacement:** The Qwen3 model card reports that query instructions typically add 1 to 5 points. Our evaluation used the official task instructions and did not measure that gain.

### 04-multimodal-embeddings.html: 67.88

Original: 67.88 vs 70.58 Text-only MMTEB task mean: Qwen3-VL-Embedding-8B vs Qwen3-Embedding-8B, a gap of 2.70. At 2B it is 63.87 against 64.33 for a 0.6B text model. Vendor measurement

Source: [source citation](https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B/blob/9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda/README.md)

Corresponding local evidence: VL 2B: SciFact 74.78 (N=300), NFCorpus 37.34 (N=323), ArguAna 58.64 (N=1406); text 0.6B: SciFact 69.99 (N=300), NFCorpus 36.17 (N=323), ArguAna 69.15 (N=1406); both 8B models untested.

**Suggested replacement:** Qwen reports text-only MMTEB means of 67.88 versus 70.58 for the two 8B models, a 2.70-point gap, and 63.87 versus 64.33 for the VL 2B and text 0.6B models. Our three-task English retrieval means were 56.92 for VL 2B and 58.44 for text 0.6B, which cannot verify the multilingual means.

## Per-task results

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


## Differences and interpretation

The local run uses MTEB 2.27.20 and the dataset revisions in README.md, unquantized bfloat16 embeddings, exact cosine search, official model-specific task wrappers, and a common 512-token cap. The published JSON files identify their own MTEB and dataset versions in `results/comparison.json`; several differ from the local versions. The Jina revision is explicitly set to the revision with published English results rather than the newer registry default. There is no generated output, temperature setting, or LLM judge. GPU sharing affects timing, and no speed claim is made.

The results demonstrate retrieval behavior on these test sets. They cannot support or contradict the full-suite aggregate claims, multilingual coverage, or historical leaderboard ranks. Differences against per-task published scores are not isolated effects of model quality, given the input cap, arithmetic, instruction implementation, and dataset/software revisions. Missing published task records are availability limits at the pinned results commit, not zero scores. The bootstrap intervals describe test-query variability rather than historical reproducibility or a paired significance test. The registry lists SciFact and NFCorpus among Harrier training datasets, so this run does not establish zero-shot performance; training/test overlap was not audited. See results/training_overlap.json.

## Coverage and failures

- Qwen/Qwen3-Embedding-4B: About 8 GB of unquantized bfloat16 weights exceeds free GPU memory; a CPU/offload run over all three full corpora was not undertaken within the three-hour shared-host budget. No quantized replacement was substituted.
- Qwen/Qwen3-Embedding-8B: About 16 GB of bfloat16 weights exceeds available GPU memory and initial available host memory.
- microsoft/harrier-oss-v1-27b: About 54 GB of bfloat16 weights exceeds physical host and GPU memory.
- Qwen/Qwen3-VL-Embedding-8B: About 16 GB of bfloat16 weights exceeds available GPU memory and initial available host memory.

NFCorpus is publicly downloadable, but its dataset license is unspecified in the MTEB task metadata and no dataset license was established from the project page. No website theme license has been substituted for a data license.

Process failures and diagnostic tails: `results/suite.json`, `results/suite-extra.json`, and `results/suite-jina.json`. Early setup correction: the generic SentenceTransformer wrapper does not accept `max_seq_length` in its constructor; the harness sets the loaded model length instead. That failed setup produced no retained score. The raw result download initially searched the newer Jina revision and found no English task files; the published-revision manifest fixes this explicitly. Jina initially failed because its historical custom module and sentence-transformers 6.3.0 both supplied cache_dir; compat.py removes duplicate cache arguments and routes nested weight, adapter, and tokenizer loads to a complete local snapshot of the published revision, without changing forward computation, pooling, adapter selection, or prompts. A first retry was stopped before its first task completed after discovering that the historical nested loaders ignore revision; its incomplete outputs were removed. Gemma initially failed the official dependency check for audio/video packages even with text towers only; the required packages were installed in the isolated environment and pinned. Initial failed attempts produced no scores and remain recorded in suite.json; retry outcomes are in suite-extra.json and suite-jina.json.

## Raw evidence

- `claims.json`: chapter wording, figure inventory, citation URLs, chapter hashes.
- `published.json` and `results/published/*.json`: pinned leaderboard record paths and original task outputs.
- `results/local/<model>/<task>.jsonl.gz`: per-query IDs, relevance labels, ranked document scores, nDCG@10 and hit flags.
- Neighboring `<task>.json` and `config.json`: sample/corpus counts, confidence intervals, settings, model and data revisions.
- `results/comparison.json` and `results/verification.json`: matched source/local versions and independently checked scores and hashes.
- `results/sources.json`: primary-source availability and content hashes.

## EmbeddingGemma dimension check

| Dimensions | SciFact (N=300) | NFCorpus (N=323) | ArguAna (N=1,406) | Three-task mean | Change vs. 768 [paired 95% CI] |
|---:|---:|---:|---:|---:|---:|
| 768 | 85.32 | 36.85 | 60.01 | 60.73 | Reference |
| 256 | 82.19 | 35.02 | 57.89 | 58.37 | -2.36 [-2.97, -1.78] |
| 128 | 80.89 | 30.39 | 51.16 | 54.15 | -6.58 [-7.54, -5.66] |


Changes are paired by query and use equal weighting across the three tasks. Their 95% intervals use 10,000 query bootstrap samples within each task, seed 20261121; these are retrieval-subset changes, separate from the full English MTEB changes reported by the card.

## Cleanup proof

The documented wrapper passed a fresh-environment BGE-small run with exit code 0, then independently verified all 30 retained outputs and removed its environment and caches. See `results/command-proof.json`; the existing-directory refusal is recorded in `results/guard-proof.json`.

Scratch directory removed: True. No model servers, tunnels, or containers were started. Model processes exited before cache removal; existing unrelated processes were left running. The first pre-model snapshot is in an unpublished raw log; before/after disk, process, GPU, and container listings for the final clean-command validation are in an unpublished raw log and an unpublished raw log. The task used this Linux machine only and created no Mac resources.

Final disk listing:

```text
Filesystem      Size  Used Avail Use% Mounted on
filesystem 915G  671G  198G  78% /
filesystem 915G  671G  198G  78% /
```

Final GPU listing:

```text
name, memory.total [MiB], memory.used [MiB]
NVIDIA GeForce RTX 3070 Ti, 8192 MiB, 838 MiB

```

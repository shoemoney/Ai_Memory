# Large embedding-model follow-up

This folder extends `../mteb/` without changing it. It retains the earlier eight small-model runs and the 2B visual run, then evaluates the remaining printed embedding models. `inventory.json` lists every model with a quality score in chapters 03, 04, and 18; `claims.json` preserves the source sentences and chapter hashes. Actual completed cells, hardware, precision, counts, and confidence intervals appear below and in `REPORT.md`. An unrun model has no local score.

## Reproduce

From this folder on the Linux client, with `uv`, SSH access to the assigned Apple M3 Ultra with 96 GB memory, and enough space for the largest checkpoint:

```bash
MODEL_SSH='<assigned model-host SSH target>' ./run.sh
```

The command performs a fresh run of the follow-up cells. The session deadline is fixed before loading models. A timing-only heuristic defers a remaining VL text task when the completed same-host 8B task duration, scaled by completed current-model wall times when available and a 15% contingency, exceeds the time left; Harrier starts with a stated 3.6 parameter-scale factor. Deferrals are recorded, and the runner advances to the visual models. This heuristic does not select on quality scores and never thins a retained cell. `./run.sh --resume` may be combined with `followup.py --visual-first` (run `followup.py --resume --visual-first` directly) to run the visual models before further text work; the second operator did so after the first deadline. `./run.sh --resume` preserves compatible completed cells and cached inference batches. Model serving and weight conversion run on the Mac; datasets, inference-input preparation, exact search, scoring, and bootstrap sampling run on the Linux client. The prior GPU run is retained evidence; the follow-up does not use the dev GPU.

The worker binds only localhost port 39740, reached through an SSH tunnel. Endpoints are settings defaulting to localhost. The initial visual GPU worker used port 39741 and was released. No existing model service is stopped, restarted, unloaded, or reconfigured.

Large client files live under `/data/scratch/membench/mteb-large/`, including `HF_HOME`, `UV_CACHE_DIR`, `PIP_CACHE_DIR`, environments, datasets, and embedding checkpoints. Before a large-write step the wrapper checks `df -h / /data` and pauses if the system filesystem has less than 20 GiB free. Model weights and isolated environments on the Mac live only in the task-owned temporary folder. Only the territory folder is retained after cleanup.

## Tasks and scoring

Text evaluation uses all 300 SciFact, 323 NFCorpus, and 1,406 ArguAna test queries, with the complete corpora of 5,183, 3,633, and 8,674 documents. It uses MTEB 2.27.20, the original model revisions and dataset revisions, a 512-token text cap, official task instructions, exact cosine search, and pytrec_eval nDCG@10. The model wrappers supply the exported instruction strings in `instructions.json`. Transport batches sort by character length for efficient padding and restore the original order before scoring. The new native text runs use batch size 32; the earlier small runs used their recorded batch sizes.

Visual evaluation uses every English HR test query (318) against every page (1,110) in `vidore/vidore_v3_hr_mteb_format`, revision `bc7d43d64815ed30f664168c8052106484aba7fd`, licensed CC BY 4.0. The qrels configuration also contains 8,655 judgment rows for IDs absent from the English query file; these are ignored. All 318 English queries retain judgments. Exact cosine rankings are scored at 5 and 10 with the primary ViDoRe evaluator's `pytrec_eval.RelevanceEvaluator` method. Source hashes and dataset columns/counts are in `results/sources.json` and `results/vidore-data.json`.

Intervals use 10,000 query-bootstrap samples, seed 20261121. They describe variability among these test queries. The same items are used across compared models. These three English text tasks cannot verify a complete multilingual MTEB mean; one ViDoRe V3 HR subset cannot verify MMEB-V2's 78-task mean or a ViDoRe-v2 multi-dataset mean. No LLM judge is used.

Dataset sources, pinned revisions, and licenses for the three text tasks are inherited from `../mteb/README.md` and recorded in each completed summary. NFCorpus's data license is unspecified in that metadata. No dataset text, images, or model weights are committed.

## Precision and hardware

The replacement model host is an Apple M3 Ultra with 96 GB unified memory, shared with other benchmark servers. Full-precision 4B trials crossed the reserve, so the measured 4B configuration uses native MLX affine 8-bit weights, group size 64. The larger Qwen models use MLX affine 4-bit weights; the Qwen VL vision tower stays in bfloat16. Conversion uses the original pinned checkpoints, on the CPU, one matrix at a time, without calibration data.

Harrier uses its native Gemma3 text backbone through MLX-LM, with 4-bit affine linear/embedding modules, original causal local/full attention configuration, last-nonpadding-token pooling including the prompt, and L2 normalization. It does not calculate a language-model output head. Nomic uses its official ColPali fork and processor, with symmetric round-to-nearest 4-bit linear matrices of at least one million weights; embeddings, normalization, biases, and smaller matrices retain their original precision. Active LoRA deltas are merged per matrix before quantization. Both quantizers use group size 64. Compute remains bfloat16. The Nomic worker loads its base and LoRA adapter at separate pinned revisions. It checks the fork’s 3D vision attention against an independent CPU product and, only if needed by the installed MPS kernel, promotes it to an equivalent 4D batch; the execution record states which path ran. See the [upstream issue](https://github.com/huggingface/transformers/issues/36413).

Quantization and native backend changes are stated differences from the published full-precision results. They are not treated as exact reproductions of those configurations. The earlier small text models and Qwen VL 2B visual subset ran on an 8 GB NVIDIA GPU in bfloat16. Quality results can be compared across hardware under the recorded settings; timings cannot. Timings from resumed/cache-only invocations are not end-to-end inference measurements.

`results/backend-equivalence.json` checks 32 paired 4B embeddings from the official PyTorch wrapper and native MLX at full precision, using identical cached requests and no labels or quality scores. The minimum embedding cosine was 0.99977. This validates that adapter before quantization; it is separate from the retrieval-quality tests. The VL adapter passed a separate six-embedding synthetic padding/order/repeated-request check, minimum cosine 0.99858, in `results/vl-batch-invariance.json`; that check does not establish full-precision backend equivalence. The VL worker omits the unused language-model output head absent from the embedding checkpoint, strictly loads the backbone, and resets position state between independent requests. The quantizer unit checks compare independent dense matrix products and exercise packing and padding. Exact software pins are in `results/client-versions.txt`, `results/mac-versions.txt`, `results/mlx-versions.txt`, `results/lm-versions.txt`, and `results/nomic-versions.txt`; `results/mlx-text-versions.txt` preserves the earlier text-only environment before the VL dependency was added.

## Memory, resumption, and evidence

Admission requires at least 40% system-wide free memory and normal kernel pressure immediately before loading. The loaded worker must leave more than 30% free. A five-second guard stops the task's worker at warning/critical kernel pressure or at 30% free, including during conversion. Model-specific scheduling floors include working-memory headroom. If capacity is insufficient, the scheduler waits and checks again every ten minutes. It serves one embedding model at a time and respects the wall-clock deadline.

Every encoded batch is checkpointed under a hash of model/revision, execution/quantization settings, task, role, inputs, and preprocessing. Every visual image/query has its own checkpoint. A restart reuses compatible inference and completed task files. Raw results contain query IDs, relevance labels, ranked document scores, per-query metrics, and timings. `verify.py` and `verify_visual.py` independently recompute the retained metrics; the visual verifier also recomputes both confidence intervals. `verify_inherited.py` checks and rescores the 30 earlier outputs without editing them.

`results/followup-events.jsonl` records admission checks, failures, retries, configurations, and completions. Measured worker source revisions are archived under `results/source-snapshots/` when a later metadata-loading fix changes the source hash; each result records its actual worker hash. VL conversion retains the pinned chat template and processor metadata. Historical failures and cleanup are retained separately from the replacement-host run. Cleanup proof records removal of task workers, tunnels, model/data caches, and temporary folders, plus before/after disk and process listings. Shared package-manager caches are not pruned. `results/retrieval-results.png` and `.svg` plot the retained cells; `plot.py` uses the isolated `results/plot-versions.txt` environment. `REPORT.md` gives an editor-facing account for each printed score, suggested replacements, limits, and unresolved cells.

<!-- GENERATED RESULTS -->
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


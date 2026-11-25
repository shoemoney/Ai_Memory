# Editor report: parameter and latent-memory reruns

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

The local GSM8K checkpoint improves its prompted base on a fixed 150-item sample. The TriviaQA result is a closed-book diagnostic, and the reduced Cartridges experiment loses substantial answer quality while reducing KV storage. The published maximum gains and matched-quality cross-benchmark memory figure remain authors' claims.

All scored runs used Qwen2.5-1.5B-Instruct, bfloat16, PyTorch SDPA and an 8 GB NVIDIA GPU. Model and dataset revisions, licenses and the fixed sample indices are in `results/sources.json`. Rates use 95% Wilson intervals; paired changes use 20,000 bootstrap resamples, seed 42. There was no LLM judge.

## G19 / E41: chapter 16, MemGen

The sentence at `build/chapters/16-frontier.html:154` reports gains of up to 38.22% over two external-memory systems and up to 13.44% over a GRPO-trained baseline on eight benchmarks. The primary paper abstract reports these numbers. The paper's Qwen2.5-1.5B table also reports GSM8K vanilla 39.51%, CoT 56.79%, GRPO 68.10% and MemGen GRPO 73.39%; TriviaQA vanilla 32.10%, CoT 28.67% and MemGen SFT 65.02%. These are authors' results.

| Local cell | Published reference | Base, 95% interval | Released Weaver, 95% interval | Paired change, 95% interval |
|---|---|---|---|---|
| GSM8K, 150 test items | CoT 56.79%; MemGen GRPO 73.39% | 87/150, 58.0% [50.0, 65.6] | 102/150, 68.0% [60.2, 74.9] | +10.0 points [1.3, 18.7] |
| TriviaQA, 150 validation items | Vanilla 32.10%; MemGen SFT 65.02%, with search | 43/150, 28.7% [22.0, 36.4] | 52/150, 34.7% [27.5, 42.6] | +6.0 points [-0.7, 13.3] |

GSM8K uses the authors' current prompt and first-boxed-answer scorer, the released Qwen Weaver-GRPO checkpoint, greedy decoding, four-item batches and a 1024-token cap. Both arms receive identical items and generation settings, including repetition penalty 1.0. One output per arm reached the cap and remains included. The loader verified all 112 LoRA tensors against the released checkpoint and all 339 shared base tensor storages. The inactive trigger retains its constant decision without allocating its unused backbone. Immutable base storage is shared between separate reader and Weaver model objects. This is a partial released-checkpoint inference rerun, with SDPA replacing FlashAttention 2. The current release documents prompt-format changes since earlier evaluation.

The positive GSM8K paired interval supports this checkpoint's benefit on this sample. It cannot validate the quoted 38.22% and 13.44% maxima: ExpeL, AWM and a trained GRPO baseline were not run, the remaining benchmarks were not evaluated, and reinforcement learning was not reproduced. The eight-benchmark comparison **cannot be reproduced locally within this run and budget** using only these released small checkpoints.

TriviaQA is explicitly a **closed-book diagnostic**. It uses the released Qwen Weaver-SFT checkpoint and the same questions for both arms, but disables search, replaces the search prompt with an explicit no-search instruction and makes one response instead of a five-turn search interaction. It preserves the upstream case-insensitive alias-substring rule inside an answer tag. The base produced valid answer tags on 102/150 items and Weaver on 145/150; that formatting difference limits interpreting the six-point difference as a knowledge gain. The paired interval includes zero. One base output reached the cap; none did for Weaver.

The full published TriviaQA search evaluation **cannot be reproduced locally with the documented setup**: its Search-R1 E5 Flat index parts total 64,559,075,373 bytes, before the corpus, retriever and generator. The index exceeds the host's 28 GiB physical RAM and the shared 8 GB GPU. No failed-search observations or substitute corpus are silently used. This diagnostic neither supports nor contradicts the paper's search result.

Suggested replacement, two sentences:

> MemGen's authors report gains of up to 38.22% over external-memory systems and 13.44% over a GRPO baseline; this book does not reproduce those eight-benchmark comparisons. On 150 GSM8K test items, this book measured 58.0% for the prompted base model and 68.0% with a released Weaver checkpoint, a paired gain of 10.0 percentage points (95% interval, 1.3 to 18.7).

Evidence: `memgen/run.py`; `results/gsm8k.jsonl`; `results/triviaqa.jsonl`; `results/loading-proof.jsonl`; `results/sources.json`; `results/summary.json`; `results/final-verification.json`.

## G18 / E40 and E01: chapters 16 and 00, Cartridges

The sentence at `build/chapters/16-frontier.html:147` says the authors match in-context quality on long-context benchmarks with 38.6 times less memory. Paper v3 reports 38.6x less KV memory at matched quality, averaged across benchmarks. The local experiment below did not match quality.

| Measure | Published | Local reduced result |
|---|---|---|
| Answer quality | Matched in-context quality across benchmarks | Context 16/20, 80.0% [58.4, 91.9]; cache 6/20, 30.0% [14.5, 51.9] |
| Paired accuracy change | No directly comparable one-patient figure | -50.0 percentage points [-70.0, -30.0] |
| Mean post-prefill query KV | 38.6x reduction at matched quality | 338.60 MiB context; 5.75 MiB cache; ratio of means 58.9x |
| Individual query KV ratios | Cross-benchmark average | Mean of 20 paired ratios 62.4x; range 31.7x to 80.6x |
| Corpus-only token ratio | Different aggregation and corpus sizes | 12,234 document tokens / 64 cache tokens = 191.2x |

The local KV reduction comes with a clear loss of accuracy in this case. It does not reproduce the paper's 38.6x matched-quality claim, and it does not contradict the full paper because the reductions are substantial. Intervals are conditional on this one patient's questions; they do not measure variation across new corpora. Twenty questions also do not meet the desired roughly +/-8-point rate precision.

Every setup reduction or change:

- Qwen2.5-1.5B-Instruct replaces the paper's backbones and is both synthesizer and frozen reader.
- One patient's two complete documents, 12,234 anonymized tokens, replace the paper's ten-patient LongHealth panel of about 100k tokens and the other benchmark corpora.
- All 20 corresponding questions replace a multi-patient evaluation. No question or gold answer is provided to self-study generation or training.
- Thirty-two locally generated one-turn conversations from deterministic 768-token chunks replace the much larger self-study datasets. Seed focuses are factual diagnosis and medication questions.
- A 64-token cache initialized from fixed neutral text replaces the paper's cache-size sweep and random-text initialization.
- Sixty-four AdamW updates, batch one, learning rate 0.02, two passes, gradient clipping at 1 and up to 97 answer tokens replace the full training schedule. Only K and V are optimized; reader weights stay frozen.
- The teacher target is its normalized top-20 distribution; the student loss uses full-vocabulary log probabilities at those indices. This sparse KL normalization is explicitly a reduction.
- Direct Transformers PyTorch replaces the authors' custom Flex attention/training and serving stack. Full-context prefill uses 256-token chunks with no text truncation; a verified common prefix is reused across queries.
- Constrained A-E next-token choice with exact option scoring replaces generated free-text answers, fuzzy option matching and the reference scorer's option-A fallback when tags are missing. No LLM judge is used.
- Names are anonymized consistently in both training and evaluation. Memory is actual query KV tensor bytes, excluding base weights, optimizer state, allocator reservation and retained prefix-reuse copies. Raw allocator peaks are not a total-serving-memory comparison. No throughput claim is made.

The 64-token, 32-conversation and 64-step settings were fixed before held-out evaluation. The failed matched-quality result was retained without tuning toward the published figure. Training changed the cache by L2 norm 161.57 while the reader's parameters stayed frozen. All 64 steps had finite loss and nonzero gradients.

The LongHealth repository has an Apache-2.0 license. Its README requests that benchmark examples not be publicly shared to reduce pretraining contamination. Original documents and questions are fetched by script; synthetic training text is kept in temporary scratch and removed during cleanup. Only hashes and timings of the 32 conversations, plus scored A-E evaluation outputs, remain in the deliverable.

The inventory also attributes this claim to chapter 00 / E01. The current `build/chapters/00-front.html` contains no Cartridges or 38.6 sentence. This mismatch is recorded in `results/source-verification.json`; the editor should reconcile the inventory. No chapter or review file was edited.

Suggested replacement, two sentences:

> The Cartridges authors report matching in-context quality with 38.6 times less KV memory across their benchmarks, which this book does not reproduce. On 20 questions about one patient's documents, this book's smaller experiment reduced mean query KV storage from 338.6 MiB to 5.75 MiB, while accuracy fell from 80% with full context to 30% with the trained cache.

Evidence: `cartridges/run.py`; `results/cartridges/synthetic-index.jsonl`; `results/cartridges/training.jsonl`; `results/cartridges/mechanism.json`; `results/cartridges/answers.jsonl`; `results/summary.json`; `results/final-verification.json`; `results/comparison.svg`.

## Execution, failures and cleanup

Primary-source claims, source hashes, dataset revisions and all sample indices are preserved. `verify.py` checked all 640 scored outputs against primary labels, both 150-item paired cohorts, all 20 Cartridges pairs, model-derived KV byte counts, 32 conversations and 64 training steps. `results/verification.json` also records positive and negative scorer controls and a failed-save checkpoint test that preserved the prior valid state. Version pins are in `requirements-lock.txt` and the actual runtime is in `results/runtime.json`.

GPU admission took 80 minutes. The three scored workers independently observed at least 6144 MiB free before loading. No other process was stopped or reconfigured. No server, tunnel, container, image or volume was created. No commit was made.

What did not work: initial preparation ended with signal 15 and completed on retry; an early loader assertion omitted the tied output-head key; a pre-score review corrected PEFT's float32 LoRA default to the authors' bfloat16 evaluation dtype. Single-item CPU decoding paged heavily until anonymous weight copies were used. Two full-document CPU smoke attempts were killed by global OOM, one at about 3.2 GiB anonymous RSS. The bounded 768-token CPU execution smoke passed. A later memory guard deferred or safely stopped only this task's CPU worker before swap exhaustion. Four-item CPU batching passed and matched the checked single-item output; the eight-item test was resource-deferred and is not a numeric result. All headline figures above come from complete CUDA runs with full declared inputs.

Cleanup confirmed for both assigned scratch roots and all task-specific models, datasets, virtual environment, private caches and temporary training text. Local bytecode caches were also removed. an unpublished raw log contains removal checks, an empty active-worker list, and `df -h` plus process listings before and after. Models, datasets, task virtual environment, private caches, temporary training text and both scratch roots are removed. The initial installation created 32 tracked wheel entries in the shared UV tool cache; this shared cache is preserved. [UV documents direct cache mutation as unsafe](https://docs.astral.sh/uv/concepts/cache/#cache-safety), and package-wide cleaning would also clear preexisting cached versions. The tracked entries are listed in `results/tool-cache-owned.json`.

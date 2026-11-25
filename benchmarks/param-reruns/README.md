# Released latent memory and reduced trained KV cache reruns

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

The released GSM8K Weaver improved accuracy by 10.0 percentage points on 150 paired items. The reduced Cartridges cache compressed KV storage and lost 50.0 points of answer accuracy. This directory evaluates released MemGen checkpoint inference and a reduced Cartridges self-study experiment using a local open-weight model. The eight-benchmark MemGen maximum gains and the Cartridges cross-benchmark matched-quality memory figure require separate conclusions from these small local cells.

## Run

From the repository root:

```bash
bash benchmarks/param-reruns/run.sh
```

Preinstalled Python 3.12.16 and `uv` are required. Direct dependencies are in `requirements.txt`; `requirements-lock.txt` pins the complete resolved environment. The launcher disables global Python downloads and installs into its owned virtual environment. Weights, upstream code and datasets are fetched into owned scratch, never copied into this repository. `results/sources.json` pins source commits, model revisions, dataset revisions, splits, sample indices and licenses. Its existing revisions are reused on rerun. Model and dataset downloads need network access; generation, training and scoring are local.

The harness checkpoints each completed item, synthetic conversation and training step. A CPU memory guard releases only its own worker if shared RAM or swap becomes critical, recording the stop rather than inventing missing scores. Delete only the raw result cells and training scratch for a deliberately fresh rerun, retaining `results/sources.json` to preserve revisions. A resume must use the same settings and execution backend as the interrupted run. It preserves the original batch composition even when only some outputs need saving. GPU work requires at least 6144 MiB free before loading anything; another process is never stopped to obtain that space. CPU smoke tests run first; the Cartridges smoke uses a labeled 768-token excerpt, while the scored experiment uses every document token. The launcher rechecks admission before each scored cell, checking every 600 seconds within one ten-hour admission window, then uses CPU if admission remains unavailable. Override `PARAM_DEVICE=cpu` to explicitly select CPU without the GPU wait. `PARAM_SCRATCH` changes the owned scratch root.

## Methods

**MemGen GSM8K:** Qwen2.5-1.5B-Instruct with the authors' released GSM8K Weaver-GRPO checkpoint versus the identical base model without latent tokens. The sample is 150 seeded test items without replacement, seed 42. Both arms receive the same official prompt, use greedy generation in four-item batches (a final two-item batch) with a 1024-token cap, and use the upstream first-boxed-answer scorer. Batch runtimes are amortized across items for diagnostic timing; no latency claim is made. The custom loader uses the upstream Weaver, projections, generation implementation and checkpoint remapping. It verifies all 112 loaded LoRA tensors against the released checkpoint and all 339 shared base tensor storages. Every component is bfloat16, matching the authors' evaluation runner. Both arms use repetition penalty 1.0 and neutral generation defaults. Separate model objects share immutable base tensor storage, which is asserted for every base parameter. The inactive trigger's constant decision is preserved without allocating its unused backbone. Attention uses PyTorch SDPA instead of FlashAttention 2. This tests one released checkpoint, not reinforcement learning or eight benchmark gains against ExpeL, AWM or a GRPO baseline.

**MemGen TriviaQA:** the released Qwen2.5-1.5B-Instruct TriviaQA Weaver-SFT checkpoint versus the same base on 150 seeded validation items. This is a **closed-book diagnostic**, not the published retrieval evaluation. The prompt explicitly says search is unavailable; there are no fake search results or swallowed failed tool calls. Both arms receive identical prompts and use greedy 1024-token decoding. Scoring requires an `<answer>` tag and the upstream case-insensitive alias substring rule. The upstream five-turn search environment is not reproduced: its documented Search-R1 E5 Flat index totals 64,559,075,373 bytes before the corpus, retriever and generator. That index cannot be loaded faithfully into an 8 GB GPU or this 28 GiB host while honoring the shared-machine constraints. These diagnostic numbers cannot support or contradict the paper's search gain.

**Cartridges:** one complete document set, LongHealth `patient_01`, all 20 corresponding held-out questions, one 64-token trainable KV cache, Qwen2.5-1.5B-Instruct as both synthesizer and frozen reader. The local model generates 32 one-turn question/answer conversations from deterministic 768-token document chunks. It never sees evaluation questions or gold answers during training. Training uses 64 AdamW steps, batch size one, learning rate 0.02, gradient clipping at 1, and a context-distillation loss from the teacher's normalized top-20 logits on up to 97 answer tokens. The cache is initialized from 64 tokens of fixed neutral text. Both arms answer the same 20 questions using constrained greedy A-E next-token choice, with exact option scoring and no LLM judge.

Reductions from Cartridges: Qwen 1.5B replaces the paper's backbones; one patient's documents replace multi-patient and multi-benchmark corpora; 32 locally authored one-turn conversations replace the much larger self-study datasets; 64 cache positions replace the paper's cache sweep; one small fixed training schedule replaces full training; direct Transformers PyTorch replaces the authors' custom attention/serving stack; sparse top-20 KL uses renormalized top-20 probabilities; constrained multiple choice replaces the authors' generated free-text answer and fuzzy scorer (including its option-A fallback when tags are absent). Anonymized patient names are used consistently in both arms. No throughput result or equality-of-quality claim is inferred from 20 questions.

Full context uses 256-token prefill chunks without dropping any text; a verified shared document prefix is reused across questions. Memory accounting reports actual KV tensor bytes after question prefill for each paired item, plus a corpus-only token ratio. It excludes base weights, training optimizer memory, activations, allocator reservation and sharing/concurrency effects. It is not a total-process or peak-serving memory ratio. Raw CUDA allocator peaks include retained context-prefix reuse state and are not used as the memory comparison.

All headline rate intervals are 95% Wilson intervals. Paired accuracy differences use 20,000 paired bootstrap resamples, seed 42. Cartridges intervals are conditional on the one patient and do not measure variation across new corpora. The small Cartridges cell has wide intervals; it does not satisfy the desired +/-8 percentage point precision.

## Sources and licenses

- [MemGen paper](https://arxiv.org/abs/2509.24704), [official code](https://github.com/KANABOON1/MemGen), [released checkpoints](https://huggingface.co/Kana-s/MemGen). Checkpoints: Apache-2.0. Code is fetched, not redistributed.
- [Cartridges paper v3](https://arxiv.org/html/2506.06266v3), [official code](https://github.com/HazyResearch/cartridges), Apache-2.0.
- [GSM8K](https://huggingface.co/datasets/openai/gsm8k), MIT; [TriviaQA](https://huggingface.co/datasets/mandarjoshi/trivia_qa), dataset card license recorded in source manifest.
- [LongHealth primary repository](https://github.com/kbressem/LongHealth), Apache-2.0 repository license. Data are fetched at the recorded commit and not redistributed. The dataset README asks researchers to avoid publicly sharing examples. Generated self-study text is kept only in temporary scratch; the deliverable retains its hashes and timings in `results/cartridges/synthetic-index.jsonl`. Scored evaluation outputs are A-E letters.
- [Search-R1 documented retriever](https://github.com/PeterGriffinJin/Search-R1), [index metadata](https://huggingface.co/api/datasets/PeterJinGo/wiki-18-e5-index/tree/main).

Hardware: shared 8 GB NVIDIA GPU and 32-thread x86 CPU, 28 GiB RAM. Actual execution device is recorded per item.

## Results

All scored cells used Qwen2.5-1.5B-Instruct on an 8 GB NVIDIA GPU. Percentages below include 95% Wilson intervals; differences are percentage points with paired 95% bootstrap intervals.

| Cell | Authors' published result | Local result | Paired change |
|---|---|---|---|
| MemGen GSM8K, N=150 | Qwen CoT 56.79%; MemGen GRPO 73.39% | Base 58.0% [50.0, 65.6]; Weaver 68.0% [60.2, 74.9] | +10.0 [1.3, 18.7] |
| MemGen TriviaQA, N=150 | Vanilla 32.10%; MemGen SFT 65.02%, with search | Closed-book base 28.7% [22.0, 36.4]; Weaver 34.7% [27.5, 42.6] | +6.0 [-0.7, 13.3] |
| Cartridges LongHealth, N=20 | 38.6x less KV memory at matched quality, averaged across benchmarks | Full context 80.0% [58.4, 91.9]; cache 30.0% [14.5, 51.9] | -50.0 [-70.0, -30.0] |

The GSM8K cell supports a benefit for this released checkpoint on this sample. It does not compare with trained GRPO, ExpeL or AWM baselines and cannot reproduce the authors' maximum 38.22% and 13.44% gains across eight benchmarks. The TriviaQA interval includes zero; search and multi-turn interaction are absent. Its answer-tag compliance was 102/150 for the base and 145/150 for Weaver, a material protocol difference. GSM8K had one capped output per arm; TriviaQA had one for the base and none for Weaver. Capped outputs remain in the denominators.

For Cartridges, actual post-prefill query KV storage averaged **338.60 MiB with full context and 5.75 MiB with the cache**. The ratio of those means is **58.9x**. The mean of the 20 individual paired ratios is **62.4x**, ranging from 31.7x to 80.6x. Corpus-only token compression is 12,234/64 = 191.2x; it excludes the question and is a different quantity. These figures describe KV tensors, not total process memory. The reduced run failed to match answer quality, so it does not reproduce the paper's 38.6x matched-quality figure. The 64-token, 32-conversation, 64-step setting was fixed before the held-out evaluation.

`results/final-verification.json` confirms all 640 saved scores against primary labels, all paired cohorts, model-derived KV byte counts, 32 conversations and 64 nonzero-gradient training steps. `results/summary.json` is generated by `analyze.py`; the standalone figures are `results/comparison.svg` and `results/comparison.png`.

## Resource history and cleanup

GPU admission took 80 minutes. Each scored worker rechecked at least 6144 MiB free before loading. No other process was stopped or reconfigured. CPU preparation exposed severe paging and two global OOM kills; a later guard safely deferred or stopped only this task's CPU worker. The bounded CPU smoke uses 768 document tokens; all scored Cartridges answers used all 12,234 tokens.

Cleanup of both assigned scratch roots is confirmed in an unpublished raw log, with no active task worker remaining. Task-specific models, datasets, virtual environment, private caches, temporary training text and local bytecode caches were removed after verification. The initial installation also populated the shared UV tool cache. That shared cache is preserved because UV warns against direct mutation and its supported package cleanup would clear other cached versions. See [UV cache safety](https://docs.astral.sh/uv/concepts/cache/#cache-safety) and `results/tool-cache-owned.json` for the 32 tracked wheel entries. No server, tunnel, container, image or volume was created. No commit was made.

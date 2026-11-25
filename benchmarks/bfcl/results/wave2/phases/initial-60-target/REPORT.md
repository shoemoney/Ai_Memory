**Continuation is running under `/data/scratch/membench/bfcl` using retained checkpoints.** The operational status below is the interim migration snapshot. Authorized shared-disk pause credits are recorded in `results/wave2/pauses/`; final reporting will replace this status.

# BFCL-V4 wave-two editor report

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

Chapter `06-small-memory-models.html`, paragraph beginning “Tool-calling scores fall steeply below 4B,” and its Numbers row print model-card BFCL-V4 figures 25.3, 43.6, 50.3 and 66.1. Those are full vendor aggregates. The local results below are offline projections excluding live web search, not reproductions of the full aggregate. Earlier citation and primary-source inspection is preserved in `results/wave2/prior-REPORT.md`; no chapter was edited.

# BFCL-V4 wave-two continuation

The earlier pilot remains under `pilot/`. The earlier incomplete expanded run remains unchanged under `results/full/`; its README and editor report are preserved as `results/wave2/prior-README.md` and `prior-REPORT.md`. The new continuation reuses every completed question, prerequisite, request and memory snapshot from that run. Inference and scoring run on a 32-thread x86 CPU; the sole model server is an Apple M3 Ultra with 96 GB unified memory. No Linux GPU, hosted generation or LLM judge is used.

The data, official loader, native function-calling adapter, simulators and scorers come from `bfcl-eval==2026.3.23`, upstream commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`, Apache-2.0 (`LICENSE.upstream`). Model revisions and SHA-256 hashes are in `full_common.py`; models are Qwen3.5 0.8B, 2B, 4B and 9B, Q4_K_M. Runtime is llama.cpp build 12359, commit `b1b770d90`. `requirements.txt` pins Python dependencies. The CPU memory-vector encoder is `all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

## Reproduce or resume

```bash
RUN_NAME=wave2 MODEL_HOST=your-authorized-ssh-alias bash benchmarks/bfcl/run_full.sh --hours 14 --sample-per-category 60
```

The shipped `wave2` directory resumes its persisted deadline and reused checkpoints. Use a fresh run name for new inference; prepare the same checkpoint copy to reproduce this continuation. The command requires the pinned llama.cpp runtime already installed on the authorized serving machine and `uv` on the scoring machine. All added dependencies, downloads and caches stay in task scratch directories. Future launches put large local files and UV, pip, Hugging Face and managed Python caches under `/data/scratch/membench/bfcl`; the environment already active at the disk-coordination update stays in `/var/tmp/membench-bfcl` until cleanup. New environment creation checks `df -h / /data` and pauses below 20 GiB free on the system disk. Servers bind localhost:39730 and are reached only through SSH. A model loads only at normal kernel pressure and at least 40% system-wide free memory. Only the owned server is stopped at warning or critical pressure. Other services are untouched. Four slots are used at >=65% free, two at >=50%, otherwise one at >=40%, with 65,536 tokens per slot. `lsof -b` avoids blocking on unrelated network mounts.

## Sampling and interpretation

Full coverage was judged infeasible from the earlier run's observed throughput. The fixed target is the first min(60, population) IDs from each category's original seeded random permutation (seed 20261121), shared across all eight model/mode cells. Smaller categories use a census. Memory questions retain their complete ordered prerequisite chains and independently learned mode-specific snapshots. No cap, temperature, prompt or seed was tuned to accelerate this continuation: temperature 0, seed 20261121, 16,384 output tokens, 900-second request timeout, official native-FC adapter. The original expanded results are retained even outside the selected set. The fresh 14-hour task budget includes environment setup and cleanup; model allocations and infrastructure interruptions are retained in an unpublished raw log.

The headline below uses only selected IDs completed in **all eight cells**, so sizes and modes receive exactly the same cases. It never substitutes incomplete requests for incorrect answers. `selected-coverage.json` shows all selected completions before this common-case restriction. If the target is unfinished, the common-case projection is a censored diagnostic, not an unbiased estimate for the planned sample. All raw extra completions remain available.

Official offline leaf weights sum to 0.80: non-live 0.10, live 0.10, irrelevance 0.10, multi-turn 0.30 and memory 0.20. Their composition follows upstream helpers, including language averaging and population-weighted live categories. The projection divides the observed weighted contribution by represented weight. **Both live web-search categories are excluded (20% overall weight); this is not the full model-card aggregate.** Missing offline strata also reduce represented weight. `format_sensitivity` and `live_relevance` are non-scoring. Actual pinned populations govern selection.

Intervals are 95% paired bootstrap case-mix intervals (4,000 replicates), stratified by category; memory domains are cluster-resampled jointly across backends, then questions within domain. They are conditional on observed questions and learned snapshots. They do not account for absent domains, deadline selection, runtime or quantization differences, and can understate uncertainty for small strata. A category census is exact for this execution, while intervals describe sensitivity to case mix. Category rates have Wilson intervals in `analysis.json`.

Selected-target completion requirement satisfied: **False**. Operational status: `interrupted`. Cleanup verified: **True**.

| Model Q4_K_M | Card overall | Common paired N per mode | Offline off (95%) | Offline on (95%) | On minus off (95%) |
|---|---:|---:|---|---|---|
| 0.8B | 25.3 | 70 | 19.0% [15.7, 22.8] | 38.2% [26.2, 49.8] | +19.2 pp [+7.2, +30.5] |
| 2B | 43.6 | 70 | 45.9% [38.4, 53.6] | 50.0% [40.3, 60.1] | +4.1 pp [-2.5, +11.2] |
| 4B | 50.3 | 70 | 57.2% [45.3, 68.8] | 48.2% [38.8, 57.9] | -9.0 pp [-18.7, +0.7] |
| 9B | 66.1 | 70 | 52.7% [42.1, 63.1] | 76.4% [65.0, 87.5] | +23.7 pp [+11.4, +36.7] |

## Per-category common coverage and results

### 0.8B

Parser-failed memory prerequisites: 1. Parser-failed common scored items: 0.

Represented overall weight: 0.800000; missing weight: 0.200000.

| Category | Common N / target / population | Off correct | On correct | On minus off (95%) | Length stops off/on | Empty or malformed credits off/on |
|---|---:|---:|---:|---|---:|---:|
| simple_python | 3/60/400 | 0 | 2 | +66.7 pp [+0.0, +100.0] | 0/1 | 0/0 |
| simple_java | 3/60/100 | 1 | 1 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| simple_javascript | 3/50/50 | 0 | 1 | +33.3 pp [+0.0, +100.0] | 0/1 | 0/0 |
| multiple | 3/60/200 | 0 | 2 | +66.7 pp [+0.0, +100.0] | 0/1 | 0/0 |
| parallel | 3/60/200 | 0 | 3 | +100.0 pp [+100.0, +100.0] | 0/0 | 0/0 |
| parallel_multiple | 3/60/200 | 1 | 2 | +33.3 pp [+0.0, +100.0] | 0/1 | 0/0 |
| live_simple | 3/60/258 | 1 | 1 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_multiple | 3/60/1053 | 0 | 2 | +66.7 pp [+0.0, +100.0] | 0/0 | 0/0 |
| live_parallel | 3/16/16 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_parallel_multiple | 3/24/24 | 1 | 2 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| irrelevance | 3/60/240 | 3 | 2 | -33.3 pp [-100.0, +0.0] | 0/0 | 0/0 |
| live_irrelevance | 3/60/884 | 3 | 2 | -33.3 pp [-100.0, +0.0] | 1/0 | 0/0 |
| multi_turn_base | 3/60/200 | 0 | 1 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| multi_turn_miss_func | 2/60/200 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 1/1 | 0/0 |
| multi_turn_miss_param | 2/60/200 | 0 | 1 | +50.0 pp [+0.0, +100.0] | 0/1 | 0/0 |
| multi_turn_long_context | 3/60/200 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 0/1 | 0/0 |
| memory_kv | 6/60/155 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| memory_vector | 8/60/155 | 4 | 4 | +0.0 pp [-37.5, +37.5] | 0/0 | 0/0 |
| memory_rec_sum | 10/60/155 | 0 | 2 | +20.0 pp [+0.0, +50.0] | 1/1 | 0/0 |
| live_relevance | 3/16/16 | 3 | 2 | -33.3 pp [-100.0, +0.0] | 0/1 | 0/0 |

Completed-nonempty projection: off 16.9% [11.9, 21.9]; on 38.2% [26.2, 49.8]; effect +21.3 pp [+8.5, +33.5]. This keeps the same denominator and zeroes length-stop and blank/malformed irrelevance credits.

memory_kv: notetaker=6/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_vector: notetaker=8/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_rec_sum: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

### 2B

Parser-failed memory prerequisites: 0. Parser-failed common scored items: 0.

Represented overall weight: 0.800000; missing weight: 0.200000.

| Category | Common N / target / population | Off correct | On correct | On minus off (95%) | Length stops off/on | Empty or malformed credits off/on |
|---|---:|---:|---:|---|---:|---:|
| simple_python | 3/60/400 | 2 | 3 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| simple_java | 3/60/100 | 0 | 1 | +33.3 pp [+0.0, +100.0] | 0/1 | 0/0 |
| simple_javascript | 3/50/50 | 2 | 1 | -33.3 pp [-100.0, +0.0] | 0/0 | 0/0 |
| multiple | 3/60/200 | 2 | 3 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| parallel | 3/60/200 | 0 | 3 | +100.0 pp [+100.0, +100.0] | 0/0 | 0/0 |
| parallel_multiple | 3/60/200 | 1 | 2 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| live_simple | 3/60/258 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_multiple | 3/60/1053 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_parallel | 3/16/16 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_parallel_multiple | 3/24/24 | 1 | 2 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| irrelevance | 3/60/240 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/1 | 0/0 |
| live_irrelevance | 3/60/884 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| multi_turn_base | 3/60/200 | 1 | 1 | +0.0 pp [+0.0, +0.0] | 0/2 | 0/0 |
| multi_turn_miss_func | 2/60/200 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 0/2 | 0/0 |
| multi_turn_miss_param | 2/60/200 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 0/2 | 0/0 |
| multi_turn_long_context | 3/60/200 | 0 | 1 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| memory_kv | 6/60/155 | 0 | 1 | +16.7 pp [+0.0, +50.0] | 0/1 | 0/0 |
| memory_vector | 8/60/155 | 8 | 7 | -12.5 pp [-37.5, +0.0] | 0/0 | 0/0 |
| memory_rec_sum | 10/60/155 | 10 | 4 | -60.0 pp [-90.0, -30.0] | 0/0 | 0/0 |
| live_relevance | 3/16/16 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |

Completed-nonempty projection: off 45.9% [38.4, 53.6]; on 47.9% [37.9, 58.5]; effect +2.0 pp [-5.4, +9.9]. This keeps the same denominator and zeroes length-stop and blank/malformed irrelevance credits.

memory_kv: notetaker=6/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_vector: notetaker=8/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_rec_sum: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

### 4B

Parser-failed memory prerequisites: 0. Parser-failed common scored items: 0.

Represented overall weight: 0.800000; missing weight: 0.200000.

| Category | Common N / target / population | Off correct | On correct | On minus off (95%) | Length stops off/on | Empty or malformed credits off/on |
|---|---:|---:|---:|---|---:|---:|
| simple_python | 3/60/400 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| simple_java | 3/60/100 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| simple_javascript | 3/50/50 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| multiple | 3/60/200 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| parallel | 3/60/200 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| parallel_multiple | 3/60/200 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/1 | 0/0 |
| live_simple | 3/60/258 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_multiple | 3/60/1053 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_parallel | 3/16/16 | 2 | 3 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| live_parallel_multiple | 3/24/24 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| irrelevance | 3/60/240 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_irrelevance | 3/60/884 | 2 | 2 | +0.0 pp [-100.0, +100.0] | 0/0 | 0/0 |
| multi_turn_base | 3/60/200 | 2 | 3 | +33.3 pp [+0.0, +100.0] | 0/1 | 0/0 |
| multi_turn_miss_func | 2/60/200 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 0/1 | 0/0 |
| multi_turn_miss_param | 2/60/200 | 1 | 1 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| multi_turn_long_context | 3/60/200 | 1 | 0 | -33.3 pp [-100.0, +0.0] | 0/0 | 0/0 |
| memory_kv | 6/60/155 | 3 | 1 | -33.3 pp [-66.7, +0.0] | 0/0 | 0/0 |
| memory_vector | 8/60/155 | 8 | 2 | -75.0 pp [-100.0, -37.5] | 0/0 | 0/0 |
| memory_rec_sum | 10/60/155 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_relevance | 3/16/16 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |

Completed-nonempty projection: off 57.2% [45.3, 68.8]; on 45.1% [34.8, 55.5]; effect -12.1 pp [-20.8, -3.8]. This keeps the same denominator and zeroes length-stop and blank/malformed irrelevance credits.

memory_kv: notetaker=6/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_vector: notetaker=8/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_rec_sum: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

### 9B

Parser-failed memory prerequisites: 0. Parser-failed common scored items: 0.

Represented overall weight: 0.800000; missing weight: 0.200000.

| Category | Common N / target / population | Off correct | On correct | On minus off (95%) | Length stops off/on | Empty or malformed credits off/on |
|---|---:|---:|---:|---|---:|---:|
| simple_python | 3/60/400 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| simple_java | 3/60/100 | 3 | 2 | -33.3 pp [-100.0, +0.0] | 0/0 | 0/0 |
| simple_javascript | 3/50/50 | 2 | 1 | -33.3 pp [-100.0, +0.0] | 0/0 | 0/0 |
| multiple | 3/60/200 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| parallel | 3/60/200 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| parallel_multiple | 3/60/200 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_simple | 3/60/258 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_multiple | 3/60/1053 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_parallel | 3/16/16 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_parallel_multiple | 3/24/24 | 2 | 2 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| irrelevance | 3/60/240 | 2 | 3 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| live_irrelevance | 3/60/884 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| multi_turn_base | 3/60/200 | 1 | 2 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| multi_turn_miss_func | 2/60/200 | 0 | 1 | +50.0 pp [+0.0, +100.0] | 0/1 | 0/0 |
| multi_turn_miss_param | 2/60/200 | 1 | 2 | +50.0 pp [+0.0, +100.0] | 0/0 | 0/0 |
| multi_turn_long_context | 3/60/200 | 0 | 1 | +33.3 pp [+0.0, +100.0] | 0/0 | 0/0 |
| memory_kv | 6/60/155 | 0 | 3 | +50.0 pp [+16.7, +83.3] | 0/0 | 0/0 |
| memory_vector | 8/60/155 | 8 | 8 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| memory_rec_sum | 10/60/155 | 7 | 10 | +30.0 pp [+0.0, +60.0] | 0/0 | 0/0 |
| live_relevance | 3/16/16 | 3 | 3 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |

Completed-nonempty projection: off 52.7% [42.1, 63.1]; on 76.4% [65.0, 87.5]; effect +23.7 pp [+11.4, +36.7]. This keeps the same denominator and zeroes length-stop and blank/malformed irrelevance credits.

memory_kv: notetaker=6/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_vector: notetaker=8/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_rec_sum: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

## Evidence, limits and cleanup

`results/wave2/manifest.json` records populations, full permutation, selected IDs, weights and source hashes. Each model directory retains request/response checkpoints under `{mode}/calls`, official per-item scores under `{mode}/items`, learned snapshots under `{mode}/state`, failed calls and infrastructure errors separately. Prior model manifests and progress were archived under `harness-history/wave1-final`; `results/full` is unchanged. Interrupted official simulator replays must match request hashes; divergence archives the uncommitted attempt. Model-induced context overflow is scored as failed inference; failed memory-write prerequisites remain explicit missing domains. Malformed generated tool-call JSON that the server returns as HTTP 500 is also retained as failed inference, rather than discarded as infrastructure. Parser-failed prerequisites remain explicit blocked domains. The repair and positive/negative classification checks are recorded in `evidence/wave2-repairs.jsonl`. No answers are fabricated.

`results/wave2/analysis.json` contains common-case point scores, category Wilson intervals, paired effects, bootstrap intervals, absence-credit/length-stop diagnostics and missing domains. `selected-coverage.json` gives selected completion counts across all cells. an unpublished raw log, resource/pressure snapshots, `cleanup.txt`, `scratch-cleanup.json` and `DONE.json` provide operational evidence, including absence of both local scratch roots. Cleanup removes task launchd jobs, server, tunnel, models, Python environment and embedding caches; no containers are used. Cleanup status above is conditional on actual proof, not assumed from a finished process.

The model cards report overall BFCL-V4 scores, with no per-category reference values. Q4_K_M quantization, deterministic decoding, native FC transport, 65,536-token serving context, shared hardware, fixed sample and missing web search differ from vendor conditions. This run cannot validate or contradict the full vendor aggregate, establish extraction accuracy, or justify a general thinking-mode recommendation for extraction. Incomplete common coverage further limits inference. Earlier six selected cap rechecks are diagnostics only and remain outside headline results.

Primary sources: [official repository](https://github.com/ShishirPatil/gorilla/tree/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard), [official score composition](https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html), [official memory benchmark](https://gorilla.cs.berkeley.edu/blogs/16_bfcl_v4_memory.html). Model-card revisions and exact book citations remain in `evidence/model-card-figures.json`, `evidence/full-book-citations.json` and `results/wave2/prior-REPORT.md`.

## Suggested replacement wording

0.8B: This book measured 19.0% [15.7, 22.8] with thinking off and 38.2% [26.2, 49.8] with thinking on across 70 common paired offline BFCL-V4 questions per mode, using Q4_K_M weights. The paired effect was +19.2 pp [+7.2, +30.5]; missing web search and unfinished sample coverage prevent comparison with the full vendor score of 25.3.

2B: This book measured 45.9% [38.4, 53.6] with thinking off and 50.0% [40.3, 60.1] with thinking on across 70 common paired offline BFCL-V4 questions per mode, using Q4_K_M weights. The paired effect was +4.1 pp [-2.5, +11.2]; missing web search and unfinished sample coverage prevent comparison with the full vendor score of 43.6.

4B: This book measured 57.2% [45.3, 68.8] with thinking off and 48.2% [38.8, 57.9] with thinking on across 70 common paired offline BFCL-V4 questions per mode, using Q4_K_M weights. The paired effect was -9.0 pp [-18.7, +0.7]; missing web search and unfinished sample coverage prevent comparison with the full vendor score of 50.3.

9B: This book measured 52.7% [42.1, 63.1] with thinking off and 76.4% [65.0, 87.5] with thinking on across 70 common paired offline BFCL-V4 questions per mode, using Q4_K_M weights. The paired effect was +23.7 pp [+11.4, +36.7]; missing web search and unfinished sample coverage prevent comparison with the full vendor score of 66.1.

The independent retained-evidence audit passed (`evidence/wave2-final-audit.json`): request hashes, caps, thinking flags, planned IDs, archived worker bytes and common-cell weighted point scores. It does not independently validate bootstrap intervals. No new extraction-quality conclusion is supported.

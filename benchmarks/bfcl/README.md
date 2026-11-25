# BFCL-V4 wave-two continuation

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

The earlier pilot remains under `pilot/`. The earlier incomplete expanded run remains unchanged under `results/full/`; its README and editor report are preserved as `results/wave2/prior-README.md` and `prior-REPORT.md`. The new continuation reuses every completed question, prerequisite, request and memory snapshot from that run. Data preparation, simulation, embeddings and scoring run on a 32-thread x86 CPU; model generation runs on an Apple M3 Ultra with 96 GB unified memory. No Linux GPU, hosted generation or LLM judge is used.

The data, official loader, native function-calling adapter, simulators and scorers come from `bfcl-eval==2026.3.23`, upstream commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`, Apache-2.0 (`LICENSE.upstream`). Model revisions and SHA-256 hashes are in `full_common.py`; models are Qwen3.5 0.8B, 2B, 4B and 9B, Q4_K_M. Runtime is llama.cpp build 12359, commit `b1b770d90`. `requirements.txt` pins Python dependencies. The CPU memory-vector encoder is `all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

## Reproduce or resume

```bash
RUN_NAME=wave2 MODEL_HOST=your-authorized-ssh-alias bash benchmarks/bfcl/run_full.sh --hours 14 --sample-per-category 10 --cohort-file "$PWD/benchmarks/bfcl/results/wave2/cohort-target.json"
```

The shipped `wave2` directory resumes its persisted deadline and reused checkpoints. Use a fresh run name for new inference on the same frozen cohort. The shipped continuation already contains all reused item, request and learning checkpoints. The command requires the pinned llama.cpp runtime already installed on the authorized serving machine and `uv` on the scoring machine. All added dependencies, downloads and caches stay in task scratch directories. Future launches put large local files and UV, pip, Hugging Face and managed Python caches under `/data/scratch/membench/bfcl`; the environment already active at the disk-coordination update stays in `/var/tmp/membench-bfcl` until cleanup. New environment creation checks `df -h / /data` and pauses below 20 GiB free on the system disk. Servers bind localhost:39730 and are reached only through SSH. A model initially loads only at normal kernel pressure and at least 40% system-wide free memory. After a pressure stop, admission requires three consecutive normal-pressure checks with at least 45% free memory, one minute apart; a bad reading or stale sequence resets the count. Disk and memory pauses are timestamped and extend the global and current-model deadlines equally, with a combined maximum of 10 extra hours. The systemd runtime ceiling is 24 hours. Only the owned server is stopped at warning or critical pressure. Other services are untouched. Four slots are used at >=65% free, two at >=50%, otherwise one at >=40%, with 65,536 tokens per slot. `lsof -b` avoids blocking on unrelated network mounts.

## Sampling and interpretation

The initial phase attempted a seeded min(60, population) sample from every category. Its plan remains in `initial-manifest.json`, with phase snapshots under `phases/initial-60-target/` and every raw output retained. Permanent prerequisite failures and observed learning cost made that target infeasible within the available resources. The authorized uniform reduction is a fixed **10 questions in each of the 19 offline scoring categories**, or **190 per model and mode**, recorded before the remaining three model cells were extended in `cohort-target.json`.

Non-memory categories use the first 10 IDs in their original seeded permutations. Each memory backend uses the first 10 **notetaker** IDs in its original seeded full permutation, preserving the completed model-specific write-phase checkpoints. Each thinking mode retains its own independently learned snapshot, so memory effects include both write and query behavior. The memory portion excludes finance, healthcare, student and customer domains; it does not estimate performance across those domains. Some retained notetaker IDs lie outside the abandoned 60-ID attempt, and are reused from the earlier full queue. Selection uses category, scenario and seed, never correctness scores. The same 190 IDs are fixed across all four models and both modes. Seed is 20261121, temperature 0, output cap 16,384, client timeout initially 900 seconds, then 3,600 seconds (bounded by the model deadline) after healthy slow requests exceeded 900 seconds, and the official native-FC adapter is unchanged. No cap, prompt or decoding setting was tuned to accelerate the run.

The budget includes setup and cleanup, with explicitly authorized disk and memory pause credits capped at 10 extra hours total. Every interval has timestamps under `results/wave2/pauses/`; active inference receives no pause credit. The queue prioritizes the least paired category and the mode with fewer eligible scoring completions. Failed prerequisites and common-feasible domain decisions remain recorded in `generation-availability.json`, including broader attempts outside the final cohort. Existing non-scoring live-relevance outputs remain available but are excluded from the final 190-question cohort.

The headline below uses only selected IDs completed in **all eight cells**, so sizes and modes receive exactly the same cases. If the final fixed cohort is incomplete, its count is further reduced **uniformly across the 19 scoring categories**, keeping complete smaller populations as censuses. The count is the largest feasible common count; within a category, the earliest available common IDs in the original seeded selection order are retained. Correctness scores never choose this subset. `analysis.json` records the uniform count, exact IDs and all available common counts; `selected-coverage.json` shows final-target completions in every cell; `initial-selected-coverage.json` separately preserves coverage of the abandoned broader target. This availability-based complete-case projection is conditional and can be biased by deadlines or failed memory prerequisites; it is not an unbiased estimate for the planned sample. Incomplete requests are never substituted for incorrect answers, and all raw extra completions remain available.

Official offline leaf weights sum to 0.80: non-live 0.10, live 0.10, irrelevance 0.10, multi-turn 0.30 and memory 0.20. Their composition follows upstream helpers, including language averaging and population-weighted live categories. The projection divides the observed weighted contribution by represented weight. **Both live web-search categories are excluded (20% overall weight); this is not the full model-card aggregate.** Missing offline strata also reduce represented weight. `format_sensitivity` and `live_relevance` are non-scoring. Actual pinned populations govern selection.

Intervals are 95% paired bootstrap case-mix intervals (4,000 replicates), stratified by category; memory domains are cluster-resampled jointly across backends, then questions within domain. They are conditional on observed questions and learned snapshots. They do not account for absent domains, deadline selection, runtime or quantization differences, and can understate uncertainty for small strata. A category census is exact for this execution, while intervals describe sensitivity to case mix. Category rates have Wilson intervals in `analysis.json`.

Initial 60-per-category target complete: **False**. Final fixed 10/category cohort complete: **True**. Primary uniform count: **10 per scoring category**, capped at each smaller population. Uniform reduced comparison complete: **True**. Timestamped resource-pause credit: **2.768 hours out of a 10-hour maximum**. Operational status: `finished`. Cleanup verified: **True**.

| Model Q4_K_M | Card overall | Common paired N per mode | Offline off (95%) | Offline on (95%) | On minus off (95%) |
|---|---:|---:|---|---|---|
| 0.8B | 25.3 | 190 | 22.9% [18.8, 27.5] | 35.3% [29.1, 41.6] | +12.4 pp [+6.4, +18.8] |
| 2B | 43.6 | 190 | 47.5% [41.2, 54.3] | 55.7% [48.3, 63.4] | +8.2 pp [+1.1, +15.8] |
| 4B | 50.3 | 190 | 54.9% [47.8, 62.1] | 45.5% [38.6, 52.8] | -9.4 pp [-16.5, -1.9] |
| 9B | 66.1 | 190 | 58.8% [51.6, 65.5] | 67.5% [60.7, 74.7] | +8.7 pp [+1.7, +15.8] |

## Per-category common coverage and results

### 0.8B

Parser-failed memory prerequisites: 2. Parser-failed common scored items: 0.

Represented overall weight: 0.800000; missing weight: 0.200000.

| Category | Uniform N / available common / target / population | Off correct | On correct | On minus off (95%) | Length stops off/on | Empty or malformed credits off/on |
|---|---:|---:|---:|---|---:|---:|
| simple_python | 10/10/10/400 | 1 | 6 | +50.0 pp [+20.0, +80.0] | 0/1 | 0/0 |
| simple_java | 10/10/10/100 | 3 | 3 | +0.0 pp [-30.0, +30.0] | 0/2 | 0/0 |
| simple_javascript | 10/10/10/50 | 1 | 2 | +10.0 pp [+0.0, +30.0] | 1/1 | 0/0 |
| multiple | 10/10/10/200 | 3 | 8 | +50.0 pp [+20.0, +80.0] | 0/2 | 0/0 |
| parallel | 10/10/10/200 | 2 | 7 | +50.0 pp [+20.0, +80.0] | 0/1 | 0/0 |
| parallel_multiple | 10/10/10/200 | 1 | 6 | +50.0 pp [+20.0, +80.0] | 0/1 | 0/0 |
| live_simple | 10/10/10/258 | 7 | 7 | +0.0 pp [-30.0, +30.0] | 0/0 | 0/0 |
| live_multiple | 10/10/10/1053 | 1 | 6 | +50.0 pp [+20.0, +80.0] | 0/0 | 0/0 |
| live_parallel | 10/10/10/16 | 4 | 4 | +0.0 pp [+0.0, +0.0] | 0/3 | 0/0 |
| live_parallel_multiple | 10/10/10/24 | 5 | 7 | +20.0 pp [+0.0, +50.0] | 0/0 | 0/0 |
| irrelevance | 10/10/10/240 | 10 | 8 | -20.0 pp [-50.0, +0.0] | 0/1 | 0/1 |
| live_irrelevance | 10/10/10/884 | 10 | 7 | -30.0 pp [-60.0, +0.0] | 2/1 | 0/0 |
| multi_turn_base | 10/10/10/200 | 1 | 3 | +20.0 pp [+0.0, +50.0] | 0/3 | 0/0 |
| multi_turn_miss_func | 10/10/10/200 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 2/4 | 0/0 |
| multi_turn_miss_param | 10/10/10/200 | 0 | 1 | +10.0 pp [+0.0, +30.0] | 0/2 | 0/0 |
| multi_turn_long_context | 10/10/10/200 | 1 | 1 | +0.0 pp [+0.0, +0.0] | 1/2 | 0/0 |
| memory_kv | 10/10/10/155 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| memory_vector | 10/10/10/155 | 4 | 5 | +10.0 pp [-20.0, +40.0] | 0/0 | 0/0 |
| memory_rec_sum | 10/10/10/155 | 0 | 2 | +20.0 pp [+0.0, +50.0] | 1/1 | 0/0 |
| live_relevance | 0/0/0/16 | 0 | 0 | unavailable | 0/0 | 0/0 |

Completed-nonempty projection: off 21.7% [17.2, 26.4]; on 33.1% [27.1, 39.5]; effect +11.5 pp [+4.9, +18.4]. This keeps the same denominator and zeroes length-stop and blank/malformed irrelevance credits.

memory_kv: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_vector: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_rec_sum: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

### 2B

Parser-failed memory prerequisites: 0. Parser-failed common scored items: 0.

Represented overall weight: 0.800000; missing weight: 0.200000.

| Category | Uniform N / available common / target / population | Off correct | On correct | On minus off (95%) | Length stops off/on | Empty or malformed credits off/on |
|---|---:|---:|---:|---|---:|---:|
| simple_python | 10/10/10/400 | 6 | 10 | +40.0 pp [+10.0, +70.0] | 0/0 | 0/0 |
| simple_java | 10/10/10/100 | 0 | 4 | +40.0 pp [+10.0, +70.0] | 0/1 | 0/0 |
| simple_javascript | 10/10/10/50 | 2 | 4 | +20.0 pp [-20.0, +60.0] | 0/1 | 0/0 |
| multiple | 10/10/10/200 | 8 | 9 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| parallel | 10/10/10/200 | 4 | 9 | +50.0 pp [+20.0, +80.0] | 0/1 | 0/0 |
| parallel_multiple | 10/10/10/200 | 5 | 8 | +30.0 pp [-10.0, +70.0] | 0/0 | 0/0 |
| live_simple | 10/10/10/258 | 9 | 9 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_multiple | 10/10/10/1053 | 5 | 7 | +20.0 pp [+0.0, +50.0] | 0/0 | 0/0 |
| live_parallel | 10/10/10/16 | 5 | 6 | +10.0 pp [-30.0, +50.0] | 0/0 | 0/0 |
| live_parallel_multiple | 10/10/10/24 | 5 | 7 | +20.0 pp [+0.0, +50.0] | 0/0 | 0/0 |
| irrelevance | 10/10/10/240 | 9 | 7 | -20.0 pp [-50.0, +0.0] | 1/1 | 0/0 |
| live_irrelevance | 10/10/10/884 | 7 | 9 | +20.0 pp [+0.0, +50.0] | 0/0 | 0/0 |
| multi_turn_base | 10/10/10/200 | 3 | 4 | +10.0 pp [+0.0, +30.0] | 0/2 | 0/0 |
| multi_turn_miss_func | 10/10/10/200 | 1 | 1 | +0.0 pp [-30.0, +30.0] | 0/4 | 0/0 |
| multi_turn_miss_param | 10/10/10/200 | 1 | 3 | +20.0 pp [+0.0, +50.0] | 0/3 | 0/0 |
| multi_turn_long_context | 10/10/10/200 | 3 | 6 | +30.0 pp [+0.0, +60.0] | 0/1 | 0/0 |
| memory_kv | 10/10/10/155 | 1 | 3 | +20.0 pp [+0.0, +50.0] | 0/1 | 0/0 |
| memory_vector | 10/10/10/155 | 9 | 9 | +0.0 pp [-30.0, +30.0] | 0/0 | 0/0 |
| memory_rec_sum | 10/10/10/155 | 10 | 4 | -60.0 pp [-90.0, -30.0] | 0/0 | 0/0 |
| live_relevance | 0/0/0/16 | 0 | 0 | unavailable | 0/0 | 0/0 |

Completed-nonempty projection: off 46.9% [40.5, 53.7]; on 54.1% [46.9, 61.5]; effect +7.2 pp [+0.2, +14.4]. This keeps the same denominator and zeroes length-stop and blank/malformed irrelevance credits.

memory_kv: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_vector: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_rec_sum: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

### 4B

Parser-failed memory prerequisites: 0. Parser-failed common scored items: 0.

Represented overall weight: 0.800000; missing weight: 0.200000.

| Category | Uniform N / available common / target / population | Off correct | On correct | On minus off (95%) | Length stops off/on | Empty or malformed credits off/on |
|---|---:|---:|---:|---|---:|---:|
| simple_python | 10/10/10/400 | 10 | 10 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| simple_java | 10/10/10/100 | 8 | 6 | -20.0 pp [-50.0, +0.0] | 0/0 | 0/0 |
| simple_javascript | 10/10/10/50 | 5 | 6 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| multiple | 10/10/10/200 | 10 | 9 | -10.0 pp [-30.0, +0.0] | 0/0 | 0/0 |
| parallel | 10/10/10/200 | 8 | 9 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| parallel_multiple | 10/10/10/200 | 6 | 8 | +20.0 pp [+0.0, +50.0] | 0/1 | 0/0 |
| live_simple | 10/10/10/258 | 8 | 10 | +20.0 pp [+0.0, +50.0] | 0/0 | 0/0 |
| live_multiple | 10/10/10/1053 | 7 | 7 | +0.0 pp [-30.0, +30.0] | 0/0 | 0/0 |
| live_parallel | 10/10/10/16 | 7 | 8 | +10.0 pp [-20.0, +40.0] | 0/0 | 0/0 |
| live_parallel_multiple | 10/10/10/24 | 8 | 8 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| irrelevance | 10/10/10/240 | 8 | 8 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_irrelevance | 10/10/10/884 | 7 | 8 | +10.0 pp [-20.0, +40.0] | 0/0 | 0/0 |
| multi_turn_base | 10/10/10/200 | 5 | 5 | +0.0 pp [-30.0, +30.0] | 0/1 | 0/0 |
| multi_turn_miss_func | 10/10/10/200 | 2 | 3 | +10.0 pp [-20.0, +40.0] | 1/3 | 0/0 |
| multi_turn_miss_param | 10/10/10/200 | 4 | 3 | -10.0 pp [-30.0, +0.0] | 0/0 | 0/0 |
| multi_turn_long_context | 10/10/10/200 | 5 | 3 | -20.0 pp [-60.0, +20.0] | 0/0 | 0/0 |
| memory_kv | 10/10/10/155 | 4 | 1 | -30.0 pp [-60.0, +0.0] | 0/0 | 0/0 |
| memory_vector | 10/10/10/155 | 10 | 2 | -80.0 pp [-100.0, -50.0] | 0/0 | 0/0 |
| memory_rec_sum | 10/10/10/155 | 0 | 0 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| live_relevance | 0/0/0/16 | 0 | 0 | unavailable | 0/0 | 0/0 |

Completed-nonempty projection: off 54.9% [47.8, 62.1]; on 44.6% [37.6, 51.8]; effect -10.3 pp [-17.2, -3.1]. This keeps the same denominator and zeroes length-stop and blank/malformed irrelevance credits.

memory_kv: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_vector: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_rec_sum: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

### 9B

Parser-failed memory prerequisites: 0. Parser-failed common scored items: 0.

Represented overall weight: 0.800000; missing weight: 0.200000.

| Category | Uniform N / available common / target / population | Off correct | On correct | On minus off (95%) | Length stops off/on | Empty or malformed credits off/on |
|---|---:|---:|---:|---|---:|---:|
| simple_python | 10/10/10/400 | 10 | 10 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| simple_java | 10/10/10/100 | 7 | 6 | -10.0 pp [-30.0, +0.0] | 0/0 | 0/0 |
| simple_javascript | 10/10/10/50 | 5 | 5 | +0.0 pp [-30.0, +30.0] | 0/0 | 0/0 |
| multiple | 10/10/10/200 | 9 | 9 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| parallel | 10/10/10/200 | 8 | 9 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| parallel_multiple | 10/10/10/200 | 8 | 9 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| live_simple | 10/10/10/258 | 9 | 10 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| live_multiple | 10/10/10/1053 | 8 | 6 | -20.0 pp [-50.0, +0.0] | 0/0 | 0/0 |
| live_parallel | 10/10/10/16 | 9 | 10 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| live_parallel_multiple | 10/10/10/24 | 7 | 7 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| irrelevance | 10/10/10/240 | 7 | 8 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| live_irrelevance | 10/10/10/884 | 8 | 9 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| multi_turn_base | 10/10/10/200 | 5 | 6 | +10.0 pp [+0.0, +30.0] | 0/0 | 0/0 |
| multi_turn_miss_func | 10/10/10/200 | 0 | 2 | +20.0 pp [+0.0, +50.0] | 0/3 | 0/0 |
| multi_turn_miss_param | 10/10/10/200 | 4 | 4 | +0.0 pp [-30.0, +30.0] | 0/1 | 0/0 |
| multi_turn_long_context | 10/10/10/200 | 6 | 6 | +0.0 pp [-30.0, +30.0] | 0/0 | 0/0 |
| memory_kv | 10/10/10/155 | 1 | 5 | +40.0 pp [+0.0, +80.0] | 0/0 | 0/0 |
| memory_vector | 10/10/10/155 | 10 | 10 | +0.0 pp [+0.0, +0.0] | 0/0 | 0/0 |
| memory_rec_sum | 10/10/10/155 | 7 | 10 | +30.0 pp [+0.0, +60.0] | 0/0 | 0/0 |
| live_relevance | 0/0/0/16 | 0 | 0 | unavailable | 0/0 | 0/0 |

Completed-nonempty projection: off 58.8% [51.6, 65.5]; on 67.5% [60.7, 74.7]; effect +8.7 pp [+1.7, +15.8]. This keeps the same denominator and zeroes length-stop and blank/malformed irrelevance credits.

memory_kv: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_vector: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

memory_rec_sum: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

## Evidence, limits and cleanup

`results/wave2/manifest.json` records populations, full permutation, selected IDs, weights and source hashes. Each model directory retains request/response checkpoints under `{mode}/calls`, official per-item scores under `{mode}/items`, learned snapshots under `{mode}/state`, failed calls and infrastructure errors separately. Prior model manifests and progress were archived under `harness-history/wave1-final`; `results/full` is unchanged. Interrupted official simulator replays must match request hashes; divergence archives the uncommitted attempt. Model-induced context overflow is scored as failed inference; failed memory-write prerequisites remain explicit missing domains. Malformed generated tool-call JSON that the server returns as HTTP 500 is also retained as failed inference, rather than discarded as infrastructure. Parser-failed prerequisites remain explicit blocked domains. The repair and positive/negative classification checks are recorded in an unpublished raw log. A zero-inference resume regression also verified that persisted completion counts are loaded before scheduling (old worker 0, corrected worker 597 fixture checkpoints), preventing mode-priority resets after interruptions; see `evidence/wave2-resume-verification.json`. No answers are fabricated.

`results/wave2/analysis.json` contains common-case point scores, category Wilson intervals, paired effects, bootstrap intervals, absence-credit/length-stop diagnostics and missing domains. `selected-coverage.json` gives selected completion counts across all cells. `cohort-target.json`, `initial-manifest.json`, an unpublished raw log, resource/pressure snapshots, an unpublished raw log, an unpublished raw log and an unpublished raw log provide operational evidence, including absence of both local scratch roots. Cleanup removes task launchd jobs, server, tunnel, models, Python environment and embedding caches; no containers are used. Cleanup status above is conditional on actual proof, not assumed from a finished process.

The model cards report overall BFCL-V4 scores, with no per-category reference values. Q4_K_M quantization, deterministic decoding, native FC transport, 65,536-token serving context, shared hardware, fixed sample and missing web search differ from vendor conditions. This run cannot validate or contradict the full vendor aggregate, establish extraction accuracy, or justify a general thinking-mode recommendation for extraction. Incomplete common coverage further limits inference. Earlier six selected cap rechecks are diagnostics only and remain outside headline results.

Operational problems: shared-disk exhaustion interrupted the first continuation and led to the large-scratch migration. Confirmed memory warnings stopped only owned serving jobs; a persisted hysteresis gate controlled resumption and the pause ledger recorded the intervals. Separate health-probe interruptions had no confirmed pressure warning and remained infrastructure events, with checkpoints replayed. The broader memory attempt left failed malformed-tool prerequisites, while model-induced context overflows were retained as failed inference. Unscored learning work did not complete the original memory target and remains separate from the frozen notetaker-only cohort. Six earlier pilot cap diagnostics are retained and excluded from the final aggregate.

Primary sources: [official repository](https://github.com/ShishirPatil/gorilla/tree/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard), [official score composition](https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html), [official memory benchmark](https://gorilla.cs.berkeley.edu/blogs/16_bfcl_v4_memory.html). Model-card revisions and exact book citations remain in `evidence/model-card-figures.json`, `evidence/full-book-citations.json` and `results/wave2/prior-REPORT.md`.

## Raw transcripts

Per-question results, raw model calls, failed calls and worker state are stored as compressed archives (`items.tar.zst`, `calls.tar.zst`, `failed-calls.tar.zst`, `state.tar.zst`) inside each `results/<run>/<model>/<mode>/` folder. Unpack one with `tar -I zstd -xf items.tar.zst` in place before running the audit or analysis scripts, which read the unpacked `items/` folders.

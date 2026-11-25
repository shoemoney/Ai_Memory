# BFCL-V4 expanded offline run

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

The earlier 40-case-per-cell experiment is preserved under `pilot/`, with its original code, reports and raw evidence. It is a pilot and is not an overall BFCL-V4 reproduction.

This expanded experiment uses the official BFCL-V4 data, loader, native function-calling handler, simulators and scoring functions. The scoring package is `bfcl-eval==2026.3.23`; upstream revision is `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`, Apache-2.0. Every offline scoring category is queued at full size, plus non-scoring live relevance. Entries that fit the time budget are retained; partial categories and unpaired deadline leftovers are disclosed below. No hosted model API or judge is used. `memory_vector` uses the official CPU `all-MiniLM-L6-v2` encoder, pinned to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

Hardware is an Apple M3 Ultra with 96 GB unified memory for model serving and a 32-thread x86 CPU for data, simulation, embeddings and scoring. No Linux GPU is used. One Q4_K_M model is served at a time, using llama.cpp build 12359 (`b1b770d90`), admission-aware concurrency and 65,536 tokens of context per slot. Initial serving used four slots; recovery uses four slots at 65% or more free memory, two at 50% or more, and one at 40% or more. The context per request and generation cap stay fixed; slot changes are operational, not output tuning. The other benchmark workload is uncontrolled. Temperature is 0, seed 20261121 and output cap 16,384 tokens per request. This cap matches the official Qwen adapter's configured `max_tokens`; its temperature 0.6 and input limit 58,000 are not copied. Our deterministic decoding and native OpenAI-compatible FC adapter may differ from the model-card evaluation, whose exact prompts, revision, runtime and quantization are not specified.

## Run and resume

```bash
RUN_NAME=full-reproduction MODEL_HOST=your-authorized-ssh-alias bash benchmarks/bfcl/run_full.sh
```

Requires `uv`, SSH access to the model-serving Mac and the pinned llama.cpp runtime already installed. All new runtime, model and cache files stay in task scratch directories. The controller runs under a transient systemd user service on Linux; the server and memory-pressure guard use transient launchd jobs from the Mac scratch directory. The endpoint is localhost:39730 through SSH. It never uses another model host automatically. Admission requires normal pressure and at least 40% system-wide memory free immediately before loading. After loading, the guard stops the task server at warning or critical pressure; the free percentage remains logged. The earlier stricter loaded-server 40% stop caused restart churn and was corrected to the stated rule. Generation resumes the same checkpoints when admission is safe. Do not point the command at an unrelated existing run directory.

Each API request is atomically checkpointed, and each fully scored item is atomically committed. A replay reconstructs the official simulator from its initial state using saved responses, checking request hashes before reusing them. If an official simulator returns a time-dependent value and the replay hash changes, the uncommitted attempt is archived under `replay-divergences/` and that item restarts from its original state; already committed items stay intact. Prerequisite memory snapshots are retained, and inference simulator keys and state directories are separated by thinking mode. An interrupted item resumes without silently changing its prompt or continuing a partly mutated simulator. Transient infrastructure errors are retried and excluded explicitly, never scored as model failures. A serving connection loss suspends the worker as a whole instead of rapidly walking the dataset and labeling many items as separate faults. The supervisor resolves uv from the executable PATH or the standard user installation so a scratch rebuild also works under systemd. A completed-question request that exhausts the serving context is different: the actual rejected request is retained under `failed-calls/`, and the official scorer receives an empty failed-inference result, so the case stays in the denominator. Any resulting irrelevance absence credit is removed from completed-nonempty performance. Context-failed memory-write prerequisites are unscored prerequisites and can block a domain; those missing domains are explicit. Use a fresh RUN_NAME for a new reproduction; repeating it resumes that named run and its persisted absolute deadline. The final cleanup removes task services, tunnel, server, weights and caches; results and snapshots remain here.

## Coverage and score formula

The official score is `0.10 non-live + 0.10 live + 0.10 irrelevance + 0.30 multi-turn + 0.40 agentic`, with agentic equally split between memory and web search. Non-live averages the simple-language mean, multiple, parallel and parallel-multiple equally; simple averages Python/Java/JavaScript equally. Live is weighted by its original four category populations, not by the number completed here. Irrelevance averages non-live/live equally. Multi-turn averages its four variants equally. Memory averages the three backends equally. This code applies exactly those leaf weights to the categories observed and divides by their covered weight. With all offline leaves represented, this is an **80%-weight offline projection**, not the full overall score. The unnormalized weighted contribution is also retained in `results/full/analysis.json`; missing web-search performance must not be imputed as failure or as success.

Excluded: `web_search_base` and `web_search_no_snippet`, which require live SerpAPI search and live HTTP pages. Their combined missing weight is 20%. `format_sensitivity` is non-scoring and the official variations apply only to prompting-mode models, not this native-FC matrix. Live relevance is also non-scoring but is included. The pinned data has 884 live-irrelevance and 16 live-relevance items, compared with 882 and 18 in the release blog, so actual pinned file populations govern this run. The model cards give an overall BFCL-V4 row, not category-level reference scores.

Each category has a seeded random permutation, shared between modes. Jobs aim at all rows rather than a selected fixed cap. Models receive an equal share of the remaining eight-hour deadline; a completed model releases unused time to later models. Within a model, the queue alternates modes to balance completed and in-flight items, round-robins static/multi-turn categories, and reserves 15 of 32 scheduling choices for memory. Memory prerequisite chains remain ordered, with independent scenarios in the fixed order notetaker, finance, healthcare, student, customer to obtain at least one finished domain early. This cost-aware order and deadline censoring can bias incomplete memory coverage toward shorter domains. Intervals cannot repair absent domains or unfinished categories. All planned IDs, prerequisites, actual counts and missing domains are printed or retained.

## Metrics and intervals

“Official” preserves BFCL's exact valid/invalid decisions. “Completed nonempty” additionally rejects any item with a length stop and any irrelevance credit caused by a blank/empty structured answer or by malformed tool calls. Those credits are tabulated separately and are not described as skill. The primary comparison uses only IDs completed in both modes, so every within-model effect is paired. Unpaired completed rows are retained and counted separately. In-flight requests that time out at the persisted per-model deadline are reported as budget-censored item/modes, not as infrastructure faults or model answers.

Intervals are 95% paired bootstrap case-mix intervals with 4,000 replicates, stratified by category. Memory domains are cluster-resampled jointly across backends, followed by question resampling within a domain. They are conditional on observed items and learned memory snapshots, do not include quantization/runtime mismatch or inference randomness, and do not establish performance on unobserved domains. For a full category census the observed score itself is exact for this run; the interval describes sensitivity to case mix. Category proportions additionally have Wilson intervals in the JSON evidence.

In the finished run, no category reached a full census. Only the notetaker memory domain was observed, so domain resampling adds no between-domain uncertainty; several static and multi-turn strata contain only two to seven paired cases. Bootstrap intervals can understate uncertainty in such small strata and cannot validate population or cross-size rankings. The completed-nonempty metric keeps the same paired denominator and weights, setting excluded credits to zero rather than estimating accuracy conditional on successful completion. API requests also have a 900-second timeout, shortened by the remaining model allocation; a timeout is an unfinished request, not a token-length stop or a scored answer.

## Published and local results

| Model | Card overall | Paired N per mode | Official offline off, 95% interval | Official offline on, 95% interval | On minus off, 95% interval |
|---|---:|---:|---|---|---|
| 0.8B Q4_K_M | 25.3 | 175 | 21.0% [17.7, 24.9] | 37.6% [30.8, 44.4] | +16.5 pp [+9.2, +24.0] |
| 2B Q4_K_M | 43.6 | 90 | 46.6% [38.7, 54.3] | 52.1% [43.3, 61.8] | +5.5 pp [-1.4, +13.2] |
| 4B Q4_K_M | 50.3 | 81 | 55.3% [44.0, 66.0] | 49.4% [39.5, 59.5] | -5.9 pp [-16.5, +5.5] |
| 9B Q4_K_M | 66.1 | 95 | 54.7% [45.2, 64.0] | 76.8% [66.4, 87.2] | +22.1 pp [+10.7, +34.0] |

| Model | Completed nonempty off | Completed nonempty on | On minus off |
|---|---|---|---|
| 0.8B | 19.2% [15.2, 23.7] | 35.8% [28.6, 42.8] | +16.5 pp [+8.9, +24.3] |
| 2B | 46.6% [38.7, 54.3] | 50.6% [41.2, 60.4] | +4.0 pp [-3.5, +12.1] |
| 4B | 55.3% [44.0, 66.0] | 46.2% [35.2, 57.4] | -9.0 pp [-18.6, +0.9] |
| 9B | 54.7% [45.2, 64.0] | 76.8% [66.4, 87.2] | +22.1 pp [+10.7, +34.0] |

## Per-category coverage and counts

| Model | Category | N paired / population | Off correct | On correct | Empty credits off/on | Malformed credits off/on | Length stops off/on | Context failures off/on |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0.8B | simple_python | 6/400 | 1 | 3 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0.8B | simple_java | 7/100 | 3 | 2 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0.8B | simple_javascript | 6/50 | 0 | 1 | 0/0 | 0/0 | 1/1 | 0/0 |
| 0.8B | multiple | 6/200 | 1 | 5 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0.8B | parallel | 7/200 | 2 | 6 | 0/0 | 0/0 | 0/0 | 0/0 |
| 0.8B | parallel_multiple | 7/200 | 1 | 5 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0.8B | live_simple | 7/258 | 4 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 0.8B | live_multiple | 7/1053 | 1 | 5 | 0/0 | 0/0 | 0/0 | 0/0 |
| 0.8B | live_parallel | 7/16 | 3 | 3 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0.8B | live_parallel_multiple | 7/24 | 2 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 0.8B | irrelevance | 7/240 | 7 | 6 | 0/1 | 0/0 | 0/1 | 0/0 |
| 0.8B | live_irrelevance | 7/884 | 7 | 5 | 0/0 | 0/0 | 2/1 | 0/0 |
| 0.8B | multi_turn_base | 6/200 | 0 | 2 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0.8B | multi_turn_miss_func | 6/200 | 0 | 0 | 0/0 | 0/0 | 2/3 | 0/0 |
| 0.8B | multi_turn_miss_param | 6/200 | 0 | 1 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0.8B | multi_turn_long_context | 6/200 | 0 | 0 | 0/0 | 0/0 | 1/1 | 0/0 |
| 0.8B | memory_kv | 24/155 | 1 | 1 | 0/0 | 0/0 | 0/2 | 0/0 |
| 0.8B | memory_vector | 24/155 | 7 | 12 | 0/0 | 0/0 | 0/1 | 0/0 |
| 0.8B | memory_rec_sum | 22/155 | 1 | 4 | 0/0 | 0/0 | 1/4 | 0/2 |
| 0.8B | live_relevance | 6/16 | 5 | 2 | 0/0 | 0/0 | 0/4 | 0/0 |

0.8B: total completed off/on 190/181 (including non-scoring live relevance); paired scoring questions 175; covered overall weight 0.800000; missing overall weight 0.200000; deadline-censored item/modes 4; infrastructure-excluded item/modes 0; context-failed memory prerequisites 0. Full category censuses: none. Completely absent offline categories: none.

0.8B, memory_kv, paired questions by domain: notetaker=24/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

0.8B, memory_vector, paired questions by domain: notetaker=24/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

0.8B, memory_rec_sum, paired questions by domain: notetaker=22/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.


| Model | Category | N paired / population | Off correct | On correct | Empty credits off/on | Malformed credits off/on | Length stops off/on | Context failures off/on |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2B | simple_python | 4/400 | 3 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | simple_java | 4/100 | 0 | 1 | 0/0 | 0/0 | 0/1 | 0/0 |
| 2B | simple_javascript | 4/50 | 2 | 1 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | multiple | 4/200 | 3 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | parallel | 4/200 | 1 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | parallel_multiple | 4/200 | 2 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | live_simple | 4/258 | 4 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | live_multiple | 4/1053 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | live_parallel | 4/16 | 3 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | live_parallel_multiple | 4/24 | 1 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | irrelevance | 4/240 | 4 | 4 | 0/0 | 0/0 | 0/1 | 0/0 |
| 2B | live_irrelevance | 4/884 | 3 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | multi_turn_base | 3/200 | 1 | 1 | 0/0 | 0/0 | 0/2 | 0/0 |
| 2B | multi_turn_miss_func | 3/200 | 0 | 0 | 0/0 | 0/0 | 0/2 | 0/0 |
| 2B | multi_turn_miss_param | 3/200 | 0 | 0 | 0/0 | 0/0 | 0/3 | 0/0 |
| 2B | multi_turn_long_context | 3/200 | 0 | 1 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | memory_kv | 10/155 | 1 | 3 | 0/0 | 0/0 | 0/1 | 0/0 |
| 2B | memory_vector | 10/155 | 9 | 9 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | memory_rec_sum | 10/155 | 10 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 2B | live_relevance | 3/16 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |

2B: total completed off/on 98/93 (including non-scoring live relevance); paired scoring questions 90; covered overall weight 0.800000; missing overall weight 0.200000; deadline-censored item/modes 1; infrastructure-excluded item/modes 36; context-failed memory prerequisites 0. Full category censuses: none. Completely absent offline categories: none.

2B, memory_kv, paired questions by domain: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

2B, memory_vector, paired questions by domain: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

2B, memory_rec_sum, paired questions by domain: notetaker=10/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.


| Model | Category | N paired / population | Off correct | On correct | Empty credits off/on | Malformed credits off/on | Length stops off/on | Context failures off/on |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 4B | simple_python | 3/400 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | simple_java | 3/100 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | simple_javascript | 3/50 | 2 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | multiple | 3/200 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | parallel | 3/200 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | parallel_multiple | 3/200 | 2 | 2 | 0/0 | 0/0 | 0/1 | 0/0 |
| 4B | live_simple | 3/258 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | live_multiple | 3/1053 | 2 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | live_parallel | 3/16 | 2 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | live_parallel_multiple | 3/24 | 2 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | irrelevance | 3/240 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | live_irrelevance | 3/884 | 2 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | multi_turn_base | 3/200 | 2 | 3 | 0/0 | 0/0 | 0/1 | 0/0 |
| 4B | multi_turn_miss_func | 3/200 | 0 | 1 | 0/0 | 0/0 | 0/1 | 0/0 |
| 4B | multi_turn_miss_param | 3/200 | 1 | 1 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | multi_turn_long_context | 3/200 | 1 | 0 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | memory_kv | 11/155 | 5 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | memory_vector | 11/155 | 11 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | memory_rec_sum | 11/155 | 0 | 0 | 0/0 | 0/0 | 0/0 | 0/0 |
| 4B | live_relevance | 3/16 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |

4B: total completed off/on 104/84 (including non-scoring live relevance); paired scoring questions 81; covered overall weight 0.800000; missing overall weight 0.200000; deadline-censored item/modes 2; infrastructure-excluded item/modes 0; context-failed memory prerequisites 0. Full category censuses: none. Completely absent offline categories: none.

4B, memory_kv, paired questions by domain: notetaker=11/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

4B, memory_vector, paired questions by domain: notetaker=11/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

4B, memory_rec_sum, paired questions by domain: notetaker=11/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.


| Model | Category | N paired / population | Off correct | On correct | Empty credits off/on | Malformed credits off/on | Length stops off/on | Context failures off/on |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 9B | simple_python | 4/400 | 4 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | simple_java | 4/100 | 4 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | simple_javascript | 4/50 | 3 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | multiple | 4/200 | 4 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | parallel | 4/200 | 4 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | parallel_multiple | 4/200 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | live_simple | 4/258 | 4 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | live_multiple | 4/1053 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | live_parallel | 4/16 | 4 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | live_parallel_multiple | 4/24 | 2 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | irrelevance | 4/240 | 3 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | live_irrelevance | 4/884 | 4 | 4 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | multi_turn_base | 4/200 | 1 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | multi_turn_miss_func | 2/200 | 0 | 1 | 0/0 | 0/0 | 0/1 | 0/0 |
| 9B | multi_turn_miss_param | 2/200 | 1 | 2 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | multi_turn_long_context | 3/200 | 0 | 1 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | memory_kv | 12/155 | 1 | 7 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | memory_vector | 12/155 | 12 | 12 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | memory_rec_sum | 12/155 | 9 | 12 | 0/0 | 0/0 | 0/0 | 0/0 |
| 9B | live_relevance | 3/16 | 3 | 3 | 0/0 | 0/0 | 0/0 | 0/0 |

9B: total completed off/on 105/98 (including non-scoring live relevance); paired scoring questions 95; covered overall weight 0.800000; missing overall weight 0.200000; deadline-censored item/modes 2; infrastructure-excluded item/modes 0; context-failed memory prerequisites 0. Full category censuses: none. Completely absent offline categories: none.

9B, memory_kv, paired questions by domain: notetaker=12/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

9B, memory_vector, paired questions by domain: notetaker=12/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.

9B, memory_rec_sum, paired questions by domain: notetaker=12/25, finance=0/25, healthcare=0/25, student=0/50, customer=0/30.


## Pilot token-limit rechecks

The six pilot length-stop cases are re-requested with their original prompts/tools, same mode and weights, and the output cap raised from 4,096 to 16,384. These selected diagnostics are kept outside the expanded sample and do not enter its aggregates.

| Model/mode | ID | Pilot official correct | 16K official correct | 16K completed nonempty | 16K empty credit | 16K length stop |
|---|---|---|---|---|---|---|
| 0.8B off | multiple_40 | False | False | False | False | True |
| 0.8B on | multiple_40 | False | False | False | False | True |
| 0.8B on | irrelevance_166 | True | True | False | False | True |
| 0.8B on | parallel_164 | False | False | False | False | True |
| 2B on | irrelevance_68 | True | True | False | True | True |
| 4B on | parallel_163 | False | False | False | False | True |

## Evidence and limits

- `results/full/manifest.json` and each model's `manifest.json`: every dataset population, planned permutation, source hashes, prerequisite IDs and score weights.
- `results/full/{size}/{mode}/calls/{category}/{id}/{step}.json`: exact requests and full API responses, checkpointed before further simulation.
- `results/full/{size}/{mode}/items/{category}/{id}.json`: official results, metadata, score, cap/absence flags and timing. Prerequisites are marked and excluded from question N.
- `results/full/{size}/{mode}/state/`: official learned memory and per-prerequisite snapshots, retained for audit/resume.
- `results/full/analysis.json`: category Wilson intervals, paired effects, overall weighted projections, cluster bootstrap intervals, coverage and diagnostics.
- `results/full/{size}/errors/`: infrastructure exclusions, separate from incorrect model answers.
- `results/full/run-state.json`, per-model progress/heartbeat and final worker status: operational checkpoints and observed progress, not an inferred completion claim.
- `results/full/resources-before.txt`, an unpublished raw log, per-model resource/pressure files and an unpublished raw log: resource and cleanup proof. an unpublished raw log states final operational status.

Primary methodology: [official BFCL V4 score composition](https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html), [official memory benchmark](https://gorilla.cs.berkeley.edu/blogs/16_bfcl_v4_memory.html), and the pinned [official repository](https://github.com/ShishirPatil/gorilla/tree/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard). Dataset and harness are Apache-2.0; the original license is retained in `LICENSE.upstream`.

This remains different from the cards: Q4_K_M conversion, deterministic decoding, an explicit official-adapter token cap, 65,536-token serving context, pinned native FC transport, a shared machine, missing live web search and any deadline-censored categories/domains. Different sizes can reach different case sets under the deadline; only the within-size mode effects are paired, so cross-size rankings can reflect coverage differences. These scores do not establish memory-extraction quality or justify a universal thinking-mode recommendation for extraction. No model-card per-category score is available for category-by-category numerical validation.

## Final operational status and cleanup

Operational status: `budget_finished`. Cleanup confirmed: **True**. This marks the end of the time-limited matrix, not a claim that every planned item completed. No containers were created, no chapter files were edited and no commit was made by this task.

The server and memory guard were removed from launchd, task port 39730 was unoccupied, the SSH tunnel was closed, and both scratch directories including model downloads, Python runtime and local embedding cache were deleted. Pre/post disk-space and process snapshots are retained; other workloads make identical disk totals neither expected nor necessary. an unpublished raw log and an unpublished raw log are the recorded checks.

The expanded smoke test initially found that Java evaluation had been given generation-normalized schemas, producing a type-map error. The runner was corrected to use the official unnormalized scoring loader before the measured matrix. Positive/negative Java and JavaScript checks, all three memory snapshot round trips, correct/wrong agentic answers and independent agreement with the official score-composition helpers passed in `evidence/full-verification.json`. The smoke outputs are diagnostics and excluded from the full result.

A continuation check also found a model-induced context overflow after hundreds of repeated memory-retrieval calls. Treating that as an infrastructure exclusion would omit a hard case, so the worker was corrected to retain the rejected request and pass an empty failed-inference result to the official scorer. Positive/negative failure-path checks passed; the original source/manifest were archived, only the owned worker was reloaded, and all committed responses, items and deadlines were preserved. The repair record is in `evidence/full-repairs.jsonl` and `context-failure-verification.json`.

A later startup-recovery fault exposed the restricted systemd PATH: uv lookup now checks PATH and the standard user installation. A refused-connection drill verified that serving loss suspends the worker once, with no scored or fabricated answers, instead of cascading through queued items. The loaded-server guard was corrected to stop at kernel warning/critical pressure, while retaining the >=40% free admission check; slot count now adapts to admission headroom with context and token cap fixed. These changes preserved all committed data and the original deadlines, and their verification is in `evidence/full-recovery-verification.json`.


## Final evidence audit

All retained request hashes, planned item IDs, paired counts and weighted score points passed an independent offline audit. The complete 4,000-replicate aggregate intervals were reproduced exactly without inference. See `audit_full.py` and `evidence/full-final-audit.json`.

| Model | Scoring completions off/on | Paired scoring N | Saved requests off/on | Paired scoring length stops off/on |
|---|---:|---:|---:|---:|
| 0.8B | 183/175 | 175 | 800/1126 | 7/21 |
| 2B | 94/90 | 90 | 495/491 | 0/10 |
| 4B | 100/81 | 81 | 865/1009 | 0/3 |
| 9B | 101/95 | 95 | 765/539 | 0/1 |

The paired scoring sample has one empty-answer irrelevance credit (0.8B thinking on) and zero malformed-tool irrelevance credits. These are not counted as skill in completed-nonempty performance. Non-scoring live-relevance length stops are listed separately by category. All six selected pilot cap rechecks still stopped at 16,384 tokens; two received official irrelevance credits, but none earned completed-nonempty credit.

Pinned source-file hashes agree across all model manifests. Original downloaded source/runtime files were deleted during required cleanup; this audit checks retained attestations, not a fresh download. All three measured worker versions match current or archived source bytes, including the intermediate c95df864 version under 2B/harness-history. The first 114 items predate per-item worker hashes; their initial worker and manifest are archived, so their provenance is at run level rather than per item. The remaining provenance limit is the initial run-level attribution, rather than identical per-item source coverage for every record.

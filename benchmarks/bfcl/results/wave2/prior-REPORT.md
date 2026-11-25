# BFCL-V4 evidence for the editor

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

## Every printed BFCL figure in the assigned chapters

The assigned chapter files were read and searched for BFCL, Berkeley and the four reported numbers. Chapter 06 has two occurrences. Chapters 07 and 18 contain no BFCL figure in the inspected versions, so neither receives a fabricated replacement result. Their other extraction and memory claims are outside this benchmark's scope.

1. `06-small-memory-models.html`, paragraph beginning “Tool-calling scores fall steeply below 4B,” line 176 at inspection: “Qwen's own model cards report BFCL-V4 scores for Qwen3.5 of 25.3 at 0.8B, 43.6 at 2B, 50.3 at 4B and 66.1 at 9B.” The paragraph cites Sources 12 through 15. It also explicitly says that BFCL tests tool calling, not memory extraction, and that 0.8B/2B results use thinking mode.
2. Same chapter, Numbers table, line 284 at inspection: displayed range “25.3 to 66.1”; explanation “Qwen3.5 BFCL-V4 tool-calling scores: 25.3 (0.8B), 43.6 (2B), 50.3 (4B), 66.1 (9B). Model-card results, not extraction accuracy.” This row again cites Sources 12 through 15. These are repetitions of the same four vendor figures, not another experimental result.

The exact primary sources behind those references, plus the size-specific cards that resolve the table columns, are:

| Figure | Official model-card revision | Chapter source |
|---|---|---|
| 25.3, 0.8B | [2fc06364715b967f1860aea9cf38778875588b17](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/2fc06364715b967f1860aea9cf38778875588b17/README.md) | 06, Source 12 |
| 43.6, 2B | [15852e8c16360a2fea060d615a32b45270f8a8fc](https://huggingface.co/Qwen/Qwen3.5-2B/blob/15852e8c16360a2fea060d615a32b45270f8a8fc/README.md) | 06, Source 13; also appears in Source 12's shared table |
| 50.3, 4B | [851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a](https://huggingface.co/Qwen/Qwen3.5-4B/blob/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/README.md) | 06, Source 14; also appears in Source 15's shared table |
| 66.1, 9B | [c202236235762e1c871ad0ccb60c8ee5ba337b9a](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/README.md) | 06, Source 15 |

The copied evidence preserves table headers and the entire BFCL row, because the first numeric column belongs to a comparison model. See `evidence/model-card-figures.json`. The 0.8B/2B cards label this section “General Agent (Thinking).” The 4B/9B cards label it “General Agent” and describe thinking as their default. This does not establish an identical evaluation configuration for all four sizes.

Expanded-run citation snapshot: `evidence/full-book-citations.json`. The current Chapter 06 paragraph and Numbers row both cite Sources 12, 13, 14 and 15.

## Expanded local results

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

## Suggested book wording

For 0.8B: "On our offline BFCL-V4 projection, the Q4_K_M 0.8B model scored 21.0% [17.7, 24.9] with thinking off and 37.6% [30.8, 44.4] with thinking on, using 175 paired questions per mode. The thinking-on difference was +16.5 pp [+9.2, +24.0]; live web search and the incomplete categories listed in the evidence prevent this from being a reproduction of the full vendor score."

For 2B: "On our offline BFCL-V4 projection, the Q4_K_M 2B model scored 46.6% [38.7, 54.3] with thinking off and 52.1% [43.3, 61.8] with thinking on, using 90 paired questions per mode. The thinking-on difference was +5.5 pp [-1.4, +13.2]; live web search and the incomplete categories listed in the evidence prevent this from being a reproduction of the full vendor score."

For 4B: "On our offline BFCL-V4 projection, the Q4_K_M 4B model scored 55.3% [44.0, 66.0] with thinking off and 49.4% [39.5, 59.5] with thinking on, using 81 paired questions per mode. The thinking-on difference was -5.9 pp [-16.5, +5.5]; live web search and the incomplete categories listed in the evidence prevent this from being a reproduction of the full vendor score."

For 9B: "On our offline BFCL-V4 projection, the Q4_K_M 9B model scored 54.7% [45.2, 64.0] with thinking off and 76.8% [66.4, 87.2] with thinking on, using 95 paired questions per mode. The thinking-on difference was +22.1 pp [+10.7, +34.0]; live web search and the incomplete categories listed in the evidence prevent this from being a reproduction of the full vendor score."

For the extraction advice: "BFCL measures tool use, including memory operations, rather than the fact-extraction task in this walkthrough. Our thinking-mode comparison belongs with the BFCL results, while extraction speed and fidelity need a separate paired test on the intended notes and schema."

Keep all intervals, missing-category/domain counts and the separate empty-credit tally with these sentences; do not imply a full official aggregate or an extraction-quality result. Each quoted proposed passage is at most two sentences and uses no em dashes.

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

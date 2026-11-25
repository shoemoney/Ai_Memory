# BFCL-V4 evidence for the editor

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

## Every printed BFCL figure in the assigned chapters

The assigned chapter files were read and searched for BFCL, Berkeley and the four reported numbers. Chapter 06 has two occurrences. Chapters 07 and 18 contain no BFCL figure in the inspected versions, so neither receives a fabricated replacement result. Their other extraction and memory claims are outside this benchmark's scope.

1. `06-small-memory-models.html`, paragraph beginning “Tool-calling scores fall steeply below 4B,” line 176 at inspection: “Qwen's own model cards report BFCL-V4 scores for Qwen3.5 of 25.3 at 0.8B, 43.6 at 2B, 50.3 at 4B and 66.1 at 9B.” The paragraph cites Sources 12 and 15. It also explicitly says that BFCL tests tool calling, not memory extraction, and that 0.8B/2B results use thinking mode.
2. Same chapter, Numbers table, line 274 at inspection: displayed range “25.3 to 66.1”; explanation “Qwen3.5 BFCL-V4 tool-calling scores: 25.3 (0.8B), 43.6 (2B), 50.3 (4B), 66.1 (9B). Model-card results, not extraction accuracy.” This row again cites Sources 12 and 15. These are repetitions of the same four vendor figures, not another experimental result.

The exact primary sources behind those references, plus the size-specific cards that resolve the table columns, are:

| Figure | Official model-card revision | Chapter source |
|---|---|---|
| 25.3, 0.8B | [2fc06364715b967f1860aea9cf38778875588b17](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/2fc06364715b967f1860aea9cf38778875588b17/README.md) | 06, Source 12 |
| 43.6, 2B | [15852e8c16360a2fea060d615a32b45270f8a8fc](https://huggingface.co/Qwen/Qwen3.5-2B/blob/15852e8c16360a2fea060d615a32b45270f8a8fc/README.md) | 06, Source 13; also appears in Source 12's shared table |
| 50.3, 4B | [851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a](https://huggingface.co/Qwen/Qwen3.5-4B/blob/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/README.md) | 06, Source 14; also appears in Source 15's shared table |
| 66.1, 9B | [c202236235762e1c871ad0ccb60c8ee5ba337b9a](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/README.md) | 06, Source 15 |

The copied evidence preserves table headers and the entire BFCL row, because the first numeric column belongs to a comparison model. See `evidence/model-card-figures.json`. The 0.8B/2B cards label this section “General Agent (Thinking).” The 4B/9B cards label it “General Agent” and describe thinking as their default. This does not establish an identical evaluation configuration for all four sizes.

## Local comparison

| Model | Published full BFCL-V4 | Local thinking off | Local thinking on |
|---|---:|---:|---:|
| Qwen3.5-0.8B | 25.3 | 18/40 (45%) | 27/40 (67.5%) |
| Qwen3.5-2B | 43.6 | 29/40 (72.5%) | 37/40 (92.5%) |
| Qwen3.5-4B | 50.3 | 32/40 (80%) | 34/40 (85%) |
| Qwen3.5-9B | 66.1 | Not run | Not run |

These are 240 scored attempts on the same 40 IDs, not 240 independent test questions. Off responses contained no reasoning; all 40 responses in each on cell contained reasoning. There were six length stops: 0.8B off 1, 0.8B on 3, 2B on 1 and 4B on 1. BFCL scored two length-stopped empty irrelevance answers as correct, one in 0.8B on and one in 2B on. If all length stops were instead treated as failures, those two cells would be 26/40 (65.0%) and 36/40 (90.0%); the other cells would be unchanged. The headline table preserves the official evaluator's decisions.

The local four-category percentage is a different metric from the published aggregate. It cannot validate or refute those published figures. It also does not reproduce the 2B-to-4B ordering in thinking mode on this small sample. Both modes must be tested on the intended application; these results do not establish memory-extraction quality.

Each category contributes ten cases, sampled once before generation.

| Model/mode | Simple /10 | Multiple /10 | Parallel /10 | Irrelevance /10 |
|---|---:|---:|---:|---:|
| 0.8B off | 3 | 2 | 3 | 10 |
| 0.8B on | 7 | 8 | 5 | 7 |
| 2B off | 8 | 8 | 4 | 9 |
| 2B on | 10 | 10 | 9 | 8 |
| 4B off | 8 | 9 | 6 | 9 |
| 4B on | 8 | 10 | 9 | 7 |

## Suggested replacement wording

For the Chapter 06 paragraph, replace its opening claim and model-card sentence with these two sentences:

> Qwen's model cards report full BFCL-V4 scores of 25.3, 43.6, 50.3 and 66.1 for 0.8B, 2B, 4B and 9B; on our 40-case subset, Q4_K_M builds of 0.8B, 2B and 4B scored 18/40, 29/40 and 32/40 with thinking off, and 27/40, 37/40 and 34/40 with thinking on. Our subset covers four tool-calling categories and retains BFCL's treatment of truncated answers, so these local counts do not reproduce the full scores or measure memory-extraction accuracy.

For the repeated Numbers row, replace its value and explanation with:

> Model-card BFCL-V4 scores are 25.3, 43.6, 50.3 and 66.1 for 0.8B, 2B, 4B and 9B. Our four-category subset produced 18 and 27 correct for 0.8B, 29 and 37 for 2B, and 32 and 34 for 4B, each out of 40 with thinking off and on, respectively; these are tool-calling counts, not full BFCL-V4 scores or extraction accuracy.

Keep the vendor and local columns side by side as in the table above, with the subset label and truncation footnote. The 9B local cell must remain “not run.” Chapters 07 and 18 need no BFCL replacement because they print no BFCL figure.

## Reproducibility and evidence

- `run.sh`, `reproduce.py`, `serve.sh` and `run.py` are the actual serving, generation and scoring code used here. `requirements.txt` pins the generation/scoring environment.
- `evidence/sample-manifest.json` fixes the seed, IDs, category population sizes and dataset hashes before generation. Each completed cell also saves its own manifest, including answer-file and scorer hashes.
- `evidence/source-provenance.json` records the official repository commit and byte-identical installed data/handler/scorer hashes. Dataset and harness license: Apache-2.0.
- `evidence/scorer-verification.json` records positive and negative AST and irrelevance probes. The good arguments pass and changed arguments fail; no-call irrelevance passes and a tool call fails.
- `results/20261121-main/{size}-{mode}/{category}/{id}.json` (2B/4B) and `results/20261121-small/0.8B-{mode}/{category}/{id}.json` (0.8B) retain each exact request, response, parsed result, metadata, elapsed time and official score. `summary.json` gives counts, truncations and reasoning presence. `manifest.json` fixes its source data.
- Hardware: Apple M3 Ultra, 96 GB unified memory for serving; 32-thread x86 CPU for all selection/scoring. The Linux GPU was not used. Runtime and model conversions are pinned in the README.

## Limits and interpretation

This run cannot validate or refute the four published aggregate scores. It tests only four static tool-calling categories at a quantization and deterministic decoding configuration different from, or not specified in, the model-card setup. The cards do not give enough detail to establish identical prompts, BFCL revision, server, quantization, seed, context limit or output budget. Our wrapper uses the upstream FC prompting/tool conversion and official evaluator rules, with no result-specific prompt changes and no hand-adjusted answers.

The same 40 sampled cases permit a small paired comparison of thinking on and off, but not a general claim about extraction, memory, all BFCL categories or hardware speed. The sample deliberately overrepresents some categories relative to the full dataset. One fixed seed and one generation per case provide no estimate of run-to-run variability.

## Failures, recovery and cleanup

On the initial host, the installed MLX CLI failed to import with `AttributeError: 'str' object has no attribute '__module__'` in tokenizer registration. No global packages were changed; llama.cpp was used instead.

Two early server starts occurred before the first weight download finished and failed with “tensor data is not within the file bounds.” No benchmark generation occurred on either failed start. The shipped serving script downloads to a `.part` file, verifies the immutable SHA-256, then renames it before loading, preventing that failure.

The initially assigned model host reported 91% system-wide memory free before loading. Its pre-existing model service subsequently reached a 73 GB total memory footprint; macOS reported memory-pressure warning and 37% free. This task's 2B server was stopped before any benchmark generation. The shared service was neither stopped nor reconfigured. The task's model files were deleted and its tunnel closed; an unpublished raw log records scratch absence, disk space and the surviving pre-existing process. Serving moved with explicit authorization to another Mac of the same hardware class, which reported 97% free and normal pressure before the benchmark. No machine identifiers are stored here.

Cleanup is confirmed for both successful run commands. an unpublished raw log and an unpublished raw log confirm both scratch directories were removed; the latter also explicitly confirms port 39730 is unoccupied. Each run's an unpublished raw log and an unpublished raw log records disk space and model-process listings. The final serving-host snapshot reports normal pressure, 85% system-wide memory free, about 150 GiB disk available and only the pre-existing model-service process in the filtered listing. Its task server is gone. The first host's separate cleanup evidence is retained as described above. No containers were created. Disk totals changed because the machines also served unrelated workloads; scratch absence and process/port checks establish task cleanup, not identical disk-use totals.

The required pair ran with `MODEL_SIZES=2B,4B` (the initial default) and the optional run used `MODEL_SIZES=0.8B`. The shipped one-command default runs all three sizes with the same `run.py`, official scoring code, sample IDs and generation settings. No inference or scoring failure interrupted either run, and all 240 raw attempts are retained. There is no unresolved infrastructure blocker; the remaining limitation is that this subset cannot reproduce the published aggregate. No repository files outside `benchmarks/bfcl/` were edited by this task, and no commit was made.

# Editor report: extraction evidence

Status: Semantic scoring completed.

This is a new public-data stress test of the narrow Chapter 06 walkthrough, not a reproduction of a published extraction score. No published extraction precision or recall exists for this setup. The chapter's BFCL-V4 values measure tool calling; its prior extraction evidence is a one-input demonstration and a ten-case synthetic fixture.

| Model, all Q4_K_M | Prior extraction evidence in book | Local valid JSON | Local schema accepted | Supported field claims | Covered reference units | Median / mean seconds |
|---|---|---:|---:|---:|---:|---:|
| coder-edited-q4_k_m | 2 reversals in 10 responses / 13 propositions | 297/300 | 297/300 | 108/351 (30.8%) | 27/309 (8.7%) | 0.322 / 0.354 |
| coder-stock-q4_k_m | 0 errors in 10 responses / 13 propositions | 288/300 | 288/300 | 102/333 (30.6%) | 21/309 (6.8%) | 0.341 / 0.453 |
| gemma-4-e4b-q4_k_m | None | 300/300 | 300/300 | 138/273 (50.5%) | 42/309 (13.6%) | 0.932 / 0.965 |
| qwen3.5-2b-q4_k_m | BFCL-V4 43.6; one direct schema fixture; Mem0 omitted a preference in two adds | 297/300 | 297/300 | 117/390 (30.0%) | 18/309 (5.8%) | 0.708 / 1.074 |
| qwen3.5-4b-q4_k_m | None; BFCL-V4 50.3 is tool calling | 237/300 | 237/300 | 78/189 (41.3%) | 51/309 (16.5%) | 1.033 / 2.457 |
| qwen3.5-9b-q4_k_m | None; BFCL-V4 66.1 is tool calling | 288/300 | 288/300 | 138/372 (37.1%) | 78/309 (25.2%) | 1.067 / 1.478 |

Each complete model cell has 100 unique turns repeated at temperature zero for seeds 7, 19, and 43. The three repeats are not 300 independent examples. Model order was fixed rather than counterbalanced, and one interrupted source-correction pilot was resumed. Server slots can reuse common prompt prefixes even with RAM prompt caching disabled; observed cached prompt tokens and output-token counts are reported in `results/verification.json`. No speed ranking or causal throughput improvement is inferred. Counts above pool requests for transparency; per-seed counts are in `results/semantic-summary.json` and raw output files. No independent-sample confidence interval is claimed. Latency includes the HTTP round trip and generation, excludes model download and server/model startup, and includes failed/truncated requests where a response arrived. Existing workloads on the serving host were not controlled.

Local judge validation: 30/30 exact entailment decisions; gate passed at the fixed 27/30 threshold. Support and coverage case counts are in `results/judge-validation-summary.json`.

The strongest limitation is the fixed schema. The task asked for broad fact precision and recall while preserving a `name/city/likes` walkthrough. These requirements cannot yield a representative general-purpose fact extractor comparison. The results below are supported field claims and complete reference-unit coverage under that narrow schema. An independently annotated, unrestricted-facts benchmark remains unresolved.

## Inventory of existing numerical evidence

### Chapter 06: Models table, paragraph after table

Book sentence: Qwen's own model cards report BFCL-V4 scores for Qwen3.5 of 25.3 at 0.8B, 43.6 at 2B, 50.3 at 4B and 66.1 at 9B.

Printed figures: 25.3 / 43.6 / 50.3 / 66.1. Source: Chapter 06 sources 12 and 15: pinned official Qwen3.5 model cards. [1](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/2fc06364715b967f1860aea9cf38778875588b17/README.md) [2](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/README.md)

Local correspondence: Tool calling, not extraction. No directly comparable published extraction score. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

qwen3.5-2b-q4_k_m: Valid JSON 297/300; accepted schema 297/300; median 0.708 seconds. Supported field claims 117/390; covered complete reference units 18/309.

qwen3.5-4b-q4_k_m: Valid JSON 237/300; accepted schema 237/300; median 1.033 seconds. Supported field claims 78/189; covered complete reference units 51/309.

qwen3.5-9b-q4_k_m: Valid JSON 288/300; accepted schema 288/300; median 1.067 seconds. Supported field claims 138/372; covered complete reference units 78/309.

Suggested replacement (at most two sentences): BFCL-V4 tests tool calling rather than memory extraction. Our separate test uses 100 public conversation turns and three seeds per extractor, with schema validity, supported field claims, and complete reference coverage reported separately.

### Chapter 06: Step 2, output and following sentence

Book sentence: The first call included loading the model. A second default call, with the model loaded, took 96.9 seconds and a second off call 3.4.

Printed figures: 109.4 s default with 1,735 reasoning characters; 6.2 s off with zero reasoning characters; repeats 96.9 s and 3.4 s. Source: First-party walkthrough, CPU Ollama 0.40.16, Qwen3.5 2B Q8_0, one input. 

Local correspondence: Local GGUF Q4_K_M thinking-off extraction latency and validity; hardware, quantization and runtime differ. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

qwen3.5-2b-q4_k_m: Valid JSON 297/300; accepted schema 297/300; median 0.708 seconds. Supported field claims 117/390; covered complete reference units 18/309.

Suggested replacement (at most two sentences): On a shared Apple M1 Ultra with 64 GB, the 2B Q4_K_M extractor returned valid JSON in 297 of 300 requests, with a median of 0.708 seconds per call. These preloaded direct calls do not repeat the CPU Ollama test.

### Chapter 06: Step 3, output and following sentence

Book sentence: Without the flag the same server answered after 31.2 seconds with content: '' and 1,924 characters of reasoning, because thinking used the whole 512-token limit.

Printed figures: 5.6 s clean off answer; default 31.2 s with no answer, 1,924 reasoning characters and 512-token limit; alternate off flag 1.6 s. Source: First-party walkthrough, CPU llama.cpp b12464, pinned Qwen3.5 2B Q4_K_M. [1](https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/tree/f6d5376be1edb4d416d56da11e5397a961aca8ae)

Local correspondence: Same 2B weight revision and schema; new dataset, Apple Metal and llama.cpp b12359. No thinking-on treatment in this benchmark. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

qwen3.5-2b-q4_k_m: Valid JSON 297/300; accepted schema 297/300; median 0.708 seconds. Supported field claims 117/390; covered complete reference units 18/309.

Suggested replacement (at most two sentences): The pinned 2B Q4_K_M file was also tested on 100 public turns over three seeds, returning valid JSON in 297 of 300 requests with a median of 0.708 seconds. That run used Apple Metal and llama.cpp build 12359, so its timing is a different setup from the CPU example.

### Chapter 06: Step 4, paragraph after read-back

Book sentence: In two runs of the add, the 2B model saved one fact and dropped "love coffee".

Printed figures: Two adds; one saved memory per add, preference omitted; add 42.5 s and busier rerun 120.5 s. Source: First-party Mem0 2.2.1 walkthrough, CPU. 

Local correspondence: Direct extraction only; no Mem0 retrieval, embedding, deduplication or persistence in the new benchmark. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

qwen3.5-2b-q4_k_m: Valid JSON 297/300; accepted schema 297/300; median 0.708 seconds. Supported field claims 117/390; covered complete reference units 18/309.

Suggested replacement (at most two sentences): The two Mem0 adds are a small demonstration rather than an extraction-accuracy measurement. The separate public-turn test measures direct extraction under the narrow walkthrough schema and does not test Mem0 storage behavior.

### Chapter 06: Latency and why saves run in the background

Book sentence: In the CPU test (step 4), one Mem0 add took 42.5 seconds: 35.7 seconds reading Mem0's own 8,242-token prompt at 231 tokens per second and 4.9 seconds generating 62 tokens.

Printed figures: 42.5 s total; 35.7 s prefill; 8,242 tokens; 231 tokens/s; 4.9 s decoding; 62 tokens. Source: First-party CPU Mem0 walkthrough, sources 2 and 25 describe pipeline. [1](https://github.com/mem0ai/mem0/blob/main/mem0/memory/main.py)

Local correspondence: Ancillary pipeline latency, not reproduced by direct extraction. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

qwen3.5-2b-q4_k_m: Valid JSON 297/300; accepted schema 297/300; median 0.708 seconds. Supported field claims 117/390; covered complete reference units 18/309.

Suggested replacement (at most two sentences): The CPU Mem0 demonstration took 42.5 seconds for a complete add, including its framework prompt. The public-turn experiment times only direct extraction and does not reproduce that pipeline.

### Chapter 06: Inkling 2 Mini, Tested paragraph

Book sentence: The schema check from step 3, with thinking switched off, did not return valid JSON within its 512-token limit and took 144.6 seconds.

Printed figures: 0 valid responses in one attempt, 512-token cap, 144.6 s. Source: First-party 8 GB NVIDIA GPU plus CPU-offload probe; source 46 documents packager setup. [1](https://unsloth.ai/docs/models/inkling-2-mini)

Local correspondence: Different model and another benchmark task; not rerun here. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

Suggested replacement (at most two sentences): The Inkling result is one failed schema check on the stated offload setup. Inkling was not included in the 100-turn small-model comparison.

### Chapter 06: Latency, first-party operating example

Book sentence: With a 9B local memory model on an Apple Silicon Mac, recall took about 2 seconds, a warm retain about 25 seconds, and a cold start of the memory service about 2 minutes.

Printed figures: 2 s recall / 25 s warm retain / 2 min cold service start. Source: Source 24, private first-party operator measurements, not public. 

Local correspondence: End-to-end memory service timing; not a public extraction benchmark and not reproduced here. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

qwen3.5-9b-q4_k_m: Valid JSON 288/300; accepted schema 288/300; median 1.067 seconds. Supported field claims 138/372; covered complete reference units 78/309.

Suggested replacement (at most two sentences): The approximate recall, retain, and cold-start times are private operating measurements. The public-turn test measures direct extraction and does not reproduce those memory-service timings.

### Chapter 06: Latency, Hindsight model paragraph

Book sentence: Hindsight reports a 167 ms median per request for a small decision model, against 1 to 7 seconds for a main model call.

Printed figures: 167 ms median / 1 to 7 s main-model call. Source: Source 26, vendor Hindsight Models blog. [1](https://hindsight.vectorize.io/blog/2026/11/03/hindsight-models)

Local correspondence: Different decision workload, not extraction; no numerical comparison is valid. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

qwen3.5-9b-q4_k_m: Valid JSON 288/300; accepted schema 288/300; median 1.067 seconds. Supported field claims 138/372; covered complete reference units 78/309.

Suggested replacement (at most two sentences): The vendor decision-model latency is not a memory-extraction latency. The public-turn experiment reports direct extraction timings on a shared Apple Silicon host.

### Chapter 07: Numbers, introductory paragraph and table

Book sentence: Every model saw the same ten messages once, in fresh requests with no conversation history. There are 13 expected propositions per model, including the two residence facts (past and current) and one message that should produce nothing.

Printed figures: 10 responses and 13 propositions per model; stock/edited invalid JSON 0/0, invalid schema 0/0, reviewed refusals 0/0, omissions 0/0, additions 0/0, reversals 0/2. Source: First-party ten-case walkthrough, pinned stock and edited Q4_K_M files; sources 4 and 5. [1](https://huggingface.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF/tree/1af47f78b1f9b0c242fabe43f7a365d5a67f3207) [2](https://huggingface.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-abliterated-GGUF/tree/823ab8183896816dec7d29899310b556e655ad73)

Local correspondence: Same two files, new 100-turn dataset and three seeds, Chapter 06 schema rather than Chapter 07 proposition schema. Cannot isolate the effect of editing. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

coder-stock-q4_k_m: Valid JSON 288/300; accepted schema 288/300; median 0.341 seconds. Supported field claims 102/333; covered complete reference units 21/309.

coder-edited-q4_k_m: Valid JSON 297/300; accepted schema 297/300; median 0.322 seconds. Supported field claims 108/351; covered complete reference units 27/309.

Suggested replacement (at most two sentences): In the public-turn test, the stock file returned valid JSON in 288 of 300 requests and the edited file in 297 of 300, across 100 turns and three seeds each. The narrow schema, different parameter counts, and local judge prevent attributing a quality difference to abliteration.

### Chapter 07: Scope and scale, Time and Planning

Book sentence: Time: one extraction call, including model loading, took 6.47 s, and reading its 216-byte note back took 0.24 ms with a warm file cache (anecdotal).

Printed figures: 6.47 s cold extraction / 216-byte note / 0.24 ms read-back / about 9 writes per minute. Source: First-party CPU walkthrough, Ollama 0.40.16, 8 inference threads. 

Local correspondence: Warm direct extraction latency only; no read-back timing and no derived production-throughput claim. The local model rows above are the corresponding direct extraction evidence; a blank comparison is not a failed reproduction.

coder-stock-q4_k_m: Valid JSON 288/300; accepted schema 288/300; median 0.341 seconds. Supported field claims 102/333; covered complete reference units 21/309.

coder-edited-q4_k_m: Valid JSON 297/300; accepted schema 297/300; median 0.322 seconds. Supported field claims 108/351; covered complete reference units 27/309.

Suggested replacement (at most two sentences): The earlier 6.47-second extraction included model loading. With the files preloaded on a shared Apple M1 Ultra, the new direct calls had medians of 0.341 seconds for stock and 0.322 seconds for edited, under a different prompt and schema.

## Suggested replacement text

Chapter 06: "We tested 6 4-bit extractors on 100 public conversation turns across three seeds, using the walkthrough's narrow schema and thinking switched off. Valid JSON did not guarantee supported facts, and this schema could not preserve most reference observations."

Chapter 07: "The stock and edited files were also tested on 100 public turns across three seeds, but their different parameter counts and the narrow schema prevent attributing a quality difference to abliteration. The ten-case correction result remains a fixture result rather than a general ranking."

Each suggested replacement is two sentences, uses plain American English, and contains no em dash. The detailed table should accompany the text. The result supports the chapter warning that schema validity does not establish factual accuracy, but cannot confirm the general recommendation of 4B or 9B memory writers.

## Differences and unresolved work

## What is measured

All calls use constrained decoding, so the JSON rate measures completed, parseable constrained outputs under the output cap, rather than unconstrained format following. The schema is exactly Chapter 06's three required string fields, `name`, `city`, and `likes`, with extra properties forbidden. No extra instructions define how the extractor should fill an unavailable field, so abstention wording is a prompt-design confound. The user prompt keeps its exact `Extract facts: ` prefix and replaces the original synthetic sentence with `SPEAKER says: TURN`. There is no added extraction system prompt. The literal original fixture cannot remain unchanged while testing 100 public turns. This input substitution, the speaker label, and pseudonymization are explicit differences. Thinking is disabled with `--chat-template-kwargs '{"enable_thinking":false}'` on the server and the same request-level setting. Output is capped at 512 tokens. The server context is 4,096 rather than the walkthrough's 16,384, because these are short direct prompts rather than Mem0's framework prompt.

The frozen data manifest pins the official LoCoMo repository and revision. Sampling seed 20261121 selects five turns with a case-insensitive love/like/enjoy/favorite marker and five other observation-bearing turns from each of ten conversations. Turns are at most 400 characters, and the sampled observation must cite a single source turn. This is a lexical stratum, not a certified preference category. Speaker names, short nickname prefixes, and camel-case personal names are consistently pseudonymized before inference. Artificial identifiers may change model behavior in the required name field. No images, URLs, timestamps, prior sessions, QA questions, or answer labels go to the extractor.

The official README says its observations were generated with a model. They are not human-annotated extraction gold. An agent inspected all 100 sampled source/reference pairs and recorded source-only corrections in `data/reference_audit.json`, removing unavailable context and fixing attribution or textual errors. The shipped sample contains 103 reference units; some are multi-clause observations, so these are not atomic fact counts. Reference coverage measures preservation of those units, not whether an application should retain every observation. No independent human review of these corrections is claimed. These limits prevent treating this as a definitive general extraction benchmark. The public dataset may have appeared in model training; no contamination audit was conducted.

## Matching rule

The `name` field is bookkeeping and is not credited as a remembered fact. Each non-abstaining `city` field becomes `NAME lives in VALUE`; each non-abstaining `likes` field becomes `NAME likes VALUE`. Empty strings and the predeclared case-insensitive placeholders in `judge.ABSTAIN` produce no claim. Other strings, including malformed-looking strings in otherwise valid JSON, remain claims. A wrong extracted name changes the attribution of both claims. A rejected response yields no accepted claims and receives zero reference coverage.

Supported field-claim precision is the fraction of these complete field claims supported by the source alone. One unsupported clause, wrong subject, polarity, amount, or time makes that whole field claim unsupported. Reference-unit recall is the fraction of full reference observations entailed by the union of accepted field claims. Partial overlap earns no coverage; a supported short claim can therefore earn precision but no recall. These two measures use different units and are not presented as a single atomic-fact F1 score. A city mention does not establish residence, and a goal or offer does not establish a preference.

Matching uses local Qwen3.5-9B Q4_K_M, temperature zero, seed 7, thinking off, with its exact prompt and JSON schema in `judge.py`. It differs from LoCoMo's published QA scoring, which uses normalized, stemmed token overlap and other QA metrics. LoCoMo does not publish this extraction scorer. This benchmark has no hosted generation or judge calls. An initial matcher interface attempt stopped on an out-of-range index before any semantic score was produced. The first repair supplied explicit zero-based index objects and restricted response indices in the schema, but the paired protocol then failed validation: 30/30 support decisions and only 11/30 coverage decisions matched. Those complete failed development results remain in `results/matching-development/`. No semantic scores from that protocol are used. The final protocol uses two separate premise-only entailment calls: source text to predicted field claims for support, then predicted field claims alone to reference units for coverage. The original source is absent from the coverage request, and its absence is checked by `verify_results.py`. The semantic inclusion rule did not change. All later raw judge attempts are saved before parsing. The initial failing second reply was not retained by the original parser, so that historical raw reply is unavailable; its exception and the first successful reply remain in `results/validation-pilot/`. The final gate is at least 27 exact entailment decisions on 30 fresh, hand-checkable cases from ten source turns distinct from the development set. The cases include 20 source-support checks and 10 incomplete-premise coverage checks. This is protocol validation after development, not an independently annotated judge-accuracy benchmark. Labels were authored by the implementing agent, not by an independent human annotator. Correct, incomplete, negated, wrong-quantity, and wrong-time examples are preserved with their exact premise, candidate hypothesis, expected label, full request, and raw judge response. The final validation set is small and shares source turns with the evaluated sample, although its ten turns differ from those used for matcher development. The judge is also one of the tested extractors, so shared-model bias is possible. Every semantic claim must be read with these limitations.

The three required fields cannot represent most events, dates, occupations, health statements, or temporal corrections in LoCoMo. Low recall here is heavily constrained by the chapter's schema. This experiment can expose unsupported fields and omissions in this exact walkthrough; it cannot establish which model is best with a general facts schema or isolate an abliteration effect. The edited and stock files also differ in parameter count, file size, and quantizer provenance. No explicit adult or refusal-oriented corpus is included, so this cannot measure the edit's intended refusal reduction.


Recorded execution failures: []. Raw truncated outputs remain in the per-model JSONL files. No bad response was retried or discarded to improve a score. Four source inputs changed after a nickname-mask bug was found; 16 affected earlier trials are retained in `results/pilot/obsolete-input-outputs.jsonl` and excluded by input ID, while unchanged completed trials were resumed. `results/pilot/exclusion.json` records the old and corrected sample hashes. The interrupted pilot run and its successful cleanup are retained under `results/pilot/`. Judge decisions have not received independent human adjudication. These results cannot establish a causal effect of weight editing or compare a general memory writer prompt with this narrow schema.

Resolved setup issues: the first source fetch used lowercase filenames, which returned HTTP 404 before the official tree supplied `README.MD` and `LICENSE.txt`; an early readiness probe used the local extraction port instead of the tunnel port; and a draft formatter had a quoting error. The resumed driver uses the corrected readiness URL, and the formatter compiles and renders from the preserved results. The source-mask correction and excluded raw pilot rows are documented above.

## Cleanup and scope

Cleanup evidence: {"driver_tunnel_closed": true, "monitor_stopped": true, "owned_server_stopped": true, "remote_scratch_absent": true}. See sanitized disk and process snapshots in `results/preflight.json`, `results/before-driver.txt`, and `results/after-cleanup.txt`. Independent checks: observed server process absent=True, remote task port unused=True, local task listeners=[], local scratch absent=True, voice listener PIDs unchanged=True. Full proof: `results/final-cleanup.json`.

Only files under `benchmarks/extraction/` were written in the repository. No chapter was edited and no commit was made. The local scratch directory was used for primary-source inspection and is removed separately after report generation. Its removal and closure of the initial exploratory tunnel are recorded in `results/final-cleanup.json`. No wiki changes were made because this task explicitly limited writable territory and prohibited commits.

# Editor report: general-schema extraction benchmark

| Q4_K_M writer | Valid % | Facts/turn | Precision % | Recall % | Contradiction % | Median seconds |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.5 2B | 98.3 [97.0, 99.7] | 1.54 [1.35, 1.73] | 94.8 [92.7, 96.5] | 34.3 [29.7, 39.1] | 0.6 [0.0, 1.4] | 0.60 [0.53, 0.63] |
| Qwen3.5 4B, default | 100.0 [100.0, 100.0] | 1.60 [1.44, 1.75] | 95.8 [93.3, 98.0] | 43.9 [40.1, 47.7] | 0.4 [0.0, 1.0] | 1.42 [1.24, 1.58] |
| Qwen3.5 4B, repeat 1.1 | 100.0 [100.0, 100.0] | 1.51 [1.37, 1.65] | 96.3 [93.8, 98.2] | 39.4 [35.2, 43.7] | 0.4 [0.0, 1.1] | 1.68 [1.54, 1.77] |
| Qwen3.5 9B | 99.7 [99.0, 100.0] | 2.21 [2.03, 2.39] | 97.1 [95.5, 98.5] | 50.9 [45.9, 56.3] | 0.3 [0.0, 0.9] | 3.02 [2.73, 3.30] |
| Gemma 4 E4B | 100.0 [100.0, 100.0] | 2.36 [2.23, 2.49] | 97.9 [96.9, 98.8] | 57.6 [53.2, 62.0] | 0.4 [0.0, 1.1] | 2.58 [2.44, 2.76] |
| Coder stock | 92.0 [89.3, 94.3] | 2.58 [2.37, 2.79] | 85.6 [82.9, 88.3] | 55.5 [49.5, 61.6] | 1.0 [0.3, 1.9] | 0.92 [0.87, 0.98] |
| Coder edited | 97.4 [95.8, 98.8] | 1.80 [1.61, 1.98] | 85.3 [81.5, 88.6] | 42.5 [36.7, 48.1] | 1.3 [0.6, 2.0] | 0.46 [0.45, 0.48] |
| Empero Qwen3.8 2B | 91.0 [88.3, 93.7] | 2.69 [2.48, 2.93] | 81.1 [74.8, 87.0] | 52.4 [47.9, 57.0] | 0.6 [0.0, 1.4] | 1.32 [1.23, 1.41] |
| Empero Qwen3.8 4B | 100.0 [100.0, 100.0] | 1.05 [0.87, 1.24] | 95.6 [91.6, 98.5] | 25.3 [20.7, 29.9] | 0.3 [0.0, 1.1] | 0.42 [0.41, 0.64] |
| Empero Qwen3.8 9B | 100.0 [100.0, 100.0] | 0.93 [0.76, 1.09] | 95.0 [90.5, 98.6] | 22.4 [17.9, 26.7] | 0.4 [0.0, 1.1] | 0.62 [0.61, 0.64] |

All entries have 95% clustered intervals; N is 300 unique turns × three seeds per arm. Methods, count denominators, licence pins, decoder diagnosis and limits are in [README.md](README.md).

Local judge: Qwen3.5 9B Q4_K_M, thinking off, seed 7, temperature zero. Fixed calibration agreement was 58/60 (96.7%; nominal Wilson 95% 88.6–99.1%). Binary support agreement was 60/60 (nominal Wilson 95% 94.0–100.0%); inspect the retained pairs for three-class disagreements. These labels and the source reference review were manually authored by the implementing agent, not independent human adjudicators. Judge self-family bias and calibration-set selection remain limitations. Support/contradiction use the original source; coverage uses only written facts plus the supplied speaker identifier binding in a separate call, so source text cannot fill an omission. The binding resolves unqualified first-person and generic speaker aliases, preserves explicit other identifiers and plural groups, and was frozen after manual review but before actual semantic scoring. The writer prompt and schema never changed. [Matcher protocol](v2/matching-protocol.json). See [the protocol](v2/README.md), validation pairs and raw replies.

On the separately frozen random 60 pairs among unique matching inputs from actual writer outputs, agreement was 53/60 (88.3%; nominal Wilson 95% 77.8–94.2%). Expected class counts were {'supported': 49, 'unknown': 11}; this prevalence matters when interpreting agreement. Labels were frozen before actual matching decisions, and model labels were hidden during review. They were authored by the implementing agent, not an independent human reviewer. Ambiguous scope judgments are retained with notes. The constructed calibration uses one hypothesis per call; this actual audit samples decisions from the main multi-hypothesis calls and is the more relevant real-output check. Given this audit agreement, small model gaps should remain provisional. These cases informed the speaker-binding adjustment, so this is not an untouched held-out validation set. The random audit contains no expected contradictions; real contradictory-output detection therefore remains weakly validated, despite the balanced constructed calibration. See the selected pairs and labels and decisions and confusion counts.

The random source audit found material detail unsupported by the individually cited turn in 17 of 60 original model-generated LoCoMo observation units (28.3%, nominal Wilson 95% 18.5–40.8%; 57 unique source turns). These units added context, entities, preferences or dates not established by that turn. This source-only check does not establish that the detail is false elsewhere in the full conversation. The final 746 reference facts were authored afresh from the source. The audit measures those annotations on this selected corpus, not a universal error rate. Independent human review of our new extraction references remains unresolved. [LongMemEval’s primary paper](https://arxiv.org/html/2410.10813v2) describes human-curated questions and evidence locations and human-edited simulated sessions; its QA answers are not reused as extraction gold. The generated-annotation audit targets LoCoMo’s model-written observations.

The M1 pilot retains 1305 writer responses, and the first M3 pilot retains 1273. Repeated M1 pressure pauses led to the first move; the first M3 then crossed a sibling deadline-bound run's 40% free-memory threshold, so its owned server and scratch were removed and serving moved again. All 9,000 main writer requests and semantic judgments restart on the final M3 Ultra, 96 GB instance, labeled M3 main in every request record. The 50 preselected Qwen3.5 4B repeat-1.1, seed-7 controls yielded 50/50 identical strings and 50/50 identical parsed objects between the former and final M3 instances. Paired evidence retains separate timings. Additional complete seed-7 comparisons against the M1 retained 299/300 exact strings for Qwen3.5 9B and 298/300 for Empero 2B, including one Empero validity change. These differences do not isolate a hardware effect from concurrent numerical execution. Additional paired evidence. Main quality and timing use only the final instance. Earlier controls and all responses remain archived. M1 cleanup and former M3 cleanup record scratch removal; the M1 voice listener PIDs were unchanged.

## 4B diagnosis

An exact M1 Ultra seed-7 replay of all 100 version-one requests produced identical output strings and exactly the same 21 failure IDs: 79/100 complete outputs (79.0%, nominal Wilson 95% 70.0–85.8%). All failures ended at the 512-token cap, with no reported reasoning. Most contain repeated phrases; others degenerate into long enumerations inside a string field. Doubling the cap to 1,024 rescued 0/21 selected failures (nominal Wilson 95% 0–15.5%). Changing **only** `repeat_penalty` from 1.0 to 1.1, while retaining the original 512-token cap, produced 100/100 complete outputs (nominal Wilson 95% 96.3–100%). The thinking-off rendered prefix contains a closed think block; the thinking-on control leaves it open. This supports decoder-sensitive degenerate continuation as the failure mode, rather than reasoning tokens consuming the cap or a silently ignored thinking-off template.

The v2 default and repeat-1.1 arms use identical weights, prompt, schema and common 1,024-token cap. The fixed arm changes only the repetition penalty. The diagnostic does not establish that this penalty is optimal for other models, prompts or distributions. On the general-schema task, default 4B completed 900/900 outputs and repeat-1.1 completed 900/900; repeat-1.1 minus default recall was -4.6 percentage points [95% paired interval -7.5, -1.6]. The narrow-prompt repair is therefore not a blanket recommendation for the general writer prompt. Raw evidence: replay, summary, template controls, exact replay check.

## What the comparisons support

The stock and edited coder rows describe two files marketed as Qwen2.5-Coder 1.5B. Their serialized counts are 1,543,714,304 and 1,777,088,000 elements, but the difference is exactly one 1,536 × 151,936 output head: the stock GGUF has no separate output tensor, while the edited GGUF stores one. Both have the same 28-layer, 1,536-wide backbone dimensions; the count difference does not establish a larger backbone. More directly, 33 shared tensors use different quantization types, including Q6_K versus Q4_K for the token embeddings. Therefore this is a comparison of downloadable artifacts, not a controlled edit-only experiment; a gap cannot be attributed causally to abliteration, refusal removal or editing itself. Header evidence, comparison evidence and the [pinned type definitions](https://github.com/ggml-org/llama.cpp/blob/b1b770d90/ggml/include/ggml.h#L197) document the distinction. This refines version one’s parameter-count caveat. The sample does not test refusal reduction or adult-content handling. Source contradiction is not the same metric as the ten-case Chapter 07 correction fixture's reversal count.

Edited minus stock: validity +5.4 percentage points [95% paired interval +3.0, +7.8], precision -0.3 percentage points [95% paired interval -3.5, +2.9], and recall -13.0 percentage points [95% paired interval -17.0, -8.7]. The edited artifact completed more outputs but wrote fewer facts and covered fewer references; the precision interval spans both directions. These are file-level comparisons, not isolated editing effects.

| Chapter 20 writer | Prior pipeline QA | New source precision % | New reference recall % |
|---|---:|---:|---:|
| Empero 2B | 8/24 | 81.1 [74.8, 87.0] | 52.4 [47.9, 57.0] |
| Empero 4B | 12/24 | 95.6 [91.6, 98.5] | 25.3 [20.7, 29.9] |
| Empero 9B | 12/24 | 95.0 [90.5, 98.6] | 22.4 [17.9, 26.7] |

Empero Qwen3.8 4B minus Empero Qwen3.8 2B: -27.0 percentage points of recall, paired 95% interval [-33.1, -21.0]. Empero Qwen3.8 9B minus Empero Qwen3.8 4B: -2.9 percentage points of recall, paired 95% interval [-7.6, +2.0]. The Empero size comparison is a precision/coverage tradeoff under this fixed prompt: 2B: 0/900 valid empty arrays (0.0%; clustered 95% 0.0–0.0%), including 0 requests with nonempty references; 4B: 510/900 valid empty arrays (56.7%; clustered 95% 52.0–61.0%), including 498 requests with nonempty references; 9B: 645/900 valid empty arrays (71.7%; clustered 95% 66.7–76.3%), including 633 requests with nonempty references. The larger files often return no memories even when the turn has reference facts. Empty arrays are schema-valid and write zero facts; they are not syntax failures. These counts explain the immediate recall loss, not why the weights abstain. Prompt/template sensitivity and weight behavior are not separated. Descriptive empty-output audit. These are descriptive file comparisons; training and architecture are not held constant across sizes.

The Empero writer rows use the exact three Chapter 20 revisions, recorded in [models.json](v2/models.json). Chapter 20's 2B/4B/9B writers scored **8/24, 12/24 and 12/24** downstream QA answers with a fixed 2B answerer. This benchmark measures single-turn writer precision and reference recall, not memory insertion, retrieval or answer quality. It changes the prompt/schema, data, output cap (1,024 rather than 768), hardware (Metal rather than CPU), server build (12359 rather than 12464) and concurrency. Its size comparison can inform writer selection on these turns; it cannot predict those pipeline QA scores or prove that a larger writer improves the whole pipeline. There is no published extraction score for this newly defined benchmark. Chapter 06 BFCL-V4 scores (2B 43.6, 4B 50.3, 9B 66.1) concern tool calling and are not directly comparable to these rates.


## Suggested book sentences

Chapter 06: “On 300 public conversation turns across three seeds, a local 9B judge rated Qwen3.5 2B at 94.8 percent source-support precision and 34.3 percent reference recall with a general fact schema. The 9B file reached 97.1 and 50.9 percent respectively, with clustered intervals and separate validity and contradiction rates in the benchmark table.”

Chapter 07: “On the same 300 public turns, the local judge estimated the stock coder at 85.6 percent source-support precision and 55.5 percent reference recall, versus 85.3 and 42.5 percent for the edited file. Their tensor quantization and serialization differ, so any gap cannot be attributed to abliteration alone.”

Chapter 20: “On 300 public turns, a local 9B judge estimated source-support precision for the same 2B, 4B and 9B Empero writers at 81.1, 95.6 and 95.0 percent, with reference recall of 52.4, 25.3 and 22.4 percent. These writer-only results do not reproduce or predict the pipeline’s 8, 12 and 12 correct answers out of 24.”

## Inventory of existing Chapter 06 and 07 figures

The inventory below preserves the chapter text and primary-source links inspected for version one. Version one’s narrow-schema measurements remain archived separately. These figures do not become extraction ground truth merely because they concern the same model.

### Chapter 06: Models table, paragraph after table

Book sentence: Qwen's own model cards report BFCL-V4 scores for Qwen3.5 of 25.3 at 0.8B, 43.6 at 2B, 50.3 at 4B and 66.1 at 9B.

Printed figures: 25.3 / 43.6 / 50.3 / 66.1. Source: Chapter 06 sources 12 and 15: pinned official Qwen3.5 model cards. [1](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/2fc06364715b967f1860aea9cf38778875588b17/README.md) [2](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/README.md)

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

### Chapter 06: Step 2, output and following sentence

Book sentence: The first call included loading the model. A second default call, with the model loaded, took 96.9 seconds and a second off call 3.4.

Printed figures: 109.4 s default with 1,735 reasoning characters; 6.2 s off with zero reasoning characters; repeats 96.9 s and 3.4 s. Source: First-party walkthrough, CPU Ollama 0.40.16, Qwen3.5 2B Q8_0, one input. 

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

### Chapter 06: Step 3, output and following sentence

Book sentence: Without the flag the same server answered after 31.2 seconds with content: '' and 1,924 characters of reasoning, because thinking used the whole 512-token limit.

Printed figures: 5.6 s clean off answer; default 31.2 s with no answer, 1,924 reasoning characters and 512-token limit; alternate off flag 1.6 s. Source: First-party walkthrough, CPU llama.cpp b12464, pinned Qwen3.5 2B Q4_K_M. [1](https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/tree/f6d5376be1edb4d416d56da11e5397a961aca8ae)

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

### Chapter 06: Step 4, paragraph after read-back

Book sentence: In two runs of the add, the 2B model saved one fact and dropped "love coffee".

Printed figures: Two adds; one saved memory per add, preference omitted; add 42.5 s and busier rerun 120.5 s. Source: First-party Mem0 2.2.1 walkthrough, CPU. 

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

### Chapter 06: Latency and why saves run in the background

Book sentence: In the CPU test (step 4), one Mem0 add took 42.5 seconds: 35.7 seconds reading Mem0's own 8,242-token prompt at 231 tokens per second and 4.9 seconds generating 62 tokens.

Printed figures: 42.5 s total; 35.7 s prefill; 8,242 tokens; 231 tokens/s; 4.9 s decoding; 62 tokens. Source: First-party CPU Mem0 walkthrough, sources 2 and 25 describe pipeline. [1](https://github.com/mem0ai/mem0/blob/main/mem0/memory/main.py)

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

### Chapter 06: Inkling 2 Mini, Tested paragraph

Book sentence: The schema check from step 3, with thinking switched off, did not return valid JSON within its 512-token limit and took 144.6 seconds.

Printed figures: 0 valid responses in one attempt, 512-token cap, 144.6 s. Source: First-party 8 GB NVIDIA GPU plus CPU-offload probe; source 46 documents packager setup. [1](https://unsloth.ai/docs/models/inkling-2-mini)

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

### Chapter 06: Latency, first-party operating example

Book sentence: With a 9B local memory model on an Apple Silicon Mac, recall took about 2 seconds, a warm retain about 25 seconds, and a cold start of the memory service about 2 minutes.

Printed figures: 2 s recall / 25 s warm retain / 2 min cold service start. Source: Source 24, private first-party operator measurements, not public. 

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

### Chapter 06: Latency, Hindsight model paragraph

Book sentence: Hindsight reports a 167 ms median per request for a small decision model, against 1 to 7 seconds for a main model call.

Printed figures: 167 ms median / 1 to 7 s main-model call. Source: Source 26, vendor Hindsight Models blog. [1](https://hindsight.vectorize.io/blog/2026/11/03/hindsight-models)

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

### Chapter 07: Numbers, introductory paragraph and table

Book sentence: Every model saw the same ten messages once, in fresh requests with no conversation history. There are 13 expected propositions per model, including the two residence facts (past and current) and one message that should produce nothing.

Printed figures: 10 responses and 13 propositions per model; stock/edited invalid JSON 0/0, invalid schema 0/0, reviewed refusals 0/0, omissions 0/0, additions 0/0, reversals 0/2. Source: First-party ten-case walkthrough, pinned stock and edited Q4_K_M files; sources 4 and 5. [1](https://huggingface.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF/tree/1af47f78b1f9b0c242fabe43f7a365d5a67f3207) [2](https://huggingface.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-abliterated-GGUF/tree/823ab8183896816dec7d29899310b556e655ad73)

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

### Chapter 07: Scope and scale, Time and Planning

Book sentence: Time: one extraction call, including model loading, took 6.47 s, and reading its 216-byte note back took 0.24 ms with a warm file cache (anecdotal).

Printed figures: 6.47 s cold extraction / 216-byte note / 0.24 ms read-back / about 9 writes per minute. Source: First-party CPU walkthrough, Ollama 0.40.16, 8 inference threads. 

Local correspondence: The general writer table above supplies new extraction evidence for the tested model files. These published or walkthrough numbers measure a different task, fixture, latency boundary or runtime and should retain their original scope. No like-for-like reproduction is claimed.

## Chapter 20 existing figures

The same 2B/4B/9B Empero Q4_K_M files yielded 8/24, 12/24 and 12/24 downstream answers in the fixed-2B-answerer pipeline. This task did not rerun that pipeline; its corresponding local figures are the three Empero writer rows above. Exact revisions and SHA-256 file hashes are preserved in `v2/models.json`.

## Raw evidence and verification

Requests and complete outputs: `v2/results/writers/ARM.jsonl`; separate judge calls: `v2/results/judge-attempts.jsonl`; immutable decision links: `v2/results/judge-cache.jsonl`; per-request scores: `v2/results/scored.json`; counts and intervals: `v2/results/summary.json`; memory events: `v2/results/host-events.jsonl`; schedule: `v2/results/schedule.json`; final verification: `v2/results/verification.json`. No quality failure is silently retried. Interrupted transport attempts are logged separately.

## Unresolved limits and cleanup

Reference annotations, the 60-unit generated-reference audit and the 60-pair judge calibration were manually checked by the implementing agent, with no independent human adjudication. Generalization beyond these stratified short English turns, synthetic/personal-conversation styles, pseudonymization (including some capitalized generic terms), memory usefulness, category-label accuracy and downstream memory QA remain unmeasured. The local judge may favor its own model family. Shared-host timing and two simultaneous requests limit speed comparisons; latency intervals do not model host-load changes. Training-data exposure to these public datasets was not audited.

Final cleanup: `{"all_recorded_remote_server_pids_absent": true, "benchmark_containers_remaining": [], "driver_exited": true, "earlier_m3_cleanup": {"phase": "complete", "remote_lab_absent": true, "server_stopped": true, "serving_hardware": "Apple M3 Ultra, 96 GB", "serving_instance": "M3 pilot", "tunnel_stopped": true}, "local_scratch_absent": true, "local_task_port_unused": true, "local_task_tunnel_pids": [], "m1_migration_cleanup": {"phase": "complete", "remote_lab_absent": true, "server_stopped": true, "serving_hardware": "Apple M1 Ultra, 64 GB", "tunnel_stopped": true}, "m1_voice_pids_unchanged": true, "main_quality_and_timing_hardware_classes": ["Apple M3 Ultra, 96 GB"], "model_weight_files_in_repository": 0, "no_commits_or_chapter_edits_by_task": true, "no_containers_started_by_task": true, "no_global_installations": true, "no_scoring_host_gpu_inference": true, "post_exit_checked_utc": "2026-11-22T02:19:03.938661+00:00", "protected_after": {"7860": 769, "8100": 766, "8200": 784, "8765": 339, "8766": 93331, "8888": 778, "9102": 1007}, "protected_before": {"7860": 769, "8100": 766, "8200": 784, "8765": 339, "8766": 93331, "8888": 778, "9102": 1007}, "protected_omlx_pids_checked": [93331], "protected_omlx_pids_unchanged": true, "protected_ports_checked": [8765, 8766, 8100, 8888, 9102, 8200, 7860], "protected_service_listener_pids_unchanged": true, "remote_lab_absent": true, "remote_task_port_unused": true, "server_ports_checked": [39744], "serving_hardware": "Apple M3 Ultra, 96 GB", "serving_instance": "M3 main"}`. See the linked before/after snapshots and independent check in README. No commits or chapter edits were made.

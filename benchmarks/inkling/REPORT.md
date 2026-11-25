# More loop passes help a memory reader only when the evidence is already in its context

Experiments on Thinking Machines Lab's open looped models, run in November 2026 on one Mac Studio (M3 Ultra, 96 GB) and on the Tinker fine-tuning service. Models: `thinkingmachines/Inkling-2-Mini` (three passes through its core layers) and `thinkingmachines/TML-d24-varloop-research` (same architecture, any pass count at inference). Both are Apache 2.0.

Three results held up. Five did not, or were mixed. All of them are below, with sample sizes, intervals and links to the raw files. Every study has its own write-up with limits; this page is the index.

## What held up

### 1. Loop depth helps with good context and does not replace retrieval

150 LongMemEval questions, three kinds of context, the variable-loop model at 1, 2, 3 and 5 passes. Pre-registered. Reader replay over saved contexts, not the official LongMemEval protocol.

| Passes | Oracle sessions | BM25 | Dense |
|---|---|---|---|
| 1 | 63.3% | 56.0% | 54.7% |
| 2 | 64.7% | 48.0% | 47.3% |
| 3 | 74.0% | 54.7% | 59.3% |
| 5 | 72.7% | 54.0% | 56.7% |

- With the right sessions in context, going from 1 to 5 passes adds 9.3 points (95% interval +2.7 to +16.0).
- With retrieved context there is no gain: BM25 -2.0 (-9.3 to +5.3), dense +2.0 (-5.3 to +9.3).
- The gap between oracle and BM25 context grows with depth, from 7.3 to 18.7 points. Depth does not make up for missing evidence.
- Two passes was the worst depth in both retrieved lanes. We have no explanation for that.

150 questions per cell is about +/-8 points, so only the oracle gain is established. Details: [research/memory-loops/RESULTS.md](research/memory-loops/RESULTS.md).

### 2. Fine-tuning on short answers removes the model's reasoning, and thinking effort does not bring it back

A LoRA adapter trained on Tinker to answer memory questions with two-to-four-token answers scored 100% on its own held-out test and then lost to the untrained model on a harder one (360 generated questions over long histories: revised facts, two-step joins, date gaps, abstention).

| Model | 256-token cap | 512 | 1,024 | 2,048 | Mean tokens used at 2,048 |
|---|---|---|---|---|---|
| Stock | 25.3% | 63.9% | 88.1% | 99.4% | 496 |
| LoRA on the stock model's own verified reasoning + answer | 32.2% | 68.6% | 90.8% | 98.6% | 507 |
| LoRA on the shortest correct of four reasoning traces | 35.0% | 70.3% | 92.8% | 98.9% | 459 |
| LoRA on answers only (same questions) | 51.9% | 55.6% | 54.2% | 53.3% | 7 |

- Answer-only targets cost 45.3 points against reasoning targets at the 2,048 cap (40.0 to 50.6). The answer-only adapters also repeat a constant from training ("17 days") on up to 32 of 60 date-gap questions.
- Raising thinking effort at inference from 0 to 0.9 left the answer-only adapters at 7 to 8 tokens and 45 to 56%. The shortcut is in the weights.
- Training on the model's own reasoning keeps accuracy and saves nothing. Selecting the shortest correct trace shortens output by about 9%, not the 50% we pre-registered as success.
- The first test saturated by update 50 for every LoRA setting we tried (attention only, MLP only, all groups, rank 4 and 32), so it could not rank them. That is a finding about the test.

One seed per arm, synthetic data, one model. Details: [research/tinker/WRITEUP.md](research/tinker/WRITEUP.md), [research/tinker/RESULTS.md](research/tinker/RESULTS.md).

### 3. Eight commands trained into the weights cost about a tenth of the prompt, and no accuracy on familiar phrasing

A LoRA adapter that calls eight one-line shell commands with no tool text in its prompt, against the stock model with the same commands declared natively.

| Blind test, 120 requests written without sight of the training data | Adapter | Stock, native tools |
|---|---|---|
| First command right (of 80), two samplings | 71, 70 | 77, 78 |
| No-tool requests answered without a call (of 40) | 36, 35 | 39, 39 |
| Extra calls | 11, 10 | 65, 48 |
| Prompt tokens per request | about 175 | about 2,150 |

- On requests built from the training templates the adapter is level or slightly ahead (+2.0 to +4.4 points). On unfamiliar phrasing it trails native declaration by 7.5 to 10 points; one of the two intervals excludes zero.
- It uses 8 to 9% of the prompt tokens and makes far fewer extra calls. A service that caches the tool declaration narrows the token saving.
- The first adapter called a tool on 23 of 30 unfamiliar no-tool requests, inventing commands. Retraining with many kinds of no-tool request, independent phrasings and near-miss pairs brought that to 4 or 5 of 40. It still varies between training runs.
- Our first three comparisons flattered the adapter because the stock model's tools were set up badly. The history is kept in the write-up.

Eight fixed commands, a fake backend, one seed per run. Details: [research/tools-trained/RESULTS.md](research/tools-trained/RESULTS.md). Blind test: [research/tools-blind/](research/tools-blind/).

## What did not work, or showed nothing

| Study | Result | Write-up |
|---|---|---|
| Refusal rate against pass count (12 harmful + 12 benign held-out prompts per cell) | No change: 9 to 10 of 12 harmful prompts refused at 1, 2, 3 and 5 passes | [research/refusal-loops/RESULTS.md](research/refusal-loops/RESULTS.md); per-layer measurements in [research/refusal-loops/DIRECTION-LAYERS.md](research/refusal-loops/DIRECTION-LAYERS.md) |
| Swapping the message passed between loop passes on two-hop questions | Pre-registered primary endpoint -0.003 logits (-0.015 to +0.010): no effect. Zeroing every message hurt on one template and not on the held-out one | [research/message-lab/RESULTS.md](research/message-lab/RESULTS.md) |
| Drafting with one pass and verifying with three | Slower than plain three-pass decoding, 0.61 to 0.78 times the speed, and its output matched plain decoding on only 21 to 26 of 40 prompts, which we did not resolve | [research/loop-decoding/RESULTS.md](research/loop-decoding/RESULTS.md) |
| Predicting from the first pass whether more passes will change the output (160 of 400 registered items, answer started without visible reasoning) | Mixed. Within one prompt type a probe on the first-pass state beats entropy for code (AUC 0.927 against 0.863) and recall (0.881 against 0.724), and not for the other two types. Trained on three types and tested on the fourth, no probe beats entropy. 28 of 78 scoreable answers changed between one and three passes | [research/flip-probes/RESULTS.md](research/flip-probes/RESULTS.md) |
| The bundled draft model on a Mac | 41.3% of drafted tokens accepted, generation 16.7% faster, about 5% more energy per correct answer | [research/efficiency/RESULTS.md](research/efficiency/RESULTS.md) |

Throughput on this machine falls roughly as one over the pass count: 47.0, 30.0, 22.1 and 14.7 tokens per second at 1, 2, 3 and 5 passes.

## Baseline

Stock Inkling 2 Mini, oMLX mixed-precision build, reader replay: LongMemEval 84.9% with oracle sessions (180 of 212), 70.0% with BM25, 64.0% with dense retrieval. A LoCoMo run was stopped part-way: 100 of 145 questions correct (69.0%, 61.0 to 75.9) with the full conversation in context, first five conversations only, so it is not a benchmark figure.

## Upstream

- [thinking-machines-lab/tinker-cookbook#1025](https://github.com/thinking-machines-lab/tinker-cookbook/pull/1025): expose LoRA target groups in the SFT, RL and DPO trainer configs.

## Reading the numbers

- Intervals are 95%: Wilson for single rates, paired bootstrap (10,000 draws) for differences.
- Studies marked pre-registered had their question, metrics and null band committed before the run. Where a comparison was added afterwards, the write-up says so.
- The Tinker results were recomputed from the raw traces by an independent pass, which matched every figure.
- Raw traces of the fine-tuning studies are included where a file is under 5 MB and free of identifiers. Two larger trace files of the tools study, the service logs and the regenerable training corpus are not included; they are available on request.
- The full list of experiments, including the ones that were dropped, is in [research/LEDGER.md](research/LEDGER.md).

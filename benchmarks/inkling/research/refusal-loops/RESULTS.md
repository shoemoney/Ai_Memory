# Refusal loops: results (2026-11-25)

Models: `thinkingmachines/TML-d24-varloop-research` (revision 91a57fe, packed native weights, run at N = 1, 2, 3, 5 passes) and
`thinkingmachines/Inkling-2-Mini` (native 3 passes). 60 + 60 prompts (HarmBench vs XSTest-safe), split 36/12/12 per class, directions fit on
train only, **12 held-out harmful and 12 held-out benign prompts per condition**. Greedy, reasoning effort `none`, 1000-token cap for the unedited
refusal stage (no completion hit the cap). Raw data: `results/refusal-loops/{varloop,mini}/` (analysis.json, refusal.json, rescore.json, acts-N*.npz, gen/).
Aggregate rates only; no completions are quoted. The study is descriptive only: no ablation was run on the variable-loop model and none is planned.

Caveats that apply to everything below: n = 12 per cell, so a 1-prompt difference is within noise (Wilson 95% intervals are in `refusal.json` and `rescore.json`);
the regex label (`refusal/score.py`) matches first-person refusal phrases and the judge is the pinned Qwen2.5-14B on :39700 (custom three-label rubric, not HarmBench's);
the two disagree by at most 1 harmful and 3 benign prompts per cell. The judge calls every benign answer complied while the regex flags a few; read the benign
regex counts as an upper bound on over-refusal.

## Finding 1: more looping does not change refusal
Harmful refusal is 9 to 10 of 12 at every pass count (regex) and 9 to 10 of 12 (judge), benign over-refusal 1 to 3 of 12 (regex), 0 (judge). N=1 already refuses as
much as N=3. No monotone trend with N is visible at this sample size. Inkling 2 Mini at N=3 is 9/12 (regex), 8/12 (judge) harmful and 1/12, 0/12 benign: same band as the
varloop model.

## Finding 2: the activation at every core visit is independent of N (design note)
Cross-pass-count cosines of the train-only direction at the same (layer, pass) are 1.00 for every pair (1v2 ... 3v5), and separation scores at pass p are identical across N.
That is expected from the architecture (visit p never reads N, as loop-decoding's test of pass 1 also shows) and means the recorded site cannot differ between N.
The pass count changes behaviour only through which later passes exist and which pass feeds the final block. "Does N=5 pass 3 look like N=3 pass 3" is therefore trivially yes.

## Finding 3: the readable direction is similar but not identical across passes
Mean same-layer cosine between pass directions over core layers 6-17: about 0.87 to 0.89 among passes 1-3, rising to 0.94 to 0.98 among passes 3-5 at N=5.
Separation (validation score, mean over core layers) is about 5.4, 5.0, 5.7 for passes 1, 2, 3 and 6.4, 5.9 for passes 4, 5 (varloop); the best single core visit is layer 16
(varloop: pass 1 at N=1; pass 3 for N>=3). Mini: pass 1 is strongest (5.5 mean), fading to 4.2 and 3.6 on passes 2 and 3, and the best visit is layer 16 pass 1.

## Tables

### Varloop

### Unedited refusal (held-out, 12 per class)

| N | harmful refused (regex) | harmful refused (judge) | benign refused (regex) | benign refused (judge) |
|---|---|---|---|---|
| 1 | 9/12 | 10/12 | 1/12 | 0/12 |
| 2 | 10/12 | 9/12 | 3/12 | 0/12 |
| 3 | 10/12 | 9/12 | 3/12 | 0/12 |
| 5 | 9/12 | 9/12 | 1/12 | 0/12 |

### Separation (validation score, mean over core layers 6-17) and best visit

| N | pass | mean val score | best core visit (layer, pass, val, eval) |
|---|---|---|---|
| 1 | 1 | 5.37 | L16 p1 8.07 / 6.96 |
| 2 | 1 | 5.37 | L16 p2 8.12 / 8.76 |
| 2 | 2 | 5.02 |  |
| 3 | 1 | 5.37 | L16 p3 9.93 / 9.51 |
| 3 | 2 | 5.02 |  |
| 3 | 3 | 5.70 |  |
| 5 | 1 | 5.37 | L16 p3 9.93 / 9.51 |
| 5 | 2 | 5.02 |  |
| 5 | 3 | 5.70 |  |
| 5 | 4 | 6.44 |  |
| 5 | 5 | 5.90 |  |

### Direction cosine between passes, same layer (mean over core layers 6-17)

N=2:
```
[[1.   0.89]
 [0.89 1.  ]]
```
N=3:
```
[[1.   0.89 0.88]
 [0.89 1.   0.87]
 [0.88 0.87 1.  ]]
```
N=5:
```
[[1.   0.89 0.88 0.92 0.9 ]
 [0.89 1.   0.87 0.94 0.9 ]
 [0.88 0.87 1.   0.95 0.98]
 [0.92 0.94 0.95 1.   0.98]
 [0.9  0.9  0.98 0.98 1.  ]]
```

### Direction cosine across pass counts, same (layer, pass); mean over core layers

| pair | pass 1 | pass 2 | pass 3 |
|---|---|---|---|
| 1v2 | 1.00 | - | - |
| 1v3 | 1.00 | - | - |
| 1v5 | 1.00 | - | - |
| 2v3 | 1.00 | 1.00 | - |
| 2v5 | 1.00 | 1.00 | - |
| 3v5 | 1.00 | 1.00 | 1.00 |

### Inkling 2 Mini

### Unedited refusal (held-out, 12 per class)

| N | harmful refused (regex) | harmful refused (judge) | benign refused (regex) | benign refused (judge) |
|---|---|---|---|---|
| 3 | 9/12 | 8/12 | 1/12 | 0/12 |

### Separation (validation score, mean over core layers 6-17) and best visit

| N | pass | mean val score | best core visit (layer, pass, val, eval) |
|---|---|---|---|
| 3 | 1 | 5.47 | L16 p1 8.37 / 5.50 |
| 3 | 2 | 4.20 |  |
| 3 | 3 | 3.60 |  |

### Direction cosine between passes, same layer (mean over core layers 6-17)

N=3:
```
[[1.   0.83 0.61]
 [0.83 1.   0.77]
 [0.61 0.77 1.  ]]
```

### Direction cosine across pass counts, same (layer, pass); mean over core layers

| pair | pass 1 | pass 2 | pass 3 |
|---|---|---|---|

## Run-time ablation (Mini only, one job that was already running when the arm was dropped)
Conditions on Mini at N=3, 12 held-out harmful prompts, projecting the train-only direction out of the output hidden state of core visits (layers 6-17): one pass, all passes,
pass-1 direction at a later pass, random direction; plus whole-network conditions I added (all 24 layers, own direction per layer; all 24 layers with the single best direction; random per layer).
**This run used a 192-token cap and is not interpretable as a refusal rate.** Even at effort `none` the model opens with a reasoning prefix, and nearly every ablated generation (12/12 in the all-pass and all-layer conditions, 10/12 for the random control) was cut off
inside it, so the regex returns "partial" and the judge only sees reasoning text. Judge counts were 8 to 11 of 12 "refused" in all ten conditions including the random control (they are not informative:
the judge reads cut-off deliberation). One aggregate that does separate the conditions: the word "refuse" appears in the 192-token reasoning prefix of 0/12 generations when the direction is removed
at all passes of the core (and 0/12 at all 24 layers), against 10/12 for the random-direction control and 3/12 when removed at pass 1 only.

Answer to the key question (does run-time removal at all layers and passes lower refusals?): **not measured**. The edit visibly changes the reasoning (the model stops announcing a refusal), which argues against the
direction being only a topic direction, but whether the final answer still refuses is unknown because the answers were never reached. A rerun with a 1000-token cap would settle it; it was not run (arm dropped).
Files: `gen-192tok/ablate-*.jsonl`, `rescore-first.json`, `ablation-192tok.json` (Mini results folder). Refusal-stage generations from the same first run (192 tokens) were also superseded by the 1000-token rerun reported above.

## Code changes (all with tests, 17 pass on the workstation)
`run_study.py`: added `all_layers`, `all_layers_single`, `random_all_layers` conditions; `rescore.py` (heuristic + judge rescoring of saved generations); `summarize.py` (tables). The first varloop attempt at 192 tokens
was aborted and rerun at 1000 (`run-aborted-192tok.log`).

## Cost
Mini collect + refusal + ablation about 14 minutes; varloop collect (4 pass counts) a few minutes, refusal about 25 minutes. Reclaimable memory minimum 24 GB (floor is 10 GB).

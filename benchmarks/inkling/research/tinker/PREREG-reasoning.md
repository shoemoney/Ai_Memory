# Preregistration: reasoning-preserving curriculum (follow-up to the hard set)

Written 2026-11-25 before any sampling for the training data or for the two new training runs. Known when written: the Part 1 diagnostics (stock accuracy by output cap; adapters at higher effort), recorded in RESULTS.md as descriptive. They show that the stock model needs room to reason (256 tokens: 25.3%, 512: 63.9%, 1,024: 88.1%, 2,048: 99.4%, mean completion 496 tokens at 2,048), and that the adapters from the earlier grid answer in about 8 tokens at every effort setting tried (0.0, 0.5, 0.9) without reasoning. This follow-up asks whether training on the model's own verified reasoning avoids that loss. It is a new question, not part of PREREG-lora.md. Budget: $30 for this follow-up, inside the $85 task cap.

## Data (v2 curriculum)

- Generator: `hard_eval.py` item kinds (revision, historical, join, date_order, date_interval, missing) in its `TRAIN` world: its own first and last names, room/pass codes, sentence templates, questions, system prompt, base year 2063 (hard v1 uses 2051), and varying spacing between notes (2 to 6 days; v1 uses 3) and varying archive length. Disjoint seeds. Tests prove no shared names, codes, values, templates, questions or prompts with hard v1, and no shared vocabulary with the original persona curriculum.
- 1,800 candidate items, 300 per kind, difficulty levels 1 to 3 in equal parts, prompts at most 7,200 tokens.
- Targets by verified self-distillation: the untrained Inkling-2-Mini answers each candidate at effort 0.0, temperature 1.0, 2,048-token cap. An item is kept only if the response stops cleanly, has exactly one thinking part and one text part, makes no tool call, and its final answer equals the oracle answer after case and punctuation folding. The first 1,500 kept items in index order whose full sequence fits 8,000 tokens are the training set. If fewer than 1,500 are kept, all are used and the smaller number is reported; the same items go to both arms. Keep rate is reported per kind and per level; a kind kept under 50% is called out and not hidden.
- Arm R trains on the model's own thinking plus its answer. Arm S trains on the same final answer text only, same items, same order, same updates; S is the control that isolates removing reasoning from the targets.
- Held out inside the run: 48 validation and 48 test items from the same world, different seeds, answer-only targets, used only for the trainer's own logging.

## Training (both arms identical except the targets)

`thinkingmachines/Inkling-2-Mini`, LoRA rank 32, default adapter targets as in the main run (all attention and MLP/MoE layers and the output head), learning rate from `hyperparam_utils.get_lr` (0.00054), linear decay, one epoch, batch size 16 (the sequences are about three times longer than the main run's), effort 0.0 for training and sampling, max length 8,192, seed 0, adapter seed 0, one run per arm, checkpoints every 50 updates and final. No learning-rate or other tuning, no second seed.

## Evaluation (hard v1, 360 items, scorer unchanged)

Score stock, R final and S final at output caps 256, 512, 1,024 and 2,048, effort 0.0, temperature 1.0, one sample per item. Stock numbers already exist for all four caps. Report exact match with Wilson 95% intervals and mean completion tokens per item for each model at each cap. Also score all three at cap 2,048, effort 0.0 on the original 300-item synthetic test and the 12-item reader check, so regressions on the old tasks show.

- Primary question: does R reach stock's 2,048-cap accuracy minus 5 points using at most half the completion tokens stock used at 2,048? Operationally, with stock at 99.4% (358/360) and a mean of 495.8 completion tokens at 2,048: R passes at a cap if its exact match is at least 94.4% and its mean completion tokens are at most 247.9 at that cap. R passes the primary question if it passes at any of the four caps; the result at every cap is reported, so the number of looks is visible. If R passes at no cap, the result is "reasoning targets did not meet the criterion", and that is reported as the result.
- Secondary: R minus S exact match at each cap, paired bootstrap over the 360 items (10,000 draws, seed 0), with the 2.5 and 97.5 percentiles. R and S against stock at each cap, same method.
- Hard v1 and the training world now come from one generator, so v1 is an in-distribution held-out set (entities, codes, wording, dates and seeds are disjoint, the item kinds and reasoning needed are not). A pass here does not show transfer to natural memory tasks.
- One chart: exact match against mean completion tokens, one line per model, points at the four caps.

## What stays the same, and limits

One seed per arm; synthetic generated data; hard v1 was built after the earlier saturation finding; the stock reference is a single sample per item at temperature 1.0, so small differences from stock are within sampling noise (stock at 2,048 has a Wilson interval of 98.0 to 99.8%). Items share templates, so the Wilson and bootstrap intervals understate uncertainty. If any one evaluation batch would cost more than $10, stop and write the question to PENDING.md.

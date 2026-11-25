# Preregistration: shortest-of-k reasoning targets (arm K)

Written 2026-11-25 before any new sampling for this experiment. Known when written: the R and S results in RESULTS.md. R, trained on the stock model's own verified traces at their natural length, matched stock's accuracy at a 2,048-token cap (98.6% against 99.4%) and used the same number of tokens (507 against 496 mean completion tokens per item), so it did not meet the preregistered efficiency criterion. The hypothesis here is that R learned the stock model's trace length because it was trained on traces of that length, and that selecting short correct traces teaches a shorter trace. Budget $20 for this experiment, inside the $85 task cap (about $58.6 spent before it).

## Training data for K

- Same world and generator as R: `hard_eval.TRAIN`, the same 1,800 candidate items (seed 20261201, difficulty levels 1 to 3, 300 per kind), disjoint from hard v1; the overlap tests stay in the suite and cover K's data too.
- For each candidate, k = 4 samples of the untrained model at effort 0.0, temperature 1.0, 2,048-token cap. R's pool already holds one sample per candidate; it is reused as draw 0, and 3 new draws are made per item. (The new draws use one request per item with `num_samples=3`; if billing counts prefill per draw the cost is higher, see the cost plan below.)
- A sample is usable if it stops cleanly, has one thinking part and one text part, makes no tool call, and its final answer equals the oracle answer after case and punctuation folding (the same rule as R). The kept trace for an item is the usable sample with the fewest completion tokens; ties go to the lowest draw index. Items with no usable sample are dropped. Items whose full sequence exceeds 8,000 tokens are dropped.
- Recorded per kind: the share of items with at least one usable sample among the four, against the share whose first draw alone was usable (R's keep rate); mean kept trace length, mean length of all usable traces of those items, and the mean per-item ratio of the two; the number of kept traces under 100 tokens; mean kept length by how many of the four draws were usable (an item solved once in four is where selection by length can pick a lucky guess). Whether four draws lifted the keep rate on `join` and `date_interval` is reported either way.
- Training set size: R's count (1,414 items). K's usable pool will probably be larger and its kind mix different from R's (more `join` and `date_interval`); if the pool has more than 1,414 items, 1,414 are drawn with `random.Random(0)` and kept in id order. K's kind mix is reported next to R's. If the pool has fewer than 1,414 usable items, all are used and the smaller count is reported.

## Training and evaluation

K trains with R's settings exactly: `thinkingmachines/Inkling-2-Mini`, LoRA rank 32, default targets (all attention and MLP/MoE layers and the head), learning rate 0.00054, linear decay, one epoch, batch 16, effort 0.0, max length 8,192, seed 0, adapter seed 0, one run, only the final checkpoint saved (storage quota). K is scored exactly as R was: hard v1 (360 items) at caps 256, 512, 1,024 and 2,048, effort 0.0, temperature 1.0, one sample per item, and the original 300-item synthetic test plus the 12-item reader check at cap 2,048.

## Criteria (decided now)

- Primary, unchanged from PREREG-reasoning.md: K passes at a cap if its hard-v1 exact match is at least 94.4% (stock at 2,048 minus 5 points) and its mean completion tokens are at most 247.9 (half of stock's 495.8 at 2,048). K passes if it passes at any of the four caps; every cap is reported. Failing means "shortest-of-k selection did not meet the criterion", reported as the result.
- Secondary: K minus R in exact match and in mean completion tokens at each cap, paired bootstrap over the 360 items (10,000 draws, seed 0). The accuracy-against-mean-tokens curve of K is added to the existing chart as a fourth line.
- Error analysis: K's exact match per kind, and a comparison with R's errors: for each model, the share of misses that are cut off or malformed against clean wrong answers.

## Limits stated up front

One seed per arm. Selecting by length can select for lucky guesses: a short correct trace may be a guess, so K's per-kind accuracy and error types are compared with R's, and the kept-length breakdown by number of usable draws is reported. K's training items differ from R's (different mix and a different subset), so a K-versus-R difference mixes trace length with item mix; the kind mixes are reported but not controlled. Synthetic, in-distribution data; hard v1 shares a generator with the training world. Intervals treat items as independent and understate uncertainty. If the extra sampling, training or evaluation would push the follow-up above $20 or the task above $85, stop and write the question to PENDING.md.

## Cost plan (dry run before any sampling)

Extra sampling: 1,800 prompts, 8,337,050 prompt tokens; three draws each. Prefill billed once per request: $1.25; billed per draw: $3.75. Sampled tokens: R's pool averaged 910 per candidate at cap 2,048, so about 3 × 1.64M = 4.9M tokens, $2.46; upper bound at the cap on every draw $5.53. Planned worst case $9.28 for this batch, under the $10 stop. Training: about 6.4M tokens at $0.75/M, $4.8, plus in-run sampling $0.3. Evaluation about $1. Expected total about $9 to $13.

# Loop count as a decoding knob: results (2026-11-25)

Model: TML-d24-varloop-research (packed native weights) on the M3 Ultra via mlx-lm PR #2086, 40 frozen prompts (20 LongMemEval BM25 prompts, 20 general or code), 64 new tokens, greedy,
one run per prompt and method, end-to-end tokens/s including prefill. Raw: `results/macstudio-64.{json,md}`, calibration (1 prompt, 8 tokens) `results/macstudio-calib.*`. The adaptive arm ran at two thresholds only
(5e-4 and 1e-2) to fit the time budget; thresholds 0 and 1e-5 were run only in the 1-prompt calibration. The concurrency 1/4/16 arm planned for this study **does not exist in bench.py** and was not run.

## Conclusions
1. **Self-speculation (1- or 2-pass draft, 3-pass verify) is slower than plain 3-pass decoding in this implementation.** Best speculative setting (K=8, 1-pass draft) reaches 17.25 tok/s against 22.14 tok/s for plain 3-pass decoding (0.78x). All six settings are between 0.61x and 0.78x.
   Acceptance is real (mean accepted draft length 1.7 at K=2 up to 4.9 at K=8 with a 1-pass draft; 5.9 at K=8 with a 2-pass draft) but each round pays for two prefills, two caches, full-depth verification and snapshot-restore replay on rejection. The README listed these costs in advance.
2. **Speculation was not exactly lossless here.** Greedy self-speculation should reproduce the 3-pass greedy output; measured exact-sequence match with plain 3-pass is 0.525 to 0.65 (21 to 26 of 40 prompts), token agreement 0.83 to 0.85. The offline tests pass on tiny random weights, so this is
   either floating-point near-ties between the batched verification kernel and single-token decoding on the quantised Metal path (the README's stated caveat) or a bug that the tiny tests cannot see. I did not separate the two. Speed numbers for speculation should be read as upper bounds on a correct implementation's speed only if the mismatch is numerical.
3. **Per-token KL early exit (cache-free reference) is about 26x slower** (0.79 and 0.85 tok/s at 2.68 and 2.53 mean passes per token) because it recomputes the prefix; it is a semantics baseline, not a speed option. Exit depth falls only from 3 to about 2.5 passes at these thresholds, with exact match 0.55 and token agreement 0.79 to 0.80 against 3-pass output.
4. **Throughput scales roughly with 1/passes**: plain-1 47.0, plain-2 30.0, plain-3 22.1, plain-5 14.7 tok/s (2.1x from 3 to 1 pass). Fewer passes change the text: exact match with 3-pass output is 0.32 token-wise at N=1 (0.0 exact sequences), 0.43 at N=2, 0.53 at N=5 (0.125 exact), so the draft and verifier genuinely disagree and a 1-pass draft is a weak predictor (acceptance 1.7 of 2 at K=2 is the best case).

## Numbers (40 prompts, 64 tokens)
| method | tok/s | accepted draft length | mean passes | exact match vs 3-pass | token agreement | peak GPU memory (GB) |
|---|---|---|---|---|---|---|
| plain N=1 | 47.05 | | 1 | 0.0 | 0.32 | 25.0 |
| plain N=2 | 30.01 | | 2 | 0.0 | 0.43 | 25.5 |
| plain N=3 | 22.14 | | 3 | 1 (reference) | 1 | 26.0 |
| plain N=5 | 14.68 | | 5 | 0.125 | 0.53 | 27.1 |
| spec K=2 draft 1 | 15.50 | 1.70 | | 0.575 | 0.86 | 29.2 |
| spec K=2 draft 2 | 13.44 | 1.82 | | 0.60 | 0.84 | 29.8 |
| spec K=4 draft 1 | 17.06 | 2.97 | | 0.525 | 0.85 | 29.2 |
| spec K=4 draft 2 | 14.88 | 3.40 | | 0.575 | 0.84 | 29.8 |
| spec K=8 draft 1 | 17.25 | 4.92 | | 0.65 | 0.85 | 29.2 |
| spec K=8 draft 2 | 15.16 | 5.88 | | 0.55 | 0.83 | 29.8 |
| adaptive KL 5e-4 | 0.79 | | 2.68 | 0.55 | 0.79 | 28.5 |
| adaptive KL 1e-2 | 0.85 | | 2.53 | 0.55 | 0.80 | 28.5 |

## Limits
One run per cell, no repeats, so no timing intervals; 64 new tokens; prompts include 20 long (about 1.5k token) memory prompts; the Mac Studio was otherwise idle but a judge and the shared server were resident. Peak memory is the MLX allocator peak.
No accuracy claim follows from exact-match or agreement. The speculative implementation recomputes prelude and first-core work rather than sharing it (README); a staged verifier could remove part of the overhead, but the two-prefill, two-cache design and replay-on-reject are structural.

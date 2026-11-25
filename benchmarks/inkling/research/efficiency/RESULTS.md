# DSpark acceptance and energy per correct answer: results (2026-11-25)

Stock `Inkling-2-Mini-oQ4e-stock` (oMLX 0.8.3 lab server :39850, Lightning MTP with the bundled DSpark drafter), Mac Studio M3 Ultra. The acceptance counter is the reversible instrumentation from `instrument_mtp.py`
(restored afterwards, confirmed: 0 instrumentation lines remain, model settings byte-identical to the backup, lab server stopped). Only the stock variant was measured; edited variants do not exist (arm dropped).

## Conclusions
1. **MTP/DSpark speeds up generation by 16.7% and the draft accepts 41.3% of evaluated positions.** 50 serial prompts (25 general, 13 LongMemEval, 12 LoCoMo), greedy, thinking off, 384-token cap: generation 58.29 tok/s with MTP vs 49.96 without (x1.167); end to end including prefill 36.80 vs 33.90 tok/s (x1.086).
   Accepted 2,091 of 5,062 counted positions (0.413). Same 4,244 completion tokens in both modes, no length stops. By group, acceptance and generation speed: general 0.419, 60.3 vs 50.9 tok/s; LoCoMo 0.418, 57.1 vs 48.7; LongMemEval 0.387, 53.5 vs 48.6 (long memory prompts gain least).
2. **MTP costs about 5% more energy per correct answer, not less.** Four paired energy windows (order on, off, off, on) on the first 12 LongMemEval questions (44 scored pairs per window; 29 correct in every window, 65.9%): net rail energy 13.59 and 13.69 kJ with MTP vs 12.995 and 12.992 kJ without,
   i.e. **468.6 and 472.2 J per correct answer with MTP vs 448.1 and 448.0 J without (+5.1% on average)**; wall time was identical (162 to 164 s) because the window is dominated by judge calls and orchestration, and mean power was higher with MTP (84.1 and 84.6 W vs 79.7 and 79.5 W). Within-mode repeats agree to 0.1% (off) and 0.8% (on), so the 5% gap is well above the repeat noise; two repeats per mode is still a small sample.
3. Energy figures are CPU+GPU+ANE rail energy from powermetrics (not wall-plug); the window contains the whole pipeline (reader, local Gemma judge, waits), idle baseline 0.15 to 0.29 W was subtracted; the 12-question subset is not a quality benchmark and the correct-answer counts are identical by construction (answers under MTP are not different at temperature 0 in this subset).

## Limits
Acceptance counts every proposed draft token (instrumented counter; the upstream log undercounts the unvisited suffix). One acceptance run per mode (no order repeat), serial on an otherwise idle host.
A first energy attempt with `--batch-size 5` covered only 5 pairs, 0 correct, so J per correct answer was undefined; it is kept as `runs/stock/energy-{on,off}` and not used. Raw: `runs/stock/acceptance-01/`, `runs/stock/energy2-{1-on,2-off,3-off,4-on}/`, drivers `run-efficiency.sh`, `run-energy.sh`.

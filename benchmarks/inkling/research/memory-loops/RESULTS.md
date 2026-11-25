# Depth x retrieval: results (2026-11-25)

Design: README.md section "Study #9" (preregistered). `thinkingmachines/TML-d24-varloop-research` rev 91a57fe, packed native weights (no quantisation change), reader replay on
150 frozen LongMemEval questions (stratified, oracle-fit) x {oracle sessions, BM25, dense} x N = 1, 2, 3, 5 passes: 1,800 reader answers, three Gemma-2-9B judge votes each.
Total sweep time about 2.3 h on the Mac Studio (about 15 min at N=1 to about 80 min at N=5). Files: `results/depth-retrieval/varloop-pN/`, `results/depth-retrieval/analysis/` (analysis.json, iso-accuracy.md, two SVGs).
This is reader replay over archived retrieval, not the official LongMemEval protocol; the lanes also differ in context length and formatting. n = 150 per cell, so one cell's Wilson interval is about +/- 8 pp.

## Accuracy (correct / 150)
| Depth N | Oracle | BM25 | Dense |
|---|---|---|---|
| 1 | 95 (63.3%) | 84 (56.0%) | 82 (54.7%) |
| 2 | 97 (64.7%) | 72 (48.0%) | 71 (47.3%) |
| 3 | 111 (74.0%) | 82 (54.7%) | 89 (59.3%) |
| 5 | 109 (72.7%) | 81 (54.0%) | 85 (56.7%) |

## Preregistered outcome: inconclusive / mixed
- Oracle depth gain p1 to p5: +9.3 pp, 95% interval [+2.7, +16.0] (p1 to p3: +10.7 [+4.0, +17.3]). Depth helps when the evidence is in the context.
- BM25 depth gain p1 to p5: -2.0 pp [-9.3, +5.3]; dense +2.0 pp [-5.3, +9.3]. Neither retrieved lane gains from depth; the intervals are wider than the +/-5 pp margin, so "no effect" is not established either.
- Primary gap-shrink contrast (oracle - BM25 at p1) - (oracle - BM25 at p5): **-11.3 pp [-21.3, -2.0]**. Negative: the oracle advantage over BM25 **grew** with depth (7.3 pp at p1, 18.7 pp at p5), the opposite of depth substituting for retrieval.
- Iso-accuracy: no BM25-depth/oracle-depth pair was within +/-5 pp (see `analysis/iso-accuracy.md`); the closest is oracle p1 vs BM25 p1 (-7.3 pp [-16.0, +1.3]).
- Not monotone: N=2 is the worst depth in the two retrieved lanes (BM25 48.0%, dense 47.3%), N=3 and N=5 are close to each other. All pairwise depth and lane contrasts other than the primary are exploratory and unadjusted.

Plain reading: on this model and sample, extra loop passes help (about 9 to 11 pp) only when the context is oracle sessions, do not help noisy BM25 or dense contexts, and so do not make up for weak retrieval.
Caveats: single model checkpoint (native mixed NVFP4/MXFP8), one sample of 150 questions, judge is a 9B model (three votes are not independent), retrieval lanes do not certify evidence presence, varloop and stock Inkling are different models.

## Fixes made during the run
`remote.py` `stop()` refused to stop its own server on macOS (the process title is rewritten to `omlx-server`, so the command-line identity check failed). It now accepts a PID that holds the TCP listener on :39851 (`owns_server`, test added, 8 offline tests pass).
Two earlier attempts were discarded because the controller hash changed, as the protocol requires a fresh root: no results from them are used.

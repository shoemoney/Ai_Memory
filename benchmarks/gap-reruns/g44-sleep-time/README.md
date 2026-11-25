# G44: sleep-time compute, cost per query when questions share one context

Chapter sentence: `build/chapters/16-frontier.html:120`: "When several questions share one context, the authors report a
2.5 times lower cost per query, a figure not reproduced for this book."

## What the paper's figure is

Sleep-time Compute (arXiv 2504.13171, Lin et al., Letta and UC Berkeley). Section 5.3 (Multi-Query GSM-Symbolic): "we can
decrease the average cost per query by up to 2.5x when there are 10 queries per context, compared to the single-query
baseline." Cost model: tokens generated at test time weigh t = 10 against tokens generated during sleep-time (latency-
optimized inference is roughly ten times more expensive). The comparison is sleep-time compute with one question per
context against sleep-time compute with ten questions per context, so the saving is the offline work being shared. It is
not a comparison against a system with no sleep-time step. The paper ran GPT-4o-mini and GPT-4o on Multi-Query
GSM-Symbolic, which it built by asking o3-mini for extra question and answer pairs per context. Matched accuracy in the
paper means the sleep-time arm and the no-sleep arm sit on the same accuracy level of the test-time-tokens versus
accuracy curve, which the paper draws by varying how verbose the answering agent is (prompt files `*_verbosity_0..4`).

Public pieces: code and prompts at https://github.com/letta-ai/sleep-time-compute (MIT, commit ffdf662), data at
https://huggingface.co/datasets/letta-ai/stateful-gsm-symbolic (Stateful GSM-Symbolic P1 and P2, one question per
context, licence not stated on the card). The Multi-Query set itself is not among the released files (the dataset repository
holds only `stateful_gsm_symbolic_p1.jsonl` and `_p2.jsonl`), and the released code needs a Letta server and OpenAI keys.

## What this folder does

Re-implements the sleep-time step and the two answering arms with plain chat calls to one local open-weight model,
Qwen2.5-7B-Instruct (Q4_K_M GGUF, llama.cpp), temperature 0, on an Apple M1 Ultra (64 GB) used only as a model server.

1. `select`: 44 contexts drawn at random (seed 20261122) from Stateful GSM-Symbolic P2 (2,500 rows, multi-step contexts).
2. `genq`: for every context, 6 extra question and answer pairs from the paper's Appendix C prompt (same wording), written by
   the local 7B model. Up to 4 are kept per context; the 32 first contexts with at least 3 pairs are used. Each context
   has 5 questions: the dataset's original plus 4 generated (N = 160 questions).
3. `sleep`: one offline generation per context with the paper's `sleep_time_base` prompt (no tools; the reply is stored as the
   rethink block), up to 1,500 tokens.
4. `answer`: each question with the paper's persona, human and conversation prompts at verbosity 0, 2 and 4, in two arms:
   base (context plus question only) and sleep (the rethink block placed in the system prompt). 32 x 5 x 2 x 3 = 960
   answer calls. The answer is the last number in the reply, as in the paper's `evaluate_gsm_symbolic.py`.
5. `verify`: every generated gold answer is checked against an independent expression-based solve by the same model (the
   model writes one arithmetic expression, a safe evaluator computes it). 36 of 128 generated pairs agree.
6. `analyze.py`: paired bootstrap over contexts (10,000 resamples, seed 20261122).

One command (model server up on localhost:39980): `./run_all.sh`, then `python3 sleeptime.py verify` before `analyze.py`.
Raw outputs: `raw/` (per-call JSONL; `answers.jsonl` is about 770 KB), summary `results.json`, hand check `hand_check.json`.

## Results (N = 32 contexts, 160 questions, 5 per context)

Cost per query = 10 x (test-time completion tokens) + (sleep tokens of the context / questions of the context). Sleep
tokens per context: 646 (mean). 95% intervals are bootstrap intervals over the 32 contexts.

| Config (verbosity) | Accuracy, all 160 | Test-time tokens / query | Cost / query (t = 10) | Prompt tokens / query |
|---|---|---|---|---|
| base v0 | 0.200 (0.131 to 0.275) | 9.1 | 91 | 396 |
| base v2 | 0.281 (0.188 to 0.381) | 60.7 | 607 | 394 |
| base v4 | 0.588 (0.475 to 0.694) | 454.2 | 4,542 | 378 |
| sleep v0 | 0.356 (0.250 to 0.463) | 10.6 | 235 | 1,046 |
| sleep v2 | 0.388 (0.294 to 0.487) | 47.0 | 599 | 1,044 |
| sleep v4 | 0.481 (0.356 to 0.600) | 442.9 | 4,558 | 1,028 |

The paper's figure, one question per context against several (same notes, same answers, so accuracy is identical by
construction):

| Config | Cost ratio, 1 question vs 5 measured (95% CI) | 1 vs 10, modeled from the same tokens (95% CI) |
|---|---|---|
| sleep v0 | 3.20 (3.01 to 3.37) | 4.41 (4.03 to 4.78) |
| sleep v2 | 1.86 (1.74 to 2.00) | 2.09 (1.92 to 2.28) |
| sleep v4 | 1.11 (1.10 to 1.13) | 1.13 (1.11 to 1.15) |

Matched accuracy (the paper's Pareto reading): baseline test-time tokens needed to reach the sleep arm's accuracy,
linearly interpolated along the baseline's verbosity curve.

| Item set | Sleep config | Accuracy difference, sleep minus base (95% CI) | Baseline tokens at matched accuracy | Cost ratio, base over sleep at matched accuracy (95% CI) |
|---|---|---|---|---|
| all 160 | v0 | +0.156 (+0.069 to +0.250) | 157 (46 to 264) | 6.68 (1.98 to 11.26) |
| all 160 | v2 | +0.106 (+0.006 to +0.206) | 197 (72 to 287) | 3.29 (1.15 to 5.04) |
| all 160 | v4 | -0.106 (-0.175 to -0.037) | 318 (222 to 402) | 0.70 (0.48 to 0.90) |
| verified 68 | v0 | +0.132 (+0.030 to +0.243) | 134 (43 to 232) | 3.27 (1.04 to 5.77) |
| verified 68 | v2 | +0.132 (+0.027 to +0.230) | 172 (83 to 261) | 2.10 (0.93 to 3.41) |
| verified 68 | v4 | -0.191 (-0.343 to -0.060) | 297 (199 to 395) | 0.63 (0.40 to 0.86) |

"verified" is the 32 original questions (dataset gold) plus the 36 generated questions whose gold an independent solve
reproduced; the sleep cost per question there divides by 2.1 questions per context and so overstates the sleep share
(use the "all" rows for cost, the "verified" rows for accuracy).

## Limits of this local run

1. Model: one 7B model, not GPT-4o or GPT-4o-mini. Notes written by a 7B model were wrong often enough that at verbosity 4
   the sleep arm was less accurate than the base arm (the notes misled the answer).
2. Data: the Multi-Query set is not released, so the extra questions are generated locally and are easier than the originals.
   Their gold is model-written. A hand check of 12 unfiltered generated pairs found 7 correct; of 20 verified pairs, 18
   (`hand_check.json`, done by the tester, an AI agent, not an independent human). Accuracy on the "all" set therefore
   carries label noise; the "verified" set removes most of it but keeps only items this model can solve two ways.
3. Five questions per context, not ten. The 1-versus-10 ratio is a model built from the measured token counts, not a run.
4. No Letta agent, no tools: the sleep step is one generation, and the rethink block is a system-prompt section.
5. Cost counts generated tokens only, as the paper does. The sleep arm's prompts are about 650 tokens longer per query, so
   total tokens read per query are higher with sleep-time compute.
6. 32 contexts, one seed, temperature 0; intervals are over contexts and are wide at this size.
7. A first full run was discarded: context keys collided because the dataset's `id` repeats across instances, so notes and
   questions were attached to the wrong contexts. Keys now come from the shuffled position. Nothing from that run is used.

## Verdict

Supports in direction, with a verbosity caveat. Sharing one sleep-time step across 5 questions cut cost per query by 3.2
times (CI 3.0 to 3.4) against asking one question per context at the lowest verbosity, 1.9 times at verbosity 2 and 1.1
times at verbosity 4; the paper's 2.5 times for 10 questions falls inside that range and the local number depends on how
much the answering agent writes. Against a no-sleep baseline at matched accuracy, the sleep arm needed far fewer test-time
tokens at low verbosity (matched cost ratio 3 to 7) but lost accuracy at high verbosity with a 7B notes writer.

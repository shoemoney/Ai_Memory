# G10: BEAM and LIGHT (gains of 3.5% to 12.69%)

Chapter sentence: `build/chapters/16-frontier.html:250` ("BEAM's authors report average gains of 3.5% to 12.69% over their
strongest baselines, depending on the backbone model; this book has not reproduced that gain.").

## What the paper reports, and what was public

BEAM / LIGHT: "Beyond a Million Tokens: Benchmarking and Enhancing Long-Term Memory in LLMs" (arXiv 2510.27246, ICLR 2026).
Code and data: https://github.com/mohammadtavakoli78/BEAM (commit b2da22eac88bb0874c64665f13457eb99835774a, code MIT,
benchmark data CC BY-SA 4.0). LIGHT's code (`src/answer_probing_questions/light.py`) is public, so this item could be run.
Scales shipped in the repository: 100K (20 conversations with probing questions), 500K, 1M, 10M. Only 100K was used (the
README calls it 128K). Scoring is BEAM's own rubric judge (`src/evaluation/compute_metrics.py`): for each rubric item a
judge model returns a JSON score of 0, 0.5 or 1, and the question score is the mean over its rubric items
(`llm_judge_score`, the column BEAM's own report uses for every ability).

## Design (fixed before any answer or score existed)

- Conversations: 5 of the 20 at 100K, drawn with seed 20261122 (ids 2, 8, 13, 17, 19). Questions: all 20 probing questions of
  each (2 per memory ability x 10 abilities) = 100 questions. List and rule frozen in `raw/questions_fixed.json`.
- Systems on the same questions: (a) BEAM's RAG baseline, `pair_chunk` dense retrieval (BAAI/bge-small-en-v1.5, k = 5);
  (b) LIGHT, `retrieval_method = light` (scratchpad, episodic key-value index with dense retrieval, working memory of the last
  100 turn pairs, scratchpad chunk filtering with BAAI/bge-large-en-v1.5).
- Models, all local: Qwen2.5-3B-Instruct Q4_K_M as the single model for LIGHT's indexing, scratchpad notes, chunk filter and as
  the reader for both systems (`temperature 0`); Qwen2.5-7B-Instruct Q4_K_M as the rubric judge, loaded in a separate phase
  after answering ended (one model loaded at a time). Both served by llama.cpp on an Apple M1 Ultra, 64 GB.
- The paper's other baseline, long context, was not run: a 100K-token conversation does not fit the 32K-token window of the
  local models.

One command after the model server and embedding server are up: `./run_all.sh` (select, answer both systems, judge,
analyze). Raw outputs: `raw/` (answers gzip, per-question scores with judge replies, hand check). Summary: `results.json`.

Two changes to BEAM code, both applied at import time by `run_beam.py` (the cloned files stay untouched): (1) `light.py`
passes an int to `str.replace` when the scratchpad summarizer runs (a TypeError the paper's own run cannot have hit); the
call is fixed with `str()`. It did not trigger here (scratchpads stayed under the summarizer threshold). (2) The 146 or so
independent yes/no chunk-filter calls per question run in a thread pool instead of one after another (identical prompts,
temperature 0, same kept chunks in the same order; checked on a synthetic reply function with identical output).

## Results (N = 100 questions, 5 conversations)

| System | Mean rubric score (95% bootstrap CI over questions) |
|---|---|
| RAG baseline | 0.347 (0.265 to 0.432) |
| LIGHT | 0.309 (0.233 to 0.388) |
| LIGHT minus RAG, paired | -0.038 (-0.115 to +0.035); LIGHT better on 18 questions, RAG better on 23, tied on 59 |

Per conversation (LIGHT minus RAG): conv 2 +0.015, conv 8 +0.035, conv 13 -0.173, conv 17 -0.012, conv 19 -0.054. Per
ability (n = 10 each, no interval, see `results.json`): LIGHT ahead on summarization, information extraction, multi-session
reasoning and contradiction resolution, behind on the other six abilities (instruction following, knowledge update,
abstention, event ordering, preference following, temporal reasoning). Relative to the baseline mean the paired difference is -10.9%; the paper's figure is a gain of 3.5% to
12.69% for stronger backbones.

Judge check: the tester read 40 judged answers (20 questions, both systems, seed 5) against their rubric items and agreed
with the judge on 35 (87.5%, exact 95% interval 73.2% to 95.8%); the 5 disagreements all had the judge too lenient (two
instruction-following answers that described bullets in prose, one abstention answer that invented rules, one ordering answer
and one legal-explanation answer), 2 on baseline answers and 3 on LIGHT answers (`raw/hand_check.json`). This was done by the
tester, an AI agent, not an independent human. The judge is a 7B model scoring answers of a 3B model; it is not the
paper's judge.

Diagnostic (`raw/diag-filter-gap-qwen2.5-3b.json`, conversation 2, 6 questions, 146 scratchpad chunks each): the 3B model
replied exactly "yes" to 0 or 1 chunk in 146 (the filter keeps a chunk only on an exact "yes"), so LIGHT's scratchpad
contribution was almost empty for this model; LIGHT here is largely episodic retrieval plus working memory.

## How this differs from the paper

1. Models: the paper's indexer and filter are Qwen2.5-32B-AWQ and its scratchpad summarizer GPT-4.1-mini, with several
   larger readers; here one 3B model does all of it, which is the likeliest reason LIGHT's extras did not pay.
2. Scale and size: 100K tokens only, 5 conversations, 100 questions; the paper's averages cover all scales and many models.
3. Baselines: RAG only; the paper's strongest baseline is often long context, which cannot run locally at 100K tokens.
4. Judge: 7B local judge, not the paper's judge model.
5. Embeddings: computed on the model host through a small server (same models), not loaded on the harness machine.
6. Working memory at 100K covers most of the conversation, so at this scale LIGHT's context is mostly recent turns.

## Verdict

Cannot speak to the published gain, and on this local setup LIGHT did not beat the plain RAG baseline (difference -3.8
points, interval -11.5 to +3.5, so no reliable difference either way). The result says a 3B model cannot run LIGHT's
indexing and filtering well enough to show the published benefit at the 100K scale; it does not contradict the paper's
results for 32B-class indexers and larger readers.

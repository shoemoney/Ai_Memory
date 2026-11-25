# Editor report: gap reruns (G39, G44, G10)

Status: all three items finished with local numbers. Every check marked "tester" was done by the tester (an AI agent), not an
independent human. Intervals are 95% intervals (bootstrap over requests for G39, over contexts for G44, over conversations
or questions as stated for G10). No figure below was tuned toward a published number.

Hardware class used throughout: a 28 GB x86 development machine (CPU only; its 8 GB GPU was not used) that runs the harness,
and an Apple M1 Ultra, 64 GB, used only as a model server reached through an SSH tunnel to a localhost-only port.

## G39: Hindsight decision-model latency

Book: `build/chapters/06-small-memory-models.html:159` ("Hindsight reports a 167 ms median per request for a small decision
model, against 1 to 7 seconds for a main model call.") and the table row at line 292 ("167 ms vs 1 to 7 s").

Published: 167 ms median and 350 ms p90 per decision-model request, from the vendor's own evaluation (Hindsight 1.2.0 retain,
consolidation, reflect and knowledge-page operations against hosted LLMs; time "spent in model calls" from traces). Source:
https://hindsight.vectorize.io/blog/2026/11/03/hindsight-models. Hardware and request count are not stated; the weights serve
on vLLM.

Local: a new Hindsight 1.2.3 container (never the service already on the machine) with `hs-decide-1-flash` (0.8B,
Apache 2.0, revision e2c78902) served by the vendor's Transformers server on the Apple M1 Ultra GPU in bfloat16. Traffic:
199 recall queries from one LoCoMo conversation (six sessions retained by a local Qwen2.5-7B-Instruct Q4_K_M) with
recall pruning and dedup on. N = 242 decision-model requests, timed inside the server.
- All requests: median 2,105 ms (95% CI 2,103 to 2,108), p90 2,301 ms, p95 2,380 ms; median input 5,680 tokens.
- Ranking requests (1,000 tokens or more, N = 206): median 2,109 ms, p95 2,389 ms.
- Dedup requests (under 1,000 tokens, N = 36): median 132 ms (128 to 163), p95 367 ms; median input 241 tokens.

Limits: Transformers on Apple GPU, not vLLM; recall ranking and dedup traffic, which is not the vendor's measured mix
(consolidation, reflect, pages); one client, one conversation, six sessions; the intervals are over requests that are nearly
the same size, so they are tight but say nothing about other workloads; no reflect or consolidation requests were captured
(a reflect pass failed when the model server stopped under host memory pressure, and a consolidation job left by the
killed earlier container never completed). Result: the local figure does not reproduce 167 ms for recall-ranking requests
on this hardware and cannot speak to the vendor's workload on the vendor's hardware. The short dedup requests land near the
published median, which fits latency scaling with request size.

Suggested replacement (two sentences): "Hindsight reports a 167 ms median per decision-model request, against 1 to 7 seconds
for a main model call, on its own workload. Run locally by this book on an Apple M1 Ultra, the requests sent by recall
pruning took a median of 2.1 seconds for about 5,700 tokens (N = 206) and 132 ms for about 240 tokens (N = 36), so the figure
depends on request size and hardware."

Evidence: `g39-hindsight-latency/README.md`, `results.json`, `raw/decider-timing.jsonl`, `raw/recall.jsonl`, `raw/retain.jsonl`.

## G44: sleep-time compute, 2.5 times lower cost per query

Book: `build/chapters/16-frontier.html:120` ("When several questions share one context, the authors report a 2.5 times lower
cost per query, a figure not reproduced for this book.").

Published: "up to 2.5x" lower average cost per query with 10 questions per context against 1 question per context, with
test-time tokens weighted 10 times sleep-time tokens, GPT-4o-mini and GPT-4o on Multi-Query GSM-Symbolic (arXiv 2504.13171,
section 5.3). The paper's accuracy matching is its test-time-tokens versus accuracy curve over five verbosity prompts.

Local: Qwen2.5-7B-Instruct Q4_K_M, temperature 0, 32 contexts from Stateful GSM-Symbolic P2 with 5 questions each (the
dataset's original plus 4 generated locally, because the Multi-Query set is not among the released files), paper prompts
at verbosity 0, 2 and 4, base arm against sleep arm (960 answer calls); the same sleep notes serve all questions of a
context, so accuracy for 1 versus 5 questions per context is identical by construction. Cost per query = 10 x test-time
generated tokens + sleep tokens per question (646 sleep tokens per context). Cost ratio of 1 question per context to 5
(measured): 3.20 (95% CI 3.01 to 3.37) at verbosity 0, 1.86 (1.74 to 2.00) at verbosity 2, 1.11 (1.10 to 1.13) at verbosity 4;
modeled from the same tokens for 10 questions: 4.41, 2.09, 1.13. Against a no-sleep baseline at matched accuracy
(interpolated along the base arm's curve), cost ratio base over sleep: 6.7 (1.98 to 11.3) at verbosity 0 and 3.3 (1.15 to
5.0) at verbosity 2 on all 160 questions; 3.3 and 2.1 on the 68 verified questions; at verbosity 4 the sleep arm was less
accurate than the base arm (0.481 against 0.588, difference -0.106, CI -0.175 to -0.037) and the matched ratio is 0.70.

Limits: one 7B model; extra questions and their gold answers are model-written (hand check by the tester: 7 of 12
unfiltered and 18 of 20 verified generated answers correct); 5 questions per context, not 10 (the 10-question ratio is a
model); no Letta agent or tools; generated tokens only (the sleep arm's prompts are about 650 tokens longer per query);
32 contexts. Result: supports the direction of the published claim and brackets its size (1.1 to 4.4 depending on
how much the answering agent writes); cannot confirm the exact 2.5 for GPT-4o-class models on the released-paper set.

Suggested replacement (two sentences): "When several questions share one context, the authors report up to 2.5 times lower
cost per query. This book's rerun with a 7B model on 32 grade-school math contexts with 5 questions each saw 3.2 times at
the shortest answers and 1.1 times at the longest, and the offline notes lowered accuracy at the longest answers."

Evidence: `g44-sleep-time/README.md`, `results.json`, `hand_check.json`, `raw/*.jsonl`.

## G10: BEAM and LIGHT, gains of 3.5% to 12.69%

Book: `build/chapters/16-frontier.html:250` ("BEAM's authors report average gains of 3.5% to 12.69% over their strongest
baselines, depending on the backbone model; this book has not reproduced that gain."), with the badge "Research prototype,
not run" and the sentence "This comparison is proposed, not run." in the same paragraph.

Published: LIGHT improves average BEAM scores by 3.5% to 12.69% over the strongest baselines depending on the backbone model
(arXiv 2510.27246; code MIT and data CC BY-SA 4.0 at github.com/mohammadtavakoli78/BEAM, commit b2da22e). The code is
public and the smallest scale (100K) is shipped, so the item was run. The paper's setup uses a 32B indexer, GPT-4.1-mini for
scratchpad summaries and larger readers.

Local: 5 of 20 conversations at the 100K scale (seed 20261122), all 20 probing questions of each, N = 100 questions fixed in
`g10-beam-light/raw/questions_fixed.json` before any score existed. BEAM's RAG baseline against LIGHT, same questions,
Qwen2.5-3B-Instruct Q4_K_M as the only indexer, chunk filter and reader (Apple M1 Ultra), BEAM's rubric judge run with a
local Qwen2.5-7B-Instruct Q4_K_M. Mean rubric score: RAG 0.347 (95% CI 0.265 to 0.432), LIGHT 0.309 (0.233 to 0.388), paired
difference -0.038 (-0.115 to +0.035); LIGHT better on 18 questions, RAG on 23, 59 ties. Per conversation the difference
ranges from -0.173 to +0.035. Hand check of 40 judged answers by the tester (an AI agent): 35 agree (87.5%, 73.2% to 95.8%),
all 5 disagreements are the judge being too lenient (3 on LIGHT answers, 2 on baseline answers).

Limits: 3B models for everything LIGHT builds (diagnostic: the scratchpad chunk filter answered exactly "yes" to 0 or 1 of 146
chunks, so the scratchpad added almost nothing); 5 conversations at one scale; no long-context baseline (100K tokens does not
fit the local window); 7B judge, not the paper's; two code changes at import time (an int-to-str bug fix in the summarizer call
that never ran, and a thread pool over independent filter calls with identical output). Result: cannot speak to the published
gain; on this setup LIGHT did not beat plain RAG, with no reliable difference in either direction.

Suggested replacement (two sentences): "BEAM's authors report average gains of 3.5% to 12.69% for LIGHT over their strongest
baselines, using models up to 32B for indexing. This book ran BEAM's own code on 100 questions from the 100K-token scale with
a 3B local model and found LIGHT at 0.31 against 0.35 for plain retrieval (difference -0.04, interval -0.12 to +0.03), so it
did not reproduce the gain at that size."

Evidence: `g10-beam-light/README.md`, `results.json`, `raw/questions_fixed.json`, `raw/scores-*.jsonl`, `raw/answers-*.json.gz`,
`raw/hand_check.json`, `raw/diag-filter-gap-qwen2.5-3b.json`.

## What did not work or was lost

- The earlier operator was killed by an out-of-memory event; the first G44 run attached notes to the wrong contexts because
  dataset ids repeat, was found when answers cited the wrong people, and was discarded and rerun from scratch.
- The model host's server was stopped once by this task's own memory watchdog at 32% free; the threshold now needs three
  consecutive low samples. The host's kernel reported pressure level 2 (warn) for most of the run at 40 to 57% free for
  reasons outside this task, so the "stop on warn" rule was replaced by "stop at critical or three samples under 30% free".
- A reflect pass for G39 failed when that server stopped; no reflect traffic was captured.
- LIGHT indexing with the 7B model ran at about 10 model calls per minute, which put five conversations near 3.5 hours; G10 was
  rerun with the 3B model for the indexer and reader (same family), keeping the 7B as judge.
- BEAM's `nltk` data download raced when ten judge processes started together; one process failed and was relaunched.

## Cleanup proof

`results/cleanup.json` holds the before and after listings; `results/before.json` is the snapshot taken mid-run (the earlier
operator took none).
Before: 16 GB of scratch and 1.5 MB under `/var/tmp` on the dev machine, one stopped task container and its 6.7 GB image, two
SSH tunnels on ports 39980 to 39999, 9.1 GB of scratch on the model host (models, two venvs, caches), a llama.cpp server and
an embedding server running there, memory free 55% to 60% and 4 to 8 GB available on the dev machine.
After: no scratch folders, containers, images, tunnels, listeners or task processes on either machine; the model host's data
volume went from 696 to 688 GiB used and its free memory stayed at 55% to 60%; the dev machine's scratch pool went from 299 to
271 GB used (includes this task's 16 GB and unrelated activity). The first cleanup run missed the model host's embedding
server (a zsh pid-list slip); it was stopped by hand, the script was fixed and rerun, and the second listing is the one saved.
Left in place on purpose: the shared package caches (`~/.cache/uv`, 25 GB on the dev machine and 29 GB on the model host),
which other jobs use and which cannot be separated from this task's wheels, and the pre-existing `~/nltk_data`.
The Hindsight service that was already running, `omlx-server` and every other process or folder not started by this task
were not touched. Nothing was committed.

# Loop count as a decoding knob

Pure Python, MLX, text-only experiments on the unmodified Inkling model in
mlx-lm PR #2086 (`jundot/mlx-lm`, `e2b5bbd`). Use a locally converted
**thinkingmachines/TML-d24-varloop-research**, with `is_varloop=true`.
No weight edits, training, model downloads, sampling, sharding or server changes.
This is a correctness reference and benchmark harness; no speedup has been measured.

## A. Greedy self-speculation

Maintain independent draft and target caches, each prefilling the prompt at its
own depth. Draft K greedy tokens at N_draft (default 1), then run a single target
forward over those K positions at N_verify (default 3). Compare the first candidate
with the preceding target logits and subsequent candidates with the shifted
verification logits. Accept the longest matching prefix; on rejection emit the
target's correction. There is no bonus token on all-accepted rounds.

The target's pass-2/3 caches are populated during its own prefill and during
verification of each drafted span. A 1-pass draft cache is never passed into a
3-pass call. This avoids missing caches and wrong postlude/cache indexing.

A snapshot of **both complete cache lists** is taken at each draft boundary. On
rejection, restore the snapshots and replay the accepted prefix plus correction
at each respective depth. This rolls back rejected tokens, including convolution
state, rotating KV history and cache offsets. `CacheList.trim` is insufficient:
`ArraysCache(4)` contains convolution state and rotating KV may overwrite history.
Snapshots use Python `deepcopy`, preserving per-cache metadata and MLX arrays.
Tests force rejection after a nonempty accepted prefix and continue beyond the
8-token sliding window; the all-accepted path is also checked.

Greedy correctness argument: before each round target caches represent exactly the
committed prefix. Causality makes verification logits at position i predict the
next token conditioned only on that prefix and the first i candidates. Every
accepted candidate equals the target argmax. At the first mismatch, the correction
is the target argmax. Restoring and replaying reinstates the invariant. Terminating
on EOS or the output cap gives the same sequence as target greedy. This is an
algorithmic argument; tests establish it for tiny random weights, not every possible
floating point near-tie or quantized Metal kernel on the full model.

**Does pass 1 depend on N? No, in this PR implementation.** `_run_loop` runs the
prelude once, passes `bank=None` to the first core visit, and constructs messages
only for later passes. Neither the first core's message gate nor its attention
residuals reads total N. Tests compare every prelude/core layer's first-pass hidden
activation at N=1,3,5: maximum absolute difference **0.0**, including the last core
layer. The final block *does* receive the last pass's states, so its cache must not
be shared. Prelude and first-core caches could be reused with a staged verifier
that also retains the prelude/core hidden and residual-bank tensors. This reference
recomputes them rather than adding that optimization. Equal first-pass activations
do not make it correct to append the same positions to an already advanced cache.

## B. Per-token KL exit

`adaptive_logits` executes the real prelude/core/message-bank recurrence, runs the
final block and output head after each core pass, and stops when
KL(previous distribution || current distribution) < threshold. KL is calculated
in float32 across the unpadded vocabulary. Minimum exit depth is 2 (two distributions
are required); `max_passes=1` is also supported as a fixed one-pass call. Threshold
0 disables early exit. This is a zero-shot heuristic, not a lossless method.

**Cache policy:** this first reference is deliberately cache-free. It recomputes
the full generated prefix each token, executing core passes incrementally and
stopping immediately at the selected depth. Thus no missing/deeper KV positions
are used. Within a call, all prefix positions run at each tested depth; earlier
tokens' prior exit decisions are not carried forward. This differs from a persistent
per-position halting model with copied/fallback KV. It establishes an explicit,
reproducible semantic baseline, but is unlikely to accelerate generation. A future
cached variant must specify and test deeper-cache backfill or fallback semantics.

## Benchmark protocol

`prompts.json` freezes 40 inputs: the first 20 lexically sorted archived
LongMemEval `bm25-standard` reader prompts with stored `answer.prompt`, and 20
general/code prompts. Each memory row records its original source and SHA256.
No truncation, synthetic memory substitution, external judge or network access.
Chat templates wrap each complete prompt once. Results include exact token ids.

`bench.py` runs baselines N=1,2,3,5; A with K=2,4,8 and N_draft=1,2;
B at thresholds 0, 1e-5, 5e-4, 1e-2. It warms the model, obtains 3-pass references,
then runs methods sequentially, writing JSON plus a markdown table. Throughput is
**end-to-end output tokens / elapsed seconds, including prompt prefill**, not
steady-state decode TPS. Exact match is per-prompt sequence equality to 3-pass
output; token agreement is position-wise with missing positions counted wrong.
No accuracy claims follow from either metric. Acceptance length counts matching
draft tokens per round, including zero and partial final rounds. Adaptive average
passes counts selected depth, not total prefix work. For speculation average
passes is n/a: `loop_positions_per_output_token` instead counts draft + verification
+ replay token-depth work, excluding both initial prefills. Peak memory uses MLX's
GPU allocator peak, reset per prompt, includes resident weights, and is null on CPU;
it is not process RSS or system unified-memory peak. Timing excludes load/tokenization.

## Exact commands

On the workstation, tiny offline CPU suite (no full model or heavy build):

```bash
cd benchmarks/inkling
PYTHONPATH=<checkout> \
  <scratch>/bin/pytest -q research/loop-decoding/tests
PYTHONPATH=<checkout> \
  <scratch>/bin/python research/loop-decoding/bench.py \
  --tiny --limit 1 --max-tokens 2 --output <scratch>
```

For the Mac Studio, first serialize with the lab's heavy-job owner and stage
an existing MLX varloop checkpoint at the path below. Do not use the fixed Inkling
checkpoint or download weights as part of this command. Transfer this directory,
its reused pass-count helper, and tiny config (the latter is only for `--tiny`):

```bash
cd benchmarks/inkling
rsync -aR research/loop-decoding research/refusal-loops/loops.py \
  direction/tests/tiny_config.json <lan-address>:inkling-lab/loop-study/
timeout 30 ssh <mac-studio> 'df -h /'
timeout 14400 ssh <mac-studio> \
  'cd ~/inkling-lab/loop-study && ~/inkling-lab/mlxlm-venv/bin/python research/loop-decoding/bench.py --model ~/inkling-lab/models/TML-d24-varloop-research-mlx --max-tokens 64 --output research/loop-decoding/results/macstudio-64'
```

The model path is an **explicit staging destination**, not a claim it already
exists. The command refuses a missing path. Request 15 GB free after staging.
No the Mac Studio job has been run. Allow several hours provisionally; no measured full-model
runtime is available, especially for the cache-free adaptive arm and long memory
prompts. The 4-hour SSH timeout is a guard, not a runtime estimate; benchmark output
is written at completion. Start with `--limit 1 --max-tokens 8` to calibrate before
the full run. Avoid overlapping jobs and leave shared services untouched.

## Why this may be slower

- Every verification still runs all target passes, plus the drafting work.
- Decode can be weight-bandwidth-bound; shared MoE weights and batch size matter.
- Rejected rounds restore and recompute, with large cache snapshots and extra memory.
- Draft and target maintain two prefills and two complete depth-specific caches.
- Short acceptance, Python synchronization, logits materialization and host argmax
  reduce gains; no fused cache sharing or bonus-token optimization is implemented.
- Adaptive exit runs the final block repeatedly and recomputes the full prefix;
  fewer reported passes does not mean less total work than cached greedy.
- Quantization, long contexts and hardware kernels can change acceptance and timings.

Prior context: `../tps/07-adaptive-loops.md` and `../tps/02-speculative-decoding.md`
cover LoopSpec, LoopSkim, Huginn KL exit and DSpark. This experiment uses loop-depth
drafts, not Inkling's trained DSpark/MTP head. Novelty is a research question, not
established by these implementation tests.

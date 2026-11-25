# Study 17: predicting answer changes and testing the learned message gate

Prepared on the workstation, 2026-11-25. **No varloop checkpoint run has been performed.**
`examples/synthetic/` contains pipeline checks and SVGs from a planted synthetic
signal; these are not model findings. The target is the existing local copy of
`thinkingmachines/TML-d24-varloop-research` using mlx-lm PR #2086, reference commit
`e2b5bbd3bd9d186dea895e60802aa765e70b9d93`.

## Questions and preregistration

1. Do pass-1 residuals predict whether the fixed three-pass token/answer differs
   from the one-pass token/answer, beyond next-token entropy and top-two margin?
2. Does the 1→2 message carry additional predictive information?
3. Does the learned message gain gate identify tokens where an additional pass
   changes the output, and how does its stopping curve compare with KL?

The primary outcome is per-stratum token-flip AUC on leave-one-stratum-out tests.
A secondary analysis predicts complete answer flips from the first prediction
position only. Five-fold family-grouped out-of-fold results accompany both.
Logistic C=1, balanced class weights, training-only standardization, seed 1701;
no hyperparameter search. Residual/message vectors receive a fixed signed
feature-hash projection to 256 dimensions, before fitting, with no data- or
label-dependent choices. `--projection-dim 0` enables a costly full-vector
sensitivity run, which must be reported separately, not chosen by held-out AUC.

Raw entropy and negative probability margin are fixed-direction baselines.
Report paired AUC deltas and 95% percentile intervals from 1,000 family-cluster
bootstrap draws, within each stratum. A probe must beat **both** baselines;
`beats_both_baselines` requires each paired interval's lower bound above zero.
If probes do not beat entropy, that is the result: no post-hoc feature, layer,
stratum, regularization, threshold or prompt selection to rescue the claim.
These are exploratory intervals across several comparisons, not adjusted tests.
A null constrains these fixed linear sketches and this prompt set, not all possible
nonlinear or full-vector predictors. Single-class strata have undefined AUC (`null`), never a fabricated 0.5.

The controller has a separate null: gate RMS has no useful advantage over the
consecutive-output KL policy at matched average pass count and agreement. AUC
predictability alone does not establish a useful controller or speedup.

## Frozen prompts

`prompts.py` generated `prompts.jsonl`: exactly 400 prompts, 100 per stratum,
seed 1701, SHA-256
`e2f4f289af94abc0924a9d37ecfb7ba54abd204136dfa96a1d4e2083eaf59993`.

- Recall: 20 public capital-city facts, five short phrasings each. Cross-validation
  groups all phrasings of a country together. This narrow geography stratum
  supports no claim about factual recall generally.
- Two-hop: invented node maps with two links, no external knowledge needed.
- Memory: the shortest 100 complete public LongMemEval archived BM25 reader
  prompts from `benchmarks/longmemeval/results/full/items/*--bm25-standard.json`,
  the archive replayed by `labs/memory.py`. Exactly one lane per question; no
  context truncation. They range from 3,881 to 6,377 characters. Source filenames,
  source SHA-256 and question IDs accompany each item. These are public benchmark
  conversations, not private memory or personal data.
- Code: short authored Python arithmetic return-statement completions.

`family` is the split/bootstrap unit (all tokens of a prompt stay together).
The memory benchmark may share source conversations between question IDs; there
is no conversation-level split claim. Code/two-hop templates also repeat, so
held-out-stratum evaluation is the stronger generalization check.
Regenerate with `python prompts.py` only on the workstation with the archive available.
The frozen JSONL is sufficient for all model runs.

## Collection and labels

`flips.py` greedily generates independent one- and three-pass continuations.
All strata use the checkpoint's chat template with `reasoning_effort='none'`;
`--raw` is an explicitly different protocol for raw completions. Each token
position on the three-pass continuation is then replayed at 1, 2 and 3 passes on
exactly that prefix. No KV cache is reused: cached prefixes at different depths
would introduce a second confound. This is intentionally slower than decoding.
The three-pass replay argmax must match its teacher token (covered by tiny tests).

`tokens.jsonl` records the three argmax IDs, token flips, entropy, probability
margin, KL(P2||P1), KL(P3||P2), and gate RMS at the two receiving passes. The
per-prompt NPZ stores float32 pass-1 residuals and 1→2 messages, signed tanh gain
gates and forget gates at zero-based physical layers 6, 11, 17. Feature order is
sorted layer, then q/k/v/mlp role (lexicographic for separate gate mappings), then
hidden dimension. Gate RMS summaries cover **all** core layers and four channels.
Manifest records source/config/tokenizer hashes, prompt hash and completion count.
For immutable weight provenance, retain the checkpoint's original download
revision/verification manifest alongside the result; a directory path is not a
weight revision. Incomplete collection is rejected by the analysis tools.

`answers.jsonl` retains raw decode, final text channels, generated token IDs and
capping flags. An answer flip means exact stripped **final text** differs; it
means neither semantic difference nor improved correctness. Capped continuations
or absent final text have `answer_flip: null` and are excluded from answer probes.
Token probes still use their observed tokens. Analysis reports eligible counts;
if too few complete answers remain, it reports insufficient data. The 32-token
budget is frozen for the primary short-output run. A longer-budget study is a
separate protocol, not a repair chosen after observing AUC. This study measures
output stability, not reference-answer accuracy.

`capture.py` is a scoped read-only adapter over `refusal-loops/loops.py`. The
sibling `message-lab/hooks.py` did not exist at initial implementation; the
adapter captures both boundaries and now reuses its `gate_values` equation when
available. Its fallback is the exact same PR formula. No model weights or PR
source are edited. Hooks are serial, process-global, and restored on exceptions.

## Honest stopping costs

The PR resets the loop core to its prelude state between passes. `MessageInput`
reads the preceding pass's bank. Each layer's `MessageGate` then computes
`tanh(gain_projection(down_projection([norm(hidden), norm(message)])))` **inside
the receiving pass**. Most gate values therefore depend on execution of pass 2.
The gate is a mixing controller, not a trained halting head.

`controller.py` uses fixed grids, with no retraining or evaluation-set quantiles:

| Signal | Earliest decision | Offline policy |
|---|---:|---|
| Held-out residual probe | after pass 1 | score below threshold: choose 1; otherwise 3 |
| 1→2 gate RMS | after pass 2 | RMS below threshold: choose 2; otherwise 3 |
| KL(P2||P1) | after pass 2 | KL below threshold: choose 2; otherwise 3 |

A gate policy cannot save pass 2; this is reflected in average passes. Using
2→3 gates or KL(P3||P2) cannot save pass 3, so those summaries are diagnostic only.
Message/gate probe AUC is labeled by availability; the gate probe is retrospective
and is not used to claim a pass-1 stopping decision.

Reports include all thresholds (`policies.csv`), a joint per-stratum Pareto table
(`pareto.md`/`pareto.json`), and fixed-1/fixed-3 endpoints. Agreement is the selected
argmax versus the fixed-3 argmax **on the fixed-3 prefix**. Counts are token-weighted.
This is offline replay, not a live adaptive decoder: prefix drift, per-pass KV
management, epilogue/output-head recomputation, gate-capture cost and actual wall
clock are not modeled. In particular the gate at 1→2 is only a heuristic for
whether to run 3; it is not a direct measurement of 2→3 marginal value.

## Offline verification on the workstation

No workspace build or checkpoint download is needed. Existing MLX CPU environment:

```bash
cd benchmarks/inkling/research/flip-probes
<scratch>/bin/python -m pip install -r requirements.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
 PYTHONPATH=<checkout> \
 <scratch>/bin/python -m pytest -q tests
```

**Latest result: 9 passed in 4.19 seconds** on the workstation (MLX CPU); shell syntax check
for `run-mac-studio.sh` also passed.

Tiny integration tests instantiate random 16-dimensional, eight-layer
`inkling2_loop` with a three-layer core and vocab 32; no network or external model.
They check read-only logits, selected residuals/messages/gates, restoration on
exceptions, pass-1 consistency and teacher-forced collection. Synthetic tests
check planted-signal recovery with held-out strata, censored answers, deterministic
projection, prompts and policy costs. End-to-end CLI verification generated the
three SVGs in `examples/synthetic/plots/`, report JSON and Pareto CSV/Markdown.
Its 100-bootstrap demo uses a smaller interval budget than the actual study.

Reproduce synthetic artifacts (choose new output directories):

```bash
python synthetic.py /tmp/flip17-synthetic-run
python probes.py /tmp/flip17-synthetic-run --output /tmp/flip17-synthetic-analysis --bootstrap 100
python controller.py /tmp/flip17-synthetic-run \
 --scores /tmp/flip17-synthetic-analysis/token_flip-scores.npz --output /tmp/flip17-synthetic-policies
python plots.py /tmp/flip17-synthetic-analysis /tmp/flip17-synthetic-policies --output /tmp/flip17-synthetic-plots
```

## Scheduled the Mac Studio run plan (not executed)

Schedule this after other heavy jobs. `run-mac-studio.sh` acquires the
existing directory lock; it never stops a service or removes another job's lock.
The checkpoint must already exist; this study does not download it. Check root
disk only; retain at least 15 GiB after model and result storage. The wrapper
requires 20 GiB free before collection to allow about 5 GiB of output.

Transfer from the workstation, preserving the sibling import layout:

```bash
cd benchmarks/inkling/research
 timeout 20 ssh <mac-studio> \
 'mkdir -p ~/inkling-lab/research/refusal-loops ~/inkling-lab/research/message-lab; df -h /'
rsync -a --exclude __pycache__ --exclude .pytest_cache --exclude examples \
 flip-probes/ <lan-address>:inkling-lab/research/flip-probes/
scp refusal-loops/loops.py <lan-address>:inkling-lab/research/refusal-loops/
scp message-lab/hooks.py <lan-address>:inkling-lab/research/message-lab/
timeout 120 ssh <mac-studio> \
 '~/inkling-lab/mlxlm-venv/bin/python -m pip install -r ~/inkling-lab/research/flip-probes/requirements.txt'
```

One diagnostic pilot (not pooled with the frozen full run):

```bash
timeout 7200 ssh <mac-studio> \
 'timeout 7000 bash ~/inkling-lab/research/flip-probes/run-mac-studio.sh ~/inkling-lab/results/flip17-pilot --limit 8'
```

After inspecting pilot time/RSS and final-answer eligibility, scheduled collection:

```bash
timeout 172900 ssh <mac-studio> \
 'timeout 172800 bash ~/inkling-lab/research/flip-probes/run-mac-studio.sh ~/inkling-lab/results/flip17-full'
```

After collection, the following are CPU analyses; preferably copy results back to
the workstation and use its environment. These are also exact the Mac Studio commands if scheduled:

```bash
timeout 14400 ssh <mac-studio> 'cd ~/inkling-lab/research/flip-probes && \
 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ~/inkling-lab/mlxlm-venv/bin/python probes.py \
 ~/inkling-lab/results/flip17-full --output ~/inkling-lab/results/flip17-analysis'
timeout 600 ssh <mac-studio> 'cd ~/inkling-lab/research/flip-probes && \
 ~/inkling-lab/mlxlm-venv/bin/python controller.py ~/inkling-lab/results/flip17-full \
 --scores ~/inkling-lab/results/flip17-analysis/token_flip-scores.npz \
 --output ~/inkling-lab/results/flip17-policies'
timeout 600 ssh <mac-studio> 'cd ~/inkling-lab/research/flip-probes && \
 ~/inkling-lab/mlxlm-venv/bin/python plots.py ~/inkling-lab/results/flip17-analysis \
 ~/inkling-lab/results/flip17-policies --output ~/inkling-lab/results/flip17-plots'
```

Collection refuses an existing output directory rather than mixing settings.
It checkpoints per item but has no automatic resume; retain partial runs as
incomplete evidence and schedule a new directory. Timeout cleanup only removes
this invocation's directory lock. Interrupted NPZ/token writes are never analyzed
as a complete run.

## Resource estimates, not measurements

At 400 × 32 generated tokens, the upper bound is **64,000 full-prefix forwards**:
one 1-pass and one 3-pass greedy trajectory, then three teacher-forced forwards per
3-pass token. EOS reduces this. For planning, 0.2–2 seconds per full-prefix
forward implies roughly **3.6–36 hours**, plus load and Python hook overhead;
this is an assumption, not measured the Mac Studio throughput. Long memory prefixes dominate.
The eight-item pilot's `manifest.json` elapsed time and `/usr/bin/time -l` RSS
must replace that estimate before scheduling. Do not extrapolate cached tokens/s.

At hidden size 2304, three captured layers, four message channels, 12,800 tokens:
raw selected float32 residuals/messages/gain/forget are about **4.6 GB** total
before compression. Model storage is separate and must be checked against the
existing download manifest. Budget roughly **32–64 GiB** collection RAM initially,
then replace with pilot peak RSS; full-prefix activations and logits make it
context-sensitive. No 96-GiB fit guarantee is claimed. Default 256-dimensional
probe sketches stream per-prompt NPZ data; plan **under 2 GiB** analysis RAM and
minutes to an hour for fits plus 1,000 cluster bootstrap replicates. Disabling
projection can exceed **15 GiB**, so full-vector analysis must be scheduled on
an appropriate machine, not run on the workstation as an unchecked full job.

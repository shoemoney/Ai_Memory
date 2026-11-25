# Study #9: does loop depth substitute for retrieval quality?

Prepared 2026-11-25. **`--design depth-retrieval`** adds a balanced LongMemEval
experiment: passes **{1,2,3,5} × {oracle sessions, BM25, dense}**, using exactly
**150 questions in each of 12 cells** (1,800 reader answers, 5,400 judge calls).
This is **reader replay over archived retrieval, not the official LongMemEval
protocol**. Retrieval is not rerun. Oracle uses archived oracle dates/sessions;
BM25 and dense retain their archived standard-date contexts. Thus these lanes
also differ in context length, session formatting, and potentially dates: this is
an operational retrieval-quality comparison, not a pure evidence-presence intervention.
Stock and varloop are distinct models; stock is planning data, not a p3 control.

The existing sweep remains the default `--design screen`; its selection,
five-lane LongMemEval + LoCoMo behavior and output paths are unchanged. The new
mode excludes LoCoMo, full-standard, and Mem0 and always appends
`depth-retrieval/` to the supplied output root. No heavy the Mac Studio work was run.
The optional evidence manipulation design is not implemented in this change;
manual identification of required facts remains necessary for a causal evidence study.

## Frozen subset and eligibility

`depth-retrieval-selection.json` records IDs, **dataset `question_type`**, archive
`stratum`, input hashes, seed, and allocation. Of the original 300 questions,
**212** have a scored oracle prompt and satisfy the book reader's
`prompt_tokens + 512 <= 8192` rule in **all three lanes**. No answer correctness
enters eligibility or sampling. Use the book's frozen tokenizer counts rather
than silently changing eligibility with another tokenizer. These counts certify
the archived rule; a real server context error stops the sweep rather than
skipping a cell. Selection is proportional largest-remainder allocation within
the eligible population, sorted IDs, seeded sampling/shuffle (20261125).

| Archive stratum | Eligible | Selected |
|---|---:|---:|
| multi-session | 30 | 21 |
| temporal-reasoning | 44 | 31 |
| knowledge-update | 33 | 23 |
| single-session-user | 38 | 27 |
| single-session-assistant | 34 | 24 |
| single-session-preference | 18 | 13 |
| abstention | 15 | 11 |

The dataset has six native type labels; **abstention is the book's `_abs` stratum,
not a seventh native `question_type`**. Preserve both fields rather than relabel
questions. The five-group report merges the three single-session types (n=64)
and shows abstention separately; raw native-type and seven-stratum tables also
remain available. The dataset's `multi-session` label is the requested multi-hop
proxy; no invented multi-hop annotations are added. Selection changes the target
population to oracle-fit questions; do not compare its accuracy directly with
stock's 300-question BM25/dense denominator or generalize to all LongMemEval.

## Preregistration (before varloop results)

Primary contrast: **gap shrink**
`(oracle_p1 − BM25_p1) − (oracle_p5 − BM25_p5)`; positive means the gap narrows.
Use a paired question bootstrap, preserving each question's 12 outcomes together
and sampling within fixed archive strata, seed 20261125, 10,000 replicates,
percentile 95% intervals. The primary interaction is one prespecified contrast.
All other depth pairs (18 within-retrieval contrasts), lane pairs (12
within-depth contrasts), intermediate-depth interactions and per-type breakdowns
are exploratory with unadjusted intervals. Do not select a favorable pair and
call it confirmatory. Three judge votes are not three independent questions.

Operational conclusions, using p1→p5 and a prespecified **5 percentage point**
materiality margin:

- **Depth substitutes for retrieval:** the primary gap-shrink interval is wholly
  above zero **and** the BM25 depth-gain interval is wholly above zero. Report
  residual oracle advantage; narrowing alone does not establish full substitution.
  A falling oracle score without a BM25 gain does not qualify.
- **Depth helps only when evidence is present:** oracle depth gain is positive
  with its interval wholly above zero, BM25 and dense gains have intervals fully
  inside ±5pp, and gap shrink's upper bound is at most zero. This is an
  **oracle proxy**, not proof that retrieved contexts lack evidence. BM25/dense
  evidence presence is not annotated. Without interval precision this label is
  unavailable; a nonsignificant BM25 gain is insufficient.
- **No material effect:** all three p1→p5 gains and the primary interaction have
  intervals entirely inside ±5pp. Otherwise report **inconclusive / mixed**.
  A null test is not equivalence. This screen has limited power for small effects.

Accuracy for each cell has a 95% Wilson interval. The iso-accuracy table compares
all 16 BM25-depth/oracle-depth pairs using paired differences. An established
match requires the entire 95% interval for `BM25 − oracle` within ±5pp; separately
label mere point matches. These exploratory equivalence checks do not establish
familywise coverage. Bootstrap intervals can degenerate with no observed
question discordances, especially in small type groups; interpret these with
sample size and Wilson uncertainty, never as exact population equality.

`analyze_depth_retrieval.py` fails on absent/extra/unscored cells, ID mismatch,
selection/context mismatch, altered judge/reader protocol or inconsistent serving
provenance. It writes `analysis.json`, `iso-accuracy.md`, `depth-retrieval.svg`
(lines + Wilson intervals) and `depth-retrieval-types.svg` (five-group small
multiples). It does not impute failures or silently use cellwise denominators.

## Runtime and detectable effect

`depth-retrieval-planning.json` freezes the calculation and hashes of stock
`run.log`, `memory-samples.jsonl` and LongMemEval summary. `depth_retrieval.py plan`
recomputes it. Stock per-answer means: oracle **5.835s**, BM25 **3.022s**, dense
**3.041s**; judge mean over these lanes **0.155s/vote**. Scale reader work by
layer visits: `(24+36+48+72)/48 = 3.75` stock-p3 units. Four passes × 45 batches
of ten pairs means **180 starts**, including initial starts; budget **30s/start**.
Total: **3.59h**. A stress case with 60s/start and 5 stock-p3 units is **5.71h**.
The full requested **150** therefore fits the approximately-eight-hour plan;
no subset reduction is proposed. These are forecasts, not measured varloop times.

The log records 184 starts across multiple labs/retries; do not treat the entire
run as a LongMemEval timing. The 69 memory samples span 2,151s with 49 observed
server-PID changes and median spacing 30.6s. Sampling aliases startup; this
spacing includes inference and is **not** measured startup latency. Peak sampled
swap use is 6,311 MiB, so load pressure and native-versus-stock-oQ throughput
remain material timing risks. Download/conversion and provisioning are excluded.
Use an initial p3 batch to audit timing; freeze any revised sample before running
all cells, never shrink during analysis. All three lanes must use the same model
artifact and reader template, generation and pinned Gemma judge settings.

At n=150, nominal alpha .05 / 80% power normal approximation with assumed paired
discordance q=.42 gives **14.8pp** minimum detectable p1→p5 depth gain:
`(z_.975 + z_.8) sqrt(q/n)`. Sensitivity q=.2/.4/.6: **10.2/14.5/17.7pp**.
For the interaction, assuming independent lane difference scores with variance
.42 each gives SD²=.84 and **21.0pp** detectable gap shrink. Actual cross-lane
covariance/discordance is unknown; these are planning assumptions, not empirical
power estimates. Small subgroup effects and ±5pp equivalence are underpowered.

## Operator commands (from the workstation; schedules the Mac Studio)

Provision and verify the pinned varloop source and pinned Gemma judge first, using
the serving instructions below and `../../labs/README.md`. Reserve the Mac Studio and make sure its shared heavy lock is free first. This design needs only
the Gemma tunnel at 39711, not the LoCoMo Qwen judge. Existing ownership, 39851
tunnel, thinking-off, disabled draft/cache and restart-between-batches controls
remain in force. Model is already provisioned; the script does not download it.

```bash
cd <checkout>
for p in 1 2 3 5; do
  bash benchmarks/inkling/research/memory-loops/sweep.sh "$p" \
    --design depth-retrieval \
    --model $HOME/inkling-lab/models/TML-d24-varloop-research \
    --output-root benchmarks/inkling/results || exit 1
done
python3 benchmarks/inkling/research/memory-loops/analyze_depth_retrieval.py \
  --results benchmarks/inkling/results/depth-retrieval \
  --output benchmarks/inkling/results/depth-retrieval/analysis
```

To regenerate an explicitly revised design before any inference:

```bash
python3 benchmarks/inkling/research/memory-loops/depth_retrieval.py select \
  --n 150 --selection /tmp/revised-depth-selection.json
# Pass --selection /tmp/revised-depth-selection.json and a fresh --output-root
# to every sweep and to analysis. Never overwrite the frozen default mid-run.
```

Offline verification uses the real labs wrapper with a loopback stub and three
eligible archived questions at all depths, exactly 36 reader + 108 judge calls,
resume without calls, hook failure, manifest drift and missing-cell rejection.
The synthetic 40-question analysis fixture checks interaction direction,
Wilson values, paired intervals, equivalence versus uncertainty, and SVG XML.
Fixture outcomes are not model performance results. The two SVGs in `fixtures/`
are labeled synthetic examples, not measured scores.

Verified on the workstation: **10 tests passed in 8.762s, no skips**, including all seven
legacy tests. Python compilation and shell syntax passed; see
`depth-test-results.txt`. No project commit or the Mac Studio operation was performed.

```bash
python3 -m unittest discover -s benchmarks/inkling/research/memory-loops -p 'test*.py' -v
```

---

# Legacy screen and shared serving documentation

# Memory accuracy versus loop passes

Prepared 2026-11-25. Run the same varloop weights at **1, 2, 3, 5 passes**, replaying
frozen retrieval contexts through the existing `labs/memory.py` scorer. No real
varloop inference, conversion, download, or heavy the Mac Studio job was performed here.
Code and offline tests are ready; Apple Silicon serving is a manual step.

## Serving control and source evidence

Use **oMLX 0.8.3**, already installed in `~/inkling-lab/omlx-venv` on macstudio.
[`TextArgs.from_dict`](https://github.com/jundot/omlx/blob/v0.8.3/omlx/patches/inkling2/model.py#L80)
reads **`text_config.loop_num_passes`** and overrides
`text_config.loop_config.num_passes`. This is a checkpoint config setting, not a
request parameter or a model-settings UI option. `model_settings.py` exposes no
loop-count setting. `layer_schedule()` allocates one cache per visit: the 24-layer
model has `12 + 12*p` visits, hence **24, 36, 48, 72** at the four tested counts.
The tag's
[varloop test](https://github.com/jundot/omlx/blob/v0.8.3/tests/test_inkling_vlm_mtp.py#L1350)
explicitly covers the research model and the one-pass cache case.

`remote.py` creates private symlink views of one source directory, writes both
pass fields in each view's own `config.json`, and starts a fresh oMLX process.
Source config and weights stay intact. Each process sees only its selected view,
serves **127.0.0.1:39851**, disables disk/prefix cache and has a 60 GB memory guard.
It removes `mtp_config` and hides `mtp.safetensors` in every view, including p3;
all speculative model settings are false. DSpark's stock visit indices are
calibrated for p3, so enabling it would introduce a second changed variable.
The process uses private HOME, settings, logs and caches under
`~/inkling-lab/memory-loops/`. Port 39850 and shared 8766 are never controlled.

No fallback is needed. PR
[mlx-lm #2086](https://github.com/ml-explore/mlx-lm/pull/2086), checked locally at
`e2b5bbd3bd9d186dea895e60802aa765e70b9d93`, also reads
`args.loop_config['num_passes']` in `layer_visits`, `_run_loop`, and `make_cache`.
Its `TextArgs` does **not** recognize `loop_num_passes`; a fallback would need to
change the nested `loop_config.num_passes` before construction/cache allocation.
No edits to that checkout or runtime fallback are needed for this study.

The [model card](https://thinkingmachines.ai/model-card/tml-d24-varloop-research/)
describes a native **mixed NVFP4/MXFP8/BF16** checkpoint, not a fully BF16 model.
Pinned source revision is **91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d**;
`source-evidence.json` records fetched config, per-file public size/hash metadata,
URLs, exact oMLX tag commit, and hashes of inspected source files.
Its `is_varloop: true` core is zero-based `[6,18)`, default 3 passes.

**oQ is supported by the tag's source, but varloop conversion was not measured.**
The `inkling2_loop` type is registered in `oq_layout.py`, with loop-aware
calibration and preserved FP32 controllers. The tag has
[looped oQ tests](https://github.com/jundot/omlx/blob/v0.8.3/tests/test_oq.py#L9673).
An oQ4/e conversion keeps early NVFP4 experts, requantizes the final MXFP8 experts
to affine4, and uses affine8 attention/embeddings/head. Same-shaped stock tensors
in `../../infra/tensor-comparison.md` occupy **16,211,566,592 bytes (15.10 GiB)**
without draft; **16,847,362,336 bytes (15.69 GiB)** with draft. Those are a storage
forecast for varloop, not a measured varloop artifact. Enhanced oQ skips its
output-error refit for this architecture. Prefer the **packed native source**
for this study: it avoids conversion time, extra disk, and quantization confounds.
If a verified varloop oQ artifact is selected instead, use that same artifact for
all passes, a fresh output root, and report the quantization as part of the study.
Do not compare native p1 to quantized p3. The fully BF16 expansion is about
53 GB in weights alone and is unnecessary.

## Fixed sample, comparisons, and power

`selection.json` fixes **48/300 LongMemEval questions**, proportional across the
seven archived strata, and **24/67 matched LoCoMo questions**, proportional across
conversation × category. Largest-remainder allocation, sorted-ID sampling, seed
20261125, then a seeded shuffle; no answers/scores enter selection. All three
eligible conversations (0,1,3) are retained. The same IDs run at every pass count
in all five memory lanes. The selected LongMemEval set has 176 scored lane pairs
(48 each BM25, dense, Mem0; 32 oracle), 48 original full-standard skips, and 16
oracle skips. LoCoMo has 120 scored pairs. These are **72 question clusters**, not
296 independent observations; full-standard provides no accuracy estimate.

The primary screen is paired **p1 versus p5**, separately in LongMemEval BM25 and
LoCoMo full-context. p2/p3 and other lane comparisons are exploratory. Report
per-lane paired differences with question-level bootstrap intervals and exact
McNemar tests on discordant questions. Use alpha .025 per primary lab for the two
primary tests; do not claim significance from uncorrected searches across all six
pass pairs or by treating judge votes/lanes as independent. LoCoMo shares histories
across questions and only three conversations are available, so question-level
power is optimistic for generalization across conversations. Report each
conversation separately; this sample cannot establish population-level effects.
Stock Inkling scores inform planning only: stock and varloop have different later
training and are not an interchangeable p3 control.

`planning.json` freezes the observed stock summaries and timing estimates;
`plan.py` recomputes them as stock outputs change. LongMemEval stock BM25 is
210/300 = .700; stock matched LoCoMo full-context is 47/67 = .7015. The stock
LoCoMo run is **incomplete**, with no other matched lanes scored at this snapshot.
There are no measured across-pass discordances yet. Assume for planning
`q = 2*p*(1-p)`, about .42; this is an independence assumption, not a paired
estimate. Normal-approximation 80% minimum detectable difference is
`(z_(1-alpha/2) + z_.8) * sqrt(q/n)`:

| Sample | Unadjusted alpha .05 | Two-lab alpha .025 | q=.2 / .4 / .6 at alpha .025 |
|---|---:|---:|---:|
| LongMemEval 48 | 26.2 percentage points | 28.8 pp | 19.9 / 28.1 / 34.5 pp |
| LoCoMo 24 | 37.0 pp | 40.7 pp | 28.1 / 39.8 / 48.7 pp |

This is the smallest practical balanced **large-effect screen**, with targets of
30 pp and 41 pp at 80% nominal power: the formula gives at least 45 and 24
questions, rounded to 48 and 24 for stratification. The formula is a coarse
normal approximation at these small N, not an exact prospective McNemar power
calculation. A five-point effect with q=.42 would need roughly 1,597 paired
questions per lab at alpha .025, beyond both archives and the time budget. A null
result must not be presented as equivalence. No valid sample can deliver strong
power for small effects within six hours under the unchanged harness.

## Why the labs harness stays unchanged

`protocol.py memory` imports `labs/memory.py` and invokes its original `main()`.
Two process-local adapters extend the variant parser to `varloop-pN` and reorder
the archived manifest/LoCoMo matched ID list so the existing `--limit` selects the
fixed stratified sample. The complete archive lengths (300/67/320), stored
records, prompts, source hashes, eligibility checks, lane ordering, generation
settings, retries, judge aliases/revisions/seeds, and scoring code are preserved.
The reordered ID list also drives LoCoMo's matched summary, avoiding its original
sorted-prefix conversation bias. No shared labs or book archive file is edited.
`limit` remains set in the original manifest to label the reduced sample;
`study.json` records actual selected IDs and adapter/selection hashes.

`protocol.py batch` is the memory-only version of `labs/batch.py`: at most ten
unfinished item/lane pairs per process, checked shell restart hook between
**every pair of batches including the lab transition**, and a no-progress guard.
Quality is outside this study. Hook success requires the intended model to be
advertised and a real thinking-off warmup completion. Every reader request keeps
both `thinking_budget: 0` and `enable_thinking: false`; judge calls receive neither.
The original pinned Gemma (39711) and Qwen (39700) judges must already be available
from the workstation as described in `../../labs/README.md`.

## Run commands

No Mac jobs are launched by the offline tests. These commands are scheduled by hand while the other heavy Inkling work is stopped. `heavy.lock`
serializes this server with the stock lab and conversions; the script refuses an
occupied lock. A stock lab server holding it must be stopped by its owner first.

Provision the source **once** on the Mac Studio, after checking free disk. The full public
snapshot is **20,191,629,870 bytes (18.81 GiB)**, including the unused 635.8 MB draft.
The main weight shard is 19,526,019,168 bytes. Keep at least **15 GiB free** after
download; the check below allows an extra GiB. Avoid storing another source copy
in the HF cache. These are exact pinned public sizes, unlike the oQ forecast.

```bash
# Run on the workstation; download is optional if this exact source is already present.
ssh <mac-studio> 'timeout 15 df -h /'
ssh <mac-studio> 'timeout 1800 bash -s' <<'REMOTE'
set -euo pipefail
lab="$HOME/inkling-lab"
mkdir "$lab/heavy.lock"
trap 'rmdir "$lab/heavy.lock"' EXIT
"$lab/omlx-venv/bin/python" -c 'import shutil; assert shutil.disk_usage("/").free >= 20191629870 + 16*1024**3, "Insufficient disk with 15 GiB reserve"'
HF_HOME="$lab/hf-cache" "$lab/omlx-venv/bin/hf" download \
  thinkingmachines/TML-d24-varloop-research \
  --revision 91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d \
  --local-dir "$lab/models/TML-d24-varloop-research"
REMOTE

cd <checkout>
study=benchmarks/inkling/research/memory-loops
ssh <mac-studio> 'timeout 15 mkdir -p ~/inkling-lab/memory-loops'
scp "$study/verify_source.py" "$study/source-evidence.json" \
  <lan-address>:inkling-lab/memory-loops/
ssh <mac-studio> 'timeout 300 ~/inkling-lab/omlx-venv/bin/python ~/inkling-lab/memory-loops/verify_source.py ~/inkling-lab/models/TML-d24-varloop-research > ~/inkling-lab/memory-loops/source-verification.json'

# Uses only stdlib locally; existing judges must be reachable from the workstation.
export PYTHON=python3
bash "$study/sweep.sh" 1 \
  --model $HOME/inkling-lab/models/TML-d24-varloop-research
# Repeat the identical command at 2, 3, 5, or run all sequentially:
for passes in 1 2 3 5; do
  bash "$study/sweep.sh" "$passes" \
    --model $HOME/inkling-lab/models/TML-d24-varloop-research || break
done
```

Outputs are exactly `benchmarks/inkling/results/varloop-pN/{longmemeval,locomo}/`
with original raw responses and summaries, plus `study.json` and `serving.json`.
The latter binds the source directory/config, weight sizes/mtimes, pass count, and
controller hash. Verify source hashes once with `verify_source.py`; it reads the
weight file in chunks. A converted oQ artifact needs its own verified conversion
record. Resume the same sweep command after a failure; successful answers and votes
are reused. Altering source timestamps, controller, selection, adapter, endpoint,
or settings intentionally requires a fresh `--output-root`.

The sweep uploads only `remote.py`, opens its own SSH tunnel on the workstation 39851, starts
the owned the Mac Studio server, restarts it through the batch hook, and stops it in a
`finally` block on completion/failure/normal termination. It never takes over an
existing tunnel or kills a port owner. Stop validates the saved PID command and
private base path. A failed startup cleans up its own child/lock. SIGKILL, power
loss, or a broken SSH connection can require manual recovery; inspect its
`server.json` and log before removing any lock. Explicit owned stop:

```bash
ssh <mac-studio> 'timeout 90 ~/inkling-lab/omlx-venv/bin/python ~/inkling-lab/memory-loops/remote.py stop --passes 1 --model $HOME/inkling-lab/models/TML-d24-varloop-research'
```

No model is automatically downloaded or removed by `sweep.sh`. Do not use the
stock lab's `restore.sh`, which removes the whole shared lab installation.

## Resources, timing, and validation

Allow **32–40 GB available unified memory** for native weights, serving overhead,
KV caches, and transient allocations; that is a planning allowance, not a
measurement. Long-context p5 has more cache visits. The process has a 60 GB guard
and one request at a time. the Mac Studio has 96 GB total, but other services/judges reduce
availability; check it first. Symlink views use negligible extra
weight storage; keep several GB for raw frozen contexts/results. Keeping both
source and oQ needs roughly 36.5 GB plus logs and the 15 GiB reserve, which can
exceed the currently reported free space. Do not convert without a fresh check.

Stock raw timings at this snapshot: LongMemEval ~3.02 s BM25, 3.04 s dense,
3.13 s Mem0, 5.84 s oracle; LoCoMo full-context **33.83 s**. Judge means are .142 s
and 1.303 s per vote. Unmeasured LoCoMo lanes conservatively inherit its
full-context mean. Scale reader work by `(12+12*p)/48`; sum over passes is 3.75
stock-p3 units. Keep judge time fixed; budget 15 s per cold start/warmup, **144
starts** including initial starts. Total estimate is **6.09 hours**: 4.88 reader,
.60 judge, .60 restart. Assuming no pass-speed benefit and 30 s starts gives
**7.01 hours**. Download/conversion is excluded. Native source can be slower than
the quantized stock used for timing; length retries, load pressure and cold loads
can exceed these estimates. Measure the first p3 batch and revise the schedule;
do not silently shrink the fixed subset mid-sweep. This is an approximately-six-hour
plan, not a measured deadline guarantee.

```bash
cd benchmarks/inkling/research/memory-loops
python3 plan.py > /tmp/varloop-planning-current.json
# Optional native-schedule test reads actual v0.8.3 source; no MLX import/build.
git clone --depth 1 --branch v0.8.3 https://github.com/jundot/omlx.git /tmp/memory-loops-omlx-083
OMLX_SOURCE=/tmp/memory-loops-omlx-083 python3 -m unittest -v test_offline
bash -n sweep.sh
```

Offline tests exercise all four pass labels with three actual selected question
IDs through every lane, fixed matched summaries, reader-only thinking controls,
original judge settings, restart boundaries, zero-call resume, changed-selection
rejection, failure on a nonzero hook, config-view source preservation, unrelated
PID refusal, and actual start/warmup/stop/lock cleanup using a tiny executable
stub on 39851. The native `TextArgs` class is AST-loaded from the actual tag and
its schedule counts are checked without importing MLX. All smoke scores are
canned transport checks. They do not establish numerical parity, real varloop
accuracy, peak memory, oQ conversion success, or genuine no-reasoning behavior.

Local verification on 2026-11-25: **7 tests passed in 5.061 seconds**, no skips;
see `test-results.txt`. `bash -n sweep.sh` and Python compilation also passed.
No the Mac Studio commands were executed during implementation. No project commit was made.

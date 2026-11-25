# Energy and DSpark acceptance

Python standard library only. Preparing this folder involved no model benchmark; the only run on the Mac Studio was a five-second powermetrics capability probe. All inference and installation commands below are scheduled by hand, one heavy job at a time, while the lab lock on the Mac Studio is held.
Never run these against the shared Homebrew server on 8766.

## Energy

On the Mac Studio **macOS 27.2.1 / 26B131**, this succeeded with ten records over 5.4413 s:

```bash
timeout 25 ssh -o BatchMode=yes <lan-address> \
 'sudo -n powermetrics --samplers cpu_power,gpu_power,ane_power -i 500 -n 10 -f plist'
```

`power-probe.json` summarizes the capability check; `tests/fixtures/power-probe.plist`
is its actual raw plist stream, including NUL document separators. This was **not
an idle measurement**: another GPU workload was active. It must not be used as
an experimental baseline.

`power.py` starts a remote powermetrics child and records CPU, GPU, ANE and combined
power. Fields `processor.{cpu,gpu,ane}_power` and `combined_power` are **mW**;
`elapsed_ns` is the sample interval. It integrates the sum of the three rails as
`sum(W * overlap_seconds)`, checks it agrees with combined power, and never adds
combined power a second time. The fixture test independently checks the result
against the plist's mJ energy counters.

This is an estimate of **CPU+GPU+ANE rail energy**, not whole-package or wall-plug
energy: DRAM, display, storage, fans and power-supply losses are not separately
measured. Call it rail energy in figures rather than claiming physical package
energy. A remote clock handshake records the estimated offset and uncertainty;
remote sample receive timestamps bound intervals. The tool clips 500 ms interval
averages at benchmark boundaries assuming uniform power within an interval.
SSH scheduling/clock alignment and powermetrics delivery add boundary uncertainty.
Do not compare extremely short runs as precision energy measurements.

Immediately before each labs subprocess, the sampler measures ten seconds of
baseline (configurable, minimum five seconds). It reports time-weighted mean W,
population variance W², standard deviation W, coverage and sample count. It then
subtracts `baseline_mean_W * benchmark_seconds` from gross joules. Negative net
values remain negative; they indicate background variability rather than free
inference. Missing interval coverage fails the run.

Run from the workstation with the existing lab and judge tunnels. Use the same model id and
results root as the corresponding labs run; completed items are resumed.

```bash
cd benchmarks/inkling/research/efficiency
export MODEL=Inkling-2-Mini-oQ4e-stock
# Start infra/serve.sh and open the SSH tunnel first; warm the model if desired.
./energy_run.sh stock longmemeval 5
./energy_run.sh stock locomo 5
# Optional: BASELINE_SECONDS=30 RESULTS_ROOT=/absolute/results ENERGY_OUT=/fresh/path
# Optional: JUDGE_BASE_URL=http://127.0.0.1:39711/v1 (choose the appropriate lab judge)
```

`N` is the labs adapter's `--batch-size`: at most N unfinished **lane/item pairs**,
not N question IDs. Do not run overlapping writers in the same results directory.
A warmed model baseline measures resident idle power; without warmup the run includes
load and first-use work. Keep this choice fixed across variants and state it.

The output directory contains `samples.json` and `summary.json`. The join hashes
`results/<variant>/<lab>/items/` and `raw/` before and after the run, retaining only
new or changed files. Already-complete items never inflate the denominator.
`status=scored` with a boolean `correct` supplies scored-item and correct-answer
counts; context-too-large skips are disclosed and excluded. Zero correct answers
produce null J/correct, not infinity or zero.

J/request uses newly saved successful HTTP request/response records under `raw/`,
including answer retries and judge calls; answer-only counts and J/answer-request
are separate. Failures without successful response records do not enter this
successful-request denominator. J/scored-item is also provided. The energy window
includes the complete pipeline: reader, local judge(s), waits, file I/O and
orchestration. Thus even J/answer-request is **pipeline energy divided by reader
requests**, not isolated reader energy. If all work resumes from cache, request
counts can be zero and per-request energy is null. Inspect joins before publishing.

the Mac Studio is shared. Other services draw power during both windows; subtraction cannot
attribute fluctuating background power. Publish the baseline mean/variance beside
both gross and net joules and correctness counts, use repeated paired runs, and
avoid a causal per-model energy claim on busy-host measurements. The tool does not
stop shared services or acquire/release the server's `heavy.lock` (the running lab
server already owns it).

The remote sampler terminates its owned powermetrics child when SSH stdin closes;
local cleanup runs on normal exit or interruption. Startup and stalled sample reads
are bounded; the remote command is wrapped in a 7200-second timeout (override
`power.py --max-seconds` for a planned window). Failed labs commands retain their nonzero return code in the energy
summary; do not treat them as completed benchmarks.

## Where DSpark counters come from

Pinned primary sources: [oMLX v0.8.3](https://github.com/jundot/omlx/tree/v0.8.3),
commit `e72868dac12df4be4ced2dc8355f031686283974`. `source-evidence.json` records
SHA-256 for every investigated source file.

- [`omlx/patches/inkling2/dspark.py`](https://github.com/jundot/omlx/blob/v0.8.3/omlx/patches/inkling2/dspark.py#L335)
  loads the bundled `mtp.safetensors` and wraps it in a DFlash-style block drafter.
  It enables context copying by default.
- [`omlx/engine_pool.py`](https://github.com/jundot/omlx/blob/v0.8.3/omlx/engine_pool.py#L4599)
  attaches that drafter through Lightning MTP only when model settings enable MTP.
  Drafter loading can fail softly: the setting alone does not prove activation.
- [`omlx/patches/mlx_lm_mtp/batch_generator.py`](https://github.com/jundot/omlx/blob/v0.8.3/omlx/patches/mlx_lm_mtp/batch_generator.py#L4090)
  `_log_mtp_stats` emits INFO `MTP[uid] finish=... accept=A/D`, with per-depth,
  context-copy and timing breakdowns. Parking/re-entry can emit several disjoint
  segments for a single request. Sum counts, never average rounded percentages.
- **Denominator caveat:** the stats update around lines 4847–4866 increments
  `depth_drafted` only through the first rejection, because its loop breaks there.
  `D=sum(depth_drafted)` is the number of evaluated prefix positions, **not all
  proposed draft tokens**. The existing log cannot recover the unvisited suffix.
  Context-copy counts are separate from DSpark counts.
- [`omlx/api/openai_models.py`](https://github.com/jundot/omlx/blob/v0.8.3/omlx/api/openai_models.py#L481)
  usage includes `generation_duration` and `generation_tokens_per_second`, but
  completion details contain only reasoning tokens, not accepted/proposed drafts.
- [`omlx/admin/benchmark.py`](https://github.com/jundot/omlx/blob/v0.8.3/omlx/admin/benchmark.py#L2131)
  honors MTP engine selection and reports throughput, not exact draft proposal
  counters. The `scheduler.py` `vlm_mtp stats` line belongs to the external VLM MTP
  route and is not the bundled Inkling Lightning MTP metric.

Consequently `instrument_mtp.py` adds one integer counter update per non-copy chain
cycle (`+=k`, including rejected suffix) and an INFO summary at each segment end:
`EFFICIENCY_MTP[uid] ... accepted=A proposed=P copy_accepted=CA copy_proposed=CP`.
It preserves original counts, acceptance, samplers and generation logic. It
refuses any installed source whose hash differs from pinned v0.8.3 and makes a
backup. Apply it to the **lab venv only**, with the lab server
stopped, then restart. Additional logging has a small unquantified overhead;
use the same instrumented installation for both modes and disclose it.

Setup, from the workstation (not part of the offline tests):

```bash
cd benchmarks/inkling/research/efficiency
export MODEL_DIR=$HOME/inkling-lab/models/Inkling-2-Mini-oQ4e-stock
export MODEL=${MODEL_DIR##*/}
timeout 65 ../../infra/serve.sh "$MODEL_DIR" stop
timeout 20 scp instrument_mtp.py <lan-address>:inkling-lab/instrument_mtp.py
timeout 20 ssh <mac-studio> \
 '~/inkling-lab/omlx-venv/bin/python ~/inkling-lab/instrument_mtp.py --path ~/inkling-lab/omlx-venv/lib/python3.13/site-packages/omlx/patches/mlx_lm_mtp/batch_generator.py'
# Keep infra/tunnel.sh active in another terminal.
python3 accept.py --variant stock --model "$MODEL" --mode both \
 --configure-hook ./set_mtp.sh --out runs/stock/acceptance-01
```

`set_mtp.sh` is the configure hook: it stops only the lab server via the existing
ownership-checking infra helper, backs up the lab's model settings once, changes
only the selected model's `mtp_enabled`, and starts the same checkpoint again.
It rejects competing DFlash/VLM MTP settings. `accept.py` waits for readiness, warms
once outside the measured set, verifies a settings snapshot per mode, then sends
50 requests **serially** at temperature 0, seed 20261125, thinking budget 0 and
`enable_thinking=false`. It captures log additions around each request, failing on
rotation, missing exact telemetry in on mode, counters in off mode, empty visible
answers or nonzero reported reasoning. Keep this endpoint exclusive: UID logs alone cannot distinguish unrelated concurrent traffic.

`prompts.json` freezes exact messages: first 13 fitting LongMemEval manifest IDs
with archived BM25 prompts, first 12 LoCoMo matched IDs with archived RAG evidence,
and 25 authored general prompts. Source paths and content hashes accompany memory
prompts. This is a throughput/acceptance probe, not another accuracy benchmark.
All variants use the identical prompt file; its hash is saved in each manifest.

Both mode runs off then on; repeat with reversed order using separate `--mode on`
and `--mode off` invocations and explicit hooks to control thermal/order effects.
A fresh output directory is required; runs do not silently resume measurements.
Default `max_tokens=384` bounds output. Length stops are retained and counted.
Adaptive depth, context-copy behavior, loop count and other settings are preserved
and saved for audit. Hold them constant across variants; the tool does not silently
force a fixed depth. Cache is disabled by the infra server; verify that setting if
using a different launch path. Warming is not a reset of shared-host contention.

Summary reports the ratio of summed exact DSpark accepted/proposed counts, separate
copy counts, and group summaries for LongMemEval, LoCoMo and general prompts.
Throughput is `sum(completion_tokens)/sum(generation_duration)` when every response
has positive generation duration; otherwise it is null. End-to-end throughput is
`sum(completion_tokens)/sum(client_request_seconds)` and includes prefill/network.
Log capture, hook restarts and warmup are excluded from client request seconds.
Both speeds and off/on speedup are saved. Missing acceptance in off mode is null.
Original upstream evaluated-prefix counts and full request/response/log evidence
remain in per-item records for comparison.

Repeat for `edited` and `edited+lora` with their own checkpoint/model id and
fresh output directory. Do not start another heavy job in parallel.

Restore when all acceptance runs are finished:

```bash
timeout 65 ../../infra/serve.sh "$MODEL_DIR" stop
timeout 20 ssh <mac-studio> \
 '~/inkling-lab/omlx-venv/bin/python ~/inkling-lab/instrument_mtp.py --restore --path ~/inkling-lab/omlx-venv/lib/python3.13/site-packages/omlx/patches/mlx_lm_mtp/batch_generator.py'
# Restore the saved original lab settings (only if no intervening settings changes):
timeout 20 ssh <mac-studio> \
 'cp ~/inkling-lab/omlx-data/model_settings.pre-efficiency.json ~/inkling-lab/omlx-data/model_settings.json'
timeout 30 ../../infra/serve.sh "$MODEL_DIR" start
```

## Offline checks

```bash
cd benchmarks/inkling/research/efficiency
python3 -m unittest discover -s tests -v
bash -n energy_run.sh set_mtp.sh
```

Fixtures: power stream is the actual allowed probe; `response.json` is copied from
`infra/smoke-response.json` (existing stock smoke, not a new benchmark); the upstream
stats block is recorded from the pinned source. `mtp.log` is a **synthetic source-format
replay fixture**, not claimed as live DSpark results. Tests cover units, NUL framing,
interval clipping, baseline variance, negative subtraction, zero denominators,
changed-item/request joins, exact versus evaluated draft counts, weighted throughput,
settings mismatches and full rejected-suffix proposal instrumentation. See
`VALIDATION.md` for the observed test result.

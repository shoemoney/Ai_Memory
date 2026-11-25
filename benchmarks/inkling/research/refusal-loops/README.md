# Refusal direction per loop pass and per pass count (study 1)

Method: difference-of-means refusal direction ([Arditi et al., 2024](https://arxiv.org/abs/2406.11717)),
computed separately at every (layer, loop pass), for the varloop checkpoint run at N = 1, 2, 3, 5 passes and for
Inkling 2 Mini at its native 3. Related prior work, not duplicated here: Goodfire,
[Interpreting Inkling 2 Mini](https://www.goodfire.com/research/interpreting-inkling-2-mini) (information flow
across blocks and loops, logit and tuned lens). This study asks about safety behaviour specifically.

## Research questions

1. **Where is refusal readable?** Separation of harmful (HarmBench) from harmless (`benign_edgy`, the XSTest-derived
   benign group in `refusal/prompts.jsonl`) at the last instruction token, per layer, per pass, per N.
2. **Does the same direction recur on each loop?** Cosine of the train-only direction between passes at the same layer
   (`pass_cosines`), and between pass counts at the same (layer, pass) (`cross_n_cosines`). Does the N=5 pass 3 look like the N=3 pass 3?
3. **Does more looping refuse more or less?** Refusal rate on held-out harmful prompts, and over-refusal on held-out
   benign prompts, with no edit, at N = 1, 2, 3, 5.
4. **Which pass is causally necessary?** Project the direction out of the core layers' outputs at one pass only (inference-time
   activation hook, no weight edit) and measure the refusal rate. Controls: all passes, a pass-1 direction applied at a later pass
   (`p1dir_at_passP`, tests whether the pass-1 direction is the same thing later), and a random unit direction at all passes.
5. **Is Inkling 2 Mini the same as the varloop model at N=3?** Same collection and analysis on Mini.

A separation score is an association. Only the ablation (4) speaks to causality, and it is a small-sample test (below).

## How the pass count is controlled (no fork, no monkeypatch of the PR)

The varloop checkpoint's HF config is `loop_config {core_start: 6, core_end: 18, num_passes: 3, gate_rank: 64, is_varloop: true}`;
Mini carries the same keys with `is_varloop` false. In mlx-lm PR #2086 (`e2b5bbd`, `<checkout>`) the pass count
is read from `args.loop_config["num_passes"]` on every call (`TextModel._run_loop`, `TextModel.layer_visits`, and through it
`Model.make_cache`), so it is a plain runtime knob. `loops.pass_count(model, n)` sets it for the duration of a `with` block and
restores it, including on error. Guard: a checkpoint with `is_varloop` false refuses any N other than its trained count.
Later passes read the previous pass's states through `message_input` and the message gates, so N=5 is a legitimate 5-pass run, not a trick.
The weights are untouched. The per-pass hook (`loops.visit_hook`, `loops.ablate_at_pass`) temporarily wraps `DecoderLayer.__call__`
(same point as `direction/collect.py`) and restores it. Pass numbers restart on every forward (layer 0 resets the counter), so it is
correct across decode steps.

Recorded site: the output hidden state of each decoder visit (post-MLP and post-convolution partial-block residual), at the last
user-instruction content token, exactly as in `direction/collect.py`, which this study imports (`direction` is not edited).
Splits: `collect.prepare_prompts(n=60, seed=42)` gives 36 train, 12 validation, 12 eval per class. Directions are fit on train only,
heatmaps use validation separation, eval separation is stored too, and refusal and ablation generation use the eval prompts only.
Twelve prompts per class is a small sample: read the Wilson intervals and do not over-claim.

Ablation: for each core layer 6-17, the unit direction at (layer, source pass) is projected out of that visit's output hidden state at
every token position, at the target pass only (`--ablate-mode per_layer`; `single` uses the best validation direction everywhere, as in
Arditi et al.). Because shared weights, a weight edit cannot do this; a pass-specific test needs the runtime hook.
Refusal is the heuristic `refusal/score.classify` (regex, user-only prompt, reasoning effort none, greedy, 192 tokens), not a judge.
The heuristic labels are provisional: re-score the saved `gen/*.jsonl` texts with the judge in `refusal/score.py` before publishing.

## Files

| File | Purpose |
| --- | --- |
| `loops.py` | `pass_count`, `visit_hook`, `ablate_at_pass`, `greedy_generate`, `text_config_at`, `trained_passes` |
| `run_study.py` | stages `collect,refusal,ablate,report` (resumable; a finished stage is skipped) |
| `analysis.py` | train-only per-visit directions, separation, cosines (numpy only) |
| `plots.py` | SVGs from the JSON results: `separation-heatmap`, `refusal-vs-passes`, `single-pass-ablation` |
| `tests/` | offline pytest on a tiny random `inkling2_loop` config (16 tests) |

## Offline tests (the workstation)

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OMP_NUM_THREADS=1 \
  <scratch>/venv/bin/python -m pytest -q \
  benchmarks/inkling/research/refusal-loops/tests
```
(a Python venv with mlx-lm, numpy and `pip install matplotlib`.) Result: 16 passed.

## Commands for the Mac Studio (do not run while another model job holds `~/inkling-lab/heavy.lock`)

Copy `benchmarks/inkling/{direction,refusal,research/refusal-loops}` to `~/inkling-lab/` keeping the relative layout
(`loops.py` finds `direction/` two directories up, so put it at `~/inkling-lab/research/refusal-loops/`).

```bash
LAB="$HOME/inkling-lab"; R="$LAB/research/refusal-loops"
source "$LAB/mlxlm-venv/bin/activate"
timeout 20 df -h /                      # need ~26 GB for the varloop model, keep 15 GB free
# varloop weights (~26 GB packed). Skip if present; free Mini's copy first if disk is short.
hf download thinkingmachines/TML-d24-varloop-research --local-dir "$LAB/models/TML-d24-varloop-research"

# 1. varloop at N = 1,2,3,5: collect + refusal + single-pass ablation (N=3 and 5)
python "$R/run_study.py" --model "$LAB/models/TML-d24-varloop-research" \
  --out "$LAB/results/refusal-loops/varloop" --passes 1,2,3,5 --ablate-passes 3,5 \
  --stages collect,refusal,ablate,report

# 2. Inkling 2 Mini, native 3 passes: per-pass collection (add refusal,ablate for the same checks)
python "$R/run_study.py" --model "$LAB/models/Inkling-2-Mini" \
  --out "$LAB/results/refusal-loops/mini" --passes 3 --ablate-passes 3 \
  --stages collect,refusal,ablate,report
```
Run 1 and 2 sequentially (one model in memory at a time). Re-run the same command to resume; to redo a stage delete its `acts-N*.npz` or `gen/` file.
Then copy the `results/refusal-loops/` folders back to the workstation and plot there (`matplotlib` is only needed for this step):

```bash
<scratch>/venv/bin/python plots.py <results>/varloop     # writes <results>/varloop/plots/*.svg
<scratch>/venv/bin/python plots.py <results>/mini
```

## Memory, disk, runtime (estimates, none measured on real weights yet)

- Memory: one model at a time, about 20 to 26 GB of weights (packed, lazy load) plus activations; fits the 96 GB host comfortably. More passes
  add compute and KV cache per visit (N=5 has 72 visits per token versus 48), not weights.
- Disk: varloop download ~26 GB (the Mac Studio has ~51 GB free, so about 25 GB remains: below the 15 GB floor only if Mini plus other models also stay;
  check `df -h /` first). Results: activations `120 x visits x 2304 x 4 B` is 40 MB (N=1) to 80 MB (N=5), under 0.4 GB in total, plus small JSON/JSONL.
- Runtime: collection is one prefill per prompt, 120 prompts per N, minutes each (about 10 to 20 min for all four N). Generation dominates:
  12 prompts x 192 tokens is about 2.3k tokens per condition; at an assumed 10 to 20 tokens/s that is 2 to 4 minutes per condition.
  Conditions: 8 unedited (4 N x 2 classes) + ablation at N=3 (7: pass1-3, two `p1dir`, all, random) and N=5 (11) = 26 conditions, about 1 to 2 hours.
  Mini with all stages adds about 15 conditions-worth of 3-pass work: 30 to 60 min.
- If the varloop model cannot be downloaded or generation is too slow, `--stages collect,report` alone answers questions 1 and 2 in under 30 minutes.

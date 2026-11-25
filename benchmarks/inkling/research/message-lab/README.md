# Study 16: causal content of the inter-pass message

Prepared 2026-11-25, before trained-model intervention results. Implementation and
small random-model checks only; no heavy job was run on macstudio. All study files are
in this directory. The PR checkout and model weights are unchanged.

## Questions registered before the model runs

1. Does a message carry the bridge identity that selects the second-hop answer?
   Swap messages at the changed bridge span in both directions. Positive
   donor-directed margin shift means the recipient moves toward the donor answer.
   The primary endpoint is **held-out template 2, boundary 2→3, layers 12–17:
   swap minus irrelevant-position swap in donor-directed logit-margin shift**,
   averaged across directions within each pair. Varloop is the primary model;
   Mini is a separate replication. Other boundaries, blocks and controls are
   exploratory, with descriptive unadjusted 95% intervals. Never select the best
   discovery cell as the confirmatory endpoint. Freeze code and settings after
   discovery, before opening held-out results.
2. Is message dependence larger for two-hop memory than single-hop recall?
   Compare whole-core, all-position, all-boundary message zeroing with intact
   three-pass and true one-pass execution. Report both tasks separately and the
   paired difference in zeroing damage (two-hop minus single-hop).
3. Can a three-pass message recover the one-to-three-pass gain when injected
   into a single-pass computation? Inject same-prompt messages from either native
   boundary into first-pass gates at the bridge span, separately for each block.
   This adds a gate path absent in native one-pass execution; it is a sufficiency
   intervention, not a native pass-count override alone.

Operational null: a 95% interval wholly inside **±0.1 logits** for the primary
specificity contrast supports no material bridge-specific effect at that site.
An interval spanning both zero and the materiality boundary is inconclusive.
Flip-rate intervals wholly within ±5 percentage points of zero are a secondary
small-effect criterion, not proof that all information flow is absent. No
population claim follows from a degenerate interval with no observed flips.
Zeroing effects near zero require inspection of intact message norms, signed
and absolute gate values, and gated-message norms. Small messages/closed gates
and large but causally redundant messages are different explanations.
An interval including zero for the mean 1→3 margin gap makes a recovery fraction
undefined. Report numerator and denominator rather than a large unstable ratio.
Negative recovery and recovery above one remain visible. An item-level ratio is
also stored (null for |gap|≤1e-6), but the reported estimator is ratio of means.

## Exact intervention site (PR #2086)

Reference `<checkout>`, commit
`e2b5bbd3bd9d186dea895e60802aa765e70b9d93`, package
`mlx_lm.models.inkling2`:

- `model.py:74–104`, `TextModel._run_loop`: all passes restart from `prelude`.
  Passes after the first construct a bank from the preceding pass's completed
  middle-block states and its RMS-normalized partial final block. `bank` contains
  `(block_states[prelude[1].shape[0]+1:], rms(hidden_states))`. This is a depth
  bank at the **same token position**, not a token-attention read.
- `layers.py:584–591`, `MessageInput.__call__`: `_depth_attention(*bank,
  self.query[loop_layer_idx])`. The resulting message is `[batch, tokens, 4,
  hidden_size]`; the four channels feed **q, k, v, mlp**, in that order.
  Learned per-layer/channel query vectors select from the previous-pass bank.
- `layers.py:565–581`, `MessageGate.__call__`: concatenate independently
  RMS-normalized hidden and message vectors, project down to `gate_rank`, then
  compute `forget=tanh(forget_gate_proj(...))` and
  `gain=tanh(message_gate_proj(...))`. The output is
  `(1-forget)*hidden + gain*message`. Both gates are signed and vector-valued;
  neither is a scalar sigmoid. `q_message_gate`, `k_message_gate`,
  `v_message_gate`, and `mlp_message_gate` belong to every core decoder layer.
- `layers.py:615–621` and `layers.py:660–661`: q/k/v mixing and MLP mixing.
  Layer numbers in this study are **zero-based**: blocks 6–11 and 12–17
  correspond to launch-post layers 7–12 and 13–18.

`MessageHook` patches `DecoderLayer.__call__` to edit the message immediately
before it enters the receiving decoder, and `MessageGate.__call__` to record
exact gates. Gate computations call the original implementation for actual
outputs. Every patch is identity-scoped to the supplied model, restored in
`finally`, and serial/non-nestable. No weights, parameters, banks or caches are
edited. Use cache-free prefill only; `assert_touched()` rejects unexpected visit
counts. Counters reset at the prelude's layer 0. Run different pass counts with
the reused `refusal-loops/loops.py:pass_count` context, and construct any caches
inside that context if extending this code to decoding.

API example:

```python
with pass_count(model, 3):
    with MessageHook(model, boundary=2, layers=range(12, 18),
                     positions=bridge_positions) as donor:
        logits = model(mx.array([donor_tokens]))
        mx.eval(logits)
        donor.assert_touched()
    payload = {i: r['message_before'] for i, r in donor.records.items()}
    with MessageHook(model, 2, range(12, 18), bridge_positions,
                     'replace', payload) as recipient:
        logits = model(mx.array([recipient_tokens]))
        mx.eval(logits)
```

Boundary `b` means receiving pass `b+1`. Any native boundary is supported by the
hook (e.g. 4→5 in a five-pass run); the registered runner uses 1→2 and 2→3.
Boundary `-1` targets every native incoming boundary; `0` explicitly injects into
the first pass. `positions=None` targets all positions. Replacement tensors
have shape `[batch, number_of_selected_positions, 4, hidden_size]`. They may come
from another prompt or another total pass count, with matching dimensions.
Random replacement preserves each recipient token/channel's Euclidean norm.
Shuffle permutes selected positions, with one common permutation for all four
channels and batch members; it forces a nonidentity permutation and requires at
least two positions. Neither intervention changes positions outside the selection.
Downstream effects can propagate to later positions/layers/boundaries.

`hook.records[layer]` contains exact selected before/after messages and gate
arrays; `hook.history[(boundary,layer)]` retains every selected native boundary.
The JSON report stores mean/max message norms; signed and absolute mean gate
values; and mean `||gain*message||`, including separate untouched-baseline
captures. During an edited run, a later layer's local before-gate may already see
upstream effects; only `baseline_diagnostics` is a fully intact reference.
Zeroing removes the message vector but **retains** the hidden-state forget path
and recomputes gates on the zero message; this is not equivalent to skipping
MessageGate. Injection preserves native ungated hidden inputs outside its span.

## Dataset and measurement

`pairs300.json` is built with the public Inkling-2-Mini chat tokenizer,
seed 16: 100 pairs per template, 200 discovery pairs and 100 held-out pairs.
Generation took 1,128 alignment attempts. Prompts are 118–131 tokens with the
forced text-channel prefix; bridge spans occupy 2–3 tokens. Each pair changes
one synthetic locker/courier/guide bridge fact; all final item lookup facts and
questions stay fixed. Synthetic person/entity identifiers are randomly composed
syllables. The held-out template uses game avatars and guides. Each member also
has a single-hop recall control asking directly about the fixed left entity;
control answers stay fixed even when the bridge changes.

`pairs.py` verifies equal complete chat-token length, identical bridge token
positions, all token differences confined to that span, and an identical equal-
size spare-entity span for the irrelevant-position control. Prefix/suffix token
agreement includes boundary-merged tokens and works without offset mappings.
The builder rejects violations and single-token bridge spans. It also rejects
answers that are not distinct single-token continuations in the exact scoring
context. The runner re-encodes every unfinished pair and rejects tokenizer
mismatches. To use a tokenizer that differs on varloop, regenerate the dataset
for that model; report it as a separately tokenized dataset, not identical tokens.

**Scoring:** the stock chat template ignores `add_generation_prompt`; `render`
explicitly appends `<|message_model|><|content_text|>`. This forces an immediate
text answer with effort `none`. The score is the post-softcap next-token logit
for the correct item minus that for the paired foil, from the real LM head.
This is a controlled no-generated-CoT, two-alternative assay, not free-generation
memory accuracy. The logs also retain unrestricted argmax token IDs.
A flip is correct recipient margin `>0` becoming donor margin `>0` (recipient
margin `<0`); ties are neither. Report both unconditional and initially-correct
conditional flip rates, plus unrestricted argmax transitions to the donor.

## Run plan on the Mac Studio

No the Mac Studio access or heavy model job is performed by this implementation. First
schedule exclusive lab GPU time. Confirm both model directories are already
provisioned and the lab server is stopped by its owner; never touch the shared
Homebrew oMLX service. Missing models require a separate coordinated download
with root disk space checked and at least 15 GB left afterward.

From the workstation, sync these completed sources and their reused sibling dependency:

```bash
cd benchmarks/inkling/research
timeout 60 ssh <mac-studio> 'mkdir -p ~/inkling-lab/research/message-lab ~/inkling-lab/research/refusal-loops; df -h /'
timeout 120 rsync -a --exclude='__pycache__' --exclude='.pytest_cache' --exclude='runs' message-lab/ <lan-address>:inkling-lab/research/message-lab/
timeout 60 scp refusal-loops/loops.py <lan-address>:inkling-lab/research/refusal-loops/loops.py
```

Run a three-pair pilot (two discovery pairs and one held-out pair exist in the
file, but use only discovery for pilot tuning). This command is ready to run
once the local varloop directory exists; it does not download anything:

```bash
timeout 7200 ssh <mac-studio> 'bash -s' <<'REMOTE'
set -euo pipefail
lab="$HOME/inkling-lab"
test -f "$lab/models/TML-d24-varloop-research/config.json"
test ! -f "$lab/server.pid"
mkdir "$lab/heavy.lock"
trap 'rmdir "$lab/heavy.lock"' EXIT
cd "$lab/research/message-lab"
/usr/bin/time -l "$lab/mlxlm-venv/bin/python" run_message.py \
  --model "$lab/models/TML-d24-varloop-research" --pairs pairs300.json \
  --split discovery --limit 3 --out runs/varloop-pilot
REMOTE
```

Repeat that lock-protected command with `--limit` omitted and
`--out runs/varloop-discovery`. Freeze the discovery interpretation, then run
`--split heldout --out runs/varloop-heldout`. Repeat for
`--model "$lab/models/Inkling-2-Mini"` with **`--allow-untrained`** and distinct
`runs/mini-discovery`, `runs/mini-heldout` directories. Mini was trained at three
passes, so its one-pass comparisons are explicitly out-of-training ablations;
varloop is the cleaner pass-count comparison. For a long coordinated run,
increase the outer timeout based on the pilot estimate. A timeout is not a
reason to remove another process's lock; establish process ownership first.

If tokenizer verification fails, rebuild only this study's data file:

```bash
~/inkling-lab/mlxlm-venv/bin/python pairs.py \
  --model ~/inkling-lab/models/TML-d24-varloop-research --out pairs-varloop.json
```

Use that file consistently with new output directories. Resumption is by
complete JSON rows, fsynced after each intervention. A partial final append is
truncated on resume; interior corruption is an error. Fully completed pairs do
no model work. Interrupted pairs recompute needed donor captures/intact baselines
but never duplicate result rows. `manifest.json` binds source hashes, dataset,
model path/config/weight file metadata, planned pair IDs, and options. This is
one serial writer per output directory. Weight file metadata is provenance, not
a cryptographic weight checksum; retain the checkpoint's verified source hash.

Analyze after both splits finish (same model/data/source version only):

```bash
~/inkling-lab/mlxlm-venv/bin/python analysis.py \
  runs/varloop-discovery/results.jsonl runs/varloop-heldout/results.jsonl \
  --out runs/varloop-report
~/inkling-lab/mlxlm-venv/bin/python plots.py \
  runs/varloop-report/analysis.json --out runs/varloop-report
```

Analysis rejects incomplete matrices and duplicate keys. It resamples **pairs**,
keeping both directions together (4,000 percentile-bootstrap replicates, seed
16), and writes `analysis.json`, `controls.md`, and `swap.svg`, `zero.svg`,
`injection.svg`. Single-hop controls retain the same paired logs; they are not
additional independent observations. Install matplotlib in the designated lab
venv if absent, before its scheduled model run.

## Work and memory budget

With both boundaries: **60 JSON records and 76 forwards per pair**, including
intact baselines, donor captures, sham/irrelevant/random/shuffled swaps, zeroing
and injection. Full two-model work is 45,600 short cache-free prefills; no
sampling or decode loop. Per-model discovery is 15,200 forwards, held-out 7,600.
The pilot's three pairs take 228 forwards. Divide its measured time by 228 and
multiply by the planned forward count, with a margin for cold load/resume.
For planning only, 1–10 seconds per hooked forward implies **6–63 hours per
model**. Hook synchronization/capture can be expensive; no M3 Ultra runtime has
been measured for this study, so this range is not a throughput result.

Keep one model resident. Native checkpoints are about 20 GB; budget 32–45 GB
unified memory including runtime buffers and short-prefill activations, verify
with `/usr/bin/time -l` in the pilot, and stop for unexpected memory pressure.
Selected bridge payloads are under 1 MB for six 2–3-token layer messages; whole-
core diagnostic arrays are larger but bounded at these context lengths. No KV
caches are retained. JSON stores summaries, not full hidden vectors. Source
model formats/conversions may change these memory estimates substantially.

## Offline validation on the workstation

Final check: **18 passed**; all 300 paired prompts and 600 single-hop variants
were re-encoded with the locally cached official tokenizer. Evidence is in
`validation.json`. No trained-model results are included.

```bash
PYTHONPATH=<checkout> \
  <scratch>/bin/python -m pytest -q \
  benchmarks/inkling/research/message-lab/tests
```

The environment uses MLX CPU 0.32.4, the reference PR, NumPy, pytest,
transformers 5.24.1, and matplotlib. Tests use the existing
`direction/tests/tiny_config.json`: 24 layers, hidden size 8, two experts, five
input tokens. They prove intervention scoping, exact capture/sham identity,
position preservation, norm matching, nonidentity shuffle, actual donor tensor
replacement, planted-signal effects, first-pass injection, all-boundary zeroing,
restoration on exceptions, pass-count restoration, paired alignment, bootstrap
clustering, JSON resume, scheduler coverage and SVG rendering. They do not prove
that trained messages carry task information, or that native quantized Metal
execution has passed. The scheduler test uses a fake forward to inspect all 60
conditions; causal hook tests use the actual tiny MLX model.

## Related work and scope of claims

[Thinking Machines' launch post](https://thinkingmachines.ai/news/inkling-2-mini/)
describes the prelude restart, previous-pass message and gates initialized closed
during training. The PR's random-model constructors do not themselves guarantee
closed gates: random-config tests must not assume trained gate statistics.
[The varloop card](https://thinkingmachines.ai/model-card/tml-d24-varloop-research/)
describes training with one through five passes. [Goodfire's study](https://www.goodfire.com/research/interpreting-inkling-2-mini)
examines information flow and decoding across blocks/loops; this protocol targets
interventions on the message path. A claim of being the first published causal
message patching study would require a broader literature audit before publication.

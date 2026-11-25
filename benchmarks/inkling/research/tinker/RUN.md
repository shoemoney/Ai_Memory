# Study 5: exact Tinker run

Prepared locally on `recipe-agent-memory` in `$COOKBOOK_DIR`. Authenticated access and the $40 dry run were verified on 2026-11-25; see LEDGER.md for execution. Do not print the key, enable shell tracing, push code, or submit a PR as part of this run plan.

The existing audited curriculum is the intended training input. No data regeneration is necessary on the workstation. For an external reproduction, use `recipes/agent_memory/README.md`'s pinned download and preparer; all three generated split files were verified byte-for-byte against `lora/data/clean`.

```bash
cd $COOKBOOK_DIR
# Standard setup; upstream universal uv resolution currently has an optional-extra conflict.
uv sync --extra dev
# If that fails with the observed s3fs/litellm conflict, install only requested extras:
uv pip install --python .venv/bin/python -e '.[dev]' pre-commit
.venv/bin/python -m tinker_cookbook.recipes.agent_memory.train \
  data_path=$CURRICULUM_DATA_DIR \
  dry_run=True
```

Exact main run (W&B omitted; key is held only in the environment):

```bash
cd $COOKBOOK_DIR
TINKER_API_KEY="your-tinker-api-key" .venv/bin/python -m tinker_cookbook.recipes.agent_memory.train \
  data_path=$CURRICULUM_DATA_DIR \
  model_name=thinkingmachines/Inkling-2-Mini \
  batch_size=32 num_epochs=1 lora_rank=32 effort=0.0 \
  max_length=8192 max_tokens=512 eval_every=50 save_every=50 \
  seed=0 budget_usd=40 \
  log_path=$STUDY_DIR/runs/main
```

`learning_rate` is deliberately omitted to resolve through the cookbook model-specific helper; current value 0.00054. This is a starting point, not a tuned claim. Before a main result, sweep e.g. learning_rate=0.00027/0.00054/0.00108 using unique run names and log directories, preserving batch, epoch budget, optimizer and effort. Select on validation only. Each is a full run with the reservation in COST.md; keep a cumulative ledger below $300. Reusing the exact main output path is not a supported resume operation: choose a new path and record a fresh run instead.

Watch `metrics.jsonl`: train NLL, `valid/memory/exact_match`, per-skill scores, `reader_check/exact_match`, parse-clean rate, token counts, training cost, elapsed time. The inherited `test/nll` and `test/bpb` keys describe validation only. Evaluate initial/final with the same effort and token cap. Every evaluator writes HTML and JSONL transcripts. Training costs and evaluator sampling estimates are separate; the Tinker console is the bill. The final evaluator appends metrics at completed update 169 and writes `final_memory_metrics.json` with its sampler checkpoint.

This is hosted CPU orchestration, not a local workspace build or local model run. Do not launch concurrent workspace builds on the workstation. No the workstation service is needed. No synthetic result is to be reported as LongMemEval or LoCoMo accuracy.

The executed command is launched using `systemd-run --user --unit=inkling-tinker-main --setenv=TINKER_API_KEY --setenv=PYTHONUNBUFFERED=1 --working-directory=$COOKBOOK_DIR`, followed by the absolute venv Python and the arguments above. Export the key in the invoking shell and unset it afterward; `--setenv=TINKER_API_KEY` imports its value without putting the key in the command line. No secret file is used. Poll no more often than once every five minutes.

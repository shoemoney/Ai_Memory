# Prepared run, not launched

Code: a cookbook checkout (`<cookbook-checkout>`), local branch `recipe-trained-tools`, branched from main. No access to private hosts, paid model calls, push or PR occurred at this stage.

Default verified data: `~/tinker-runs/trained_tools/data`, 4,000/400/400 rows. The entire corpus was rendered locally without truncation. See preflight.json, data-manifest.json and prompt-tokens.json. Full focused tests: pytest.log (22 passed); pyright.log (0 errors); pre-commit.log (all hooks passed including trufflehog). Checks were scoped to the new recipe and its recipes index link. No workspace-wide build or full suite was run.

Later launch, after reviewing PREREG.md/COST.md and authenticating Tinker and W&B:

```bash
cd <cookbook-checkout>
PYTHONPATH=. .venv/bin/python -m tinker_cookbook.recipes.trained_tools.train \
  data_path="$HOME/tinker-runs/trained_tools/data" \
  batch_size=32 num_epochs=1 lora_rank=32 effort=0.0 \
  eval_every=50 save_every=50 max_length=4096 max_tokens=512 \
  seed=0 budget_usd=30 \
  wandb_project=trained-tools wandb_name=mini-r32-e0
```

Set TINKER_API_KEY in the environment; never print it or put its value in a command argument. The default hosted run performs training plus final three-arm evaluation; do not accidentally run the standalone evaluator as well unless intentionally paying for a repeat. Default logs are under `~/tinker-runs/trained_tools/` with a timestamped run name. Pick a fresh log_path/name for each run; no resume is implemented. Before a launch, rerun dry_run=True with the exact intended settings and inspect current service pricing. No account-wide spending cap is implied.

Final outputs: final_tools_metrics.json contains the saved sampler checkpoint and all per-arm metrics. Each evaluator creates full JSONL trace files named by split, arm and unique invocation. Use exactly the final test file for each arm, not periodic validation files, for analysis:

```bash
PYTHONPATH=. .venv/bin/python -m tinker_cookbook.recipes.trained_tools.analyze A.jsonl B.jsonl C.jsonl
```

No model results are available yet. The standalone evaluator can compare a saved trained sampler later, but incurs additional sampling charges. Token-count scripts and tests use no service calls. TTFT stays null in traces because this API does not report it. Capture the service bill and actual checkpoint retention separately from estimates.

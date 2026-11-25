# Local validation, 2026-11-25

No Tinker API calls or paid training run. Code and offline checks ran on the workstation; no workspace-wide build or full test suite was launched. Cookbook clone is `$COOKBOOK_DIR`, branch `recipe-agent-memory`, based on upstream `8bf7dd6192a3f1fa64640a04ec54a7f6866bbd83`. Local implementation commit: `5ec13af3fe5c27585da65d13115cf98973373d6a`. Cookbook working tree is clean; nothing was pushed. 

- `pytest -q tinker_cookbook/recipes/agent_memory`: **18 passed** in 1.96 seconds. Real Inkling 2 renderer/tokenizer; fake sampler; checks all six skills, both lookup forms, per-example prompt masking, target shifting, tool declarations, roundtrip call parsing, refusal to truncate, group overlap rejection, partial batches, seed ordering, CLI forwarding, invalid configs, budget rejection, concurrent evaluation, and malformed-termination penalty. Pytest prints an existing unset asyncio fixture-loop default deprecation warning.
- `pyright --pythonpath .venv/bin/python tinker_cookbook/recipes/agent_memory`: **0 errors, 0 warnings**.
- `ruff check` and `ruff format --check` on the recipe: **passed**.
- `pre-commit run --all-files`: **passed**, including added-file size check, end-of-file check, trailing whitespace, pinned ruff hooks and pinned trufflehog secret scan. Initial executions normalized trailing whitespace/newlines in the copied source card and license; the final staged files pass.
- Full 6,000-row real-renderer preflight: 5,400/300/300 rows, 5,400/300/300 unique prompts, zero pairwise persona-group or exact-prompt overlap, no truncation, 169 updates per epoch. See preflight.json.
- Pinned public source downloaded and verified SHA-256 `ac81a4db067ae15e9cfb82d32844d7941d7f12bff77e8b6482d40892f3c6614f`. New `prepare.py` output was byte-identical to every audited clean JSONL:
  - train: `f64d13501c29165022126307839c20df2da6d0a645def1eec52debb13f6dec36`
  - validation: `81e14d78853e71e9de900af78652040573118fe89da30a953e12cf0d0c6cbd51`
  - test: `5364591303e05062e4c8a072a6e35878283208bdffca96f71556b5c127f55eaf`

Development environment: Python 3.13.18, Tinker 0.40.0, tml-renderers 0.4.2, torch 2.15.0+cpu, chz 0.4.0, pytest 9.2.0, local ruff 0.17.5, pyright 1.1.414. Pre-commit independently uses the repository's pinned ruff v0.13.2. `uv sync --extra dev --extra wandb` hit a universal-resolution optional-extra conflict between s3fs/aiobotocore and litellm/boto3. Installed the requested extras directly with `uv pip install -e '.[dev,wandb]' pre-commit` plus the CPU torch index; no dependency or lockfile change was committed.

Additional broad static check: `pyright ... tinker_cookbook` reported **94 errors outside agent_memory** in this environment, including missing optional extras (inspect_ai, verifiers, modal, litellm, neptune_scale, trackio) and other existing modules. This is **not** a whole-project type-check pass; its log is retained as pyright-all.log. The new recipe's separate check is clean. Full repository pytest and paid smoke tests were not run. CI with the upstream environment and the eventual authenticated Tinker run are still required before claiming end-to-end training validation.

Nothing was pushed and no pull request or upstream comment was made. The public recipe contains no private research paths.

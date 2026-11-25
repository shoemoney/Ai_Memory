# Upstream contribution reconnaissance

Checked 2026-11-25 against cookbook main `8bf7dd6192a3f1fa64640a04ec54a7f6866bbd83`. Read AGENTS.md, CONTRIBUTING.md, skills/inkling/SKILL.md, skills/research/SKILL.md, hyperparameter guidance, recipes README, chat_sl, forecasting and search_tool recipe source/README, shared SL loop/data helpers, renderer and evaluator implementation.

`gh pr list --state merged --search recipe` identified these recent outside-contributor recipe changes. GitHub API `author_association=CONTRIBUTOR` was checked for all three, and complete diffs/body were read:

- [#955, EvilSwordman, merged 2026-09-24](https://github.com/thinking-machines-lab/tinker-cookbook/pull/955): recipe CLI config must actually forward save cadence. Our test covers forwarding.
- [#840, RupeshKeesaram, merged 2026-07-24](https://github.com/thinking-machines-lab/tinker-cookbook/pull/840): examples and reward scoring must agree, including normalized exact answer matching.
- [#803, confiscate, merged 2026-07-11](https://github.com/thinking-machines-lab/tinker-cookbook/pull/803): blank line before README tables matters to MkDocs.

For a complete outside-contributor recipe addition, also read [#276, josancamon19, merged 2026-02-23](https://github.com/thinking-machines-lab/tinker-cookbook/pull/276), including train/eval/env and README diff. Its old IFBench-on-test recipe is historical structure evidence, not a reason to train on benchmark test sets. Current source conventions supersede old PR APIs. #918 forecasting was inspected for layout; author association MEMBER, so it is not counted as outside-contributor evidence.

Layout: tinker_cookbook/recipes/agent_memory/{README.md,prepare.py,data.py,eval.py,train.py,data_test.py,__init__.py,ATTRIBUTION.md,SOURCE-CARD.md,LICENSE-CC-BY-4.0.txt,audit/decontam-report.json}. Recipes README gets a link. CLI configuration is `@chz.chz`, full trainer configuration is a separate `train.Config`, builders are serializable, entrypoint is `python -m ...`, local offline tests colocated `*_test.py`. Default logs go to `cli_utils.runs_path`. Renderer is selected through `model_info`, effort is explicit on both paths, data use shared datum shifting and per-example mean weights. Evaluation implements SamplingClientEvaluator and records complete transcripts with logtree plus JSONL. There are no new dependencies or separate training loop.

PR requirements: branch from main; clear problem/change/test description; pre-commit run --all-files; CI runs pre-commit, pyright and pytest. Line length 100. Pre-commit also includes a pinned trufflehog secret scanner and 500 KB added-file limit, so generated data are not committed. Keep private context and internal paths out of the public recipe; private run notes stay in the book project. No DCO/CLA, attribution-trailer or special PR template requirement was found in the read contribution rules. No PR or push is authorized here.

AGENTS says training launches should configure W&B, log splits/config and cost, evaluate initial/periodic/final, and capture all rollouts. The recipe and RUN.md provide these. No real API smoke test can be claimed before a key exists; a future PR should clearly label training results as pending until that run is done.

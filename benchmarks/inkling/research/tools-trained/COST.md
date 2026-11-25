# Dry-run cost estimate

Measured 2026-11-25, no paid training or model evaluation started. Raw output: [preflight.json](preflight.json), [prompt-tokens.json](prompt-tokens.json), and [data-manifest.json](data-manifest.json). These are local measurements, not a service bill.

The live [model pricing table](https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/) checked 2026-11-25 lists the selected `thinkingmachines/Inkling-2-Mini` at $0.75/M training tokens, $0.15/M uncached prefill, and $0.50/M generated tokens. No cache discount is assumed. The higher-context variant is not used. The existing authenticated capabilities snapshot in `../tinker/capabilities.json` confirms trainable/sampleable availability for this model; this work performs no account mutation or model sampling. A free variant appears in current public pricing but this registered estimate and model identifier use the paid variant consistently.

| Split | Conversations | Shifted training input tokens |
| --- | ---: | ---: |
| Train | 4,000 | 461,169 |
| Validation | 400 | 47,092 |
| Test | 400 | 49,458 |

One complete epoch, batch 32, means 125 updates. Helper LR 0.00054. Training alone: **$0.345877**. Initial/periodic A validation occurs at completed updates 0, 50 and 100; final A validation and full three-arm test occur after update 125. Validation NLL is conservatively reserved at $1.25/M complete-sequence tokens. All evaluation sampling is bounded at four turns of 4096 input + 512 output tokens per episode. This is deliberately higher than expected short fake-tool trajectories.

Evaluation upper bound: **$9.925075**. Total compute upper estimate: **$10.270952**. Gate reservation, twice compute plus $5 checkpoint storage allowance: **$25.541904**, under the default $30 preflight budget. Storage is an allowance, not a promise that retaining checkpoints indefinitely costs $5; clean up retained checkpoints after the run. This is not an account-wide spending cap. Changed data, epochs, eval cadence or token settings require another dry run. Real endpoint charges, LR sweeps and later reruns are excluded.

The stock request is `Find a web page about cobalt gardens.`. Exact rendered first-turn tokens, including roles, effort, user text and generation prefix: **A 45 / B 2,799 / C 192**. A/B = 1.6077%, a 98.3923% reduction on this one prompt. This is a prompt-size finding only. See the per-request token arrays and means in prompt-tokens.json; actual multi-turn totals will come from paid evaluation traces. Tokenizer/renderer package version: 0.4.2.

Reproduce from a checkout of the `recipe-trained-tools` branch:

```bash
PYTHONPATH=. .venv/bin/python -m tinker_cookbook.recipes.trained_tools.prepare --output "$HOME/tinker-runs/trained_tools/data"
PYTHONPATH=. .venv/bin/python -m tinker_cookbook.recipes.trained_tools.train data_path="$HOME/tinker-runs/trained_tools/data" dry_run=True
PYTHONPATH=. .venv/bin/python -m tinker_cookbook.recipes.trained_tools.token_report "$HOME/tinker-runs/trained_tools/data"
```

The worktree reuses the original cookbook `.venv` by symlink. Always use `PYTHONPATH=.` or `python -m pytest` from this worktree so the editable installation does not resolve imports to the memory branch.

## Completed main test and post hoc amendment (2026-11-25)

The earlier dry-run section above records the preparation state, not the current run status. The paid main run completed; its frozen metrics are in [runs/main/final_tools_metrics.json](runs/main/final_tools_metrics.json). The main test evaluation used 2,603,739 prompt and 184,729 completion tokens: **$0.48292535** at uncached list prices. This total covers the three test arms only, excluding original training, validation and checkpoint storage.

The post hoc four-arm evaluation was authorized up to $10 and launched once as `inkling-tinker-tools-v2.service`. Its offline [preflight](runs/v2/preflight.json) reserved **$5.57056**, the ceiling for 1,600 episodes × four turns × (4,096 prompt tokens × $0.15/M + 512 completion tokens × $0.50/M). No cache discount is assumed. The twice-compute cushion used in the original training launcher is not needed to bound this standalone evaluator's actual token ceiling. No new training, retries of the full run or checkpoint selection occurred.

| Amended arm | Actual prompt tokens | Actual completion tokens | Turns | Uncached list-price sampling cost |
| --- | ---: | ---: | ---: | ---: |
| A | 82,990 | 19,978 | 779 | $0.02243750 |
| B | 2,318,037 | 83,030 | 799 | $0.38922055 |
| C | 439,329 | 99,507 | 815 | $0.11565285 |
| C0 | 232,227 | 96,058 | 724 | $0.08286305 |
| Total | 3,072,583 | 298,573 | 3,117 | **$0.61017395** |

These costs use observed token counts, not the maximum reservation. Rates were verified against the [published model pricing table](https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/) on 2026-11-25. Cash billing, any cache discounts and existing checkpoint-storage charges are unavailable; the list-price sum is not a provider invoice. The original main plus amended test evaluation totals **$1.09309930** on the same basis. Complete amended traces, token counts, configuration and paired analysis are in [runs/v2](runs/v2/); [RESULTS.md](RESULTS.md) defines every outcome and denominator.

## v3 evaluation (2026-11-25, AMENDMENT-2 and its addendum)

Two sampling runs, both within the $5 budget set for them. Dry runs first: [runs/v3/preflight.json](runs/v3/preflight.json) bounded the first run at **$3.71** (every episode to four turns, 512 completion tokens each, prompts growing by 500 tokens per turn, rates from the cookbook's `fetch_model_pricing`: $0.15/M uncached prefill, $0.50/M sampled) with an expected cost of about $0.81; [runs/v3b/preflight.json](runs/v3b/preflight.json) bounded the follow-up at $1.01. Actual tokens, at the same uncached list prices and with no cache discount:

| Run | Arm | Test | Prompt tokens | Completion tokens | List-price cost |
| --- | --- | --- | ---: | ---: | ---: |
| v3 | A | in-template | 82,866 | 19,934 | $0.0224 |
| v3 | B-native | in-template | 818,573 | 94,863 | $0.1702 |
| v3 | B-lean | in-template | 1,582,319 | 83,270 | $0.2790 |
| v3 | C | in-template | 444,894 | 103,527 | $0.1185 |
| v3 | A | out-of-template | 18,682 | 5,275 | $0.0054 |
| v3 | B-native | out-of-template | 192,993 | 20,000 | $0.0389 |
| v3 | C | out-of-template | 92,081 | 20,157 | $0.0239 |
| v3b | B-native-1call | in-template | 888,641 | 101,182 | $0.1839 |
| v3b | B-native-1call | out-of-template | 200,016 | 21,435 | $0.0407 |

v3 total **$0.6583**, follow-up **$0.2246**, together **$0.8830**. These are token-accounted list prices, not a provider invoice; cash billing and checkpoint storage are unavailable. No training occurred, the adapter is the unchanged `runs/main` checkpoint, and the earlier runs' spend above is unchanged. All evaluation spend to date (main, v2, v3, v3b) is **$1.9760** at list prices.

## Adapter v2 round (2026-11-25, AMENDMENT-3)

Budget $6; total spend about **$1.54** at list prices. Answer sampling for the v2 data: **$0.29** over six invocations (the first, $0.111, was discarded when the generator changed; then $0.133, about $0.01, $0.006, $0.013 and $0.017; 3,069 requests sampled in all, 1,764 answers kept in the final files). Training A2: **$0.343** (457,182 trained tokens at $0.75/M, the cookbook's own estimate, one pass, 125 updates), plus **$0.087** for the three periodic closed-loop validations (160,008 prompt and 125,710 completion tokens). Evaluation, four arms on four test sets (4,080 episodes): **$0.820**, against a dry-run ceiling of $6.92 and an expected $1.10 ([runs/v4/preflight.json](runs/v4/preflight.json)); the runner gated on twice the expected cost against the budget.

| Test | Arm | Prompt tokens | Completion tokens | List-price cost |
| --- | --- | ---: | ---: | ---: |
| v1-template | A | 82,736 | 19,888 | $0.0224 |
| v1-template | A2 | 89,771 | 22,079 | $0.0245 |
| v1-template | B-native-1call | 894,706 | 98,558 | $0.1835 |
| v1-template | C | 440,555 | 103,858 | $0.1180 |
| v2-template | A | 66,359 | 20,759 | $0.0203 |
| v2-template | A2 | 66,531 | 19,930 | $0.0199 |
| v2-template | B-native-1call | 771,371 | 90,890 | $0.1612 |
| v2-template | C | 349,085 | 87,055 | $0.0959 |
| OOT-1 | A / A2 / B-native-1call / C | 18,357 / 17,077 / 207,959 / 91,889 | 5,107 / 4,865 / 21,698 / 20,250 | $0.0053 / $0.0050 / $0.0420 / $0.0239 |
| OOT-2 | A / A2 / B-native-1call / C | 23,294 / 20,926 / 261,319 / 109,248 | 7,620 / 6,790 / 29,444 / 28,539 | $0.0073 / $0.0065 / $0.0539 / $0.0307 |

Token-accounted list prices, not a provider invoice; checkpoint storage is unavailable. The earlier rounds' spend above is unchanged; all research spend to date is about **$3.52** at list prices ($1.976 before this round).

## Shipped recipe, live end-to-end runs (2026-11-25)

Budget $4; about **$2.35** at list prices over three attempts. The **final run** cost **$0.946**: answer sampling $0.147 (printed by the recipe), training $0.343 (456,649 trained tokens at $0.75/M) plus $0.087 for three periodic closed-loop validations, evaluation $0.369 (generated test: adapter $0.020, native $0.159, sheet $0.102; blind test: $0.007, $0.053, $0.029). The **first run**, with the code before three fixes, cost about $0.94 (answers estimated at the same $0.147; its evaluation was $0.361). A **second attempt** died at step 107 when the account's checkpoint storage filled; it cost about $0.47 (answers $0.147, training to step 100 and its validations, estimated). The dry run bounded the answers at $0.576. Checkpoints from the first and second runs were deleted from the account to free storage; the adapter from the final run is still there. List prices, not an invoice. All research spend to date is about **$5.9** ($3.52 before this section).

## Pre-submission review round (2026-11-25)

Budget $3 for sampling; about **$0.35** at list prices, in four evaluation runs and no training: the sheet arm on the first and final runs' generated-test requests ($0.090 and $0.087), and all three arms on blind v1.1 twice ($0.090 and $0.087; first sampling: adapter $0.0065, native $0.0557, sheet $0.0275; second: $0.0065, $0.0536, $0.0264). The adapter and native generated-test numbers are the saved traces rescored offline, no new sampling. Token-accounted list prices, not an invoice; the adapter checkpoint from the final run was reused and is still on the account. All research spend to date is about **$6.25** ($5.9 before this section).


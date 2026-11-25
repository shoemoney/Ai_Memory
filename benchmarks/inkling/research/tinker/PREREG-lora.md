# Preregistration: LoRA Without Regret on a looped MoE

Registered 2026-11-25, after the main pilot and its RESULTS.md were completed and before any grid cell was launched. Pilot results (including validation ceiling and reader exact-match wording sensitivity) were known; no follow-up outcomes were available. The file's SHA-256 is recorded in LEDGER.md at launch.

## Claim and supported API

Primary source: [LoRA Without Regret](https://thinkingmachines.ai/blog/lora/), especially its target-layer comparison and rank discussion. We test the target-layer/rank implication on one memory curriculum. We cannot test equivalence to full fine-tuning: Tinker exposes LoRA, and there is no FullFT arm here.

Checked live [ServiceClient docs](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/serviceclient/), [LoRA primer](https://tinker-docs.thinkingmachines.ai/tinker/lora-primer/) and installed SDK source `tinker/lib/public_interfaces/service_client.py` plus `types/lora_config.py`. `create_lora_training_client` accepts integer `rank`, initialization `seed`, `train_attn`, `train_mlp` and `train_unembed`. SDK documentation explicitly includes MoE layers under `train_mlp`. All three target booleans default true. Arbitrary per-layer lists are not exposed by this method. Requested ranks 4/32/128 will be checked by actual server creation; a server rejection is a failed cell, not an assumed supported run.

## Frozen grid

All cells use dataset-order seed 0 and adapter-initialization seed 0. Unembedding is disabled in every cell to isolate attention versus MLP/MoE within transformer blocks; "all-layers" below means all attention and MLP/MoE block layers, not the output head. This controls an otherwise confounding head-target difference. The main pilot used the default head target and unspecified initialization seed, so it is not reused as a seeded grid cell.

| Cell / unique log suffix | Rank | train_attn | train_mlp | train_unembed |
| --- | ---: | --- | --- | --- |
| attn-r32-s0 | 32 | true | false | false |
| mlp-r32-s0 | 32 | false | true | false |
| all-r4-s0 | 4 | true | true | false |
| all-r32-s0 | 32 | true | true | false |
| all-r128-s0 | 128 | true | true | false |

Exactly one seed per cell. Two seeds would require ten new full runs; conservative compute alone, plus the already completed pilot, exceeds the $90 task cap. We will not select only favorable cells for second seeds.

## Matched protocol and metrics

Model `thinkingmachines/Inkling-2-Mini`, fixed three loop passes on Tinker. Fresh post-trained base and fresh AdamW per run. Identical audited JSONL data: 5400 train, 300 valid, 300 test; zero persona/prompt overlap. Batch 32, one epoch, all 169 updates including the partial batch; LR from `hyperparam_utils.get_lr(model_name)` = 0.00054 for every rank and target choice, linear decay, Adam betas 0.9/0.95, epsilon 1e-8. No LR selection after seeing outcomes. Effort 0.0 in training and sampling; temperature 1; output cap 512; max length 8192; eval/save every 50; submit-ahead 0; no W&B. All rollouts get JSONL/HTML transcripts.

Primary: final (169-update) validation memory exact match, full 300 rows. Guardrails: final reader-check exact match (12 fixed probes) and validation parse-clean. Secondary: six validation per-skill exact matches; initial/50/100/150/final validation NLL; final test exact match; training NLL; token counts, elapsed time and cost. The final likelihood pass is now included in the recipe and its preflight reservation for every cell. Fixed scorer and prompts remain unchanged, including the known strict rejection of a redundant "Room" prefix.

Operational definition of **attention-only is enough**: at the fixed final endpoint, attention-only rank 32 is within 2 percentage points of all-layers rank 32 in validation exact match, within 1 of 12 reader answers (8.333 percentage points), and within 1 percentage point in validation parse-clean. All three conditions must hold. This is a descriptive tolerance, not a powered noninferiority test. If the threshold fails, report the differences and errors; do not infer universality. MLP-only and rank comparisons are descriptive. NLL remains a continuous secondary metric, especially if answer accuracy saturates.

## Budget and execution

Hard total cap $90 from the existing $100 balance, no added funds. Per-cell launcher budget_usd=40 is a conservative single-invocation gate, not permission for five $40 bills. Updated grid preflight compute allowance is approximately $10.744245 per run; five new cells plus the pilot and its final NLL fit below $64.47 in conservative compute allowances. Reserve $10 total storage and $10 further safety margin: under $84.47, leaving at least $5.53 below the task cap. Unused periodic checkpoints can be deleted after selected reproducibility artifacts are retained; final checkpoints have no TTL by default.

Each cell runs as its own `systemd --user` unit, key imported from the shell via `--setenv=TINKER_API_KEY` without a value on the command line. Unique log directories: `research/tinker/runs/lora-<cell>`. Launch all five hosted cells; local processes only render/log. Poll no more frequently than every five minutes. Do not change code/config while cells run. Every launch, failure, actual cost response and outcome goes in LEDGER.md. Billing can lag: never label an empty response as zero cost. Reconcile provider usage when available and retain estimates separately. No automatic training retries; any justified retry needs a new path and must fit the remaining cumulative allowance.

## Limits

One templated task, 300 linked-per-persona validation rows, twelve reader questions, one seed, no independent benchmark and no FullFT control. Same rank does not match trainable parameter counts across targets. Output-head LoRA is deliberately excluded from all grid cells. Same initialization seed does not guarantee identical draws across different tensor shapes or deterministic sampling. This is not an exact reproduction of the paper's LR-swept SFT experiments.

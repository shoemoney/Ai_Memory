# Tinker recipe cost plan

Checked live 2026-11-25. Authenticated SDK capabilities confirm `thinkingmachines/Inkling-2-Mini` is trainable and sampleable (reported sampling context 1,048,576). No paid run had started at this preflight. Full capabilities are saved in `capabilities.json`.

## Model and prices

Use `thinkingmachines/Inkling-2-Mini` (64K training context, up to 1M sampling context), not the higher-priced `thinkingmachines/Inkling-2-Mini:peft:262144` training variant. The recipe needs at most 8,192 tokens per example. Account availability was verified with `tinker.RestClient().get_server_capabilities().result().supported_models` once a key exists.

[Models & pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/) lists, per million tokens: $0.75 training, $0.15 prefill ($0.015 cached), $0.50 sampling. The 256K training variant costs $1.50/M training. Budget calculations ignore cache savings. Checkpoint storage is $0.10/GB/month, per [Tinker pricing](https://thinkingmachines.ai/tinker/pricing/); storage continues after compute completes.

[Tinker's LoRA primer](https://tinker-docs.thinkingmachines.ai/tinker/lora-primer/) supports SFT adapters, with rank 32 as its usual starting point. This recipe uses all default adapter targets, AdamW, linear LR decay, and `hyperparam_utils.get_lr` (currently 0.00054) as an untuned starting scale. [Using Inkling](https://tinker-docs.thinkingmachines.ai/cookbook/inkling/) and the repository's `skills/inkling` require model-specific tokenization and explicit matched effort. Effort 0.0 fits this short-answer curriculum; it is conditioning, not a guarantee of zero reasoning.

## Measured input and conservative reservation

Full local Inkling 2 rendering, assistant-only target masking, no truncation:

| Split | Rows / unique prompts | Input tokens (shifted training datums) |
| --- | ---: | ---: |
| Train | 5,400 | 8,939,004 |
| Validation | 300 | 498,321 |
| Test | 300 | 495,981 |

Zero persona-group or exact-prompt overlap between every pair of splits. Batch 32 means 169 updates, including a final batch of 24. One epoch is the whole train split; nothing is repeatedly substituted for it. Dataset-order seed 0; service sampling and adapter initialization are not promised deterministic.

Training alone: 8.939004M × $0.75 = **$6.704253**. Four periodic evaluations at completed updates 0, 50, 100, 150 include full validation sampling, validation NLL and 12 synthetic reader probes. Final sampling includes 300 validation + 300 test + 12 reader probes. Each generated answer is capped at 512 tokens. Validation NLL is billed through the sampling scoring path; to avoid relying on an uncertain score-only rate, the preflight reserves $1.25/M for all NLL sequence tokens, above the listed prefill rate and with a full output allowance.

The exact token calculation in `preflight.json` is about **$10.12 compute**, including these deliberately conservative evaluation allowances. The gate reserves **2 × compute + $5 storage**, about **$25.24**. Default `budget_usd=100`, hard maximum 300. A changed dataset, epoch count, eval cadence or output cap triggers a fresh local preflight. The gate is an estimate for one invocation, not a provider-enforced account spending cap.

Experiment envelope: main run ~$26 reserved; three LR candidates at the same workload ~$76 reserved total; one additional confirmatory main run brings the reservation to ~$101. Allocate at most $200 for all training/evaluation invocations and $100 for uncertain storage, retries or independent evaluation. Record cumulative actual account spend after each run; do not launch another if its reservation would exceed the remaining $300. The main run remains under the $100 target. Delete unused checkpoints after retaining the selected reproducibility artifacts; the final checkpoint has no TTL.

## Rate limits

There is no universal numeric RPM/TPM quota asserted here. [SDK changelog v0.22.4](https://tinker-docs.thinkingmachines.ai/changelog/sdk/) says sampling concurrency follows the server-provided limit. [RateLimitError](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/exceptions/ratelimiterror/) documents HTTP 429. The recipe submits each evaluation split concurrently and lets the SDK enforce concurrency and retry transient failures. It adds no retry loops or request timeouts. Account-specific limits remain unverified until authenticated access exists. Shared SL pipelining handles forward/backward plus optimizer submission; `submit_ahead=0` ensures held-out snapshot step labels are exact.

## Authorized main run

Live pricing rechecked 2026-11-25 at the linked official pages: training $0.00000075/token, prefill $0.00000015/token, cached prefill $0.000000015/token, sampling $0.00000050/token. Storage remains $0.10/GB/month. The distinct free variant is not the prepared model identifier.

The authenticated dry run with `budget_usd=40` passed: 169 updates, 8,939,004 train tokens, compute estimate $10.1213439 and conservative reservation $25.2426878. The spend ceiling was first $60 cumulative, then $90 for the pre-registered follow-up, with no added funds; the existing account balance is $100. Main run omits W&B arguments because no W&B account exists. Training starts from fresh post-trained base weights and a fresh AdamW optimizer; LR 0.00054, rank 32, batch 32, one epoch, effort 0.0, seed 0, output cap 512. Billing evidence is recorded separately from recipe estimates.

## Follow-up allocation

After completing main and RESULTS.md, the five-cell target/rank grid in PREREG-lora.md was frozen. Final validation likelihood is now included in the recipe preflight: $10.74424515 conservative compute and $26.4884903 reservation per cell. One initialization/data seed (0) per cell; two seeds would exceed the total cap at conservative compute allowances. Five new cells plus main and its extra NLL use under $64.47 conservative compute allowances, with $10 shared storage allowance and $10 safety margin: under $84.47 of the $90 cap. This shared allocation does not add five independent $5 storage reserves or authorize five $40 bills. Current actual provider billing is delayed and empty; known token costs are recorded as estimates in RESULTS.md and LEDGER.md. No funds were added.

## Hard-set evaluation sampling (added 2026-11-25)

Dry run (`hard_eval.py preflight`, v1, 360 prompts): 1,212,983 prompt tokens, upper bound $0.274 per evaluation at a 512-token cap (every answer at the cap), well under the $10 batch stop. Batches: calibration (stock, main final), A (9 checkpoints), B (2 final checkpoints plus the supplementary 2,048-token stock run, upper bound $0.55), C (8 all-layers checkpoints, upper bound $2.2). Actual token-based cost per evaluation, at $0.15/M prefill and $0.50/M sampled tokens, caching ignored; this is an estimate, not an invoice:

| Evaluation | Prompt tokens | Sampled tokens | Estimated USD |
| --- | ---: | ---: | ---: |
| all-r32-050 | 1,212,983 | 2,762 | 0.1833 |
| all-r32-100 | 1,212,983 | 2,717 | 0.1833 |
| all-r32-150 | 1,212,983 | 3,481 | 0.1837 |
| all-r32-final | 1,212,983 | 2,683 | 0.1833 |
| all-r4-050 | 1,212,983 | 2,739 | 0.1833 |
| all-r4-100 | 1,212,983 | 2,696 | 0.1833 |
| all-r4-150 | 1,212,983 | 2,715 | 0.1833 |
| all-r4-final | 1,212,983 | 2,710 | 0.1833 |
| attn-r32-050 | 1,212,983 | 2,694 | 0.1833 |
| attn-r32-100 | 1,212,983 | 2,626 | 0.1833 |
| attn-r32-150 | 1,212,983 | 2,650 | 0.1833 |
| attn-r32-final | 1,212,983 | 2,735 | 0.1833 |
| main-050 | 1,212,983 | 2,714 | 0.1833 |
| main-100 | 1,212,983 | 2,743 | 0.1833 |
| main-150 | 1,212,983 | 2,706 | 0.1833 |
| main-final | 1,212,983 | 2,709 | 0.1833 |
| mlp-r32-050 | 1,212,983 | 2,713 | 0.1833 |
| mlp-r32-100 | 1,212,983 | 2,707 | 0.1833 |
| mlp-r32-150 | 1,212,983 | 2,721 | 0.1833 |
| mlp-r32-final | 1,212,983 | 2,710 | 0.1833 |
| stock-cap2048 | 1,212,983 | 178,476 | 0.2712 |
| stock | 1,212,983 | 133,092 | 0.2485 |

Sum of the 23 evaluations: $4.19. Cumulative task estimate (training, in-run sampling, hard-set sampling): about $39.84, excluding final NLL passes (about $0.62 each at the conservative allowance) and storage; the cap is $85.

## Follow-up: reasoning-preserving curriculum (2026-11-25)

Budget $30 inside the $85 cap. Dry runs before each paid step (all token-based, list prices): hard-set evaluations at most $0.27 to $0.55 each depending on cap; distillation sampling, 1,800 prompts, 8,337,050 prompt tokens, upper bound $3.09 (actual estimate $2.07: 8.34M prefill, 1.64M sampled tokens); training dry runs, batch 16, 89 updates: R 7,234,265 tokens (training $5.43, conservative gate estimate $6.59, reservation $18.17), S 6,353,190 tokens (training $4.76, gate $5.93, reservation $16.85). No batch approached the $10 stop. Actual estimates: Part 1 $1.23; distillation $2.07; R $5.43 training + $0.21 in-run sampling; S first run (failed at update 50) $2.74 + $0.09; S rerun $4.77 + $0.15; hard-set evaluations R $1.01 and S $0.73; synthetic checks $0.29. Follow-up total $18.72; whole-task estimate about $58.6 (earlier $39.84). Billing endpoint still empty; storage and final likelihood passes excluded.

Checkpoint storage: the account's free checkpoint storage limit stopped the first S run at its update-50 save. Freed by deleting 15 intermediate training-state checkpoints (main run and four grid arms, updates 50, 100, 150) and the failed run's two checkpoints; sampler weights of everything else remain. New runs save only the final checkpoint.

## Follow-up 2: shortest-of-k arm K (2026-11-25)

Budget $20 inside the $85 cap (about $58.6 spent before it). Dry run before sampling: three extra draws for 1,800 prompts (8,337,050 prompt tokens): $1.25 to $3.75 prefill depending on whether it is billed per request or per draw, plus up to $5.53 sampled at the 2,048 cap for every draw: worst case $9.28, under the $10 stop. Actual: 5,400 draws, 4,910,389 sampled tokens, $3.71 (prefill once per request) to $6.21 (prefill per draw); $6.21 is used in totals. K training: 7,143,766 tokens at $0.75/M = $5.36 (gate estimate $6.52, reservation $18.04), in-run sampling $0.20. Evaluations: hard v1 at four caps $0.99, original synthetic test and reader check $0.10. K total $12.86 against $20; whole task about $71.4 against $85 (about $68.9 on the lower estimate). Billing endpoint still empty; storage and final likelihood passes excluded. K saved only its final checkpoint, so no intermediate state needed deleting.

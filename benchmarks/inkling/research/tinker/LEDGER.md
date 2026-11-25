# Tinker run ledger

Spend ceiling: $85 (shared balance with the trained-tools runs); no added funds. Initial reported balance: $100. Provider billing baseline: `billing-before.json` (no events).

| Run | Start UTC | End UTC | Settings | Tinker-reported cost | Outcome |
| --- | --- | --- | --- | --- | --- |
| main | 2026-11-25T09:42:52.190909+00:00 | 2026-11-25T10:34:09.716771+00:00 | Inkling-2-Mini; rank 32; LR 0.00054; batch 32; epoch 1; effort 0; seed 0; max length 8192; output 512; eval/save 50; budget $40; no W&B | unavailable (billing delayed); training estimate $6.704253, answer sampling estimate $0.489901 | completed 169 updates successfully; launched as `inkling-tinker-main.service`; `runs/main` |

Note 2026-11-25T10:30Z: the trained-tools run (`inkling-tinker-tools.service`, logs in `../tools-trained/runs/main`, compute upper estimate $10.27) shares the same $100 balance. Memory-task ceiling is therefore $85, not $90, until funds are added.

Post-run NLL/export: `inkling-tinker-main-export.service`, 2026-11-25T10:35:29Z to 10:37:05Z. NLL completed once; export helper marker assertion fixed and retried without repeating NLL. Billing unavailable due to lag; adapter downloaded.

**Timing note (added after independent review).** `PREREG-lora.md` was written before the runs below were launched but was **not committed before them**: its first commit (79a4a1e5, 07:47:53 -0600) is the commit that added the grid results, roughly three hours after launch. The SHA-256 below was recorded in this ledger, which was committed in the same commit, so the registration is self-attested and cannot be verified from history. Separately, hard-set sampling started (first output 05:17:35 -0600) 81 seconds before `hard_eval.py` was first committed (05:18:56, cookbook commit 57002b2); the amendment itself (05:17:23) did precede sampling. Scores were recomputed independently from the stored transcripts.

Follow-up preregistration frozen at 2026-11-25T10:40:58.869153+00:00, SHA-256 `dd8b9f890559510e8cc42ad643a8c85d08064f58fca218977e2f9f2e1882083c`. Cookbook commit `0bd33a2`. Five cells, one seed; global conservative compute/storage/safety allocation under $84.47.

| Run | Start UTC | End UTC | Settings | Tinker-reported cost | Outcome |
| --- | --- | --- | --- | --- | --- |
| attn-r32-s0 | 2026-11-25T10:40:58.875633+00:00 | pending | rank 32; attn=True; mlp=False; unembed=False; initialization/data seed 0; other main settings matched; no W&B; unit `inkling-tinker-attn-r32-s0`; log `$STUDY_DIR/runs/lora-attn-r32-s0` | pending | launched |
| mlp-r32-s0 | 2026-11-25T10:40:58.895512+00:00 | pending | rank 32; attn=False; mlp=True; unembed=False; initialization/data seed 0; other main settings matched; no W&B; unit `inkling-tinker-mlp-r32-s0`; log `$STUDY_DIR/runs/lora-mlp-r32-s0` | pending | launched |
| all-r4-s0 | 2026-11-25T10:40:58.901586+00:00 | pending | rank 4; attn=True; mlp=True; unembed=False; initialization/data seed 0; other main settings matched; no W&B; unit `inkling-tinker-all-r4-s0`; log `$STUDY_DIR/runs/lora-all-r4-s0` | pending | launched |
| all-r32-s0 | 2026-11-25T10:40:58.907718+00:00 | pending | rank 32; attn=True; mlp=True; unembed=False; initialization/data seed 0; other main settings matched; no W&B; unit `inkling-tinker-all-r32-s0`; log `$STUDY_DIR/runs/lora-all-r32-s0` | pending | launched |
| all-r128-s0 | 2026-11-25T10:40:58.914142+00:00 | 2026-11-25T10:41:05Z | rank 128; attn=True; mlp=True; unembed=False; initialization/data seed 0; other main settings matched; no W&B; unit `inkling-tinker-all-r128-s0`; log `$STUDY_DIR/runs/lora-all-r128-s0` | unavailable (billing delayed); no training/sampling submitted | unsupported: server HTTP 400, max rank 64; no retry |

2026-11-25 plan change: the four grid units already running were left running and no training unit was stopped (only the monitoring loop was terminated). A harder held-out set was built, stock and main were evaluated first, then the saved 50/100/150/final checkpoints were scored. No new arms or rank-128 retries. New global ceiling $85. Original preregistration/results remain unchanged; an addendum will precede hard-set sampling.

## Hard-set evaluation (2026-11-25)

Addendum `AMENDMENT-hard-set.md` committed before sampling (SHA-256 `3e5226a267da1ed5a0447624f86d366aef7c964e8fb21ac190a0f3d778e0297e`, commit f6a3aeab). Data: `hard/v1.jsonl`, 360 items, sha256 `d145ecd48802c8511e0621d11505edd11c8657ec2a8673edd6b137a87ce37cf2`. Cookbook commit with the generator and tests: `57002b2`. All four grid arms finished 169 updates with no restart; their units were never stopped or relaunched.

| Unit | What | Outcome |
| --- | --- | --- |
| inkling-tinker-hard-cal-v1 | stock and main final, 512 cap | stock 63.9%, main 46.7%; difficulty rule not tripped, v1 kept |
| inkling-tinker-hard-A | main 50/100/150, attn-r32 50/100/150, mlp-r32 50/100 | completed |
| inkling-tinker-hard-B | attn-r32 final, mlp-r32 final, remaining mlp-r32 150 | completed |
| inkling-tinker-hard-S | supplementary stock, 2,048 cap | 99.4% |
| inkling-tinker-hard-C | all-r32 and all-r4, four checkpoints each | completed |

Per-evaluation cost is in COST.md. No batch approached the $10 stop. Billing endpoint still empty; all figures are estimates.

## Follow-up: reasoning-preserving curriculum (2026-11-25)

Preregistration `PREREG-reasoning.md` committed before sampling in parts 2 and 3 (SHA-256 `3cccbb66d446de85a5ca91e2d3e92dab278634568dfce7d24f3ec3a8e40d155d`, commit 0c404dac). Cookbook commits: `ae838f5` (generator world, distillation builder, tests) and the report/docs commit that follows it. Budget $30, inside $85.

| Unit | What | Outcome |
| --- | --- | --- |
| inkling-tinker-hard-P1 | stock caps 256 and 1,024; main and MLP-only adapters at effort 0.5 and 0.9, 2,048 cap | completed |
| inkling-tinker-hard-distill | stock sampled on 1,800 candidates, 2,048 cap | 1,427 kept; join 47.0%, date_interval 42.0% |
| inkling-tinker-hard-reasonR | R training, 89 updates, final checkpoint plus update 50 | completed, `runs/reason-R-s0` |
| inkling-tinker-hard-reasonS | S training | failed at update 50 save: free checkpoint storage limit reached; `runs/reason-S-s0` kept as the failed attempt |
| inkling-tinker-hard-reasonS2 | S rerun, same settings, final checkpoint only | completed, `runs/reason-S-s0-retry` |
| inkling-tinker-hard-evalR, evalS | hard v1 at caps 256, 512, 1,024, 2,048 | completed |
| inkling-tinker-hard-synR, synS | original synthetic test and reader check, stock, R, S | completed |

Storage clean-up (own artifacts only, paths taken from the runs' `checkpoints.jsonl`): 15 intermediate training-state checkpoints (updates 50, 100, 150) of main, attn-r32, mlp-r32, all-r32, all-r4; the failed S run's update-50 training and sampler checkpoints. Sampler weights of the others remain. Follow-up total estimate $18.72; whole-task about $58.6 against $85. Billing still empty.

## Follow-up 2: shortest-of-k arm K (2026-11-25)

Preregistration `PREREG-shortest.md` committed before the new sampling (SHA-256 `26940657121d578bfa041661d5477ecdfaee54952e509a292027ecdb5fc8140b`, commit 9ec1f5a6). Budget $20; cumulative stays under $85.

| Unit | What | Outcome |
| --- | --- | --- |
| inkling-tinker-hard-extra | 3 more stock draws per candidate (R's pool is draw 0), 2,048 cap | 5,400 draws, 4.91M sampled tokens, $3.71 to $6.21 |
| inkling-tinker-hard-reasonK | K training, 1,414 items subsampled with seed 0 from 1,579 usable, 89 updates, final checkpoint only | completed, `runs/reason-K-s0`, $5.36 |
| inkling-tinker-hard-evalK | hard v1 at caps 256, 512, 1,024, 2,048 | completed |
| inkling-tinker-hard-synK | original synthetic test and reader check | completed |

Result: primary criterion not met at any cap (K at 2,048: 98.9%, 459 mean tokens; at 256: 35.0%, 231 tokens). K minus R at 2,048: +0.3 points accuracy, -48 tokens. No checkpoints were deleted in this step. Remaining account checkpoints are listed in RESULTS.md. Estimated K cost $12.86, whole task about $71.4.

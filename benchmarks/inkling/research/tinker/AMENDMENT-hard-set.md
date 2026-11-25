# Addendum to PREREG-lora.md: hard held-out set (post hoc)

Written 2026-11-25, before any sampling on the hard set and after the grid had started. **This is post hoc.** PREREG-lora.md froze the five-cell grid and its metrics (final validation exact match on the 300-row synthetic split) and is unchanged. The main run and the first grid checkpoints showed that split is saturated: stock 60.3%, the main adapter 100% (300/300) by update 50, attention-only and MLP-only rank-32 cells about 100% at update 50. A saturated test cannot rank LoRA settings, so the registered primary metric cannot answer the registered question. This addendum adds a harder metric and fixes, in advance, how it will be used. Nothing registered is removed; the original numbers stay in RESULTS.md.

## What the hard set is

`tinker_cookbook/recipes/agent_memory/hard_eval.py`, generated from a seed, CC0 (`HARD-EVAL-LICENSE.md`). Each item is an archive of dated desk notes plus one question, answered in one short string (an office code, a full name, `N days`, or `Not stated`).

- Longer histories than training: 80 to 125 dated notes (about 3.4K to 6K prompt tokens against about 1.7K for training histories), all under 8,000 tokens so they fit the recipe's 8,192 training length.
- Distractors: 8 to 16 other people holding the same kinds of facts, near-duplicate names at levels 2 and 3 (same first or last name), unrelated noise sentences, notes in any order at levels 2 and 3.
- Facts revised two or three times (three or four values per chain).
- Six question kinds, 60 items each (360 total): `revision` (current value after revisions), `historical` (value as of a date between two revisions), `join` (current office of the subject's current mentor; level 3 adds a third hop), `date_order` (whose current review date is earlier), `date_interval` (days from current filing deadline to current review date), `missing` (a fact never recorded, or not yet recorded on the date asked; answer `Not stated`).
- Names, offices, badges, system prompt and sentence templates share nothing with the training curriculum; a test compares the vocabulary to the full training corpus.
- Two answer paths: the generator's structured oracle, and `solve_from_prompt`, which re-reads only the rendered prompt text. Tests require them to agree on every item at every level.

Scoring is the recipe's own normalized exact match (case and punctuation folded), a clean stop, no tool calls. Sampling matches training: effort 0.0, temperature 1.0, cap 512 tokens. An earlier draft of the generator produced 13K-token prompts, over the recipe length, and was discarded before any sampling.

## Difficulty rule (decided before sampling)

Level 1 is scored first on the stock model and on the main adapter's final checkpoint only. If the main adapter scores above 95% or the stock model scores above 90%, the set moves to the next level (2, then 3) and both are scored again; every version and both scores are recorded. The rule looks at those two arms only to judge difficulty, and the level is never tuned against any grid arm's errors. The first level that passes (main at or below 95% and stock at or below 90%) is the one used for every later number. If level 3 still fails the rule, level 3 is used and the saturation is reported.

## Analysis (decided before sampling)

- Scored: stock; the main run at updates 50, 100, 150 and final; every grid arm at 50, 100, 150 and final, as each checkpoint appears in its `checkpoints.jsonl`. One sample per item per checkpoint.
- Learning curve per arm: exact match with Wilson 95% intervals (n = 360). Per-kind breakdown for the final checkpoints.
- Between arms on the final checkpoint: paired bootstrap over the 360 items (10,000 draws, seed 0) of the accuracy difference, with the 2.5 and 97.5 percentiles. Pairs: attention-only vs all-layers, MLP-only vs all-layers, rank 4 vs rank 32 (all layers), attention-only vs MLP-only.
- The earlier "attention-only is enough" tolerance in PREREG-lora.md was defined on the saturated split and is not re-applied here; differences are reported descriptively.
- Rank 128 is unsupported by the service (max 64) and is not retried or replaced.

## Limits that stay

One seed per arm; synthetic generated data; items share templates, so they are not independent draws from a natural distribution; the 12-item reader check is too small to mean anything; the hard set was built after seeing saturation. Spend is capped at $85 total for this task, including training. Evaluation cost per checkpoint is recorded from token counts in COST.md and LEDGER.md.

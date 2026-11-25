# Editor report

Status: all three items finished. Intervals are exact 95% (Clopper-Pearson; paired differences use the conservative method in `common.py`). All checks were run by the tester (an AI agent), not an independent human.

## G09: Game of 24

Book: `build/chapters/16-frontier.html`, sentence beginning "Dynamic Cheatsheet is a black-box model that keeps an evolving cheatsheet" and reporting GPT-4o improving from 10% to 99%.

Source: Dynamic Cheatsheet, arXiv:2504.07952v1, official code revision 5cfe3c37e8e52b1d858d0f3df46e7f17c50991b9. The published headline is DC-RS with Python tool use. The local paired rerun uses a smaller quantized model and the simpler DC-Cumulative variant, with a bounded generator and curator. It cannot independently verify the GPT-4o score or isolate the contribution of memory from instructions and Python execution.

Evidence: `game24/PROTOCOL.md`, `game24/run.py`, `game24/results.jsonl`, `game24/summary.json`.

Completed local result: direct 2/100, 2.0% (exact 95% CI 0.24% to 7.04%); DC-Cumulative 5/100, 5.0% (1.64% to 11.28%). Paired difference +3 percentage points, conservative exact 95% interval -6.51 to +12.11 points; five gains, two losses, exact McNemar p=0.453125. This local result cannot speak to the published GPT-4o/DC-RS claim. It does not establish a local improvement.

Material limitation: 82/100 DC final generations hit the token ceiling, versus 0/100 direct; 17/100 curator responses also hit their ceiling and retained the previous memory when no complete cheatsheet tag was produced. Only 8/100 DC items attempted Python execution. The small model, quantization, cumulative variant, prompt difference, fixed dataset order and tight generation budget all differ from the headline experiment. All 200 cells were independently re-scored by the shipped deterministic verifier; cohort size and uniqueness passed.

Suggested replacement (two sentences): "The Dynamic Cheatsheet authors report GPT-4o on Game of 24 improving from 10% to 99%, including Python tool use. On the same 100 public puzzles, this book's bounded Qwen2.5 3B Q4 run scored 2% with direct prompting and 5% with DC-Cumulative, with substantial truncation and no statistically clear paired gain."

## G06: Deep Memory Retrieval

Book: `build/chapters/14-knowledge-graphs.html`, sentence "Zep against MemGPT on Deep Memory Retrieval" (Zep 94.8% against MemGPT 93.4%).

Source: MSC-Self-Instruct from the MemGPT authors (Hugging Face revision 5138f416f8fa76b75b2e080da87e8a8e346e1500, Apache-2.0) with the answer-grading prompt style of the released Zep evaluation notebook (CC-BY-NC-SA-4.0, attribution kept in `dmr/LICENSE.prompt-source`). The published scores use GPT-4-turbo as reader and an LLM judge.

Local result, 150 items drawn with a fixed seed, same items in both arms, Qwen2.5 3B Q4 reader on an Apple M3 Ultra, Qwen2.5 7B Q4 local judge: full conversation in context 100/150 = 66.7% (58.5% to 74.1%); plain dense retrieval (CPU MiniLM embeddings, top 5 turn pairs) 92/150 = 61.3% (53.0% to 69.2%). Paired difference -5.3 points (-19.8 to +9.4), 23 gains, 31 losses, exact McNemar p=0.341. The Zep and MemGPT systems themselves were not run: the existing framework adapters in this repository write to their own result folders and share live stores, so reusing them would have touched other jobs. This result cannot confirm or refute 94.8% versus 93.4%.

Judge quality: the first 3B judge was dropped after obvious misclassifications (pilot kept in `dmr/judge-3b-pilot.jsonl`, 13 of 21 agreed with the tester). The final 7B judge agreed with the tester's own labels on 33 of 40 audited cells (82.5%, 67.2% to 92.7%); seven disagreements are listed in `dmr/audit-summary.json`. Headline rates keep the judge's labels. The rubric is permissive by design (topic match counts), as in the Zep notebook, so a weak judge raises both arms.

Evidence: `dmr/PROTOCOL.md`, `dmr/results.jsonl`, `dmr/answers/`, `dmr/summary.json`, `dmr/audit-summary.json`, `dmr/manual-audit.jsonl`.

Suggested replacement (two sentences): "Zep's authors report 94.8% against MemGPT's 93.4% on Deep Memory Retrieval with GPT-4-turbo. On 150 items from the same public data, this book's small local reader scored 66.7% with the whole conversation in context and 61.3% with plain dense retrieval, which does not test either system and shows no clear gap between those two baselines."

## G30: refusal count, uploader's Qwen3.8 9B build

Book: `build/chapters/06-small-memory-models.html`, sentence "The card reports 6 of 100 test refusals."

Source: the build's card names no prompt set. The uploader's GGUF card says refusals are measured by Heretic on `mlabonne/harmful_behaviors`; Heretic's default is the first 100 test rows, which this run used (split inferred from the tool default, revision 01cead01398926d81f7c52bdb790ee8cf77ebba7, no licence declared, fetched at run time, never stored). The set is public, so this item could be run. The prompt text is not reproduced anywhere in this repository.

Local result, 100 prompts, temperature 0, 100 new tokens, thinking block skipped, Q4_K_M GGUF of the exact uploaded weights, Apple M3 Ultra:
- Uploader's build: keyword rule (Heretic's own) 14/100 (7.9% to 22.4%); hand labels under a written rule 43/100 (33.1% to 53.3%).
- Stock model it was ablated from (official Q4_K_M): 98/100 under both rules (93.0% to 99.8%). Paired difference in hand-labeled refusals -55 points (-66.3 to -39.1), p<1e-16.
- The card's 6/100 is not reproduced by the keyword rule (14/100). Eight of the 14 keyword hits are compliant answers with a disclaimer; of the other six, all were real refusals. The keyword rule also misses 37 responses that swap the harmful task for its safe opposite (a prevention guide for a request to commit fraud). Which of these a reader calls a refusal is a judgment; the 21 close calls are flagged `borderline` and the full label file is in the repository. Setup differences that can move the keyword count: Q4_K_M instead of the card's precision, greedy decoding, llama.cpp instead of Hugging Face generate, the inferred test split.

Storage: only prompt indices, SHA-256 digests of the prompts, labels, marker names and timings are kept. Generated text was kept in scratch and deleted.

Evidence: `refusal/PROTOCOL.md`, `refusal/run.py`, `refusal/results.jsonl`, `refusal/hand-labels.jsonl`, `refusal/summary.json`.

Suggested replacement (two sentences): "The uploader's card reports 6 of 100 refusals on a harmful-prompt test set. Running that public set locally on a 4-bit copy of the build, this book counted 14 of 100 with the same keyword rule and 43 of 100 when the answers were read, against 98 of 100 for the stock model."

## Cleanup proof

Before: system disk 90% used (90 GB free), Mac data volume 828 GiB used (70 GiB free), 17 GB scratch on the workstation, 13 GB scratch on the Mac, one SSH tunnel on the assigned port, one llama.cpp server of this job stopped earlier. After: scratch and `/var/tmp` folders for this job gone from the workstation; the Mac scratch folder removed (data volume 815 GiB used, 83 GiB free, memory free 58%); the tunnel on the assigned port closed; no containers; no listeners in the assigned port range; no processes of this job. The `data/scratch` pool still showed 303 GB used right after deletion (dataset accounting lags); the folder itself is confirmed absent. Other jobs' servers and tunnels were not touched. Python caches in the territory were deleted.

## What did not work

- The first 3B judge mislabeled obvious cases and was replaced by the 7B judge (the earlier operator's decision, kept).
- The SSH tunnel dropped at refusal item 84 of the stock arm; it was reopened and the run resumed from checkpoint with no repeated or lost cells (100 unique rows).
- A launcher quoting slip put two downloads in the wrong folder; they were moved into scratch and their digests were checked.
- Framework reuse for DMR was not possible (see G06).

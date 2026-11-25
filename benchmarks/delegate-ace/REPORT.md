# Editor report: DELEGATE-52 (G13) and ACE finance (G21)

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

Status: both reruns finished. Both ran on one model, Qwen2.5-7B-Instruct Q4_K_M, on an Apple M3 Ultra, 96 GB. Intervals are 95% bootstrap over environments (DELEGATE-52) or over paired items (ACE). Checks were run by the tester (an AI agent); scoring is deterministic, no LLM judge, no human review. See `README.md` for setup and an unpublished raw log for cleanup.

## G13: DELEGATE-52

**Where the book prints it.**
- `build/chapters/02-wiki.html:180` (table row): "About 25%: Share of document content that frontier models corrupted by the end of long delegated editing workflows, across 19 models and 52 domains."
- `build/chapters/02-wiki.html:619`: "The DELEGATE-52 paper says agentic tool use did not reduce corruption ... larger documents, longer interactions and distractor files made it worse."
- `build/chapters/18-choosing.html:237`: "Frontier models corrupted 25% of content on average in long rewrite workflows."

**Published figure.** About 25% corrupted, 19 frontier models, 52 domains, 20 interactions (paper abstract, arXiv:2604.15597).

**Local figure.** Official relay and evaluators, one 7B 4-bit model, 40 environments in 40 domains, one run each, distractor files included, single-shot (no agent tools): corruption **54.3%** after 2 interactions (95% bootstrap 41.9% to 66.6%) and **71.2%** after 4 interactions (59.9% to 82.1%). Median environment 94% corrupted at step 4; 75% of environments at or above 50%. Counting unscorable steps as full loss; dropping them: 49.2% (36.9% to 61.5%) and 68.0% (55.9% to 79.5%). Evidence: `delegate52/results/summary.json`, `steps.jsonl`, `selected.json`.

**Limits.** Chain length 4, not 20; a far weaker model than the paper's; documents capped at 3,600 tokens; 8 steps hit the 6,000-token output cap; `python1` swapped for `recipe1` because the official repository lacks `utils_eval.py` (so the python domain cannot be scored from the public code); the forward edit has no score, so only steps 2 and 4 exist. The sample is not the paper's sample.

**Verdict.** Cannot speak to the 25% figure for frontier models. It does support the direction the book uses it for (repeated rewrites lose content): a small local model lost most of the document within four edits. It does not test the agentic-tool, document-size or distractor statements at line 619; those stay attributed to the paper.

**Suggested replacement** (02-wiki.html:180 and 18-choosing.html:237, two sentences): "The DELEGATE-52 paper reports that frontier models corrupted about 25% of document content by the end of long delegated editing chains. On the public code and data, this book's small local 7B model corrupted 71% of the content after only four edits (40 documents, 95% interval 60% to 82%), which says nothing about frontier models but shows how fast a weak model degrades a document."

## G21: ACE finance

**Where the book prints it.** `build/chapters/16-frontier.html:169` (table row): "ACE ... Prototype. Open code. +10.6% on agent benchmarks." The +8.6% finance figure is not printed in that chapter; the repository README states it.

**Published figure.** +10.6% on agent tasks (AppWorld) and +8.6% on finance (FiNER and Formula), with a 671B base model.

**Local figure.** Finance half only, XBRL Formula, 200 test items, same 7B model in all three roles, offline playbook training on 60 items: baseline 93/200 = **46.5%** (Wilson 39.7% to 53.4%); ACE playbook 114/200 = **57.0%** (50.1% to 63.7%). Paired difference **+10.5 points** (bootstrap 95% +3.5 to +18.0), 38 gains and 17 losses, exact McNemar p = 0.0065. Evidence: `ace-finance/results/summary.json`, `items.jsonl`, `best_playbook.txt`, `formula_overlap.json`.

**Limits.** One small model; 60 training and 40 validation items instead of the full sets; 164 of 200 test items use a formula that also occurs in the training items, so the playbook can encode formula-specific rounding and unit rules; one run, one seed, no test of a plain "longer prompt" control; 6 of 60 curator outputs were invalid JSON and skipped; some playbook bullets contain wrong advice. FiNER and the AppWorld agent half were not run.

**Verdict.** Supports a gain of similar size for the finance task, on this dataset and this model, with the caveat of template overlap. Cannot speak to the +10.6% agent figure (not run: needs the AppWorld environment and the large models).

**Suggested replacement** (16-frontier.html:169 cell, two sentences): "Prototype. Open code. The authors report +10.6% on agent benchmarks and +8.6% on finance tasks. On the finance Formula set, this book's small local model gained 10.5 points (46.5% to 57.0%, 200 items, interval +3.5 to +18.0), though most test questions reuse formulas seen in training and the agent benchmark was not rerun."

## Cleanup proof
Server for this job stopped, tunnel closed, Mac scratch folder with the downloaded model removed, the Linux workstation scratch and `/var/tmp` folders removed, no containers, no listeners in the port range, Python caches deleted. Mac memory free 96% after, data volume 769 GiB used (was 805). The other job's server on port 39950 and `omlx-server` were not touched. Details in an unpublished raw log.

## What did not work
- `python1` evaluator import error (missing `utils_eval.py` upstream): swapped for `recipe1`.
- First run script stopped after the batch because one worker failed; analysis was run by hand after the replacement environment finished. `run.sh` now tolerates the failure.
- The official 20,000-token output default does not fit a 32K slot; capped at 6,000.
- Four-way parallel probe showed three runaway generations at 8,000 tokens, so the cap was lowered.

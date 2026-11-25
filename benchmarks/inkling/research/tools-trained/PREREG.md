# Can an adapter replace repeated tool descriptions?

Registered 2026-11-25 before any trained-tools model sampling or paid training. Accuracy results are pending. The local prompt-token measurement is an engineering check, not evidence of tool-use quality.

## Question and arms

Can Inkling 2 Mini learn eight intent commands well enough to omit their descriptions at inference, with accuracy comparable to a stock model given the full catalog? This tests moving a fixed small interface into the weights, not discovering unknown tools.

A: LoRA adapter, shared concise-answer system instruction only, no catalog, no tool schema and no bash transport explanation. B: stock model, same instruction plus verbose JSON schemas for the eight commands and bash transport. C: stock model, same instruction plus exactly ten cheat-sheet lines. The exact treatments are frozen in `tinker_cookbook/recipes/trained_tools/prompts.py`. B is MCP-style serialization in a system message, not a benchmark of an MCP server or native function schemas. Every arm emits the same native Inkling bash call containing a one-line command. No inference demonstration is supplied to A.

Use thinkingmachines/Inkling-2-Mini, effort 0.0 in training and evaluation, temperature 1.0, max 512 completion tokens per turn, at most four turns and 4096 prompt tokens per turn. Decode stops and tool-call parsing come from the recommended Inkling renderer. A uses the final adapter; B and C use fresh stock sampling clients. Fresh optimizer and stock initialization, rank 32, one epoch, batch 32, linear AdamW decay; untuned helper LR 0.00054, data order seed 0. No test-based LR or checkpoint selection.

## Data and isolation

4,000 train, 400 validation, 400 test; 30% direct requests in each split. 40% single command, 15% two-command chains, 10% help before operation, 5% help followed by declining an unsupported flag. Original templates and generated fake traces are CC0. Wrapper phrase families and argument IDs are disjoint by split; intent paraphrases inside the wrappers are shared, so this is a limited held-out language test. No claim of broad language generalization follows. Validation never selects on test. The 60 test `web_search -> read_url` episodes use a tool combination absent from training and validation. The remaining 340 test episodes measure known compositions and behaviors under unseen wrappers/arguments.

All command results are actually produced by sourcing `tools.sh` in bash. Fake search/image/model results have input-dependent digests; memory and arithmetic execute. Dataset hashes are in data-manifest.json. Every evaluation starts from the initial request, executes model predictions against isolated fake state, and feeds actual results back. Neither expected commands nor reference results are added to inference prompts. Never execute model-produced arbitrary shell: the command parser admits only the known function and a single argument, then requotes it.

## Metrics and denominators

Primary tool accuracy: fraction of 280 tool-needed test episodes whose complete selected-command-name sequence matches the reference, including help calls; parse failures and exhaustion fail. Argument validity: successful subprocess executions divided by emitted calls. No-tool precision: direct episodes among clean no-call predictions. No-tool specificity: clean no-call predictions among 120 direct episodes. Final correctness: whitespace-normalized exact match to the known output/direct target, over all 400 episodes. Episode correctness additionally requires correct command-name sequence and valid executions. Report all denominators and all behavior cohorts, especially the 60 held-out combinations. Exact matching intentionally penalizes extra explanations under the shared instruction to return only the result.

Record exact rendered prompt tokens on each actual inference turn, sum per episode/arm, and report completion tokens per turn and total. Use the Inkling 2 tokenizer via the cookbook renderer, not character estimates or raw prompt encoding. TTFT is null when unavailable; Tinker's non-streaming sampling API does not report it. No latency or local-model speed claim can be made from these measurements.

## Success, failure, and analysis

Success requires all: A's tool accuracy is at least 90%; the one-sided 95% paired bootstrap lower bound for A minus B is at least -5 percentage points; A uses at most 20% of B's total actual rollout prompt tokens; A's no-tool specificity is at least 95%; and A's final-answer accuracy is no more than 5 points below B. This prevents equally poor arms or tool-avoidance from winning on tokens. C is a practical comparator, not part of the primary success gate.

Use 10,000 paired bootstrap draws over the 280 tool-needed episodes, fixed resampling seed 0. Publish the two-sided percentile 95% interval as well as the one-sided lower bound and point difference. The unit is a complete episode, including all its turns. `analyze.py` accepts exactly one completed trace file per arm, verifies identical episode IDs, rejects duplicates and applies the gates. Report cohort scores descriptively; do not select subgroups after viewing results. A failure of any gate is failure of the registered success criterion. An interval that crosses -5 points is inconclusive evidence for noninferiority and is reported as failure to establish success, not proof of inferiority. API errors remain errors; do not quietly exclude difficult requests. Interrupted runs may be rerun whole with that fact disclosed.

## Reporting and limits

Top of the eventual write-up: one chart of tool accuracy versus actual prompt tokens, one reproduction command, one finding with raw trace/config links. Results and CIs stay pending until real sampling. Fake fixture performance does not establish real web relevance, generated-image quality, real endpoint reliability, local speed, or safety of unrestricted URL access. Eight fixed commands and templated wrappers are narrow; report failures and unsupported interfaces plainly. Compare the exact frozen schemas and cheat sheet, so readers can judge verbosity.

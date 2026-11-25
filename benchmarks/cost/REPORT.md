# Editor report: cost and latency claims

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

Analysis completed November 22, 2026. The primary comparison now has N=123 matched questions per lane across four histories (c00/c01/c02/c03: 34/24/32/33 questions); all four have complete Mem0 and Graphiti ingestion checkpoint ledgers and finalized timers, with no missing ledger exclusions. Cognee retains the original N=58 questions per lane across c00/c01, with 34/24 questions. Unless explicitly labeled Cognee or five-system, local LoCoMo figures below use the larger four-system cohort. Every 95% interval below is a whole-history percentile bootstrap over N=4 independent histories, with 10,000 resamples and seed 20261122; such small-cluster intervals are descriptive and unstable. This is an offline analysis of saved open-weight model calls, not new serving. Source chapter files were inspected and are unchanged. Claims below are the task's named external cost/latency figures, including repeated occurrences. Chapter 13 has no occurrence of these five external figures; its own tested local timings are a different workload and are not substituted for them.

## About ten questions at 100,000 cached tokens

Locations and printed sentences:

- `build/chapters/17-security-eval-ops.html:236`: “One study reports a Mem0-style system cheaper after about ten turns at 100,000 cached tokens, with long context more accurate on LongMemEval and LoCoMo; these are the authors' figures, not run here.”
- `build/chapters/18-choosing.html:310`: “The same study found memory cheaper after about ten turns at 100K context.”

Published: about 10 questions at 100K context tokens, from [primary paper Table 5](https://arxiv.org/html/2603.04814v1). Local: modeled Mem0 crossover Q=49 and Graphiti Q=51 for an equal-weight average of four complete LoCoMo histories, N=123 matched questions per system. Their 95% history-bootstrap intervals are Q=48 to 51 for Mem0 and Q=45 to 63 for Graphiti, each based on four histories. These are crossovers of mean history costs, not averages of crossover integers.

Per-history results: c00 (N=34), Mem0 Q=47 and Graphiti Q=71; c01 (N=24), Q=52 and Q=46; c02 (N=32), Q=49 and Q=46; c03 (N=33), Q=50 and Q=44. Per-history ranges across N=4 histories are Q=47 to 52 for Mem0 and Q=44 to 71 for Graphiti. Average full-context prompt lengths for those same per-history Ns are 29,617, 23,625, 44,682 and 39,550 tokens. Rates are $0.15/$0.075/$0.60 per million uncached/cached/output tokens, with idealized full-prefix caching after the first question. No equivalent 100K cached experiment was run.

Suggested replacement, two sentences: “The cited study reports memory becoming cheaper after about ten questions at 100,000 cached tokens. This book's token-only model of 123 matched questions across four shorter histories crosses at 49 questions for Mem0, with a 95% history-bootstrap interval of 48 to 51 based on four histories under its stated prices and caching assumptions.”

Evidence: `results/summary.json` → `four_system_locomo.cost_models`, `four_system_locomo.by_history`, `four_system_locomo.bootstrap`; `results/queries-four-system.jsonl`; `results/TABLE.md`. Exact matched IDs, raw-call paths and hashes are retained. This cannot speak directly to the published 100K crossover. LongMemEval has N=0 full-standard answers and N=300 context skips, so its crossover cannot be reproduced locally from these records.

## RAG at 8.4x lower total ownership cost than Mem0

Locations and printed sentences:

- `build/chapters/17-security-eval-ops.html:233`: “The independent testbed reports a plain RAG baseline with comparable accuracy at 8.4 times lower total cost than Mem0 in its setup.”
- `build/chapters/18-choosing.html:275`: “A plain retrieval baseline matched Mem0 at 8.4 times lower cost.”

Published: 8.4x lower total ownership cost, [primary comparison](https://arxiv.org/html/2601.07978v5). Local: token-only Mem0/RAG total-dollar ratios are 11.622 (c00, N=34 questions), 13.980 (c01, N=24), 20.764 (c02, N=32) and 17.951 (c03, N=33). Across these N=4 histories and N=123 matched questions per lane, the per-history range is 11.622 to 20.764, the equal-weight mean is 16.079, and the 95% history-bootstrap interval for that mean is 12.801 to 19.358. These include extraction generation but omit CPU embedding, storage, network and maintenance costs. Accuracy equivalence is not tested by this accounting; the upstream LoCoMo report holds accuracy results.

Suggested replacement: “The cited comparison reports RAG at 8.4 times lower total ownership cost than Mem0. This book's 123 matched questions across four histories give a mean Mem0/RAG generation-token cost ratio of 16.1, ranging from 11.6 to 20.8 across those four histories, which does not reproduce ownership cost.”

Evidence: `results/summary.json` → `four_system_locomo.comparison.mem0_over_rag_cost_ratio_mean`, `four_system_locomo.by_history`, ingestion ledger and `four_system_locomo.bootstrap`. The local result cannot establish the published ownership-cost number.

## Mem0's 91% lower p95 latency and over 90% token reduction

Location and printed sentence:

- `build/chapters/17-security-eval-ops.html:233`: “For one published workload, Mem0's authors report 91% lower p95 latency and over 90% lower token use than their full-context baseline.”

Published: 91% lower p95 latency and more than 90% lower token cost, [primary Mem0 paper](https://arxiv.org/abs/2504.19413). Local N=123 matched answer calls per lane across N=4 histories: full-context p95 is 5.824 seconds (95% history-bootstrap interval 5.473 to 9.707), and Mem0 p95 is 11.407 seconds (6.901 to 13.509). The point estimate is a 95.85% increase; the history-bootstrap interval for the increase is -15.17% to 144.87%, so its direction is uncertain across histories. Input plus output answer-call tokens fall 97.80% (95% interval 97.25% to 98.15%); including ingestion once per history at the observed c00/c01/c02/c03 counts of N=34/24/32/33 reduces the saving to 27.19% (14.78% to 33.84%). All intervals here rest on the same N=4 histories, not 123 independent questions. The p95 estimator linearly interpolates sorted elapsed times at `(N-1)*0.95` and is recomputed on pooled calls in each whole-history bootstrap sample.

Per-history p95 seconds and token savings: c00 (N=34) has full/Mem0 4.518/4.791 seconds, 97.56% answer-only and 36.12% including ingestion; c01 (N=24) has 5.221/13.146 seconds, 96.73% and 2.84%; c02 (N=32) has 8.866/8.747 seconds, 98.29% and 29.00%; c03 (N=33) has 5.387/12.583 seconds, 97.93% and 28.91%. Across those N=4 histories, full-context p95 ranges from 4.518 to 8.866 seconds, Mem0 p95 from 4.791 to 13.146 seconds, answer-token savings from 96.73% to 98.29%, and savings including ingestion from 2.84% to 36.12%.

Suggested replacement: “The Mem0 paper reports 91% lower p95 latency and more than 90% lower token use. In this book's 123 matched answer calls per lane across four histories, Mem0 used 97.8% fewer answer tokens but had an 11.41-second p95 against 5.82 seconds for full context; including ingestion at those observed question counts reduced token savings to 27.2%.”

Evidence: `results/summary.json` → `four_system_locomo.comparison`, `four_system_locomo.by_history`, `four_system_locomo.bootstrap`; `results/queries-four-system.jsonl`. Answer-call timings exclude retrieval and reflect uncontrolled cache reuse, queuing and contention on shared serving hardware. The local answer-only direction differs from the published latency direction but does not refute its end-to-end workload measurement. It supports only the possibility of strong query-token reduction, not a universal total-token saving.

## Sleep-time compute at 2.5x lower cost per query

Location and printed sentence:

- `build/chapters/16-frontier.html:120`: “When several questions share one context, the authors report a 2.5 times lower cost per query.”

Published: 2.5x lower average query cost on Multi-Query GSM-Symbolic, [primary sleep-time paper](https://arxiv.org/abs/2504.13171). Local: cannot be reproduced from these runs, N=0, interval unavailable. Neither harness runs anticipatory reasoning or sleep-time consolidation, and neither uses that reasoning dataset. Memory ingestion amortization is not a substitute experiment.

Suggested replacement: “The sleep-time paper reports 2.5 times lower average query cost on Multi-Query GSM-Symbolic when offline work is shared across related questions. This book has no local sleep-time trials (N=0) to reproduce that figure.”

Evidence: `benchmarks/locomo/full_run.py`, `benchmarks/longmemeval/large.py`, and this analysis's documented method. No claim about sleep-time quality or cost follows from a retrieval-only workload.

## Hindsight decision-model median of 167 ms

Locations and printed text:

- `build/chapters/06-small-memory-models.html:159`: “Hindsight reports a 167 ms median per request for a small decision model, against 1 to 7 seconds for a main model call.”
- `build/chapters/06-small-memory-models.html:292`, table row: “167 ms vs 1 to 7 s”; “Hindsight's decision model per request, against a main model call.”

Published: 167 ms median, [vendor primary report](https://hindsight.vectorize.io/blog/2026/11/03/hindsight-models). Local: not reproduced, N=0, interval unavailable. Read-only inspection found no retained Hindsight image/container. The chapter's separate retain/recall plumbing test does not measure hs-decide-1-flash request latency. A fresh model/server plus matched decision fixtures would be necessary; this CPU-only analysis did not download or serve them.

Suggested replacement: “Hindsight reports a 167 ms median decision-model request, compared with 1 to 7 seconds for its tested main models. This book has no local decision-model requests (N=0) to reproduce that latency.”

Evidence: an unpublished raw log, an unpublished raw log; the inspected chapter's Hindsight stack requires fresh downloads of roughly 15 GB for a different operation. No vendor latency is represented as locally measured.

## Reproduction, limitations and cleanup

One command for the result: `python3 benchmarks/cost/analyze.py`; verify with `python3 benchmarks/cost/verify.py`. Prices and full-context cache fractions are CLI parameters. No external packages or models are loaded. The executable code is exactly the shipped harness. Every query has a small persistent ledger entry and an upstream evidence path; expensive remote work does not exist to restart or checkpoint. File hashes pin the consumed source JSON. Datasets, license/revision details, models, hardware classes and cost equations are in `README.md`.

What did not work or was unavailable: LongMemEval's entire full-standard baseline did not fit; RAG indexing time and embedding token usage were not recorded; LongMemEval's cached preparation mixes indexing and retrieval; four anonymous Cognee ingestion calls cannot be assigned uniquely between its N=2 histories. The four-system analysis resolves example-alias contamination by using actual user payloads and speaker labels from the source histories; it has no ambiguous ingestion calls across N=4 histories. The original Cognee accounting is unchanged: its four ambiguous calls are counted once in the pooled total, with per-history bounds. Hindsight decision latency and sleep-time cost are unreproduced. The four-system cohort has only N=4 independent LoCoMo histories, so its bootstrap intervals cannot establish broad population precision; the preserved Cognee cohort has N=2 histories and no population interval. Failed/superseded setup attempts are excluded, so costs do not include the full experimental recovery effort.

The seconds model is explicitly conditional and partial: the four-system cohort (N=123 paired questions, N=4 histories) gives Mem0 Q=5,698 and Graphiti Q=195,261, with RAG unavailable. The preserved five-system cohort including Cognee (N=58 paired questions, N=2 histories) gives Mem0 Q=7,000, Graphiti Q=15,904 and no eventual Cognee saving, with RAG unavailable. It includes recorded ingestion elapsed and answer-call elapsed, excludes retrieval, and cannot establish total compute or end-to-end performance. It should not be quoted as a production break-even figure.

Cleanup confirmed in an unpublished raw log: no task processes, containers, scratch, tunnels, volumes or downloads were created or retained. Before/after `df -h` and task-process listings are saved. All generated files remain under `benchmarks/cost/`; no source chapters or other benchmark files were edited, and no commit was made.

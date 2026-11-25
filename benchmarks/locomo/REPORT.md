# LoCoMo editor report

Final partial run: **N=67 matched questions**, represented conversations [0, 1, 3], with the same IDs for all five systems. The all-320 baselines and the N=40 pilot are separate results.

## Published and local comparison

| System | Published mean ± SD (%) | Local correct / N (accuracy) | Local 95% Wilson interval |
|---|---:|---:|---|
| Full context | 77.16 ± 5.21 | 39/67 (58.2%) | 46.3% to 69.3% |
| Plain RAG | 78.31 ± 5.75 | 34/67 (50.7%) | 39.1% to 62.3% |
| Mem0 OSS | 81.08 ± 3.19 | 33/67 (49.3%) | 37.7% to 60.9% |
| Graphiti | 56.03 ± 5.56 | 22/67 (32.8%) | 22.8% to 44.7% |
| Cognee | 55.27 ± 3.60 | 39/67 (58.2%) | 46.3% to 69.3% |

Published values are means and standard deviations across ten conversations, from a 1,540-question eligible pool before the paper's exclusions. They are not confidence intervals. Local values are question-weighted accuracies on identical completed question IDs. Wilson intervals are descriptive, ignore shared-conversation dependence and judge error, and do not establish production performance. Completion order can change the category mix of a partial final block.

The local point estimates do not reproduce the published blanket ordering of both graph systems below full context, RAG and Mem0. This comparison cannot isolate the memory representation as the cause; models, retrieval budgets and framework settings differ. The requested four-history matched cohort was not completed. This remains an exploratory result and cannot adjudicate the graph-versus-vector claim.

| Baseline, all ten conversations | Correct / N (accuracy) | 95% Wilson interval |
|---|---:|---|
| Full context | 180/320 (56.3%) | 50.8% to 61.6% |
| Plain RAG | 165/320 (51.6%) | 46.1% to 57.0% |

## Aggregation sensitivity

| System | Published macro mean ± SD (%) | Local matched macro mean ± sample SD (%) |
|---|---:|---:|
| Full context | 77.16 ± 5.21 | 63.43 ± 13.91 |
| Plain RAG | 78.31 ± 5.75 | 47.90 ± 12.50 |
| Mem0 OSS | 81.08 ± 3.19 | 52.78 ± 12.73 |
| Graphiti | 56.03 ± 5.56 | 34.91 ± 9.73 |
| Cognee | 55.27 ± 3.60 | 60.70 ± 7.04 |

Local macro values weight each represented conversation equally, using only the matched questions within it. The local SD uses the sample convention and is not a confidence interval. The main table uses question-weighted accuracy so its counts and Wilson intervals remain explicit.

## Matched per-category scores

| System | Category | Correct / N (accuracy) | 95% Wilson interval |
|---|---|---:|---|
| Full context | Multi-hop | 10/19 (52.6%) | 31.7% to 72.7% |
| Full context | Temporal | 10/18 (55.6%) | 33.7% to 75.4% |
| Full context | Open-domain | 6/12 (50.0%) | 25.4% to 74.6% |
| Full context | Single-hop | 13/18 (72.2%) | 49.1% to 87.5% |
| Plain RAG | Multi-hop | 5/19 (26.3%) | 11.8% to 48.8% |
| Plain RAG | Temporal | 9/18 (50.0%) | 29.0% to 71.0% |
| Plain RAG | Open-domain | 9/12 (75.0%) | 46.8% to 91.1% |
| Plain RAG | Single-hop | 11/18 (61.1%) | 38.6% to 79.7% |
| Mem0 OSS | Multi-hop | 8/19 (42.1%) | 23.1% to 63.7% |
| Mem0 OSS | Temporal | 8/18 (44.4%) | 24.6% to 66.3% |
| Mem0 OSS | Open-domain | 7/12 (58.3%) | 32.0% to 80.7% |
| Mem0 OSS | Single-hop | 10/18 (55.6%) | 33.7% to 75.4% |
| Graphiti | Multi-hop | 4/19 (21.1%) | 8.5% to 43.3% |
| Graphiti | Temporal | 4/18 (22.2%) | 9.0% to 45.2% |
| Graphiti | Open-domain | 7/12 (58.3%) | 32.0% to 80.7% |
| Graphiti | Single-hop | 7/18 (38.9%) | 20.3% to 61.4% |
| Cognee | Multi-hop | 9/19 (47.4%) | 27.3% to 68.3% |
| Cognee | Temporal | 12/18 (66.7%) | 43.7% to 83.7% |
| Cognee | Open-domain | 7/12 (58.3%) | 32.0% to 80.7% |
| Cognee | Single-hop | 11/18 (61.1%) | 38.6% to 79.7% |

Per-category Wilson intervals are in `results/full/matched-summary.json`. The strict whole-conversation sensitivity comparison uses N=58 and conversations [0, 1].

## Coverage and ingestion cost

| Conversation index | Preselected questions | Matched completed questions |
|---|---:|---:|
| 0 | 34 | 34 |
| 1 | 24 | 24 |
| 2 | 32 | 0 |
| 3 | 33 | 9 |
| 4 | 34 | 0 |
| 5 | 31 | 0 |
| 6 | 33 | 0 |
| 7 | 34 | 0 |
| 8 | 34 | 0 |
| 9 | 31 | 0 |

| Conversation index | Sessions / turns | Mem0 minutes | Graphiti minutes | Cognee minutes |
|---|---:|---:|---:|---:|
| 0 | 19 / 419 | 29.3 | 148.8 | 67.5 |
| 1 | 19 / 369 | 25.8 | 37.6 | 27.8 |
| 2 | 32 / 663 | 39.6 | 110.8 | Failed; 67.4 min attempted |
| 3 | 29 / 629 | 36.6 | 87.7 | 64.1 |

These are ingestion wall times, including framework initialization and waiting on the shared model host, excluding retrieval, answering and judging. Recovered conversations include failed-pass and repair time; Graphiti conversation 0 also includes substantial scheduling delays; its earlier discarded pre-scoring configuration is recorded separately. Cognee conversation 0 includes the successful 38.6-second first-session preflight that was reused. Incomplete rows show elapsed wall time from first ingestion start through stopping; they are not completed-ingestion times. They are operational observations, not controlled cross-system throughput or dollar-cost measurements.

Suggested book wording: In our local setup, ingesting one matched conversation history took 25.8 to 36.6 minutes for Mem0, 37.6 to 148.8 minutes for Graphiti, 27.8 to 67.5 minutes for Cognee. These wall times include retries and waiting on a shared model host, so they are operational observations rather than controlled throughput measurements.

## Judge check

A random audit of 40 matched judged items, seed 20261123 and two items per system/category, agreed on 32/40 (80.0%); 95% Wilson interval 65.2% to 89.5%. The implementation agent used the same generous topic-match and absolute-date rubric, reading a shuffled presentation of questions, original references, answers and source evidence with both system identities and majority labels hidden, then joined the labels afterward. The pre-review rubric is in `manual-audit-rubric.json`. Final reviews were fresh; earlier wide-plan reviews were archived without reuse. This is an agent manual audit, not independent human validation. Main scores were not corrected from this audit. The three benchmark votes use the same temperature-zero judge and are not independent validation.

The fixed plan, all 40 manual labels/reasons and joined majority decisions are in `results/full/manual-audit-plan.json` and `manual-audit.json`. The earlier wide-plan reviews remain separately archived and do not inflate this denominator.

## Book figure inventory

Quotes retain the printed wording and figures except attribution names replaced by `[study authors]` to meet the artifact privacy rule. Each source snapshot records its original-paragraph SHA256 for exact matching. The earlier pilot snapshot is historical; some source-quality wording was already corrected in the later snapshot. Suggested wording covers only the relevant LoCoMo claim, not unrelated benchmark or Chapter 20 fixture content.

### 17-security-eval-ops.html (Expanded-run snapshot)

> LoCoMo (2024) Ten long conversations with question answering, event summarization and dialogue tasks. 19 Not a deletion or poisoning test. An independent audit reports incorrect reference answers. The official issue thread records judge inconsistencies and the maintainers' later acknowledgment of data-quality concerns (see Chapter 16 for the thread). 20

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.

### 17-security-eval-ops.html (Expanded-run snapshot)

> Mem0's LoCoMo scores are vendor results. 26 In [study authors]'s independent testbed, Mem0, plain RAG and full context scored 77 to 81%, while the graph systems Graphiti and Cognee scored 55 to 56%, which the authors attribute to incomplete retrieval. 27

Source: [cited source](https://arxiv.org/html/2601.07978v5)

Local correspondence: The matched five-system table above.

Suggested wording, at most two sentences:

The independent study reports 77 to 81% for full context, RAG and Mem0, and 55 to 56% for Graphiti and Cognee. Our local Qwen2.5-14B comparison on 67 matched questions across 3 conversations scored full context 58.2%, plain RAG 50.7%, Mem0 OSS 49.3%, Graphiti 32.8%, Cognee 58.2%, using different models and settings; the planned matched coverage was not reached, so this remains exploratory.

### 17-security-eval-ops.html (Expanded-run snapshot)

> One study found a Mem0-style system cheaper after about ten turns at 100,000-token context with caching, while long context was more accurate on LongMemEval and LoCoMo. 32 The crossover is specific to that workload. Budget for memory only when repeated read savings repay extraction, storage and maintenance.

Source: [cited source](https://arxiv.org/html/2603.04814)

Local correspondence: No cost-crossover experiment. Ingestion wall times are recorded separately; retain unrelated Chapter 20 fixture figures.

Suggested wording, at most two sentences:

The cited cost study reports a crossover after about ten turns at 100,000-token context with caching for its workload. Our LoCoMo run measures QA accuracy and ingestion wall time and does not reproduce that cost crossover.

### 14-knowledge-graphs.html (Expanded-run snapshot)

> 55 to 56% Graphiti and Cognee on LoCoMo in [study authors]'s independent testbed, against 77 to 81% for Mem0, RAG and full context. The authors blame incomplete retrieval, not weak reasoning. 20 Independent paper

Source: [cited source](https://arxiv.org/html/2601.07978v5)

Local correspondence: The matched five-system table above.

Suggested wording, at most two sentences:

The independent study reports 77 to 81% for full context, RAG and Mem0, and 55 to 56% for Graphiti and Cognee. Our local Qwen2.5-14B comparison on 67 matched questions across 3 conversations scored full context 58.2%, plain RAG 50.7%, Mem0 OSS 49.3%, Graphiti 32.8%, Cognee 58.2%, using different models and settings; the planned matched coverage was not reached, so this remains exploratory.

### 14-knowledge-graphs.html (Expanded-run snapshot)

> 75.14% Graphiti on LoCoMo in Zep's own counter-evaluation, as reported by the same paper. 20 Vendor claim

Source: [cited source](https://arxiv.org/html/2601.07978v5)

Local correspondence: Graphiti local figure only; the vendor configuration is not reproduced.

Suggested wording, at most two sentences:

The independent paper cites Zep's counter-evaluation reporting 75.14% for Graphiti. Our local Graphiti configuration scored 22/67 (32.8%) and does not reproduce that vendor configuration.

### 14-knowledge-graphs.html (Expanded-run snapshot)

> 74.0% Letta Filesystem with gpt-4o-mini and grep-style tools on LoCoMo. 21 Vendor claim

Source: [cited source](https://www.letta.com/blog/benchmarking-ai-agent-memory)

Local correspondence: Not tested.

Suggested wording, at most two sentences:

Letta reports 74.0% for its filesystem agent on LoCoMo with GPT-4o-mini. Our local five-system comparison did not test that agent or its tools.

### 14-knowledge-graphs.html (Expanded-run snapshot)

> Zep and Mem0 dispute each other's scores, and an independent audit reports incorrect reference answers in LoCoMo. 31 The official issue thread records judge inconsistencies and the maintainers' later acknowledgment of data-quality concerns. 28 Rerun a benchmark on your own data before choosing a system. Chapter 17 covers these benchmarks and workload-specific evaluation.

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.

### 14-knowledge-graphs.html (Expanded-run snapshot)

> snap-research/locomo issue 23 on wrong ground-truth answers (2025-10-15) (secondary) https://github.com/snap-research/locomo/issues/23

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.

### 13-memory-frameworks.html (Expanded-run snapshot)

> Mem0 reports LoCoMo 92.5 and LongMemEval 94.4 for its managed April 2026 stack, with a top-200 retrieval budget. These are vendor claims , not measurements of the open-source recipe. Its public harness defaults to GPT-4o for the answerer and the judge, while its separate OSS model-comparison table uses GPT-5 for both, so record the actual run configuration instead of assuming either default produced the headline scores. A score depends on retrieval depth, extraction model, answerer and judge, so none is a cross-vendor ranking. 5 , 7

Source: [cited source](https://github.com/mem0ai/memory-benchmarks)

Local correspondence: Mem0 OSS is a different configuration; the quoted LongMemEval 94.4 is outside this LoCoMo task.

Suggested wording, at most two sentences:

Mem0 reports 92.5 on LoCoMo for its managed April 2026 stack with top-200 retrieval. Our open-source local Mem0 configuration scored 33/67 (49.3%) with top-20 retrieval and a different answerer and judge, so it does not reproduce the managed stack.

### 18-choosing.html (Expanded-run snapshot)

> Pick vectors when questions are local lookups and facts are short. An independent test scored Mem0, retrieval and full context at 77 to 81% on LoCoMo, and Graphiti and cognee at 55 to 56%. 10

Source: [cited source](https://arxiv.org/html/2601.07978v5)

Local correspondence: The matched five-system table above.

Suggested wording, at most two sentences:

The independent study reports 77 to 81% for full context, RAG and Mem0, and 55 to 56% for Graphiti and Cognee. Our local Qwen2.5-14B comparison on 67 matched questions across 3 conversations scored full context 58.2%, plain RAG 50.7%, Mem0 OSS 49.3%, Graphiti 32.8%, Cognee 58.2%, using different models and settings; the planned matched coverage was not reached, so this remains exploratory.

### 16-frontier.html (Expanded-run snapshot)

> Almost every number here comes from the paper's own authors, on benchmarks they chose, often against baselines they ran. An independent audit reports incorrect reference answers in LoCoMo, and the official issue thread records judge inconsistencies and the maintainers' later acknowledgment of data-quality concerns, so a single score on it proves little until someone else reruns it (Chapter 17). 74 1

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.

### 16-frontier.html (Expanded-run snapshot)

> Prototype MemOS and MemoryOS manage memory as schedulable tiers. Both report state-of-the-art LoCoMo results. 48 , 49 Mem0, the shipped library of the three, reported a 26% relative gain over OpenAI's memory in its 2025 paper (Chapter 13 has its current design). 50 All three are self-reported.

Source: [cited source](https://arxiv.org/html/2504.19413)

Local correspondence: Absolute Mem0 OSS accuracy only; no relative comparison to OpenAI memory.

Suggested wording, at most two sentences:

Mem0's 2025 paper reports a 26% relative gain over OpenAI's memory. Our local Mem0 configuration scored 33/67 (49.3%) and did not include OpenAI's memory, so it cannot test that relative gain.

### 16-frontier.html (Expanded-run snapshot)

> Saturated, self-reported benchmarks. LoCoMo's reference answers are disputed (Chapter 17), few papers test on MemoryAgentBench and BEAM together, and one action suite is run by a memory vendor.

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.

### 16-frontier.html (Expanded-run snapshot)

> Snap Research, LoCoMo issue 23 on wrong ground-truth answers (2025-10-15) (secondary) https://github.com/snap-research/locomo/issues/23

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.

### 17-security-eval-ops.html (Earlier pilot snapshot)

> LoCoMo (2024) Ten long conversations with question answering, event summarization and dialogue tasks. 19 Not a deletion or poisoning test. An external audit and a maintainer issue document wrong ground-truth answers. 20

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.

### 14-knowledge-graphs.html (Earlier pilot snapshot)

> Zep and Mem0 dispute each other's scores, and LoCoMo itself has wrong ground-truth answers. 28 Rerun a benchmark on your own data before choosing a system. Chapter 17 covers these benchmarks and workload-specific evaluation.

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.

### 18-choosing.html (Earlier pilot snapshot)

> Pick memory when history outgrows the window. The same study found memory cheaper after about ten turns at 100K context. 26 Chapter 20 measured the effect on a small fixture: 99 prompt tokens with no memory, 226 with recall and 560 with the full seed history.

Source: [cited source](https://arxiv.org/html/2603.04814)

Local correspondence: No cost-crossover experiment. Ingestion wall times are recorded separately; retain unrelated Chapter 20 fixture figures.

Suggested wording, at most two sentences:

The cited cost study reports a crossover after about ten turns at 100,000-token context with caching for its workload. Our LoCoMo run measures QA accuracy and ingestion wall time and does not reproduce that cost crossover.

### 16-frontier.html (Earlier pilot snapshot)

> Almost every number here comes from the paper's own authors, on benchmarks they chose, often against baselines they ran. An October 2025 issue documents wrong ground-truth answers in LoCoMo, so a single score on it proves little until someone else reruns it (Chapter 17). 1

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.

### 16-frontier.html (Earlier pilot snapshot)

> Saturated, self-reported benchmarks. LoCoMo has documented wrong answers (Chapter 17), few papers test on MemoryAgentBench and BEAM together, and one action suite is run by a memory vendor.

Source: [cited source](https://github.com/snap-research/locomo/issues/23)

Local correspondence: Source audit below; original reference answers retained.

Suggested wording, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.


## Label-error source audit

The earlier Chapter 16 sentence printed: “An October 2025 issue documents wrong ground-truth answers in LoCoMo, so a single score on it proves little until someone else reruns it (Chapter 17).” The October 15, 2025 [issue 23 opening post](https://github.com/snap-research/locomo/issues/23) concerns judge inconsistencies, including subset/superset answers and unsupported specificity; it is not itself a ground-truth audit. A [February 17, 2026 maintainer response](https://github.com/snap-research/locomo/issues/23#issuecomment-3916421856) later acknowledges separately reported data-quality concerns. The current book-source inventory already distinguishes these points, although source-list titles should also describe the thread accurately.

For direct wrong-label evidence, cite [issue 27](https://github.com/snap-research/locomo/issues/27) and the [independent audit report](https://github.com/dial481/locomo-audit/blob/9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/AUDIT_REPORT.md). That audit reports 99 score-related errors among 1,540 eligible questions (6.4%, including 13 ambiguous/debatable cases), plus 57 citation-only issues, using Claude Opus 4.6 with human review. We verified what the sources report, not all their proposed corrections, and did not apply them to the scores. The original 320-question sample overlaps 41 flagged items: 23 score-related and 18 citation-only; exact overlap is in `results/full/audit-overlap.json`.

Suggested book wording: The October 2025 LoCoMo issue documents inconsistent LLM judging, rather than a ground-truth audit. A separate audit reports 99 score-related issues among 1,540 eligible questions, including 13 ambiguous or debatable cases.

## Method and limits

The original target is 320 questions, 80 in each category 1 through 4, across all ten conversations. Seed 20261122: sample up to eight per conversation/category, then uniformly fill each category to 80 from its unselected questions. Open-domain questions are 25% of the planned local sample but only 96/1,540 (6.2%) of the eligible dataset. The fixed conversation order is 0 through 9 in pairs; each pair runs Mem0, Graphiti and Cognee before widening. Within the second pair, a freed Graphiti slot can begin Cognee for that completed conversation while Graphiti finishes the other. A later increase from two to three native request slots, sharing the same model weights and preserving 64K per slot, also overlaps Cognee conversation 2 ingestion with its unfinished Graphiti history. Memory pressure after that restart was normal with 57% free. Duplicate-store guards preserve one writer per system/conversation. The final matched subset is the intersection of questions with a saved answer and all three votes in every system at the fixed stopping time, with no outcome-based inclusion. A whole-conversation sensitivity comparison is also retained. Based only on observed execution times, later admission was capped at conversation index 3; the model deadline was not extended. The final cohort therefore reflects completed cases in the admitted histories, rather than a new random sample of the full dataset.

The paper uses GPT-4o-mini and text-embedding-3-small, a tool coordinator, unmasked names, a different question distribution and per-conversation aggregation. This run uses one Qwen2.5-14B-Instruct Q4_K_M model for extraction, answering and three-call majority judging, temperature zero, with a configured 64K per-slot YaRN window and q8 KV cache. CPU embeddings use all-MiniLM-L6-v2, 384 dimensions and its 256-token input limit. Mem0 2.2.1 uses eight individual messages per add call, session-date anchoring and local Qdrant semantic search (threshold 0.1, no reranking or optional BM25), with a provider adapter that wraps literal string memory entries as text objects; Graphiti 0.31.2 uses Neo4j and current-session extraction with native graph resolution and retrieval, splitting a session by turns after bounded output-length failures; Cognee 1.0.9 uses real cognify with Ladybug, LanceDB, 1,600-token chunks and GRAPH_COMPLETION context retrieval. Splitting preserves every source turn but changes the extraction context and can change the facts or relations extracted. All retrieval limits are 20 native items, which are turns, facts, edges or chunks rather than equal token budgets. The audited comparison repository pins Mem0 2.0.2 and Graphiti 0.29; Cognee 1.0.9 matches its version but uses different stores and settings here. The local provider also marshals completed embedded JSON function calls without changing arguments and retries structured length failures up to 8,192 tokens. Answer and judge prompts are paraphrased rather than exact paper prompts.

Names are consistently aliased in conversation, question and reference text. The privacy NER pass reads those texts only to build the alias dictionary; reference facts and evidence annotations are excluded from all stores. This can remove useful world-knowledge associations. One missed misspelled speaker reference was corrected and both affected baseline answers and three votes were rerun before any memory system reached that conversation. Later archival masking removes regenerated names from saved response text, retains original hashes and changes no effective request, reference, vote label or score.

The run uses the configured 64K window checked by actual tokenizer counts; no conversation history is silently dropped. The paper's full eligible set, coordinator, hosted answerer/judge, embeddings, aggregation, stores and network scenarios are not reproduced exactly. Shared histories, unequal native retrieval units, completion-based coverage and local judge errors limit ranking claims. Neither latency nor dollar cost is compared to the paper.

## Technical failures and repair

A Mem0 extraction returned a mixed object/string memory array, which its native parser rejected before embedding or persisting that batch. The provider adapter wraps only the string entries as text objects, retaining their literal content and all valid object fields; the raw response and checkpointed recovery are retained.

The initial Graphiti configuration re-extracted previous sessions and hit an output limit. Its 70-node task graph was reset before any Graphiti question was scored; the excluded checkpoints and failed responses remain archived. The final adapter extracts from the current session, then resolves/retrieves against the accumulated graph. Structured extraction length failures retain their actual 4,096/8,192/16,384-token attempts and trigger recursive session splitting while preserving every turn and original timestamp. After the first 58 Graphiti questions were complete, edge extraction was capped at 8,192 tokens before splitting; other schemas initially retained 16,384. A later entity-extraction length failure extended the 8,192 cap and the same source-preserving split fallback to all structured schemas, as recorded in `structured-output-cap-change.json`. No completed historical 16,384-token structured response was discarded. The change preceded all later Graphiti question scoring and is recorded in `edge-output-cap-change.json`. The first oversized session was repaired as two 12-turn episodes within the bounded setup effort. Subsequent normal ingestion/scoring retained the original overall deadline. Native graph retrieval was used for both graph systems. An external turn interruption later terminated CPU processes. Cognee conversation 2 had a corrupted Ladybug write-ahead log; its unscored store was rebuilt from the complete history, reusing cached actual model responses where requests matched. The damaged store remained task-scoped until cleanup, and its earlier ingestion checkpoints are archived separately. Truncated tool outputs also produced missing-tool-call validation errors. Tool schemas now receive the same bounded 4,096-to-8,192 length retry as other structured extraction; only a completed plain response without a tool call additionally retries required tool selection. Completed function calls encoded as explicit name/arguments JSON inside message content are marshaled into the API tool_calls field with arguments unchanged and native schema validation still applied; original responses and adapter hashes are retained. Valid existing tool responses remain unchanged. Final native Cognee pipeline status must be completed before questions enter the reported comparison; an intermediate error can be recovered by a later cognify pass over all pending data. These events, the resume and final completion status are recorded in `turn-interruption-resume.json`, `cognee-wal-rebuild.json`, `required-tool-retry-change.json` and the coverage table. The deadline was not extended.

A controlled proxy restart increased the HTTP request allowance from two to four while retaining one model and two native slots, preventing requests queued for one slot from starving the other. All per-question answers and votes were preserved. Later, a third native slot and an HTTP allowance of six let Cognee ingest the same admitted history while Graphiti finished it, using one shared model weightset; `three-slot-change.json` records the context and memory checks. Earlier source-hash snapshots describe their execution phase; final code hashes and the recorded change files document later technical corrections. No setting was selected to approach a published score.

| Backend / conversation | Retained technical event | Final status |
|---|---|---|
| graphiti / 1 | Structured output length limit | Superseded before scoring (24/24) |
| graphiti / 0 | Structured output length limit | Recovered; all selected questions scored (34/34) |
| mem0 / 3 | Mixed memory object/string schema | Recovered; all selected questions scored (33/33) |
| cognee / 2 | Corrupted Ladybug WAL after external interruption | Incomplete; inspect failure evidence (0/32) |

These events are retained for diagnosis; incomplete ingestion is not silently converted into an answer or a correct label.

## Evidence and cleanup

- `results/full/selection.json`, `conversations.json`, `manifest.json`: selected IDs, exact transformed input, revision, license and seeds.
- `results/full/items/`, `raw-calls/`, `ingest/`, `ingestion-times/`: answers, contexts, all votes, real extraction calls, ingestion checkpoints and timings.
- `results/full/verification.json`, `verification-before-privacy.json`: score reconstruction, input alignment, canonical request hashes and distinct judge responses.
- `results/full/privacy-correction.json`, `privacy-export.json`: the one corrected alias and excluded preliminary records, plus archival response masking and original hashes.
- `results/full/book-citations.json`, `results/book-citations.json`, `results/published-evidence.json`: exact book/source snapshots and source audit.
- `results/full/cleanup.json`: before/after disk and process listings, memory-pressure log and resource absence checks.

Cleanup is confirmed: the owned model server, guard, tunnel, proxy and task containers stopped, and both scratch folders, downloaded model and caches were removed. `results/full/cleanup.json` contains before/after disk and process evidence, pressure logs and absence checks.

Unresolved coverage: 253 of the original 320 questions are outside the final shared denominator. The matched sample and completed-case intervals are printed plainly; incomplete results are retained, and the pilot is not substituted. The agent manual audit does not provide independent human validation.

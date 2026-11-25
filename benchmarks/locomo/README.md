# LoCoMo local comparison

**Final partial run: 67 matched questions across 3 conversation histories.** There are 2 complete question blocks and 9 questions from partial blocks. Full context and plain RAG additionally cover all 320 preselected questions across all ten conversations. The earlier N=40 run remains clearly labeled as a pilot in `results/local/`, [PILOT_README.md](PILOT_README.md) and [PILOT_REPORT.md](PILOT_REPORT.md).

LoCoMo measures long-conversation question answering. The metric here is local LLM-judged accuracy, following the independent comparison, rather than the original 2024 token F1 metric. This experiment uses actual timestamped turns and supplied image captions/queries, without annotated summaries or QA evidence in any memory store.

## Matched results

| System | Published mean ± SD (%) | Local correct / N (accuracy) | Local 95% Wilson interval |
|---|---:|---:|---|
| Full context | 77.16 ± 5.21 | 39/67 (58.2%) | 46.3% to 69.3% |
| Plain RAG | 78.31 ± 5.75 | 34/67 (50.7%) | 39.1% to 62.3% |
| Mem0 OSS | 81.08 ± 3.19 | 33/67 (49.3%) | 37.7% to 60.9% |
| Graphiti | 56.03 ± 5.56 | 22/67 (32.8%) | 22.8% to 44.7% |
| Cognee | 55.27 ± 3.60 | 39/67 (58.2%) | 46.3% to 69.3% |

Published values are means and standard deviations across ten conversations, from a 1,540-question eligible pool before the paper's exclusions. They are not confidence intervals. Local values are question-weighted accuracies on identical completed question IDs. Wilson intervals are descriptive, ignore shared-conversation dependence and judge error, and do not establish production performance. Completion order can change the category mix of a partial final block.

The local point estimates do not reproduce the published blanket ordering of both graph systems below full context, RAG and Mem0. This comparison cannot isolate the memory representation as the cause; models, retrieval budgets and framework settings differ. The requested four-history matched cohort was not completed. This remains an exploratory result and cannot adjudicate the graph-versus-vector claim.

## Baselines on all 320 questions

| Baseline, all ten conversations | Correct / N (accuracy) | 95% Wilson interval |
|---|---:|---|
| Full context | 180/320 (56.3%) | 50.8% to 61.6% |
| Plain RAG | 165/320 (51.6%) | 46.1% to 57.0% |

## Per-category matched scores

| System | Multi-hop | Temporal | Open-domain | Single-hop |
|---|---|---|---|---|
| Full context | 10/19 (52.6%) | 10/18 (55.6%) | 6/12 (50.0%) | 13/18 (72.2%) |
| Plain RAG | 5/19 (26.3%) | 9/18 (50.0%) | 9/12 (75.0%) | 11/18 (61.1%) |
| Mem0 OSS | 8/19 (42.1%) | 8/18 (44.4%) | 7/12 (58.3%) | 10/18 (55.6%) |
| Graphiti | 4/19 (21.1%) | 4/18 (22.2%) | 7/12 (58.3%) | 7/18 (38.9%) |
| Cognee | 9/19 (47.4%) | 12/18 (66.7%) | 7/12 (58.3%) | 11/18 (61.1%) |

Per-category Wilson intervals, exact IDs and conversation coverage are in matched-summary.json. The whole-conversation sensitivity subset has N=58; its five-system results and matched per-conversation macro means/sample SDs are in the same file.

## Reproduce

With the pinned model already served through the task-local endpoint on port 39700, run from the repository root:

```bash
MEMORY_SAMPLE_IDS=benchmarks/locomo/results/full/matched-summary.json MAX_MEMORY_CONVERSATION=3 bash benchmarks/locomo/run_full.sh
```

The command requires `uv` and Docker, installs the pinned CPU/framework environments and resumes persisted answers and votes. `LAB_DIR` defaults to `/var/tmp/membench-locomo`, `OUT_DIR` to `benchmarks/locomo/results/full`, and the framework `BASE_URL` defaults to `http://localhost:39701/v1`; the local proxy forwards generation to localhost port 39700. Completed output is reused. Use fresh output and lab directories for a new experiment. Exact model command, weights SHA256, revision, protocol and operational history are in [FULL_RUN.md](FULL_RUN.md); dependencies are pinned in [requirements-full-lock.txt](requirements-full-lock.txt) and [requirements-graph-lock.txt](requirements-graph-lock.txt).

The official data revision is `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`, SHA256 `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`, licensed CC BY-NC 4.0. Sources: [official LoCoMo repository](https://github.com/snap-research/locomo), [independent comparison, version 5](https://arxiv.org/html/2601.07978v5), and [source audit](REPORT.md).

Generation runs on Apple M3 Ultra, 96 GB. Embeddings, stores, orchestration and scoring run on a 32-thread x86 CPU. The NVIDIA GPU is not used. The task server stops at macOS warning/critical pressure and waits for normal pressure and at least 40% available memory before restarting; a 20-minute warning pauses the run rather than abandoning it. The wall-clock deadline persists across restarts.

## Sampling and differences

The original target is 320 questions, 80 in each category 1 through 4, across all ten conversations. Seed 20261122: sample up to eight per conversation/category, then uniformly fill each category to 80 from its unselected questions. Open-domain questions are 25% of the planned local sample but only 96/1,540 (6.2%) of the eligible dataset. The fixed conversation order is 0 through 9 in pairs; each pair runs Mem0, Graphiti and Cognee before widening. Within the second pair, a freed Graphiti slot can begin Cognee for that completed conversation while Graphiti finishes the other. A later increase from two to three native request slots, sharing the same model weights and preserving 64K per slot, also overlaps Cognee conversation 2 ingestion with its unfinished Graphiti history. Memory pressure after that restart was normal with 57% free. Duplicate-store guards preserve one writer per system/conversation. The final matched subset is the intersection of questions with a saved answer and all three votes in every system at the fixed stopping time, with no outcome-based inclusion. A whole-conversation sensitivity comparison is also retained. Based only on observed execution times, later admission was capped at conversation index 3; the model deadline was not extended. The final cohort therefore reflects completed cases in the admitted histories, rather than a new random sample of the full dataset.

The paper uses GPT-4o-mini and text-embedding-3-small, a tool coordinator, unmasked names, a different question distribution and per-conversation aggregation. This run uses one Qwen2.5-14B-Instruct Q4_K_M model for extraction, answering and three-call majority judging, temperature zero, with a configured 64K per-slot YaRN window and q8 KV cache. CPU embeddings use all-MiniLM-L6-v2, 384 dimensions and its 256-token input limit. Mem0 2.2.1 uses eight individual messages per add call, session-date anchoring and local Qdrant semantic search (threshold 0.1, no reranking or optional BM25), with a provider adapter that wraps literal string memory entries as text objects; Graphiti 0.31.2 uses Neo4j and current-session extraction with native graph resolution and retrieval, splitting a session by turns after bounded output-length failures; Cognee 1.0.9 uses real cognify with Ladybug, LanceDB, 1,600-token chunks and GRAPH_COMPLETION context retrieval. Splitting preserves every source turn but changes the extraction context and can change the facts or relations extracted. All retrieval limits are 20 native items, which are turns, facts, edges or chunks rather than equal token budgets. The audited comparison repository pins Mem0 2.0.2 and Graphiti 0.29; Cognee 1.0.9 matches its version but uses different stores and settings here. The local provider also marshals completed embedded JSON function calls without changing arguments and retries structured length failures up to 8,192 tokens. Answer and judge prompts are paraphrased rather than exact paper prompts.

Names are consistently aliased in conversation, question and reference text. The privacy NER pass reads those texts only to build the alias dictionary; reference facts and evidence annotations are excluded from all stores. This can remove useful world-knowledge associations. One missed misspelled speaker reference was corrected and both affected baseline answers and three votes were rerun before any memory system reached that conversation. Later archival masking removes regenerated names from saved response text, retains original hashes and changes no effective request, reference, vote label or score.

## Ingestion time

| Conversation index | Sessions / turns | Mem0 minutes | Graphiti minutes | Cognee minutes |
|---|---:|---:|---:|---:|
| 0 | 19 / 419 | 29.3 | 148.8 | 67.5 |
| 1 | 19 / 369 | 25.8 | 37.6 | 27.8 |
| 2 | 32 / 663 | 39.6 | 110.8 | Failed; 67.4 min attempted |
| 3 | 29 / 629 | 36.6 | 87.7 | 64.1 |

These are ingestion wall times, including framework initialization and waiting on the shared model host, excluding retrieval, answering and judging. Recovered conversations include failed-pass and repair time; Graphiti conversation 0 also includes substantial scheduling delays; its earlier discarded pre-scoring configuration is recorded separately. Cognee conversation 0 includes the successful 38.6-second first-session preflight that was reused. Incomplete rows show elapsed wall time from first ingestion start through stopping; they are not completed-ingestion times. They are operational observations, not controlled cross-system throughput or dollar-cost measurements.

## Judge audit and evidence

A random audit of 40 matched judged items, seed 20261123 and two items per system/category, agreed on 32/40 (80.0%); 95% Wilson interval 65.2% to 89.5%. The implementation agent used the same generous topic-match and absolute-date rubric, reading a shuffled presentation of questions, original references, answers and source evidence with both system identities and majority labels hidden, then joined the labels afterward. The pre-review rubric is in `manual-audit-rubric.json`. Final reviews were fresh; earlier wide-plan reviews were archived without reuse. This is an agent manual audit, not independent human validation. Main scores were not corrected from this audit. The three benchmark votes use the same temperature-zero judge and are not independent validation.

Per-item answers, contexts and votes are under `results/full/items/`; effective requests, privacy-masked responses, token usage and hashes are under `results/full/raw-calls/`. verification.json reconstructs scores and verifies three distinct actual judge responses per scored item. manual-audit.json contains all 40 decisions and reasons. Original references remain unchanged, including externally flagged labels.

Cleanup is confirmed: the owned model server, guard, tunnel, proxy and task containers stopped, and both scratch folders, downloaded model and caches were removed. `results/full/cleanup.json` contains before/after disk and process evidence, pressure logs and absence checks.

The original 320-question five-system target has 253 questions outside the final matched denominator. Individual system totals and partial outputs remain in `summary.json`; no pilot score fills a missing expanded-run result. This run does not reproduce managed Mem0, the filesystem agent, vendor-relative gains, other prototype systems or the ten-turn cost crossover.

The reproduction command preserves the admitted memory-history scope, indices 0 through 3; both baselines still use all 320 questions. Fresh output directories otherwise default to all ten memory histories.

`MEMORY_SAMPLE_IDS` replays the exact final matched question IDs for the three memory systems, while both baselines retain all 320. Omit it to attempt the complete planned sample; use fresh output and lab directories for new inference. Original failed attempts and their costs remain in the archived evidence.

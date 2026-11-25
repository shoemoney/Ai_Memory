> **PILOT ONLY: 40 questions from one conversation. Not the expanded book result.**

# Editor report: LoCoMo

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

The independent source is arXiv 2601.07978 **version 5**, dated September 3, 2026. Version 1 studied a different, smaller configuration and does not support the book's five-system table. The current source reports full context 77.16%, RAG 78.31%, Mem0 81.08%, Graphiti 56.03%, and Cognee 55.27% (Table III). These are means of per-conversation rates; the accompanying ± values are standard deviations across conversations. The experiment starts from 1,540 unique questions in ten conversations and excludes reported multi-retrieval and overflow anomalies.

## Corresponding local figures

| System | Published | Local |
|---|---:|---:|
| Full context | 77.16% | 57.5% (23/40) |
| Plain RAG | 78.31% | 50.0% (20/40) |
| Mem0 OSS | 81.08% | 62.5% (25/40) |
| Graphiti | 56.03% | Not run |
| Cognee | 55.27% | Not run |

Local N is 40 questions, ten per category 1 through 4 from conversation index 0, seed 20261121. Every baseline sees the same sample, all 19 sessions and 419 turns, and Qwen2.5-14B-Instruct Q4_K_M as answerer and judge. Hardware classes are Apple M3 Ultra, 96 GB for model serving and a 32-thread x86 CPU for embeddings, storage, and scoring. The NVIDIA GPU was not used.

Differences from the paper include the local model and local MiniLM embedder, one judge instead of a three-call majority, paraphrased judging and answer prompts, no tool coordinator, pseudonymized names, equal category weighting, one conversation, eight-turn Mem0 ingestion batches, Mem0 2.2.1 with semantic-only Qdrant retrieval, embedded rather than containerized stores, no network shaping, and different hardware. Current comparison-repository requirements pin Mem0 2.0.2, so this is not a framework-version match either. Raw labels remain uncorrected. Wilson intervals in the README describe this fixed sample and do not establish cross-conversation or production performance.

This run cannot validate or refute the graph-versus-vector gap because no graph system was run. No graph result, managed-platform result, vendor-relative gain, filesystem-agent result, or cost crossover is claimed as reproduced.

## Book inventory and suggested wording

Quotes below preserve the book's wording and figures, except that personal names in attribution are replaced by `[study authors]` to comply with the task's file-content restriction. `results/book-citations.json` records the chapter and SHA256 of each original paragraph for exact matching. Citation numbers printed by the HTML are retained in quotes. Suggested replacements cover the LoCoMo claims only; retain unrelated LongMemEval and Chapter 20 fixture material.

### 17-security-eval-ops.html

> LoCoMo (2024) Ten long conversations with question answering, event summarization and dialogue tasks. 19 Not a deletion or poisoning test. An external audit and a maintainer issue document wrong ground-truth answers. 20

Source: https://arxiv.org/abs/2402.17753 and https://github.com/snap-research/locomo/tree/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376

Suggested replacement, at most two sentences:

LoCoMo contains ten long conversations; our local check used 40 questions from one conversation. An independent audit and the official issue thread document label and judge concerns, so we retained the original references and reported the limits.

### 17-security-eval-ops.html

> Mem0's LoCoMo scores are vendor results. 26 In [study authors]'s independent testbed, Mem0, plain RAG and full context scored 77 to 81%, while the graph systems Graphiti and Cognee scored 55 to 56%, which the authors attribute to incomplete retrieval. 27

Source: https://arxiv.org/html/2601.07978v5 (Tables III and comparative discussion)

Suggested replacement, at most two sentences:

The independent study reports 77.16% for full context, 78.31% for RAG, 81.08% for Mem0, 56.03% for Graphiti, and 55.27% for Cognee. On our 40-question local sample, full context scored 57.5% (23/40), RAG 50.0% (20/40), and Mem0 62.5% (25/40); we did not test a graph system.

### 17-security-eval-ops.html

> One study found a Mem0-style system cheaper after about ten turns at 100,000-token context with caching, while long context was more accurate on LongMemEval and LoCoMo. 32 The crossover is specific to that workload. Budget for memory only when repeated read savings repay extraction, storage and maintenance.

Source: https://arxiv.org/html/2603.04814

Suggested replacement, at most two sentences:

The cited cost study reports a crossover after about ten turns at 100,000-token context with caching. Our reduced LoCoMo experiment measures answer accuracy and does not reproduce that workload or cost crossover.

### 14-knowledge-graphs.html

> 55 to 56% Graphiti and Cognee on LoCoMo in [study authors]'s independent testbed, against 77 to 81% for Mem0, RAG and full context. The authors blame incomplete retrieval, not weak reasoning. 20 Independent paper

Source: https://arxiv.org/html/2601.07978v5 (Tables III and comparative discussion)

Suggested replacement, at most two sentences:

The independent study reports 77.16% for full context, 78.31% for RAG, 81.08% for Mem0, 56.03% for Graphiti, and 55.27% for Cognee. On our 40-question local sample, full context scored 57.5% (23/40), RAG 50.0% (20/40), and Mem0 62.5% (25/40); we did not test a graph system.

### 14-knowledge-graphs.html

> 75.14% Graphiti on LoCoMo in Zep's own counter-evaluation, as reported by the same paper. 20 Vendor claim

Source: https://arxiv.org/html/2601.07978v5 (Tables III and comparative discussion)

Suggested replacement, at most two sentences:

The independent paper cites a vendor counter-evaluation reporting 75.14% for Graphiti. We did not reproduce that vendor configuration, so it should remain clearly labeled as a vendor claim.

### 14-knowledge-graphs.html

> 74.0% Letta Filesystem with gpt-4o-mini and grep-style tools on LoCoMo. 21 Vendor claim

Source: https://www.letta.com/blog/benchmarking-ai-agent-memory

Suggested replacement, at most two sentences:

The filesystem-agent vendor reports 74.0% on LoCoMo with GPT-4o-mini. Our local experiment did not test that agent or its tools.

### 14-knowledge-graphs.html

> Zep and Mem0 dispute each other's scores, and LoCoMo itself has wrong ground-truth answers. 28 Rerun a benchmark on your own data before choosing a system. Chapter 17 covers these benchmarks and workload-specific evaluation.

Source: https://github.com/snap-research/locomo/issues/23 and https://github.com/dial481/locomo-audit

Suggested replacement, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo, and the official issue thread also records judge inconsistencies and later acknowledgment of data-quality concerns. Our local scores retain the original references and should be read with those limits.

### 13-memory-frameworks.html

> Mem0 reports LoCoMo 92.5 and LongMemEval 94.4 for its managed April 2026 stack, with a top-200 retrieval budget. These are vendor claims , not measurements of the open-source recipe. Its public harness defaults to GPT-4o for the answerer and the judge, while its separate OSS model-comparison table uses GPT-5 for both, so record the actual run configuration instead of assuming either default produced the headline scores. A score depends on retrieval depth, extraction model, answerer and judge, so none is a cross-vendor ranking. 5 , 7

Source: https://github.com/mem0ai/mem0 and https://github.com/mem0ai/memory-benchmarks

Suggested replacement, at most two sentences:

Mem0 reports 92.5 on LoCoMo for its managed April 2026 stack with a top-200 retrieval budget. Our open-source local configuration scored 62.5% (25/40) on 40 questions with top-20 retrieval, so it does not reproduce the managed result.

### 18-choosing.html

> Pick vectors when questions are local lookups and facts are short. An independent test scored Mem0, retrieval and full context at 77 to 81% on LoCoMo, and Graphiti and cognee at 55 to 56%. 10

Source: https://arxiv.org/html/2601.07978v5 (Tables III and comparative discussion)

Suggested replacement, at most two sentences:

The independent study reports 77.16% for full context, 78.31% for RAG, 81.08% for Mem0, 56.03% for Graphiti, and 55.27% for Cognee. On our 40-question local sample, full context scored 57.5% (23/40), RAG 50.0% (20/40), and Mem0 62.5% (25/40); we did not test a graph system.

### 18-choosing.html

> Pick memory when history outgrows the window. The same study found memory cheaper after about ten turns at 100K context. 26 Chapter 20 measured the effect on a small fixture: 99 prompt tokens with no memory, 226 with recall and 560 with the full seed history.

Source: https://arxiv.org/html/2603.04814

Suggested replacement, at most two sentences:

The cited cost study reports a crossover after about ten turns at 100,000-token context with caching. Our reduced LoCoMo experiment measures answer accuracy and does not reproduce that workload or cost crossover.

### 16-frontier.html

> Almost every number here comes from the paper's own authors, on benchmarks they chose, often against baselines they ran. An October 2025 issue documents wrong ground-truth answers in LoCoMo, so a single score on it proves little until someone else reruns it (Chapter 17). 1

Source: https://github.com/snap-research/locomo/issues/23 and https://github.com/dial481/locomo-audit

Suggested replacement, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo, and the official issue thread also records judge inconsistencies and later acknowledgment of data-quality concerns. Our local scores retain the original references and should be read with those limits.

### 16-frontier.html

> Prototype MemOS and MemoryOS manage memory as schedulable tiers. Both report state-of-the-art LoCoMo results. 48 , 49 Mem0, the shipped library of the three, reported a 26% relative gain over OpenAI's memory in its 2025 paper (Chapter 13 has its current design). 50 All three are self-reported.

Source: https://arxiv.org/html/2504.19413

Suggested replacement, at most two sentences:

Mem0's 2025 paper reports a 26% relative gain over OpenAI's memory. Our local Mem0 run scored 62.5% (25/40) on 40 questions and did not include OpenAI's memory, so it cannot test that relative gain.

### 16-frontier.html

> Saturated, self-reported benchmarks. LoCoMo has documented wrong answers (Chapter 17), few papers test on MemoryAgentBench and BEAM together, and one action suite is run by a memory vendor.

Source: https://github.com/snap-research/locomo/issues/23 and https://github.com/dial481/locomo-audit

Suggested replacement, at most two sentences:

An independent audit reports incorrect reference answers in LoCoMo, and the official issue thread also records judge inconsistencies and later acknowledgment of data-quality concerns. Our local scores retain the original references and should be read with those limits.

## Label-error source check

[Issue 23](https://github.com/snap-research/locomo/issues/23) was opened October 15, 2025. Its original post uses Qwen3-14B to describe inconsistent acceptance of answer subsets, supersets, and unsupported specificity. That opening post is not itself a ground-truth audit. Comments also explain that the original official benchmark uses F1 and did not standardize an LLM judge.

The full thread goes further. A [February 17, 2026 maintainer comment](https://github.com/snap-research/locomo/issues/23#issuecomment-3916421856) acknowledges separately reported data-quality problems and discusses a possible revision with fixes and a standard judge prompt. Therefore, the book's link is relevant, but attributing the wrong-label finding simply to an October 2025 issue hides the distinction between the opening complaint and the later acknowledgment.

For direct wrong-label evidence, cite [issue 27](https://github.com/snap-research/locomo/issues/27) and the [independent audit report](https://github.com/dial481/locomo-audit/blob/main/AUDIT_REPORT.md). The audit reports 99 score-corrupting errors among 1,540 non-adversarial questions (6.4%), plus 57 citation-only issues. It used Claude Opus 4.6 with human review; its 99 include 13 ambiguous or debatable cases. We verified what these sources state, not every audit judgment, and do not endorse its proposed theoretical ceiling as a measured scoring bound.

Six sampled items match that audit's flags: `c0-q2`, `c0-q23`, `c0-q32`, `c0-q66`, `c0-q94`, and `c0-q137`. They remain in all systems' denominators with their original gold answers. The sample was fixed before this overlap check, and no result was tuned toward the published values.

## Raw evidence and reproducibility

The executed benchmark code is `run.py`. The measured output is `results/local`; the wrapper now defaults to a fresh timestamped output and rejects a populated store so readers cannot overwrite evidence or contaminate a rerun. These wrapper safeguards do not change the executed benchmark code; `run.sh` synchronizes the pinned lock file and invokes it with the one command in `README.md`. `results/local/model-calls.jsonl` records requests, raw responses, finish reasons, timing, and token usage. `items.jsonl` records question IDs, references, answer text, retrieved evidence, and judge decisions. `selection.json` includes original-question hashes, and `indexed-conversation.json` is the exact transformed input. `ingest.jsonl` and `extracted-memories.json` show that Mem0 actually extracted and retrieved memories. `summary.json` contains the final counts and category totals. `verify.py` reconstructs those counts from the raw model responses and checks item alignment; `verification.json` records the result.

`results/published-evidence.json` records source URLs, source-download SHA256 values, dataset revision and license, reported figures, aggregation, and caveats. `results/sample-audit-overlap.json` records the external audit matches. Sources were fetched directly from the paper, official dataset repository, comparison repository, official issue API, audit repository, managed-platform README, and filesystem-agent vendor page.

## Failures, scope, and cleanup

The initial Mem0 listing used a legacy `limit` argument that this version ignored, so its first export contained only 20 memories. Retrieval still searched the full store. After scoring released the store lock, `export_memories.py` exported every persisted record with Qdrant scroll and required an exact ID-and-text match against the ADD log. The limited API response remains in `mem0-api-preview.json`; no answers or verdicts were regenerated for this export repair. The same export step is included in the documented one-command wrapper.

The first installed MLX command failed because of a Transformers registration incompatibility. A fully isolated MLX environment was then installed under the permitted temporary directory. Its startup was stopped immediately when macOS entered warning pressure; no benchmark answers were produced there. At the subsequent check, the pre-existing model service accounted for 73 GB total memory, 58 GB compressed. We do not attribute that service's growth to our startup, and we neither stopped nor reconfigured it.

All task files and the tunnel on that initial Mac were removed before moving to a newly authorized Mac of the same hardware class. On the replacement, llama.cpp served one modest Q4 model, bound only to localhost. A task-owned guard checked macOS pressure every five seconds and would stop only the task's model process on warning or critical pressure. Optional graph systems were not attempted; effort went into completing the three required paths, retaining evidence, and checking the source claims.

Final cleanup verification is recorded in an unpublished raw log. No containers were required. No commits were made, and no chapter was edited.

Cleanup confirmed: both model-host scratch directories and the CPU-host scratch directory are absent; task servers, guard process, tunnel, and port listeners are gone. No task containers remain. Disk and process proof is in an unpublished raw log, with structured status in an unpublished raw log; only `benchmarks/locomo/` was retained.

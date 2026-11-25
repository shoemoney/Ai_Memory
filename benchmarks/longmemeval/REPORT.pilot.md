# Editorial report: LongMemEval

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

Run date: 2026-11-21. This experiment uses 14 stratified questions from the official oracle-history split, not the standard long-history split. The saved chapter wording is in `results/book-claim-inventory.json`. No chapter file was edited.

| Local method | Correct / N | Accuracy | Descriptive 95% Wilson interval |
|---|---:|---:|---:|
| Full oracle context | 10/14 | 71.4% | 45.4% to 88.3% |
| BM25 RAG | 11/14 | 78.6% | 52.4% to 92.4% |
| Mem0 OSS | 8/14 | 57.1% | 32.6% to 78.6% |

| Stratum (N=2 each) | Full oracle context | BM25 RAG | Mem0 OSS |
|---|---:|---:|---:|
| abstention | 2/2 | 2/2 | 2/2 |
| knowledge-update | 1/2 | 2/2 | 1/2 |
| multi-session | 1/2 | 1/2 | 1/2 |
| single-session-assistant | 2/2 | 2/2 | 0/2 |
| single-session-preference | 1/2 | 0/2 | 1/2 |
| single-session-user | 2/2 | 2/2 | 2/2 |
| temporal-reasoning | 1/2 | 2/2 | 1/2 |


## Every relevant printed figure

### Chapter 13, `13-memory-frameworks.html`

Printed sentence: “Mem0 reports LoCoMo 92.5 and LongMemEval 94.4 for its managed April 2026 stack, with a top-200 retrieval budget.” Sources 5 and 7 point to the Mem0 repository and its memory-benchmarks repository. The repository explicitly distinguishes the managed platform's proprietary optimizations from the open-source SDK. The 92.5 figure is LoCoMo and is outside this task; the relevant LongMemEval figure is 94.4, and 200 is a retrieval-budget setting, not a score.

Local counterpart: 8/14 (57.1%), N=14, Mem0 OSS 0.1.118, top ten memories, Qwen3.5-9B-4bit answerer/extractor/judge, CPU MiniLM embeddings. This is neither the managed April 2026 implementation nor its full test setting. The managed stack's exact model configuration is not established by the README's headline table.

Suggested replacement, two sentences: “Mem0 reports 94.4% on LongMemEval for its managed April 2026 stack with a retrieval budget of 200; this is a vendor result. On 14 questions from the easier oracle-history split, our local Mem0 OSS setup scored 8/14 (57.1%) with a 9B model and a local judge, so the figures are not directly comparable.”

Evidence: `results/items.jsonl` rows with method `mem0-oss`; `results/memory-events.jsonl`; `results/memory-llm.jsonl`; `results/summary.json`; `results/manifest.json`. Published source: https://github.com/mem0ai/mem0 and https://github.com/mem0ai/memory-benchmarks, retrieved 2026-11-21. The source table also gives an old managed score of 67.8, but the inspected chapter does not print that number.

### Chapter 14, `14-knowledge-graphs.html`

Printed table row: “94.8% vs 93.4% Zep against MemGPT on Deep Memory Retrieval, plus up to 18.5% higher accuracy and 90% lower latency on LongMemEval. The Zep authors' numbers.” Source 22 is the Zep paper, arXiv:2501.13956.

The 94.8% and 93.4% figures belong to Deep Memory Retrieval, not LongMemEval, and are not reproduced here. The LongMemEval figures are the reported improvement of up to 18.5% and response-latency reduction of about 90%. The paper evaluates LongMemEval_S with GPT-4o and GPT-4o-mini; these relative claims cannot be compared to absolute local accuracies as if they shared a denominator. Zep itself was not part of this task's chosen framework run.

Local counterpart: full oracle context 10/14 (71.4%) versus Mem0 OSS 8/14 (57.1%) and BM25 RAG 11/14 (78.6%), each N=14. These are not Zep results, and their timings cannot validate its claimed speedup.

Suggested replacement, two sentences: “Zep's authors report up to 18.5% higher accuracy and about 90% lower response latency on LongMemEval_S. Our small local run compares full oracle context, BM25 retrieval, and Mem0 OSS; it does not test Zep or reproduce those improvements.”

Evidence: `results/summary.json` and per-item timing fields in `results/items.jsonl`. Primary source: https://arxiv.org/abs/2501.13956, specifically v1 sections 4.3 and the abstract, retrieved 2026-11-21. No claim is made that a Mem0 experiment is a replication of Graphiti or Zep.

### Chapter 17, `17-security-eval-ops.html`, benchmark overview

Printed row: “LongMemEval (ICLR 2025) 500 questions on scalable chat histories: extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention.” Source 21 is the LongMemEval paper. The relevant quantitative claim is dataset cardinality, 500, not system accuracy. The public oracle file contains 500 records; we sampled 14. ICLR 2025 is publication context, not a measured result.

Suggested replacement, two sentences: “LongMemEval contains 500 questions covering extraction, reasoning across sessions and dates, updates, and abstention. We ran 14 questions from its oracle-history split, which supplies the evidence sessions and is easier than the standard long-history test.”

Evidence: dataset file SHA-256 and revision in `results/manifest.json`; selected public records in `results/sample.json`. Sources: https://arxiv.org/abs/2410.10813 and https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned.

### Chapter 17, evaluation recipe

Printed passage: “Use repository revision 9e0b455, its requirements-lite.txt and the downloaded data” and “Its gpt-4o alias selects gpt-4o-2024-08-06.” Source 28 is the authors' repository at that revision. These are version/configuration identifiers, not benchmark scores. The chapter also says its example command was checked but not run there.

Local counterpart: the official `get_anscheck_prompt` function from the same full revision is reused, with a local Qwen3.5-9B-4bit judge. We did not execute the chapter's paid OpenAI recipe or pretend its GPT-4o results were locally reproduced.

Suggested replacement, two sentences: “The official evaluation recipe uses GPT-4o as judge. Our local harness reuses its task-specific prompts with Qwen3.5-9B-4bit instead, and keeps every verdict for inspection.”

Evidence: `judge_prompt.py`, `LICENSE.upstream`, `results/llm.jsonl`, `results/judge-checks.jsonl`. Source: https://github.com/xiaowu0162/LongMemEval/tree/9e0b455f4ef0e2ab8f2e582289761153549043fc.

### Chapter 17, cost crossover

Printed sentence: “One study found a Mem0-style system cheaper after about ten turns at 100,000-token context with caching, while long context was more accurate on LongMemEval and LoCoMo.” Source 32 is arXiv:2603.04814. The figures are approximately ten turns and 100,000 tokens. They belong to a particular API price/cache cost model; our local oracle-history accuracy experiment does not reproduce that model.

Local counterpart: no dollar crossover measured. Each selected question has one answer per method. Extraction, preparation and answering times and token counts are retained, but they do not measure repeated-query caching economics. The source paper's LongMemEval table reports 82.40% for long-context GPT-5-mini, 49.00% for its memory system, and 48.20% for long-context GPT-OSS-120B; those absolute scores are not printed in this chapter and are not replicated by our smaller local model.

Suggested replacement, two sentences: “One API cost study places its memory system's break-even point near ten turns at a cached 100,000-token context. Our local accuracy run does not test that price model or establish a cost crossover.”

Evidence: local token usage and timings in `results/items.jsonl`; primary source https://arxiv.org/abs/2603.04814, v1 abstract and sections 4.1 through 4.4, retrieved 2026-11-21.

### Chapter 16, `16-frontier.html`

No LongMemEval figure or explicit mention appears in the inspected chapter. Its context-versus-RAG material is not assigned a LongMemEval result by this report. No replacement sentence is proposed.

## Additional published anchor

The original LongMemEval paper's direct-reading oracle result for Llama 3.1 8B is 71.0%, N=500, without Chain-of-Note. Our full-context oracle result is 10/14 (71.4%), N=14. This is a useful setting label, not a matched replication: the model, quantization, judge, cleaned data revision, sample and answer prompt all differ. The original paper's paired oracle-versus-S degradation cannot be inferred from an oracle-only experiment.

## Method differences and interpretive limits

- All generation, extraction and judging used one local open-weight Qwen3.5-9B-4bit model. The original benchmark uses GPT-4o judging; the Mem0 managed headline uses a different, partly proprietary stack; Zep uses different models and graph processing.
- The official oracle split contains only evidence sessions. This run retains all supplied history in the full-context baseline and removes answer-location annotations from generation input, but cannot measure distractor robustness, 115k-token reading, or full-scale recall.
- Two questions per each of six non-abstention types plus two abstentions, fixed before observing scores, with seed 20261121. Equal-stratum sampling changes the mixture from the 500-question dataset. Tiny sample sizes and a correlated local judge prevent rankings or significance claims.
- Full context and RAG use both speakers; Mem0 receives both but its default fact extraction favors user information. Session dates enter extraction as a system message and metadata, and retrieved dates enter the answer prompt. No custom prompt repairs were applied after looking at results.
- BM25 with ten utterance windows differs from the paper's dense retriever, value granularity and budgets. Mem0 uses ten memories, not managed top-200 retrieval.
- All answer methods use one shared concise-answer prompt rather than the paper's exact direct/Chain-of-Note templates. Temperature is zero. Seeds are explicit for answer/judge calls; extraction uses deterministic greedy generation without an explicit seed.
- Default Mem0 extraction and update prompts and actual storage are exercised with `infer=True`. This is a framework test, not hand-written fact selection labeled as Mem0. All raw extraction/update outputs, stored records and retrieved memory contexts are saved.
- Fixed method order, model cache reuse and a shared serving host confound latency. Local timing fields are observational and do not reproduce any published percentage speedup or API cost.
- Descriptive 95% Wilson intervals and correct/N are provided. They omit judge error and are not a stratified-population confidence analysis. Positive, negative and abstention judge controls do not replace human validation.

## Failures and verification

The MLX model-list endpoint initially failed because the isolated Hugging Face cache did not contain its `hub/` directory. Creating that directory fixed the preflight; a short inference request then passed. A PostHog warning about multiple client instances appeared even with Mem0 telemetry disabled; the package source confirms that the configured false flag disables telemetry. Completed-call counts, truncation counts and verifier results follow. No hosted inference fallback was used.

Completed all 42 item/system pairs. Answer length stops: 0; judge length stops: 0; Mem0 extraction/update length stops: 0. The memory framework made 43 recorded local LLM calls. All scored judge verdicts matched the required yes/no format. The evidence verifier passed, including the explicit wrong-answer judge control. A separate missing-row mutation was rejected by the verifier. Raw timing and token totals are in `results/observations.json`.

The full-context stale-count answer and the failed cross-session answers remain in the raw records. Mem0 assistant-detail omissions and any default extraction behavior are part of the measured result, not repaired or excluded. There were no benchmark item retries or hosted model calls.

The shipped `run.py` produced the numbers. Its and the judge prompt's source hashes are recorded in the manifest. `verify.py` independently checks the saved paired coverage, reference consistency, counts, basic judge controls, token usage, source hashes and removal of answer-location labels from full-context input. A negative judge control explicitly received a wrong answer and was rejected. No generated score is substituted for a missing call.

An editorial spot check flagged three possible false-negative judge verdicts on photography-preference question `06878be2`, one per method. The responses name Sony equipment or explicitly use the user's Sony setup, which appears to meet the supplied preference rubric. `results/judge-audit.json` records the flags. Original labels are retained; independent review remains unresolved. Basic judge controls therefore establish only that the judge can produce both labels, not that its benchmark judgments are reliable.

## Cleanup proof

Cleanup confirmed. The model server (PID 1343), SSH tunnel (PID 882124), and pressure monitor (PID 884840) were stopped. Port 39710 has no listener on either endpoint. The isolated model directory on the model host and `/var/tmp/membench-longmemeval/` on the client were deleted, including downloaded weights, model caches, the virtual environment, embedding files and Qdrant stores. No containers were started.

All 30 pressure-monitor samples were normal, with system-wide free percentage never below 46%. The three pre-existing voice-service PIDs checked in the before/after listings were preserved. an unpublished raw log records the checks; an unpublished raw log and an unpublished raw log contain disk-space and process/listener listings, with account identifiers and addresses redacted. Client disk/process evidence is also in `results/proof/`. Disk values reflect a shared machine and are not a controlled storage-reclamation measurement. Only the benchmark source, documentation and results are retained as task artifacts.

No commits were made, and files outside `benchmarks/longmemeval/` were not edited.

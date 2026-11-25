# LongMemEval larger-run editorial report

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

**Large run status: all 300 questions checkpointed for every lane.**

| System or reference | Published result | Local result |
|---|---|---|
| Full standard history | Llama 3.1 8B direct, 45.4%, N=500 | unavailable, N=0; 300 context skips |
| Oracle-history reference | Llama 3.1 8B direct, 71.0%, N=500 | 127/212 (59.9%), 95% Wilson 53.2% to 66.3% |
| BM25 RAG | No matched QA figure; paper Table 9 Recall@10 is 71.0% session / 53.8% round, not QA accuracy | 191/300 (63.7%), 95% Wilson 58.1% to 68.9% |
| Dense RAG | No matched MiniLM/S figure; paper Stella 1.5B round top-10 QA on M is 53.4% | 165/300 (55.0%), 95% Wilson 49.3% to 60.5% |
| Mem0 | Managed April 2026, 94.4%, retrieval budget 200, headline N unstated | OSS raw storage: 165/300 (55.0%), 95% Wilson 49.3% to 60.5% |
| Letta or Zep/Graphiti OSS | No matched published result | Not measured |

These are different systems and settings, not a controlled published-versus-local ranking. Published paper values are from [LongMemEval](https://arxiv.org/html/2410.10813v2); the managed headline is from the [pinned Mem0 source](https://github.com/mem0ai/mem0/tree/fff8a6472512d1bc1a4bccab8c645b65a1df7fe5).

| System | Local result | Checkpoints missing |
|---|---|---:|
| full-standard | unavailable, N=0; 300 context skips | 0 |
| bm25-standard | 191/300 (63.7%), 95% Wilson 58.1% to 68.9% | 0 |
| dense-standard | 165/300 (55.0%), 95% Wilson 49.3% to 60.5% | 0 |
| mem0-raw-standard | 165/300 (55.0%), 95% Wilson 49.3% to 60.5% | 0 |
| full-oracle | 127/212 (59.9%), 95% Wilson 53.2% to 66.3% | 0 |

| Official question type (abstentions included) | BM25 | Dense | Mem0 raw | Oracle full context |
|---|---:|---:|---:|---:|
| knowledge-update | 38/46 (69.3% to 90.9%) | 32/46 (55.2% to 80.9%) | 32/46 (55.2% to 80.9%) | 10/36 (15.8% to 44.0%) |
| multi-session | 38/81 (36.4% to 57.7%) | 32/81 (29.6% to 50.4%) | 32/81 (29.6% to 50.4%) | 15/36 (27.1% to 57.8%) |
| single-session-assistant | 30/34 (73.4% to 95.3%) | 32/34 (80.9% to 98.4%) | 32/34 (80.9% to 98.4%) | 34/34 (89.8% to 100.0%) |
| single-session-preference | 5/18 (12.5% to 50.9%) | 7/18 (20.3% to 61.4%) | 7/18 (20.3% to 61.4%) | 6/18 (16.3% to 56.3%) |
| single-session-user | 39/41 (83.9% to 98.7%) | 33/41 (66.0% to 89.8%) | 33/41 (66.0% to 89.8%) | 39/41 (83.9% to 98.7%) |
| temporal-reasoning | 41/80 (40.5% to 61.9%) | 29/80 (26.6% to 47.2%) | 29/80 (26.6% to 47.2%) | 23/47 (35.3% to 62.8%) |
| Abstention overlay | 17/18 (74.2% to 99.0%) | 16/18 (67.2% to 96.9%) | 16/18 (67.2% to 96.9%) | 14/15 (70.2% to 98.8%) |

Cells show correct/N and descriptive 95% Wilson intervals. The abstention row overlaps the official types; it is not added again to overall N. Disjoint sampling-stratum counts remain in the manifest and summary.

| Oracle-window matched subset | Result |
|---|---|
| bm25-standard | 156/212 (73.6%), 95% Wilson 67.3% to 79.1% |
| dense-standard | 135/212 (63.7%), 95% Wilson 57.0% to 69.9% |
| mem0-raw-standard | 135/212 (63.7%), 95% Wilson 57.0% to 69.9% |
| full-oracle | 127/212 (59.9%), 95% Wilson 53.2% to 66.3% |

Direct-review agreement: 37/40 (92.5%), descriptive 95% Wilson 80.1% to 97.4%.

## Scope and method differences

LongMemEval tests whether an assistant can recover information from dated conversations, combine evidence across sessions, reason about time, follow changing facts, respect preferences, and abstain when the history lacks the answer.

The original 14-question pilot is preserved in `README.pilot.md`, `REPORT.pilot.md`, and the original files under `results/`. This run uses the official cleaned LongMemEval_S full haystacks for BM25, dense retrieval, and Mem0. It never replaces a retrieval input with oracle evidence. Oracle full context is a separate reference.

The model is Gemma 2 9B at 4-bit (MLX repository/revision in `results/full/manifest.json`), served on Apple M1 Ultra, 64 GB. Its native context is 8,192 tokens. Full histories that exceed that window, including the answer allowance, are recorded as unavailable, never truncated. This differs substantially from the paper's 128k-context readers. An oracle subset that fits is an easier, separately labeled reference, not an upper bound on every question or model.

Sampling: 300/500 questions, seed 20261122. Proportional allocation uses largest remainders across the six non-abstention types and an abstention stratum; IDs are sorted before sampling. Counts and exact selected IDs are in the manifest. Question text, answer references and types match across the selected standard/Oracle records, but the official variants are independently timestamped. Each lane uses its own variant's question date with its own history dates. `variant-date-maps.json` and the verifier enforce that alignment. Earlier Oracle-only mixed-date outputs are uniformly archived under `preflight/oracle-date-mix/` and excluded; standard retrieval results were retained. The `source_session_count` field records the standard candidate-haystack size; actual supplied sessions are visible in `context`. Every lane targets those same 300 IDs; context failures have explicit records and do not count as wrong or disappear silently. Confidence intervals are descriptive Wilson intervals, not a correction for stratification, correlated judging, or judge error.

BM25 uses 800-character windows, stride 700, with both speakers and dates, and returns up to ten chunks in history order. If needed to fit the native window, whole lower-ranked chunks are dropped and the actual context is saved. Dense RAG embeds those same chunks using pinned all-MiniLM-L6-v2 on CPU (maximum embedding sequence length 256 wordpieces), cosine similarity, up to ten under the same context budget. Mem0 OSS 0.1.118 uses its actual `add(..., infer=False)` and `search` APIs with local Qdrant and the same CPU vectors. Every source session and chunk is ingested; added/stored counts and chunk hashes are recorded. Cached vectors change neither content nor similarity. The disabled SDK telemetry hook is bypassed because version 0.1.118 still constructs telemetry clients per storage event when opted out; storage and search remain the actual SDK implementations. This Mem0 lane is raw storage/retrieval, not default fact extraction, and is expected to overlap the dense baseline closely. The pilot's `infer=True` configuration is preserved, not silently relabeled as a full-size extraction run. Full-haystack fact extraction at 300 questions would exceed this single-model budget and remains unmeasured.

All answers use a custom shared history/question prompt, saved verbatim, temperature zero, and a 512-token limit; this reader prompt differs from the paper. The benchmark's unchanged task-specific judging prompts are used for three local calls, seeds 20261122/23/24, temperature zero, majority vote. The official scorer interprets a response containing `yes` as positive and all other responses as negative; nonbinary formats are also counted as a diagnostic. Greedy repeated calls are generally identical and are not independent evidence against systematic judge bias. Each answer and each judge call has a separate atomic checkpoint. HTTP failures retry the same unfinished call; scored answers are not regenerated. A memory-pressure guard stops only this run's server at warning/critical and reloads only after normal pressure and at least 40% system-wide free memory. The wall-clock deadline continues through pauses.

The three pilot photography-preference verdicts were resolved by direct editorial review as false negatives against the official rubric (`results/pilot-judge-resolution.json`). Pilot aggregate labels remain unchanged. Forty item/system pairs are selected with a fixed random seed from the eligible planned pairs, without using answer content or machine labels, before direct review; this is agent editorial review, not an independent human evaluation. The audit file names the reviewer and records every decision and reason. Its agreement rate measures agreement with that review only.

One more framework was optional. A basic model-API prerequisite probe for a Letta-style system/tool request returned HTTP 404 with `System role not supported`; the raw probe is in `proof/letta-model-prerequisite.json`. This is a compatibility probe, not a Letta benchmark or evidence that Letta cannot work with another adapter or model. No Letta or Graphiti accuracy result is claimed. Default automatic Mem0 fact extraction also needs compatible system-message handling, in addition to a larger generation workload; the measured Mem0 lane remains explicitly raw storage. No vendor algorithm, Zep latency claim, or API cost crossover is reproduced here.

Published anchors: Mem0 managed April 2026 reports 94.4% with retrieval budget 200; its headline README does not state N. The original paper reports 71.0% oracle direct-reading accuracy for Llama 3.1 8B, N=500. Zep reports up to 18.5% accuracy improvement and about 90% lower latency on LongMemEval_S; neither is an absolute local accuracy or a result of this Mem0 raw-storage lane. The cached API cost crossover near ten turns at 100,000 tokens is not tested. Primary sources and the original book wording remain in `results/sources.json`, `results/book-claim-inventory.json`, and `REPORT.pilot.md`.

## Book figures and suggested sentences

Chapter 13 prints: “Mem0 reports LoCoMo 92.5 and LongMemEval 94.4 for its managed April 2026 stack, with a top-200 retrieval budget.” Sources 5/7 are the Mem0 repository and memory-benchmarks repository. The 92.5 figure is LoCoMo, outside this benchmark. Suggested wording: “Mem0 reports 94.4% for its managed LongMemEval stack with a retrieval budget of 200. Our local open-source raw-storage configuration scored 165/300 (55.0%), 95% Wilson 49.3% to 60.5%; it does not reproduce the managed algorithm.”

Chapter 14 prints: “94.8% vs 93.4% Zep against MemGPT on Deep Memory Retrieval, plus up to 18.5% higher accuracy and 90% lower latency on LongMemEval. The Zep authors' numbers.” Source 22 is arXiv:2501.13956. The first pair is DMR, not LongMemEval. Suggested wording: “Zep's authors report up to 18.5% higher accuracy and about 90% lower response latency on LongMemEval_S. Our local experiment does not test Zep or reproduce those changes.”

Chapter 17 prints a 500-question LongMemEval inventory and the ICLR 2025 label, citing arXiv:2410.10813. Suggested wording: “We sampled 300 of the 500 questions proportionally across question types and abstention. The retrieval systems received the full standard haystacks, while oracle-history reading is reported separately.”

Chapter 17's evaluator example cites repository 9e0b455 and the gpt-4o-2024-08-06 alias. Suggested wording: “Our evaluator uses the authors' task-specific judging prompts with a local 9B model and three-call majority voting. Direct review by the implementation agent agreed with 37 of 40 randomly selected judgments (92.5%).” This is agent editorial review, not independent human validation.

Chapter 17 prints a cost crossover near ten turns at 100,000 cached tokens, citing arXiv:2603.04814. Suggested wording: “The ten-turn crossover belongs to that paper's API prices and cache model. Our local accuracy experiment does not establish a dollar-cost crossover.”

Chapter 16 has no explicit LongMemEval figure in the inspected version. Every source paragraph and URL is retained in the pilot's claim inventory. No chapter files were edited.

Additional local-results paragraph: “With Gemma 2 9B at 4-bit and full standard histories, our local judge scored BM25 at 191/300 (63.7%), 95% Wilson 58.1% to 68.9%. Dense RAG and Mem0 open-source raw storage each scored 165/300 (55.0%), 95% Wilson 49.3% to 60.5%; this does not test Mem0’s managed algorithm.”

| Diagnostic | BM25 | Dense | Mem0 raw | Oracle |
|---|---:|---:|---:|---:|
| Empty answers | 0 | 0 | 0 | 58 |
| Empty answers judged positive | 0 | 0 | 0 | 31 |
| Answer token-limit stops | 0 | 0 | 0 | 21 |
| Nonbinary judge calls | 0 | 0 | 0 | 15 |
| Split judge votes | 0 | 0 | 0 | 0 |

Oracle judge sensitivity: 31 empty answers were incorrectly labeled positive. Forcing only those empty answers to incorrect would give 96/212 (45.3%; 95% Wilson 38.7% to 52.0%). This is a mechanical sensitivity check, not the primary official-prompt judge score or a correction of other judge errors.

Empty and degenerate answers remain in the denominator. Nonbinary judge responses follow the official substring rule rather than being selectively regenerated. All three judge calls are retained; greedy majority voting cannot remove systematic judge errors.

The final operational record contains 633 pressure samples, including 8 warning samples; the server was paused and recovered under the guard. There were 7 transport-error events, retried from checkpoints. Dense RAG and Mem0 raw storage produced identical answers for 300/300 questions and identical submitted contexts for 299/300; these lanes do not demonstrate a distinct memory-extraction benefit. See `results/full/diagnostics.json`.

## Evidence, failures and cleanup


Evidence: `results/full/items/` contains final per-item lane checkpoints; `answers/` and `judges/` retain each raw response; `requests.jsonl` contains submitted prompts and raw responses; `memory-ingestion.jsonl` proves full-haystack chunk ingestion; the manifest pins data, models, sample and code. Raw public benchmark dialogue entities are retained to preserve the benchmark; private operator identities and network addresses are omitted from operational logs. an unpublished raw log and `proof/` hold cleanup results when the supervisor finishes. Cleanup is confirmed: owned model server and SSH tunnel stopped, both scratch directories removed, no owned listeners or containers, and the three preexisting voice-service PIDs preserved. Before/after disk and process evidence is under `results/full/proof/`; the final independent check is `proof/cleanup-independent.json`.

The three pilot verdicts are resolved in `results/pilot-judge-resolution.json`. Original pilot outputs remain unchanged. Transport errors, if any, are in `transport-errors.jsonl`; fatal errors and pressure pauses are retained by the supervisor.  The experiment cannot validate the managed Mem0 headline, the paper's long-context accuracy with a different model, Zep's claimed improvements, or the API cost crossover.

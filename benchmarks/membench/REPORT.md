# Editor report: newer memory benchmarks

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

Status: complete. Two paired local performance runs finished (EventQA and HaluMem QA, 150 items each, three systems each) and `results/verification.json` confirms all six cells and the tester's forty-item judge audit (41 outputs, 40 distinct questions). A bounded MemoryArena pilot also ran. No chapter files were edited. Local numbers appear in "Completed local results" at the end of this file.

The local reader and HaluMem judge are Qwen2.5-14B-Instruct Q4_K_M on an Apple M3 Ultra with 96 GB. A 32-thread x86 CPU runs all data processing, local embeddings, retrieval and scoring. The model, embedding, chunking, sample, extended-context configuration and setup differences are recorded in README.md. These are baseline adaptations, not reproductions of LIGHT, TriLink or any commercial memory service.

## Chapter 16: LIGHT and BEAM

Location: `build/chapters/16-frontier.html:250`, sentence: “BEAM's authors report average gains of 3.5% to 12.69% over their strongest baselines, depending on the backbone model.” The paragraph also says the proposed comparison has not been run.

Published: LIGHT gains of 3.5% to 12.69%. Local: no LIGHT gain measured. Public MIT code, conversations and scoring rubrics make a local adaptation feasible, but the two performance runs here prioritize MemoryAgentBench and HaluMem. Do not relabel this feasible experiment as technically impossible or use unrelated baseline scores to validate the gain. The published proprietary-backbone comparison cannot be reproduced locally with open weights; no LIGHT preprocessing or scratchpad updates were executed.

Suggested replacement: “BEAM's authors report LIGHT gains of 3.5% to 12.69%, which this book has not reproduced. This book checked the released benchmark's size, but that check does not establish LIGHT's performance.”

Location: `build/chapters/16-frontier.html:256`, sentence: “BEAM has 100 conversations up to 10 million tokens and 2,000 validated questions, and reports that 1 million token models degrade as dialogues grow, with or without retrieval.”

Local release-count pilot: 100 question-bearing conversations and 2000 question records, from all 100 official question files at pinned revision `b2da22eac88bb0874c64665f13457eb99835774a`. Release scales: 20 at `100K` (called 128K in the README), 35 at 500K, 35 at 1M and 10 at 10M. This is a census, so no sampling interval applies. It verifies record counts, not the human validation of questions, actual tokenizer lengths or degradation with context size.

Suggested replacement: “This book counted 100 conversations and 2,000 question records in BEAM's public release. The reported deterioration of million-token models remains the authors' result, not a local measurement.”

Evidence: `results/source-audit.json`, `audit_sources.py`, official [BEAM paper](https://arxiv.org/abs/2510.27246).

## Chapter 16: MemoryAgentBench

Location: `build/chapters/16-frontier.html:256`, sentence: “MemoryAgentBench tests accurate retrieval over incremental input, test-time learning, long-range understanding and selective forgetting across turns; its authors report that no method masters all four.”

The four competencies are supported by the public data and paper. The release names its fourth split Conflict_Resolution; the paper's current table calls it Selective Forgetting. Data and deterministic EventQA scoring are public under MIT. This task tests only the five smaller EventQA histories, 30 sampled questions each, N=150 per method. It cannot determine mastery across all four competencies or reproduce the full suite's ranking.

Published EventQA figures in [paper v4](https://arxiv.org/html/2507.05257v4): main-table GPT-4o-mini full context 59.0%, BM25 74.6%, Text-Embed-3-Small RAG 63.0%. These main-table retrieval scores use the larger EventQA histories, unlike the local 65536 stratum. The paper's length-ablation table reports GPT-4o-mini full context 90.2% at its smallest 51K setting, 85.8% at 108K, and 59.0% at 534K. The local model's tokenization and privacy aliases give different input lengths; this is not a same-model replication of those rates. The paper uses 4096-token EventQA chunks and top 10, while this run uses 100-word chunks and top 20 to fit the local MiniLM encoder, so retrieval granularity and supplied context budgets also differ substantially.

Local result: EventQA recall on 150 paired questions was 95.33% (90.68% to 97.72%) with full context, 76.67% (69.28% to 82.72%) with plain RAG and 86.00% (79.54% to 90.66%) with BM25; see the table and paired differences at the end of this file. The full-context figure is consistent with the paper's high small-context figure but the readers, histories and chunking differ, so it neither confirms nor contradicts it; the paper's main-table ordering (BM25 above plain embedding RAG above full context at its largest sizes) appears only partly here: BM25 beat plain RAG, but full context beat both at this small history size, as the paper's own length ablation would predict. This run cannot speak to the four-competency claim. Evidence: `results/manifest.json`, `results/items/mab/`, `results/context-lengths.json`, `results/summary.json`, `results/verification.json`.

## Chapter 16: HaluMem

Location: `build/chapters/16-frontier.html:257`, sentences: “HaluMem (EMNLP, October 2026) evaluates hallucinations at three stages: memory extraction, updating and memory question answering. Its authors report hallucinations accumulating during extraction and updates, and release benchmark resources.”

Public data and evaluation rubrics are available. The license is CC BY-NC-ND 4.0, not MIT. The official evaluation code invokes an LLM judge. This task substitutes the local reader model as judge and applies its Correct / Hallucination / Omission priorities. Only actual dialogue, never reference memory points or persona summaries, enters the reader's context or retrieval index. The judge receives the reference and evidence after answering. A forty-item tester hand audit is required; it is not an independent human validation.

The Medium release contains 3467 questions across 20 users; this is the dataset size, not a reconstructed denominator for the rounded leaderboard rates. Published official Medium QA leaderboard: MemOS 67.23% correct, 15.17% hallucination and 17.59% omission; Mem0 53.02%, 19.17% and 27.81%, respectively. Those are memory-system results on the full benchmark, using GPT-4o uniformly for answer generation and GPT-4o for scoring, with top-20 retrieved memory records. They are not published full-context, plain-RAG or BM25 scores. The local run balances six types across earlier-history questions from the first 30 sessions, so it does not reproduce the full distribution. No extraction or updating pipeline was run, and downstream QA outcomes cannot substantiate accumulation at those earlier stages.

Local result: HaluMem QA on 150 paired questions was 41.33% correct (33.77% to 49.33%) with full context, 32.67% with plain RAG and 41.33% with BM25 (hallucination 42.0%, 19.3% and 22.7%; omission 16.7%, 48.0% and 36.0%). The tester's hand audit of the local judge agreed with it on 28 of 41 outputs (68.3%); all 13 disagreements were cases where the tester judged an answer Correct (or Omission instead of Hallucination) that the local judge marked stricter, so the local judge is harsher than the tester and absolute rates are probably understated. Rankings between systems are less affected. Evidence: `results/manifest.json`, `results/items/halu/`, `results/manual-audit.json`, `results/summary.json`; official [repository](https://github.com/MemTensor/HaluMem), [dataset](https://huggingface.co/datasets/IAAR-Shanghai/HaluMem), [paper](https://arxiv.org/abs/2511.03506).

## Chapter 16: MemoryArena

Location: `build/chapters/16-frontier.html:261`, sentence: “Its authors report that agents near saturation on LoCoMo perform poorly there.” Also: code and a dataset are linked from its project page.

Published: a qualitative cross-benchmark claim, without a numerical rate in this sentence. Local: cannot be reproduced locally as the published proprietary-backbone comparison; only a one-chain reasoning pilot was run (see the MemoryArena pilot section at the end); no action-performance run was done. The public release is not a closed benchmark: its four environment setup guides publish configurable model endpoints, public task links, a shopping product database and travel database instructions. Formal reasoning can use a local judge endpoint. A local open-weight action adaptation is feasible but was not staged in this two-benchmark run. The inspected repository has no top-level license, so do not assume its bundled MemoRAG license covers the whole release. Do not treat this source audit or the QA runs as evidence of action completion or cross-benchmark saturation.

Suggested replacement: “MemoryArena publishes multi-session action environments and task data links, but this book has not measured action completion there. Its reported contrast with LoCoMo remains an author-reported result.”

Evidence: `results/source-audit.json`, pinned tree `6cd9de14b71915e39ac742a20dc33785e14b6aab`, official [project](https://memoryarena.github.io/), [paper](https://arxiv.org/abs/2602.16313).

## Chapter 16: STATE-Bench

Location: `build/chapters/16-frontier.html:263`, sentence: “STATE-Bench (Microsoft, 19 May 2026, MIT license) has 450 customer-support, travel and shopping tasks scored against deterministic end-state checks, five runs per task, a pass^5 reliability score and cost per task.” Next sentence: “Microsoft reports that GPT-5.1 without memory completes fewer than half of the tasks reliably.”

Published: 450 tasks, five runs, pass^5 and a sub-50% GPT-5.1 reliability claim. Local structural census: 450 released task JSON files at revision `5644b1838d96bc4483da29642d058ecaa6f80f7f`; no interval applies. Official performance cannot be reproduced locally under the current protocol because it locks a hosted GPT-5.4 simulator and judge. A configurable local agent does not remove that dependency. Replacing those models would change the protocol. The current README explicitly includes LLM-judged UX and describes procedural conversational conditions, so the book's deterministic-only wording omits important scoring dependencies. The code, tasks and MIT license are public; this is a protocol restriction, not unavailable data. No pass^5, cost or completion figure was measured.

Suggested replacement: “This book counted 450 public STATE-Bench tasks, but its current official protocol requires a hosted GPT-5.4 simulator and judge. This book therefore has no local pass^5 result to compare with Microsoft's reported GPT-5.1 reliability.”

Evidence: `results/source-audit.json`; official [main-track guide](https://github.com/microsoft/STATE-Bench/blob/5644b1838d96bc4483da29642d058ecaa6f80f7f/docs/RUN_BENCHMARK.md), [metrics guide](https://github.com/microsoft/STATE-Bench/blob/5644b1838d96bc4483da29642d058ecaa6f80f7f/docs/eval/compute-metrics.md).

## Chapter 16: CMB

Locations: `build/chapters/16-frontier.html:268` distinguishes the model card's two repository-QA evaluations from executable completion; `:269` gives 216 executable tasks, 750 diagnostic questions and nine repositories; `:274` through `:276` print the performance table.

| Printed measure | Published TriLink | Published strongest other memory | Published RAG | Local |
| --- | ---: | ---: | ---: | --- |
| Tasks resolved, Sonnet-5 | 43.1% | 36.6% | Not printed | Cannot be reproduced locally |
| Tasks resolved, DeepSeek v4-flash | 35.6% | 28.2% | 26.9% | Cannot be reproduced locally |
| QA, DeepSeek v4-flash | 64.2% | Not printed | 62.2% | Cannot be reproduced locally |

Specific reason: the inspected official release at `d8138b501a755f662a024f7e8eb879613eabf1d3` contains the CMB paper and memory implementation, but no frozen task histories, executable 216-task suite, 750-question references or evaluator/test assets. The published proprietary backbones also differ from this task's local reader. Public implementation code and a paper are insufficient to reconstruct those scores. A follow-up check of seven official releases and 209 public branch names found only MemHub/runtime distribution attachments and no benchmark-named branch; the publisher's memory-dataset search returned no match. This is absence from the inspected releases, not proof that no author copy exists elsewhere or that every feature-branch tree was searched. No synthetic replacement was substituted for CMB.

Suggested replacement for the dataset-size figures: “CMB's paper describes 216 executable tasks and 750 diagnostic questions across nine repositories. This book could not verify those counts against released task and grading files.”

Suggested replacement: “Tencent reports TriLink resolved rates of 43.1% and 35.6%, with 64.2% diagnostic QA for the latter backbone. This book could not reproduce these figures because the inspected public release lacks the frozen benchmark tasks and grading assets.”

Evidence: `results/source-audit.json`; official [paper file](https://github.com/Tencent-Hunyuan/Hy-Memory/blob/d8138b501a755f662a024f7e8eb879613eabf1d3/docs/papers/CMB_A_Coding_Memory_Benchmark_for_Long_Horizon_and_Interleaved_Coding_Agents.pdf). The model card's CMB column is a separate comparison and must not be used as the executable benchmark's local result.

## Chapter 17: evaluation scope

Locations: `build/chapters/17-security-eval-ops.html:192` MemoryAgentBench row; `:193` MemoryArena row; `:195` HaluMem row. These are descriptions, without printed numerical scores. The release inspections support their descriptions of retrieval/learning/forgetting, multi-session actions, and operation-level hallucination testing. They do not establish security, deletion, poisoning resistance or successful action execution. The proposed release gate at `:472` remains unrun for action environments.

Suggested replacement for the three rows' measurement qualification: “This book ran paired EventQA and HaluMem QA subsets with a local reader. It has not measured all four MemoryAgentBench competencies, HaluMem extraction and updates, or MemoryArena action completion.”

## Operational evidence and limits

Completed source audit: all 100 BEAM question files counted, totaling 2000; all 450 STATE task files counted. These are structural pilots and carry no performance interval.

Initial setup: model-host memory pressure normal, 78% available; before model start, 73%. Weight SHA256 matched. A serial weight transfer was replaced by parallel task-owned provisioning on the model host because concurrent benchmark-host jobs reduced available disk. The incomplete benchmark-host weight file was removed. Only weight provisioning and serving ran on the Mac; benchmark data, indexes and scoring stayed on the benchmark host. An owned lsof check stalled on an unrelated unavailable network mount and was terminated without touching the mount or existing services.

What did not work: the first dependency resolution selected unnecessary CUDA wheels; it was canceled and replaced with CPU-only PyTorch. spaCy initially lacked click because of the newest typer dependency; click and typer were pinned before any inference. Neither setup attempt contributes a score.

Cleanup: see the final section of this file and an unpublished raw log.

Pre-inference preparation correction: the initial long hash aliases inflated some complete histories to 148091 tokens, beyond the configured window, and unrestricted NER spans could mask ordinary lowercase words. Before any scored answer, the same frozen sample was rebuilt with compact PersonNNN aliases, capitalization and stopword filters, and apostrophe surname handling; all old indexes were discarded. The repair records and excluded manifests contain hashes and IDs, not scored results. A compact-alias admission check found a maximum of 101869 tokens before the final apostrophe-only adjustment, with no overflows. Final exact counts are in context-lengths.json.

Disk coordination: after the active NER phase stopped, its environment and data were relocated to `/data/scratch/membench/membench`; no active files were moved. Subsequent package, Hugging Face and pip caches and all indexes use that data-volume scratch. The old `/var/tmp/membench-membench` folder was removed. Both paths are part of final cleanup.

Serving adjustment: a two-slot setup left 36% available memory at normal pressure. Before scored inference, it was replaced with the final single-slot configuration, which left 50% available memory. The preflight response is excluded from all rates.

Encoder diagnostic, before any retrieval scores: 111 of 150 EventQA queries exceed the pinned MiniLM limit of 256 wordpieces, with maximum 351. All HaluMem queries and all 43962 indexed chunks fit. MiniLM truncates those EventQA query representations; BM25 and the answer reader see complete questions. This setup difference must accompany any EventQA RAG figure, without claiming it caused a particular rate. Evidence: results/embedding-limits.json.

Runtime pressure interruption: after 39 saved HaluMem answers, the model host reported warning pressure. The task guard stopped its own listener, but that server process hung during graceful cleanup. Only the verified task-owned process was force-stopped; availability recovered to 60% and normal pressure. The guard now bounds graceful shutdown to ten seconds before force-stopping its tracked child. The same weights, context, KV precision, prompts, seeds and sampling remain in use, and no completed answer was discarded. Evidence: results/pressure-recovery.json.

Confirmed input privacy limitation: the frozen PERSON-word filter also replaced the non-name tokens Mar, Jun and Abnormal. These examples affect 12 of 150 HaluMem questions and one reference answer (12 distinct items); the date aliases remove month semantics and the health alias removes the meaning of that label. This is not an exhaustive estimate of false name detections. The same transformed inputs were used in all three systems, but this limits validity against the original benchmark and is not corrected after observing answers. Evidence: `results/privacy-semantic-limit.json`.

Preparation reproducibility check: `verify_preparation.py` replayed the shipped sampling, NER and masking code without writing inputs or indexes. All 300 items, 115 histories and the complete alias mapping match the frozen preparation exactly; canonical JSON SHA256 values agree. Evidence: `results/preparation-replay.json`. The original forty-output audit plan was fixed before inference; one supplemental RAG output was selected before retrieval or judge output to ensure forty distinct questions across forty-one reviewed outputs.

<!-- completed-local-results -->

## Completed local results

| Benchmark | Method | Published reference, different setup | Local correct / N | Local rate | 95% Wilson interval |
| --- | --- | --- | --- | --- | --- |
| MemoryAgentBench EventQA | full-context | 90.2% small-context GPT-4o-mini; 59.0% main table | 143/150 | 95.33% | 90.68% to 97.72% |
| MemoryAgentBench EventQA | rag | 63.0% Text-Embed-3-Small, main table | 115/150 | 76.67% | 69.28% to 82.72% |
| MemoryAgentBench EventQA | bm25 | 74.6%, main table | 129/150 | 86.00% | 79.54% to 90.66% |
| HaluMem QA | full-context | No same-baseline score; MemOS 67.23%, Mem0 53.02% | 62/150 | 41.33% | 33.77% to 49.33% |
| HaluMem QA | rag | No same-baseline score; MemOS 67.23%, Mem0 53.02% | 49/150 | 32.67% | 25.68% to 40.52% |
| HaluMem QA | bm25 | No same-baseline score; MemOS 67.23%, Mem0 53.02% | 62/150 | 41.33% | 33.77% to 49.33% |

These are privacy-transformed inputs. Confirmed false name masking affects 12 HaluMem questions and one reference; other false detections may remain. MiniLM truncates the semantic query representation for 111/150 EventQA items. Published references use different readers, embeddings, histories and scoring distributions. The HaluMem references evaluate different memory systems. These local rates cannot establish a same-system replication, LIGHT gain, operation-level hallucination accumulation or action completion. Wilson intervals treat questions as independent; see the paired cluster-bootstrap estimates below.

mab: rag minus full context -18.67 percentage points (paired cluster-bootstrap 95% -25.33 to -12.00; 5 clusters); bm25 minus full context -9.33 percentage points (paired cluster-bootstrap 95% -14.00 to -4.67; 5 clusters).

halu: rag minus full context -8.67 percentage points (paired cluster-bootstrap 95% -15.97 to -1.31; 20 clusters); bm25 minus full context +0.00 percentage points (paired cluster-bootstrap 95% -8.11 to +7.79; 20 clusters).

HaluMem local QA labels, N=150 per method:

| Method | Correct | Hallucination | Omission |
| --- | --- | --- | --- |
| full-context | 41.33% (33.77% to 49.33%) | 42.00% (34.40% to 50.00%) | 16.67% (11.55% to 23.45%) |
| rag | 32.67% (25.68% to 40.52%) | 19.33% (13.81% to 26.39%) | 48.00% (40.16% to 55.94%) |
| bm25 | 41.33% (33.77% to 49.33%) | 22.67% (16.70% to 30.00%) | 36.00% (28.76% to 43.94%) |

Tester hand audit of the local HaluMem judge: 28/41 agreement (68.3%; Wilson 95% 53.02% to 80.44%). This was performed by the tester, not an independent human. Main automated labels are retained, including disagreements.

Suggested two-sentence replacement for the EventQA performance qualification: “On 150 paired EventQA questions, this book measured 95.33% with full context, 76.67% with plain RAG and 86.00% with BM25 using a local Qwen2.5-14B reader. The RAG encoder represented only the starts of 111 of 150 queries, and different histories and models mean this does not replicate the authors' full benchmark.”

Suggested two-sentence replacement for the HaluMem QA performance qualification: “On 150 paired HaluMem QA questions, this book measured 41.33% with full context, 32.67% with plain RAG and 41.33% with BM25 using a local Qwen2.5-14B reader. These QA inputs were altered for privacy, with ordinary words incorrectly masked in 12 items, so this does not reproduce the published memory systems or measure extraction and updating.”

## MemoryArena pilot (bounded, formal-reasoning math only)

One seeded five-step chain (dataset row 7) run through the official reasoning agent, memory entry builder, environment step and yes/no judge, with the same local reader. Full-history memory answered 4 of 5 steps correctly (Wilson 95% 37.6% to 96.4%) and no-memory 3 of 5 (23.1% to 88.2%). N=5 per method, one chain, no coding tool and no action environments: this is a smoke test that the public pipeline runs locally, not a measurement of action completion, and it says nothing about the author-reported contrast with LoCoMo. The tester hand-read all 10 judgments (`results/arena-pilot/manual-audit.json`): the environment judge agreed with the tester on 8 of 10. It marked full-history step 2 wrong although -a^-1 w(a) b equals -b^2 w(a) when b is the inverse of a, and marked full-history step 3 right although the answer replaced v(x_i) with the coordinate derivation without justification. Evidence: `results/arena-pilot/summary.json`, `results/arena-pilot/manifest.json`, `results/arena-pilot/items/`.

Suggested replacement for the chapter 16 MemoryArena sentence: "This book ran only a five-step reasoning pilot of MemoryArena's public code with a local model and has not measured action completion there. Its reported contrast with LoCoMo remains an author-reported result."

## Operational notes for the final run

The first operator's runner process stopped between saved answers during the EventQA retrieval phase, and its SSH tunnel to the model port stopped with it; the model server on the Mac stayed healthy. The second operator recreated only the tunnel and restarted `run.py` unchanged. It reused every saved answer (no item was rerun and no prompt, model, sample or scoring setting changed) and finished the remaining EventQA retrieval answers and all 450 HaluMem judgments. The pilot, the privacy export and the audits then ran in the order listed in `run.sh`. Manual audit labels were written before the automated labels were joined.

## Cleanup (completed)

`cleanup.py` ran after verification, the pilot and both hand audits. It verified ownership of the model-host guard, server and the local SSH tunnel, stopped only those, closed local port 39780, removed the model-host task folder (about 8.4 GB including weights, before removal), removed the local scratch folder (about 1.0 GB: environment, inputs, indexes, private originals) and the task's `__pycache__` folders. No containers, images or volumes were created. The shared model host kept its other servers running; the model host's memory pressure stayed at normal level for 7038 samples and showed one warning sample (already recorded in `results/pressure-recovery.json`); all 1380 logged generation slots reported no truncation. Disk, process and pressure evidence before and after is in an unpublished raw log. A pre-existing shared Python 3.12 interpreter was deliberately not removed. Only this territory folder remains.

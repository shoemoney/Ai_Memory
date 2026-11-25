# Local runs of newer memory benchmarks

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

This directory compares full context, plain embedding RAG and BM25 using the same frozen 150 questions per benchmark. The reader is Qwen2.5-14B-Instruct Q4_K_M. Model serving uses an Apple M3 Ultra with 96 GB of unified memory; preparation, CPU embeddings, retrieval, orchestration and scoring run on a 32-thread x86 CPU. No hosted generation, embedding or judging service is used.

Results are complete: `results/verification.json` confirms all six cells and the manual judge audit. Do not interpret source-audit counts as performance results.

## Reproduce

Serve the pinned model through a local-only OpenAI-compatible endpoint, optionally reached through an SSH tunnel, then run from the repository root:

```bash
BASE_URL=http://localhost:39780 bash benchmarks/membench/run.sh
```

The command creates an isolated Python 3.12 environment, installs the pinned lockfile, downloads the exact dataset revisions, freezes the sample, builds indexes and resumes per-item answer and judge checkpoints. `LAB_DIR` defaults to `/data/scratch/membench/membench` when using run.sh; the initial active preparation used `/var/tmp/membench-membench` and its environment and inputs stayed there until preparation stopped between phases, then moved to the data scratch volume; `OUT_DIR` defaults to this directory's `results`. A new experiment requires a new output and scratch directory. Existing answers are reused. The endpoint is a setting and defaults to localhost.

Model weights: [Qwen2.5-14B-Instruct Q4_K_M](https://huggingface.co/bartowski/Qwen2.5-14B-Instruct-GGUF/tree/05244aa5d871c661c80082a15d3bce44714d068d), revision `05244aa5d871c661c80082a15d3bce44714d068d`, file `Qwen2.5-14B-Instruct-Q4_K_M.gguf`, SHA256 `e47ad95dad6ff848b431053b375adb5d39321290ea2c638682577dafca87c008`. Serving uses llama.cpp build 12359, commit `b1b770d90`, one slot with one weightset, aggregate context 131072, 131072 tokens per slot, Q8 KV caches, flash attention and YaRN scale 4 from 32768. The extended context differs from the 64K LoCoMo configuration and exceeds the GGUF metadata's native 32K window. Every complete prompt has a 4096-token reserve; no context is silently truncated. `model_server_guard.sh` contains the actual launcher and pressure guard. It starts only at normal pressure with at least 40% available memory and stops its own server at warning or critical pressure.

## Protocol

Seed 20261122, temperature zero. Full context receives the complete eligible history, including timestamps where the data provides them. Both retrieval methods use the same 100-word chunks with an 80-word stride, retrieve up to 20 available chunks, and present selected chunks in source order. Plain RAG uses normalized exact cosine similarity with pinned [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41) on CPU, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions. Its encoder has a 256-wordpiece-token limit, which can truncate a chunk containing unusually long words or many pseudonyms. It also truncates long semantic-retrieval queries, including EventQA questions that contain prior events and candidate answers. The shared reader still receives the full question and the complete selected chunks. `results/embedding-limits.json` counts exposure separately for queries and chunks. BM25 uses rank-bm25 0.2.2 defaults with lowercase word tokenization. There is no reranker, memory extraction, store updating or graph construction.

PERSON candidate words detected by spaCy en_core_web_sm 3.8.0, apostrophe surname parts and synthetic persona subject words become compact PersonNNN aliases in word-hash order. Candidates must be non-stopwords capitalized in at least 80% of occurrences. These aliases are applied before indexing, generation and scoring. The mapping is built for privacy only; references and evidence never enter the search index. This transformation can impair pretrained associations and increases token counts. Dataset excerpts and full histories remain in disposable scratch; retained outputs contain item IDs, hashes, generated answers, scoring decisions, usage and timings. Source data are fetched by script, not copied into the repository. HaluMem's CC BY-NC-ND terms do not grant commercial republication of its dataset text.

**MemoryAgentBench:** 30 uniformly sampled questions from each of all five `eventqa_65536` histories, N=150. The paper describes five EventQA histories and 500 questions. This is a sample from the small-context EventQA stratum of Accurate Retrieval, not all four benchmark competencies. The official EventQA binary recall requires every reference answer element to appear verbatim as a case-insensitive substring. The answer instruction explicitly requests copying the selected candidate event. A semantically correct paraphrase can still fail this official metric. The paper's main EventQA figures use the full-length stratum; its small-context long-context figures are more directly relevant. Its EventQA retrieval setup uses 4096-token chunks and top 10, versus the local 100-word chunks and top 20; this changes the retrieval granularity and context budget substantially. The local 192-token initial answer cap also differs from its 40-token EventQA cap. This run cannot test whether any method masters all four competencies.

**HaluMem:** 25 questions from each of six question types, N=150. Within each type, seeded round robin spreads sampling across users before repeating a user. Eligible questions come from sessions 0 through 29 of HaluMem-Medium. Each receives only actual dialogue up to its own session, without future turns, persona summaries, reference memories or annotated evidence. The published Medium dataset contains 3467 questions across 20 users; evaluation counts are not inferred from rounded leaderboard percentages. This earlier-history sample differs from the full Medium corpus and oversamples rare question types. The reader sees no reference answers or evidence. The paper uses GPT-4o for both answer generation and evaluation, with top-20 retrieved memory records from each memory system. The same local Qwen model subsequently judges against the reference and evidence using an adaptation of the official Correct / Hallucination / Omission rubric, including hallucination priority. Invalid JSON is retried and all attempts are retained; truncated responses are not graded. This is downstream QA, not a reproduction of memory extraction or update hallucination accumulation.

Wilson 95% intervals describe question-level rates and assume independent trials. Questions share only five EventQA histories and 20 HaluMem users, so those intervals understate clustering uncertainty. Paired differences additionally use 5000 cluster bootstrap resamples, seeded identically, by history or user. No model tuning is based on reported paper scores. Shared hardware workloads prevent comparative latency or cost claims.

## Primary sources and licenses

| Benchmark | Data revision | Code revision | License and local availability |
| --- | --- | --- | --- |
| [MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench) | `7ea066982b140a19337e17e60d45d4076e042faf` | `538026089d1a8a8eff05121d0db89b388f360eba` | MIT dataset card and code; public data and deterministic EventQA scoring |
| [HaluMem](https://github.com/MemTensor/HaluMem) | `cb04336aa1b732d4b24f5186c552456b4099806e` | `d653749586bfc7d13f5b68e8851f52155b5b1650` | CC BY-NC-ND 4.0 dataset and repository license; public data and judge rubrics; local judge is an adaptation |
| [BEAM](https://arxiv.org/abs/2510.27246) | Official repository count audit | `b2da22eac88bb0874c64665f13457eb99835774a` | MIT code; public conversations and rubrics; local performance adaptation feasible |
| [STATE-Bench](https://github.com/microsoft/STATE-Bench) | Included task files | `5644b1838d96bc4483da29642d058ecaa6f80f7f` | MIT; public environments and scoring; official current protocol requires hosted GPT-5.4 simulator and judge |
| [MemoryArena](https://memoryarena.github.io/) | Linked public task and asset releases | `6cd9de14b71915e39ac742a20dc33785e14b6aab` | Dataset card declares CC BY 4.0; no top-level software license in inspected tree; fetched-source local pilot uses the official reasoning branch, published backbones differ |
| [CMB](https://github.com/Tencent-Hunyuan/Hy-Memory) | Frozen benchmark release not located | `d8138b501a755f662a024f7e8eb879613eabf1d3` | Apache-2.0 memory implementation; paper public, frozen histories and executable grading assets absent from inspected release |

`common.py` records dataset file hashes. `audit_sources.py` independently fetches pinned repository trees, counts all BEAM question files and STATE task files, and records its evidence in `results/source-audit.json`. It verifies 100 BEAM conversations and 2000 questions across the four release scales, and 450 STATE tasks. It does not measure LIGHT gains, million-token degradation or action completion.

## Evidence

- `results/manifest.json`: source pins, fixed sample IDs, sampling rule, privacy method and input hashes.
- `results/context-lengths.json`: exact local-model token counts for every admitted full history.
- `results/items/<benchmark>/<method>/<id>.json`: checkpointed raw answers, response metadata, retrieval chunk IDs, hashes and scores; HaluMem judge responses and labels.
- `results/summary.json`: reconstructed rates, strata, labels and paired cluster-bootstrap differences.
- `results/manual-audit.json`: tester's hand review of at least 40 local judge decisions, not an independent human audit.
- `results/verification.json`: pairing, length, source-hash, score reconstruction and negative-control checks.
- `results/source-audit.json`: metadata pilots and specific replication limits for the remaining benchmarks.
- an unpublished raw log: final resource cleanup evidence.

The editor-facing claim-by-claim report is `REPORT.md`. The harness never writes the book chapters and makes no commits. Cleanup is task-owned and must be performed after a run; the reproduce command does not delete evidence or automatically remove provisioned resources. After both manual audits and verification, `cleanup.py` uses system Python and the provisioner's `MODEL_SSH` and `TUNNEL_PID` environment settings. It refuses active task interpreters, verifies server/guard/tunnel ownership, stops those processes, removes only the fixed task scratch directories, and saves sanitized disk and process evidence.

Final output privacy: after every answer and judge decision is complete, `privacy_export.py` masks residual names missed by input NER, including joined synthetic relationship names. Scores and effective scoring inputs remain unchanged; original response and record hashes are retained. The export is therefore a privacy-redacted record, not a byte-identical original response. Private originals support the tester audit and score reconstruction until scratch cleanup.

Score uncertainty includes more than question sampling: the local judge can make correlated mistakes, including favoring answers produced by the same model. The tester audit measures observed agreement on a small sample and does not remove that bias or certify the dataset references.

Measured encoder limits: 111/150 EventQA retrieval queries exceed 256 wordpieces (maximum 351), while 0/150 HaluMem queries do (maximum 41). None of 3170 EventQA chunks or 40792 HaluMem chunks exceeds the encoder limit. Thus the semantic retriever represents a truncated query for 111 EventQA items; BM25 and the shared reader use their complete questions. This is a substantial setup difference, and the experiment cannot isolate its effect from other reader and retriever differences.

MemoryArena bounded pilot: `arena_pilot.py` fetches pinned official math agent, environment, and long-context-memory files into scratch and executes their public reasoning-only path through a local backend adapter. A seeded choice among three five-step chains selects dataset row 7. It compares full-history with no-memory across all five steps, withholding judge feedback from memory, freezes memory timestamps, and never invokes the coding tool. It is gated behind all 900 primary answers being scored. The dataset revision is `da1a37c8b19280e18627ca01cf368195a5e1d92e`, declared CC BY 4.0. Software source is fetched rather than redistributed because the inspected repository has no top-level license. The inspected environment step does not forward the question to its equivalence judge; that behavior is retained and will be hand-checked on every pilot judgment. This small check cannot validate cross-benchmark saturation or the full action suite.

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


MemoryArena pilot result (bounded, formal-reasoning math only):

One seeded five-step chain (dataset row 7) run through the official reasoning agent, memory entry builder, environment step and yes/no judge, with the same local reader. Full-history memory answered 4 of 5 steps correctly (Wilson 95% 37.6% to 96.4%) and no-memory 3 of 5 (23.1% to 88.2%). N=5 per method, one chain, no coding tool and no action environments: this is a smoke test that the public pipeline runs locally, not a measurement of action completion, and it says nothing about the author-reported contrast with LoCoMo. The tester hand-read all 10 judgments (`results/arena-pilot/manual-audit.json`): the environment judge agreed with the tester on 8 of 10. It marked full-history step 2 wrong although -a^-1 w(a) b equals -b^2 w(a) when b is the inverse of a, and marked full-history step 3 right although the answer replaced v(x_i) with the coordinate derivation without justification. Evidence: `results/arena-pilot/summary.json`, `results/arena-pilot/manifest.json`, `results/arena-pilot/items/`.

Suggested replacement for the chapter 16 MemoryArena sentence: "This book ran only a five-step reasoning pilot of MemoryArena's public code with a local model and has not measured action completion there. Its reported contrast with LoCoMo remains an author-reported result."



## Cleanup (completed)

`cleanup.py` ran after verification, the pilot and both hand audits. It verified ownership of the model-host guard, server and the local SSH tunnel, stopped only those, closed local port 39780, removed the model-host task folder (about 8.4 GB including weights, before removal), removed the local scratch folder (about 1.0 GB: environment, inputs, indexes, private originals) and the task's `__pycache__` folders. No containers, images or volumes were created. The shared model host kept its other servers running; the model host's memory pressure stayed at normal level for 7038 samples and showed one warning sample (already recorded in `results/pressure-recovery.json`); all 1380 logged generation slots reported no truncation. Disk, process and pressure evidence before and after is in an unpublished raw log. A pre-existing shared Python 3.12 interpreter was deliberately not removed. Only this territory folder remains.

# Local agent-memory security study

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

This complete study combines 3,000 real-library storage-tampering outcomes with four local model attack families. The model experiments are documented transfers to toy agents, rather than replications of the papers' full benchmark systems. All headline model arms use 100 paired items, including zero-success cells.

## Reproduce or validate

```bash
bash benchmarks/security/run_study.sh
```

Run from the companion repository root on Linux with Docker and Python 3.12+. The command runs or resumes storage trials, checks saved model cells, deterministically rescores answers, validates every required item and generates the combined summary. With the supplied complete checkpoints, it needs no neural model download. A fresh run downloads pinned public artifacts, serves one CPU model at a time, checkpoints per item and removes task-owned containers, downloaded weights, caches and scratch on exit. All large scratch is under `/data/scratch/membench/security/`; each large installation checks for at least 20 GiB free on the system disk. Do not run this command while another security run uses that scratch root.

To independently repeat generation, copy this folder and remove only the copied model-family JSONL files and review audit, plus the three copied storage JSONL files. The command intentionally requires actual tester inspection of at least 40 new write-review decisions before accepting a new audit. The supplied audit applies to the supplied outputs and is checked against their input hashes. This manual inspection is not an independent human annotation. `run.sh` alone reproduces the storage portion.

## Published and local results

| Family | Published reference | Local undefended | Local defended |
|---|---|---|---|
| MINJA | >95% injection; 70% attack (chapter restatement) | 0/100 (0.0%; 95% 0.00–3.70%) | 0/100 (0.0%; 95% 0.00–3.70%) |
| AgentPoison | >80% attack; <1% benign effect | 99/100 (99.0%; 95% 94.55–99.82%) | 0/100 (0.0%; 95% 0.00–3.70%) |
| InjecMEM | No chapter ASR; paper 35.6% joint / 76.6% conditional | 0/100 (0.0%; 95% 0.00–3.70%) | 0/100 (0.0%; 95% 0.00–3.70%) |
| Embedding inversion | 92% GTR/NQ, 50 corrections plus sequence beam | 0/100 (0.0%; 95% 0.00–3.70%) | 0/100 (0.0%; 95% 0.00–3.70%) |

Prompt write-review accepted 0/100 benign factual proposals (Wilson 95% 0.0–3.7%).
The reviewer rejected every tested benign factual write. Defended ASR alone therefore does not demonstrate a useful selective write policy.

Storage adds 15 native and 15 wrapper cells: five edits across three libraries, each with N=100. Every native cell accepted 100/100 edits silently (nominal Wilson 95% CI 96.3–100%); every externally anchored wrapper cell accepted 0/100 (0–3.7%). These deterministic repeats vary five seed lengths, not 100 distinct attack strategies.

See `results/study-summary.json`, `results/study-validation.json` and the combined `results/study-comparison.html`. The complete retrieval, conditional-success, utility and correction-step cells are in `results/model/summary.json`. Intervals describe these sampled toy fixtures; they do not establish robustness against an unseen attack population.

## Model, hardware and sampling

The three prompt-attack families use Qwen2.5-3B-Instruct Q4_K_M, official GGUF revision `7dabda4d13d513e3e842b20f0d435c732f172cbe`, served by llama.cpp b12464 in a pinned container. Hardware is a 32-thread x86 CPU, constrained to eight inference threads, with zero GPU layers. Its normalized mean-pooled 2,048-dimensional hidden states provide actual top-three neural retrieval. This is not a retrieval-trained encoder; low poison recall can explain low joint ASR and is reported separately. Long retrieval inputs are clipped to 510 model tokens. Evaluation and write review use temperature zero; MINJA exploration uses temperature 0.5 with fixed attempt seeds. The fixture/search seed is 20261122. Output limits are 64 tokens for MINJA, 48 for AgentPoison, 96 for InjecMEM, 12 for write review and 128 total decoder tokens for inversion. Malformed or token-limited outputs remain in the denominator; truncation counts are reported and request errors prevent completion.

Inversion uses the released GTR-base and learned Vec2Text hypothesizer/corrector checkpoints, one neural model at a time, on four CPU threads. Linear and token-embedding weights use symmetric int4/group64; scales, biases, norms and narrow relative-position embeddings remain float32. CPU matmuls cache float32 values decoded from Q4 linear weights until unload, preserving Q4 precision without claiming Q4-only resident memory. Source/model revisions, license observations, dependency freezes and container digests are shipped. No model weights or downloaded query sets are committed.

The assigned model hosts reached kernel warning pressure, so their task-owned services stopped and were cleaned. The authorized CPU fallback produced every headline model cell. Earlier Mac MINJA prototype outputs are retained as excluded diagnostics in `results/model/minja-fixed-sequence.jsonl`; they stored unsuccessful actions and lacked the source retry/admission sequence. Source inspection corrected that implementation before the CPU cohort. A source-aligned Mac pilot was later interrupted by pressure; `minja-mac-interrupted.jsonl` is also excluded. These diagnostics contribute no headline outcome or confidence interval.

## Methods and defense boundaries

MINJA follows the official five indication templates, then an unhinted injection stage, up to three attempts per stage. Only generated target actions may enter memory; defended writes also need review. Final persistence is measured on a differently worded held-out query. The 100 distinct victim/target/price triples come from a 15-product catalog; the 100 triples yield only 43 distinct held-out request patterns. The operational tool recognizes one complete product phrase in JSON. Memory stores action demonstrations instead of the original reasoning-rich trajectories, an important missing channel of the published mechanism. There is no full RAP reasoning stack, WebShop environment or purchasing action.

AgentPoison adds two official-template poison demonstrations to 2,000 benign arithmetic records (2/2,002, below 0.1%). Thirty-two fixed-seed candidate triggers are searched against genuine neural embeddings on eight training queries; 100 distinct held-out arithmetic questions have triggered and untriggered evaluations in all arms. This black-box compactness/separation search replaces the paper's gradient optimization. It is a material weakening, so local rates cannot confirm or contradict the paper's reported average.

InjecMEM uses the unchanged released health payload against 100 unique questions: 95 released evaluation queries plus the first five distinct first-user turns from the released health conversations. One hundred sports questions are unrelated-topic controls. Genuine recall determines exposure; early/late placement alternates after retrieval. The released payload is proposed directly as one memory record; chat-turn extraction and compaction are not reproduced. This is a post-insertion retrieval/generation transfer from a 7B-family payload to a 3B toy assistant, without fresh white-box optimization or full MemoryOS. Joint and retrieval-conditional success are separate.

Inversion attacks 100 distinct synthetic, generic landscape/object records, canonicalized to exactly 32 tokenizer tokens. Step zero is learned inversion; five greedy correction steps follow, with no ground-truth candidate selection or sequence beam. This low-entropy synthetic distribution, Q4 inference and five-step budget differ substantially from the paper's Natural Questions and 50-step sequence-beam setting. Undefended vectors embed the source; defended vectors embed opaque references, while text remains in a separate simulated authorized SQLite vault. The vault control tests access by reference, not semantic-search utility. The frozen-model attack sees vectors alone; knowledge of the public synthetic recipe or reference-to-source mapping is outside that probe. Recall quotation cannot protect stolen vectors.

For prompt attacks, the defense bundle reviews proposed untrusted writes, quarantines anything except exact `ALLOW`, filters recalls by application-controlled trust metadata, and quotes recalled data with source/trust labels. The model-facing agents expose no configuration-write capability. The released attacks do not request configuration changes, so a separate immutable-tool-gate control tests 100 probes per arm; it does not identify the gate's contribution to model ASR. Trust-label forgery is outside these fixtures. The separate keyed-chain storage test concerns a storage-only attacker and does not authenticate model provenance labels. No ablation identifies each defense's individual effect. Where undefended success is zero, a paired defended zero does not establish that the controls prevented an attack.

Benign factual-write review accepted 0/100 proposals. Exact arithmetic utility, unrelated-topic leakage, retrieval rates, rejected-write counts and the tester's review audit are retained beside headline ASR. The separate benign normative health-note proposal was also rejected. All 100 factual controls were rejected too, so the observed policy does not demonstrate selective benign memory acquisition on these fixtures. The benign controls are ten factual templates varied by record number, not a representative write corpus. The reviewer explicitly guards availability facts, so its handling of legitimate availability changes is not established. Attack success uses deterministic graders, never a model judge. `verify_model_graders.py` includes known positive/negative cases, incorrect source hashes and incomplete-cell rejection; these controls are not attack trials.

MINJA ordinary search success fell from 100/100 undefended to 71/100 defended. Because both arms had zero targeted redirections, this cell shows a utility loss without demonstrated ASR benefit.

AgentPoison ordinary arithmetic accuracy was 91/100 clean, 90/100 poisoned/undefended and 77/100 defended. The observed poisoning-associated drop was 1.0 percentage points, with descriptive paired-bootstrap 95% interval 0.0–3.0 points; this does not establish the published less-than-1% bound. Adding the controls cost 13.0 points relative to the poisoned/undefended arm (bootstrap 95% 5.0–21.0).

## Storage implementation

The official agmi source is pinned at `c43f1c117c82b218f389d603db08e63512ddf16c` (0.7.0, MIT), selecting its original five edits: content mutation, tail truncation, middle deletion, adjacent reordering and forged insertion. Tested libraries are langgraph-checkpoint-sqlite 3.1.1, Letta 0.16.8, Mem0AI 2.0.20 and qdrant-client 1.17.1. Mem0 uses its actual local backend, `infer=False` and the suite's deterministic hashing embedder; that storage result uses no language model. Letta uses an isolated PostgreSQL 15.16 Unix socket. Experimental storage containers have no network.

Each trial writes a fresh store/block through the normal API, verifies clean state and unedited reopen, proves the intended edit landed, then reads/verifies normally. Five seed lengths (5–9) each repeat 20 times. Letta reuses schema/actor and models reload through fresh reads, not process restart. Native and wrapper arms have matched edit/seed-length IDs. The tester-added wrapper checks an ordered HMAC-SHA256 chain against a key and expected head outside the writable store. It is not a native library feature or a durable production anchoring service. Key/head compromise, concurrency, key rotation, head-service availability and overhead were not evaluated.

Raw storage outputs, controls and hashes are in `results/{langgraph,letta,mem0}.jsonl`, `results/controls.json` and `results/validation.json`. Historical permission/disk failures are retained separately and never counted as outcomes. Only complete valid trials enter the 3,000-outcome study.

## Sources, evidence and cleanup

Primary paper checks and suggested book replacements are in [REPORT.md](REPORT.md). `fetch.py` downloads public templates/queries by revision; `results/sources.json` records hashes and licensing. MINJA and AgentPoison source are MIT; agmi is MIT; Vec2Text reference source uses Software for Open Models License 1.0. InjecMEM had no LICENSE at its pinned revision, so its inputs are fetched into scratch and not redistributed. GTR/T5 model cards say Apache-2.0; Qwen's card says `other`; learned inversion checkpoints specify no model-card license. See `results/model/model-revisions-cpu.json` for exact pins, rather than assuming uniform licenses.

`STUDY_PROTOCOL.md` and `GRADING.md` describe sampling, tools and frozen scoring. Source strings are not copied into a working payload collection. No hosted model, private dataset, real user memory, external target or GPU was used. an unpublished raw log records final owned-resource checks and disk snapshots; an unpublished raw log records the one-command resume validation. Initial storage cleanup and pressure-blocked model history remain in `results/cleanup.json` and `results/model-attempt.json`. No chapter file was edited and no commit was made.

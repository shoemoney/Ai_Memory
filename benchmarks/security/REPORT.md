# Editor report: complete local security study

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

This study completed the original storage matrix and all four local model families. Published figures and local toy-transfer estimates have different models, datasets and budgets; they should appear together with those limits, not be labeled direct replications. The combined comparison is `results/study-summary.md`; all headline model cells have N=100.

**Observed defense failure:** the prompt-attack write reviewer accepted 0/100 benign factual proposals. It rejected every tested factual write; zero defended ASR does not demonstrate a useful selective policy. The tester audit agrees with 33 of 44 decisions, retaining 11 benign false rejections.

## MINJA

Printed location: `build/chapters/17-security-eval-ops.html:53; 16-frontier.html:282 cross-reference`. Printed claim: “Over 95%” injection and “70% attack success,” attributed to a follow-up restatement.

Primary check: [MINJA paper](https://arxiv.org/html/2503.03704v5). Primary Table 1 is dataset-specific: the two GPT-4 EHRAgent rows show 95.6%/57.0% and 98.5%/90.0% injection/attack success. A universal 70% is a secondary restatement.

Local result: undefended **0/100 (0.0%; Wilson 95% CI 0.00–3.70%)**; defended **0/100 (0.0%; Wilson 95% CI 0.00–3.70%)**. The local experiment follows the public retry, success-only admission and shortening method, but uses JSON shopping search and held-out paraphrases rather than RAP/WebShop, and stores action demonstrations without the original reasoning-rich trajectories. These local estimates cannot directly confirm or contradict the original paper's benchmark rate.

Ordinary requested-product search succeeded in 100/100 undefended trials and 71/100 defended trials. The combined controls therefore imposed a 29.0-point utility loss without demonstrated ASR benefit in this cell.

Unhinted injection admission is separately 0/100 (0.0%; Wilson 95% CI 0.00–3.70%) undefended and 0/100 (0.0%; Wilson 95% CI 0.00–3.70%) defended. Only final held-out search measures persistence. The earlier fixed-sequence Mac prototype is excluded because it stored unsuccessful actions and lacked the source retry/admission logic.

Suggested replacement (two sentences): “MINJA reports dataset-specific injection and attack rates, rather than one universal success rate. This book's smaller toy redirected 0 of 100 held-out searches without controls and 0 with controls, while ordinary search success fell from 100 to 71 of 100.”

Evidence: `results/model/minja.jsonl`, `results/model/summary.json`, `STUDY_PROTOCOL.md`, `GRADING.md`, and `results/sources.json`.

## AgentPoison

Printed location: `build/chapters/17-security-eval-ops.html:54; 16-frontier.html:282 names the attack`. Printed claim: “At least 80%” average attack success and “about 1%” normal-performance effect.

Primary check: [AgentPoison paper](https://arxiv.org/abs/2407.12784). The abstract says above 80% ASR, less than 1% benign effect and below 0.1% poison fraction.

Local result: undefended **99/100 (99.0%; Wilson 95% CI 94.55–99.82%)**; defended **0/100 (0.0%; Wilson 95% CI 0.00–3.70%)**. The local 2/2,002 poison fraction matches that scale; a 32-candidate black-box neural trigger search replaces gradient optimization, and the task is arithmetic QA. These local estimates cannot directly confirm or contradict the original paper's benchmark rate.

Actual triggered poison recall was 100/100 undefended and 0/100 defended. This fixed transfer can test the poisoning mechanism and the combined controls, without establishing original-benchmark equivalence.

Untriggered arithmetic utility, clean: 91/100 exact answers; target leakage 0/100. Untriggered arithmetic utility, undefended: 90/100 exact answers; target leakage 0/100. Untriggered arithmetic utility, defended: 77/100 exact answers; target leakage 0/100. The observed poisoning-associated accuracy drop was 1.0 percentage points, with descriptive paired-percentile-bootstrap 95% interval 0.0–3.0 points (10,000 resamples, fixed seed). This does not establish a less-than-1% bound. This task-specific utility comparison is not the original paper's less-than-1% multi-benchmark estimate.

Suggested replacement (two sentences): “AgentPoison reports attack success above 80%, a poison fraction below 0.1%, and less than 1% impact on benign performance. This book's smaller neural-retrieval transfer reached 99.0% without controls and 0.0% with controls on 100 paired questions using a weaker black-box trigger search, but the reviewer also rejected all 100 benign factual writes; ordinary untriggered accuracy fell from 90 to 77 of 100 with controls.”

Evidence: `results/model/agentpoison.jsonl`, `results/model/summary.json`, `STUDY_PROTOCOL.md`, `GRADING.md`, and `results/sources.json`.

## InjecMEM

Printed location: `build/chapters/16-frontier.html:283 and 17-security-eval-ops.html:61`. Printed claim: one interaction, reliable related-topic retrieval and unrelated queries unaffected; neither location prints an ASR.

Primary check: [InjecMEM paper](https://arxiv.org/html/2608.23471v1). Paper Tables 2–3 report MemoryOS 76.6% conditional and 35.6% joint ASR; MemGPT 48.6% and 18.1%. Conditional and joint rates must remain distinct.

Local result: undefended **0/100 (0.0%; Wilson 95% CI 0.00–3.70%)**; defended **0/100 (0.0%; Wilson 95% CI 0.00–3.70%)**. The unchanged released payload is directly proposed as a memory record and transfers from its 7B-family optimization to a 3B toy model; single-chat-turn extraction/compaction is not reproduced. The 100 unique health questions include 95 evaluation queries plus five released conversation prompts; 100 sports controls are separate. These local estimates cannot directly confirm or contradict the original paper's benchmark rate.

Undefended actual poison retrieval: 0/100; conditional target success not estimable (no exposed trials). Defended actual poison retrieval: 0/100; conditional target success not estimable (no exposed trials). No forced recall or topic router is used. Unrelated-topic cells are in the full summary; ordinary response quality was not independently graded.

Suggested replacement (two sentences): “InjecMEM's MemoryOS results distinguish 76.6% conditional success from 35.6% joint success. This book's released-payload transfer achieved 0.0% joint success without controls and 0.0% with controls on 100 paired questions after direct memory insertion, with poison recalled in 0 of 100 undefended queries.”

Evidence: `results/model/injecmem.jsonl`, `results/model/summary.json`, `STUDY_PROTOCOL.md`, `GRADING.md`, and `results/sources.json`.

## Embedding inversion

Printed location: `build/chapters/17-security-eval-ops.html:55; confidentiality lesson at line 87`. Printed claim: “92%” exact recovery of 32-token inputs, with wording implying both encoders.

Primary check: [Embedding inversion paper](https://arxiv.org/html/2310.06816v1). Table 1 gives 92.0% for GTR-base/Natural Questions, using 50 corrections plus sequence beam. The hosted-encoder 32-token result is 60.9% on MSMARCO, so the chapter must not attribute 92% to both.

Local result: undefended **0/100 (0.0%; Wilson 95% CI 0.00–3.70%)**; defended **0/100 (0.0%; Wilson 95% CI 0.00–3.70%)**. Local GTR and learned Vec2Text weights are Q4, with five greedy corrections on 100 synthetic 32-token records rather than Natural Questions. Defended vectors contain opaque references; authorized vault lookup does not measure semantic-search utility. The defense implements the advice in Chapter 17 line 87 to exclude protected text at write time and refer to it by ID. These local estimates cannot directly confirm or contradict the original paper's benchmark rate.

Mean word F1 is 0.724 undefended and 0.000 defended; whole-word matches for the three varying attributes are 287/300 and 0/300, with possible incidental credit from shared scaffold. No chat model guessed from a printed vector, and ground truth did not select candidates. The hosted encoder remains outside this local-only study.

Suggested replacement (two sentences): “The authors recovered 92% of 32-token Natural Questions inputs from GTR-base embeddings; their hosted-encoder result was 60.9% on a different dataset. This book's five-step Q4 synthetic probe recovered 0 of 100 sources exactly and 0 when only opaque references were embedded; mean word-overlap F1 was 0.724 without exclusion and 0.000 with it, while semantic-search utility was not tested.”

Evidence: `results/model/inversion.jsonl`, `results/model/summary.json`, `STUDY_PROTOCOL.md`, `GRADING.md`, and `results/sources.json`.

## Direct store tampering

Printed location: `build/chapters/17-security-eval-ops.html:74`, all 15 direct edits accepted silently in the three named libraries. Primary sources are the [preprint DOI](https://doi.org/10.2139/ssrn.7461118), [publisher-deposited abstract](https://api.crossref.org/works/10.2139/ssrn.7461118) and [official agmi implementation](https://github.com/tech4biz-yasha/agmi).

Local result: 100/100 edits accepted in every native cell, nominal Wilson 95% CI 96.3–100%; 0/100 accepted in every external-chain wrapper cell, 0–3.7%. Fifteen edit/library cells produce 1,500 native and 1,500 wrapper trials. This supports the narrow storage-only result for the pinned versions and original five edits. Repetition covers five seed lengths and does not represent 100 different strategies per cell.

Suggested replacement (two sentences): “This book repeated five storage edits against each of the preprint's three pinned libraries, and all 1,500 native trials accepted the edits silently. A tester-added keyed chain with its expected head held outside the store detected all 1,500 corresponding edits, under a storage-only attacker.”

Evidence: `results/{langgraph,letta,mem0}.jsonl`, `results/summary.json`, `results/controls.json`, `results/validation.json`. Libraries are langgraph-checkpoint-sqlite 3.1.1, Letta 0.16.8 and Mem0AI 2.0.20. Mem0 uses `infer=False` and a hashing embedder for this storage test; it is separate from the neural model study. The wrapper is not a native library feature, keeps its head only in the tester process during each trial, and does not evaluate durable anchoring, key management, concurrency or performance.

## Controls, validity, failures and cleanup

The separate benign normative health-note proposal was rejected; the tester disagreed with that review decision. The prompt defense is one bundle: local-model review, quarantine, trusted-field retrieval filtering and source/trust quotation. These fixtures assume application-controlled provenance fields. An attacker who can forge those fields is outside the model comparison. Configuration edits are blocked by an immutable gate, but only separate functional probes activate it, so its contribution to ASR is not identified. The storage-chain experiment does not independently authenticate these model labels. No defense ablation or universal safety claim follows.

The benign-write reviewer accepted 0/100 ordinary proposals. The tester inspected 44 actual reviewer decisions, with input hashes and labels in `results/model/review-audit.json`; this was the tester assistant, not an independent human. Success grading is deterministic. Seeded grader controls prove positive/negative discrimination, source-hash rejection and incomplete-cell rejection, but are not attack outcomes. Invalid requests fail validation rather than becoming zeros.

The first storage attempts hit permissions and disk exhaustion; unscored records remain in separate pilot/disk-error files. Dedicated writable directories, Mem0 tmpfs and recovered disk space allowed all cells to finish. Initial Mac serving stopped on warning memory pressure. The replacement host also entered warning pressure, and its own guards stopped task-owned services; existing benchmark services were untouched. The complete headline cohort therefore uses the authorized CPU fallback. A host HTTP adapter later exited during InjecMEM while the CPU backend remained live; its unscored transport error is retained in `results/model/cpu-prompts-first-attempt.log`. Moving the same forwarding protocol into a detached task container allowed the same checkpoint IDs and seeds to resume, without dropping completed outcomes. The excluded Mac MINJA prototype and its audit are diagnostic history, not part of the final rates.

`run_study.sh` is the one-command resume/reproduction entry point. It runs exactly the shipped harness, whose pinned dependency/container/model/source manifests are included. an unpublished raw log records its completed resume validation; `results/study-validation.json` records all required cells and output hashes. an unpublished raw log records final disk snapshots and the absence of task-owned servers, tunnels, containers, aliases and scratch. Older cleanup history is retained separately.

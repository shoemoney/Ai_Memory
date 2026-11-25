# LongMemEval: small local oracle-history run

This is a reduced-history, reduced-sample experiment, not a reproduction of the headline LongMemEval_S scores. LongMemEval tests information extraction, reasoning across sessions, temporal reasoning, knowledge updates, and abstention. Its public oracle split retains only evidence sessions. Full context below means every session in that oracle split, not the approximately 115,000-token histories in LongMemEval_S.

## Run

Prerequisites: Linux with Python 3.13.18 and uv 0.13.9; a local OpenAI-compatible model endpoint, optionally reached over an SSH tunnel. No hosted inference service is used. The endpoint must resolve to this machine's loopback interface. From the repository root:

```bash
BASE_URL=http://localhost:39710/v1 MODEL=default_model bash benchmarks/longmemeval/run.sh
```

This installs the exact Python dependency versions in `requirements.txt`, downloads the pinned public dataset and CPU embedding model, runs generation and scoring, and writes to `benchmarks/longmemeval/rerun-results/`. Set `RESULTS_DIR` to a fresh directory to repeat from scratch. A completed results directory resumes by skipping scored item/method pairs. The script deletes its scratch environment and downloads on exit. Do not run two copies with the same `LAB_DIR`; its default is `/var/tmp/membench-longmemeval`.

Serve the answerer and judge with MLX-LM 0.32.2, MLX 0.32.4, Transformers 5.20.2, and huggingface-hub 2.3.0 on an Apple M1 Ultra with 64 GB unified memory. Download `mlx-community/Qwen3.5-9B-4bit` at revision `8b2b98c00a6b4d291155e4890773ca8f769aee53` into an isolated model directory. The model card declares Apache-2.0; the dataset card declares MIT. The retrieved metadata is recorded in `results/sources.json`. The exact server flags were:

```bash
mlx_lm.server --model "$MODEL_DIR" --host localhost --port 39710 \
  --chat-template-args '{"enable_thinking":false}' \
  --prompt-cache-size 1 --prompt-cache-bytes 2147483648 \
  --prefill-step-size 512 --max-tokens 2048
```

Create the configured Hugging Face cache's `hub/` subdirectory before starting MLX-LM: its model-list endpoint errors if that cache is absent. Set `HF_HOME` inside the isolated model directory. For a separate model host, tunnel port 39710 to localhost, and stop that server and tunnel and delete the isolated model directory afterward. Check macOS `memory_pressure` before loading, require at least 40% system-wide memory free, and stop your server if `kern.memorystatus_vm_pressure_level` becomes warning or critical. This run monitored that level every 30 seconds. Existing services must remain running.

The harness uses a 32-thread x86 CPU for BM25, MiniLM embeddings, Qdrant and scoring orchestration. It hides CUDA devices and explicitly selects CPU for embeddings; the machine's NVIDIA GPU was not used. The pinned PyTorch distribution has CUDA dependencies, but embedding computations in this experiment used its CPU backend. No container is needed.

## Data and scoring

- Official repository and scoring revision: [LongMemEval at 9e0b455](https://github.com/xiaowu0162/LongMemEval/tree/9e0b455f4ef0e2ab8f2e582289761153549043fc).
- Official dataset: [longmemeval-cleaned](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned), revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`, MIT license according to its dataset card. File: `longmemeval_oracle.json`, 500 records. SHA-256 and selected IDs are in `results/manifest.json`. This later cleaned release differs from the original paper release.
- Sample: seed 20261121; sort records by question ID within each sorted stratum, then Python `random.Random(seed).sample(..., 2)`. `_abs` IDs form a separate abstention stratum; all other records retain the six official question types. N=14, two per stratum, not weighted to the original category distribution. Abstention is an overlay in the official data, not a seventh original question type.
- Judge: the same local Qwen3.5-9B-4bit as the answerer, replacing the paper's GPT-4o judge. `judge_prompt.py` retains the official task-specific prompt function verbatim, with its MIT notice in `LICENSE.upstream`. It includes temporal off-by-one tolerance, preference rubrics and abstention handling. Judge output limit is 10 tokens. Basic positive, negative and abstention controls passed; this is not a validation of agreement with human judges.
- Temperature zero throughout. Explicit seed 20261121 for answer/judge requests; Mem0 uses temperature zero with no explicit seed. Thinking is disabled server-wide. Answers are limited to 512 tokens; Mem0 extraction/update calls to 2048. Raw finish reasons remain in the evidence.

## Systems

1. **Full context:** all timestamped oracle sessions, both speakers, JSON history, chronologically sorted, with no truncation. Evidence-label fields are removed before generation.
2. **Plain BM25 RAG:** split each utterance into 800-character windows with stride 700, rank with BM25Okapi defaults over lowercase word tokens, retrieve ten chunks, and restore history order. Both speakers and dates are retained. This is a lexical baseline, not the paper's Stella dense retriever.
3. **Mem0 OSS 0.1.118:** session-by-session `Memory.add(..., infer=True)`, default extraction and update prompts, the same local model, all-MiniLM-L6-v2 CPU embeddings (384 dimensions, pinned revision in the manifest), embedded Qdrant, an isolated user namespace per question, then `Memory.search(..., limit=10)`. Session dates enter as system messages and metadata. Both speaker roles are supplied, but Mem0's default extraction policy can omit assistant details. No proprietary managed algorithm, graph, custom extraction prompt or extra agent loop is used.

Every system shares the answer prompt and judge prompt. Ground-truth answers enter only the judge. Retrieved memories include session dates. Original oracle selection already gives all systems evidence-session information; this is a substantial retrieval advantage compared with standard LongMemEval_S.

## Results

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


Confidence intervals are descriptive 95% Wilson intervals treating the 14 selected questions as Bernoulli trials. Equal stratum allocation, tiny per-category samples, shared questions, and a shared local judge limit their interpretation; they do not describe judge error or establish significance between systems.

Published anchors:

| Published setup | Published figure | Local counterpart |
|---|---:|---|
| Mem0 managed April 2026 stack, retrieval budget 200 | 94.4% (N not stated in the headline table) | Mem0 OSS result above; different implementation and history setting |
| Zep paper, LongMemEval_S | Up to 18.5% higher accuracy; about 90% lower response latency | Not reproduced: Zep was not tested |
| Original LongMemEval paper, direct reading, oracle, Llama 3.1 8B | 71.0%, N=500 | Full-context result above; different model, data revision, prompt and judge |
| Cost-analysis paper, cached 100,000-token context | Break-even near ten turns | Not measured; no API prices or repeated-query cost experiment |

The vendor figure and local scores are shown together for provenance, not as comparable estimates. This experiment cannot support or contradict the vendor headline, the Zep improvement/latency claim, the full-context degradation claim, or the API cost crossover. It only describes these local configurations on these 14 oracle questions. No tuning toward the published figures was performed.

## Evidence and limits

`results/items.jsonl` contains all scored answers, references, contexts, prompts, verdicts, timings, token usage and finish reasons. `results/llm.jsonl` keeps raw answer/judge requests and responses. `results/memory-llm.jsonl` keeps raw Mem0 extraction/update requests and responses; `results/memory-events.jsonl` keeps memory actions and stored records. `results/sample.json` is the exact public-data sample. These files contain public benchmark dialogue entities, never operator identity or private machine addresses. `results/summary.json` is the aggregate; `REPORT.md` maps the book's claims to evidence and proposed wording.

Run `python3 benchmarks/longmemeval/verify.py` to audit the shipped results without a model. The verifier checks paired coverage, fixed references, source hashes, score totals, basic judge controls, token usage, and removal of evidence labels from full-context prompts. Wall-clock timings include shared-host interference and cache effects; method order was fixed, not randomized. They are not a hardware comparison or a test of Zep's latency claim. Extraction failures or omitted facts remain part of Mem0's observed behavior. An editorial spot check flagged possible false-negative verdicts on all three answers to photography-preference question `06878be2`; see `results/judge-audit.json`. Those labels remain unchanged. The raw scores are local-judge outputs, not human-validated accuracies.

Primary sources: [LongMemEval paper](https://arxiv.org/abs/2410.10813), [Mem0 repository](https://github.com/mem0ai/mem0), [Mem0 evaluation framework](https://github.com/mem0ai/memory-benchmarks), [Zep paper](https://arxiv.org/abs/2501.13956), and [memory versus long-context cost study](https://arxiv.org/abs/2603.04814).

> **PILOT ONLY: 40 questions from one conversation. Not the expanded book result.**

# Reduced LoCoMo reproduction

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

LoCoMo asks questions about facts, dates, relationships, and plausible inferences from long conversations. This is a small local adaptation of the independent comparison in [arXiv 2601.07978v5](https://arxiv.org/html/2601.07978v5), not an exact replication or an architecture ranking. The official LoCoMo repository supplies token-overlap F1 scoring; the cited comparison instead uses a generous LLM judge. This run follows that comparison's binary judging approach with a different, local judge.

## Run

With `uv` installed and the model endpoint already available through localhost, run from the repository root:

```bash
BASE_URL=http://localhost:39700/v1 MODEL=qwen2.5-14b-instruct bash benchmarks/locomo/run.sh
```

The default endpoint is localhost. Remote model serving must be reached through an SSH tunnel. `MODEL`, `BASE_URL`, `LAB_DIR` (default `/var/tmp/membench-locomo`), and `OUT_DIR` are settings. The default output is a new timestamped directory under `results/`, so the retained measured run is preserved. Existing result files are protected. Reruns require a fresh `LAB_DIR` as well as a fresh output directory, because reusing a populated Mem0 store would contaminate the run. The script creates an isolated Python 3.12.16 environment, synchronizes `requirements-lock.txt`, downloads the fixed data and embedding revisions, indexes, answers, judges, and writes all results. It does not provision a remote host or remove scratch automatically. After saving results, remove the scratch directory and stop the model server and tunnel you started.

The measured server was llama.cpp build 12359, commit `b1b770d90`, using Qwen2.5-14B-Instruct Q4_K_M. [Weights](https://huggingface.co/bartowski/Qwen2.5-14B-Instruct-GGUF/tree/05244aa5d871c661c80082a15d3bce44714d068d), file `Qwen2.5-14B-Instruct-Q4_K_M.gguf`, SHA256 `e47ad95dad6ff848b431053b375adb5d39321290ea2c638682577dafca87c008`.

Equivalent server settings, with `MODEL_FILE` pointing to those weights:

```bash
llama-server --model "$MODEL_FILE" --alias qwen2.5-14b-instruct \
  --host localhost --port 39700 --ctx-size 32768 --parallel 1 \
  --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --cache-ram 0 --jinja
```

## Data and method

[Official data and scoring code](https://github.com/snap-research/locomo/tree/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376), revision `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`. Data SHA256: `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`. The repository's `LICENSE.txt` specifies CC BY-NC 4.0. Retained question and conversation excerpts are derived from that dataset, with names replaced; the dataset's noncommercial terms remain relevant to redistribution. No license clearance for commercial republication is implied.

Fixed seed 20261121. Within conversation index 0, sample ten questions without replacement from each category 1 through 4, then sort by original question index: 40 questions total, reused for all systems. All 19 actual sessions and 419 turns are indexed. Empty date-only entries are excluded. Category 5 is excluded, as in the independent comparison. No question, answer key, evidence annotation, event summary, observation, or session summary is ingested into memory. Image captions and image queries are included as text.

Names in the data and extraction examples are replaced consistently by pseudonyms using token hashes in `name-hashes.json`; this is a transformation relative to the original benchmark. It also removes world-knowledge associations of famous names. Original question hashes and indices identify the source items without retaining their names.

Full context receives all turns with session timestamps. RAG embeds individual turns with the CPU model [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41), revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions, and uses normalized vectors with exact cosine search in NumPy, top 20. Mem0 2.2.1 uses the same local embedder, embedded Qdrant, and real `Memory.add(infer=True)` extraction. It ingests eight consecutive turns per call, preserving session boundaries, and retrieves up to 20 memories with the default threshold 0.1. Optional spaCy, BM25, and reranking are absent, so Mem0 uses semantic retrieval. Extraction is anchored to each session date by overriding its date resolver and includes instructions to preserve both speakers.

One Qwen2.5-14B-Instruct model provides extraction, answers, and one judge call per answer. Temperature is 0 and seed is 20261121. Limits are 2,048 output tokens for extraction and 256 for answers or judge responses. Length-stopped completions and invalid judge JSON cause failure rather than silently passing. The judge prompt in `run.py` paraphrases the comparison's generous topic-match policy, including absolute-date matching. Answer prompts are shared by all three systems and permit general knowledge for open-domain questions. Answers are generated before judging each backend, allowing prefix-cache reuse without sharing answers between questions.

## Hardware and versions

Generation and judging: Apple M3 Ultra, 96 GB, one model at a time for this task. Indexing, embeddings, stores, and scoring: 32-thread x86 CPU; eight PyTorch CPU threads. No NVIDIA GPU was used. Other workloads were not controlled, so latency is not an architecture or cost comparison.

Python 3.12.16; mem0ai 2.2.1; sentence-transformers 6.3.0; NumPy 2.5.5; OpenAI client 3.57.0; qdrant-client 1.20.0; PyTorch 2.15.0+cpu; Transformers 5.24.0. All resolved dependencies are pinned in `requirements-lock.txt`. The OpenAI client is only a local HTTP client; no hosted inference API is used.

## Results

| System | Published accuracy | Local accuracy, N=40 | Descriptive 95% Wilson interval |
|---|---:|---:|---|
| Full context | 77.16% | 57.5% (23/40) | 42.2% to 71.5% |
| Plain RAG | 78.31% | 50.0% (20/40) | 35.2% to 64.8% |
| Mem0 OSS | 81.08% | 62.5% (25/40) | 47.0% to 75.8% |
| Graphiti | 56.03% | Not run | Not applicable |
| Cognee | 55.27% | Not run | Not applicable |

Published figures are macro means across ten conversations, with 1,540 unique questions before the paper's anomaly exclusions, replayed in two network scenarios. The paper's plus-minus values are standard deviations across conversations, not confidence intervals. Local accuracy weights the four categories equally on one conversation. The original non-adversarial dataset has category counts 282, 321, 96, and 841; this sample has ten of each, so it is not a prevalence-weighted estimate. Wilson intervals are descriptive only: shared conversation context, a fixed stratified sample, and judge error prevent treating them as generalization guarantees.

The paper uses GPT-4o-mini for extraction, answer generation, and judging; text-embedding-3-small for embeddings; a tool-driven coordinator; and majority votes over three judge calls. This run changes those models, judge repetition, prompts, ingestion batching, framework version, store deployment, category weighting, names, hardware, and network setup. The full-context input is flattened timestamped text instead of the comparison implementation's raw conversation JSON, and Mem0 receives joined user messages instead of the original turn-role mapping. It does not reproduce the managed Mem0 service, the vendor's 26% relative gain, Graphiti's vendor result, the filesystem agent, or the 100K-context cost crossover.

This experiment cannot support or contradict the published graph-versus-vector gap because no graph system was run. Local results describe this subset and configuration only. Six sampled questions are flagged by the external label audit; original labels are retained throughout, and the external flags are not treated as adjudicated corrections. See `REPORT.md` for citation corrections and editor-ready wording.

## Evidence

- `results/local/summary.json`: counts, category counts, and descriptive intervals.
- `verify.py` and `results/local/verification.json`: offline reconstruction from raw model decisions, sample alignment, completion checks, and the measured code hash.
- `results/local/selection.json`: question IDs, pseudonymized references, original-question hashes, and categories.
- `results/local/items.jsonl`: every answer, reference, retrieved context, judge explanation, and correctness decision.
- `results/local/model-calls.jsonl`: raw local requests and responses, token usage, finish reasons, and call duration.
- `results/local/ingest.jsonl` and `extracted-memories.json`: actual Mem0 additions and the complete persisted store. `export_memories.py` scrolls the store after scoring and cross-checks every ID and text against the ADD log; `mem0-api-preview.json` retains the original limited API listing.
- `results/local/indexed-conversation.json` and `manifest.json`: exact transformed input and run settings.
- `results/published-evidence.json` and `sample-audit-overlap.json`: primary-source provenance and label-audit flags.
- an unpublished raw log: resource checks and cleanup evidence.

# Inkling reader and quality checks

These adapters change the **reader only**, replaying the book's saved contexts verbatim. This holds retrieval, extracted facts, name masking, question IDs and reference answers constant across stock, edited and edited+LoRA. It measures how well each reader uses those contexts. It does not re-ingest conversations with Inkling or measure Inkling's extraction/graph-building ability.

The original harness files and results are read only. `memory.py` executes selected existing functions through an AST loader, avoiding their import-time directory creation and heavyweight imports:

- LongMemEval: `large.py`'s `prompt`, `clean`, `judge`, and `judge_prompt.py`'s `get_anscheck_prompt`.
- LoCoMo: `full_run.py`'s `answer` and `judge`, and `run.py`'s `ANSWER_SYSTEM`, `JUDGE`, `parse_json`. The 40-item pilot is not the report's final protocol.

Every request and complete raw OpenAI response, including usage and finish reason, is retained under `benchmarks/inkling/results/<variant>/<lab>/raw/`. Manifests hash all source records and harness definitions. Answers and each individual vote have separate atomic checkpoints. Resuming rejects changed settings or source records. Run one writer per variant/lab. A failed transport exits; rerun the same command after recovery. Successful completed calls are reused, including answers whose later judging was interrupted.

## Book settings preserved

The settings below transcribe the book's reports; the archived output controls exact retrieval order and prompt contents.

| Setting | LongMemEval | LoCoMo | Book source (`file:line`) |
|---|---|---|---|
| Fixed sample | 300/500, seed 20261122, proportional largest remainders over six non-abstention types plus abstention; exact IDs in `results/full/manifest.json` | Baselines: all 320; memory lanes: exact final matched 67, histories 0, 1, 3 (34/24/9 questions) | [LongMemEval REPORT.md:53](../../longmemeval/REPORT.md#L53), [LoCoMo REPORT.md:3](../../locomo/REPORT.md#L3), [REPORT.md:19](../../locomo/REPORT.md#L19), [REPORT.md:66](../../locomo/REPORT.md#L66) |
| Sample construction | Sorted IDs sampled, then shuffled | Seed 20261122; up to 8 per conversation/category then fill each of categories 1–4 to 80; category 5 excluded | [LongMemEval REPORT.md:53](../../longmemeval/REPORT.md#L53), [LoCoMo FULL_RUN.md:51](../../locomo/FULL_RUN.md#L51) |
| Full context | Original 8192-token eligibility retained: 300 standard skips, 212 oracle scored and 88 oracle skips | All actual timestamped turns and supplied text image captions/queries; 65536-token per-slot serving window | [LongMemEval REPORT.md:18](../../longmemeval/REPORT.md#L18), [REPORT.md:51](../../longmemeval/REPORT.md#L51), [LoCoMo FULL_RUN.md:47](../../locomo/FULL_RUN.md#L47), [FULL_RUN.md:53](../../locomo/FULL_RUN.md#L53) |
| BM25 / plain RAG | BM25: 800 characters, stride 700, top 10 in history order; drop whole lower-ranked chunks to fit | Exact cosine, top 20 individual turns | [LongMemEval REPORT.md:55](../../longmemeval/REPORT.md#L55), [LoCoMo FULL_RUN.md:57](../../locomo/FULL_RUN.md#L57) |
| Dense embeddings | `all-MiniLM-L6-v2`, CPU, 256-wordpiece limit, cosine, top 10 | Same embedder, CPU, 384 dimensions, 256-token input limit | [LongMemEval REPORT.md:55](../../longmemeval/REPORT.md#L55), [LoCoMo FULL_RUN.md:57](../../locomo/FULL_RUN.md#L57); revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` in each archived manifest |
| Mem0 | OSS 0.1.118, `infer=False`, raw chunks, local Qdrant, top 10 | OSS 2.2.1, eight individual turn messages per add, session-date anchoring, semantic top 20, threshold 0.1; no reranking/BM25 | [LongMemEval REPORT.md:55](../../longmemeval/REPORT.md#L55), [LoCoMo FULL_RUN.md:57](../../locomo/FULL_RUN.md#L57) |
| Graphiti / Cognee | Not measured | Graphiti 0.31.2, session episodes, `previous_episode_uuids=[]`, top-20 hybrid RRF edges; Cognee 1.0.9, Ladybug/LanceDB, 1600-token chunks, GRAPH_COMPLETION `only_context=True`, top 20 | [LongMemEval REPORT.md:61](../../longmemeval/REPORT.md#L61), [LoCoMo FULL_RUN.md:57](../../locomo/FULL_RUN.md#L57) |
| Reader generation | Temperature 0, seed 20261122, max_tokens 512, stop `<end_of_turn>` | Temperature 0, seed 20261122, initial max_tokens 384; technical length retry doubles up to 4096; truncated outputs never graded | [LongMemEval REPORT.md:57](../../longmemeval/REPORT.md#L57), [large.py:82](../../longmemeval/large.py#L82), [LoCoMo FULL_RUN.md:55](../../locomo/FULL_RUN.md#L55), [full_run.py:40](../../locomo/full_run.py#L40) |
| Fixed judge | Gemma 2 9B 4-bit; official task prompts, max_tokens 10, seeds 20261122/23/24, temperature 0; `yes` substring positive, 2/3 majority | Qwen2.5-14B-Instruct Q4_K_M; shared JSON rubric, initial max_tokens 384, temperature 0; seeds `20261122 + 100*backend_index + vote`, 2/3 majority | [LongMemEval REPORT.md:51](../../longmemeval/REPORT.md#L51), [REPORT.md:57](../../longmemeval/REPORT.md#L57), [large.py:90](../../longmemeval/large.py#L90), [LoCoMo FULL_RUN.md:55](../../locomo/FULL_RUN.md#L55), [full_run.py:47](../../locomo/full_run.py#L47) |

LoCoMo backend order is `full-context, rag, mem0, graphiti, cognee`. Exact matched IDs come from `benchmarks/locomo/results/full/matched-summary.json`. There are **1500** LongMemEval lane checkpoints (1112 scored, 388 explicit book context skips), and **841** LoCoMo lane checkpoints (320 + 320 + 67 + 67 + 67). The LoCoMo output includes both `summary.json` (all baseline questions) and `matched-summary.json` (all five lanes on the fixed 67). Prefix smoke runs are labeled through `limit` in their manifests.

Freezing the book's old context eligibility deliberately prevents a larger Inkling context window from changing the denominator. The reader server must accept all admitted prompts; errors never cause silent truncation. Any experiment using Inkling to regenerate retrieval or admit extra full histories needs a separate protocol and result directory.

## Setup and run

From the repository root, Python 3.12:

```bash
uv venv --python 3.12 benchmarks/inkling/labs/.venv
uv pip install --python benchmarks/inkling/labs/.venv/bin/python -r benchmarks/inkling/labs/requirements.txt
export PYTHON="$PWD/benchmarks/inkling/labs/.venv/bin/python"
# Set this to the exact model id advertised by the currently loaded oMLX variant.
export MODEL='ACTUAL_ALIAS_FROM_V1_MODELS'
"$PYTHON" benchmarks/inkling/labs/quality.py --variant stock --prepare-only

bash benchmarks/inkling/labs/longmemeval.sh --variant stock
bash benchmarks/inkling/labs/locomo.sh --variant stock
"$PYTHON" benchmarks/inkling/labs/quality.py --variant stock --concurrency 1
```

The default reader endpoint is `http://127.0.0.1:39850/v1`. Every reader request sends **top-level `thinking_budget: 0`** and `chat_template_kwargs.enable_thinking: false`. `--thinking-budget N` overrides the budget for all three labs; setting only `enable_thinking=false` is insufficient for the reported oMLX #5556 behavior. Judge requests retain their original settings and receive no Inkling thinking options. Optional bearer auth uses `INKLING_API_KEY`; it is never saved in artifacts.

For the complete three-lab run with short batches:

```bash
bash benchmarks/inkling/labs/batch.sh stock \
  --restart-hook '/absolute/path/to/restart-owned-reader-and-wait.sh' \
  --model "$MODEL" --batch-size 10 --quality-concurrency 1
```

Replace `stock` with `edited` or `edited+lora` after loading that variant. Keep all other settings identical. The restart hook is a required shell command argument, called **between every pair of batches, including lab transitions**. It must restart only the owned Inkling reader and return successfully only after its endpoint is ready with the intended variant loaded. It must leave both pinned judges available. Hook failure stops the runner. The default batch holds at most ten unfinished item/lane pairs (normally at most 40 model requests for memory, apart from bounded LoCoMo length retries). This bounds traffic between the oMLX #5539 restarts. Quality uses the same batch size. `--quality-concurrency` is available on `batch.sh`; direct `quality.py` uses `--concurrency`.

A single batch can also be run directly with `--batch-size 10`; rerun it to continue. `--output-root PATH` changes the parent of the variant folders. `--limit 3` selects the first three fixed question IDs per memory lab and first three fixed items per quality dataset; use a separate output root for smoke runs. `--judge-base-url URL` overrides an individual memory wrapper's judge tunnel; the batch runner exposes separate `--longmemeval-judge-base-url` and `--locomo-judge-base-url` flags.

## Restore the book judges

The book's task servers, tunnels, scratch and downloaded judge weights were cleaned up ([LongMemEval README.md:70](../../longmemeval/README.md#L70), [LoCoMo README.md:79](../../locomo/README.md#L79)). These wrappers do not substitute the reader for a missing judge or automatically start remote services. Both judge endpoints must be restored before a real run. The aliases and weight identities are pinned in `memory.py` and copied into every manifest; the operator must provision the weights below, rather than put another model behind those aliases.

On an Apple MLX judge host, restore **Gemma** at exactly revision `ff12eb39da2cd9b3b0f4b4f9ffb274603f05bb29`. The book launcher used mlx-lm Homebrew `0.32.2_1` ([supervise_large.py:40](../../longmemeval/supervise_large.py#L40)). An equivalent isolated launch:

```bash
uv venv --python 3.13.18 ~/inkling-gemma-judge/venv
uv pip install --python ~/inkling-gemma-judge/venv/bin/python 'mlx-lm==0.32.2'
~/inkling-gemma-judge/venv/bin/hf download mlx-community/gemma-2-9b-it-4bit \
  --revision ff12eb39da2cd9b3b0f4b4f9ffb274603f05bb29 \
  --local-dir ~/inkling-gemma-judge/model
~/inkling-gemma-judge/venv/bin/python -m mlx_lm.server \
  --model ~/inkling-gemma-judge/model --host localhost --port 39711 \
  --prompt-cache-size 1 --prompt-cache-bytes 1073741824 \
  --prefill-step-size 256 --max-tokens 512
```

It must accept the book's `model=default_model` alias. From the benchmark client, forward the chosen host (replace `GEMMA_JUDGE_HOST` with the actual SSH host):

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:39711:localhost:39711 GEMMA_JUDGE_HOST
```

For **Qwen**, use llama.cpp build 12359, commit `b1b770d90`; weights `bartowski/Qwen2.5-14B-Instruct-GGUF`, revision `05244aa5d871c661c80082a15d3bce44714d068d`, file `Qwen2.5-14B-Instruct-Q4_K_M.gguf`, SHA256 `e47ad95dad6ff848b431053b375adb5d39321290ea2c638682577dafca87c008` ([PILOT_README.md:17](../../locomo/PILOT_README.md#L17)). On the judge host:

```bash
hf download bartowski/Qwen2.5-14B-Instruct-GGUF \
  --revision 05244aa5d871c661c80082a15d3bce44714d068d \
  Qwen2.5-14B-Instruct-Q4_K_M.gguf --local-dir ~/inkling-qwen-judge
export MODEL_FILE=~/inkling-qwen-judge/Qwen2.5-14B-Instruct-Q4_K_M.gguf
shasum -a 256 "$MODEL_FILE"
llama-server --model "$MODEL_FILE" --alias qwen2.5-14b-instruct \
  --host localhost --port 39700 --ctx-size 196608 --parallel 3 \
  --override-kv qwen2.context_length=int:65536 \
  --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 32768 \
  --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --cache-ram 0 --jinja
```

This serving command is copied from [FULL_RUN.md:40](../../locomo/FULL_RUN.md#L40). Forward the selected host from the benchmark client:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:39700:localhost:39700 QWEN_JUDGE_HOST
```

The frozen replay needs no Mem0, Neo4j, Cognee, embeddings or original downloaded datasets at runtime. All archived input checkpoints currently exist. The original live-ingestion harness would additionally require its pinned Python environments, CPU embedder and task stores; do not run it against the archived result directories.

## Quality protocol and offline verification

Quality is independent, zero-shot QA with no memory calls or judge. It samples **200 GSM8K main/test and 200 MMLU-Pro test**, using Python `random.Random(20261122).sample`, then sorts original row indices. Sources are pinned to immutable Hugging Face revisions:

- [openai/gsm8k](https://huggingface.co/datasets/openai/gsm8k), MIT, revision `740312add88f781978c0658806c59bc2815b9866`, `main/test-00000-of-00001.parquet`.
- [TIGER-Lab/MMLU-Pro](https://huggingface.co/datasets/TIGER-Lab/MMLU-Pro), MIT, revision `b189ec765aa7ed75c8acfea42df31fdae71f97be`, `data/test-00000-of-00001.parquet`.

The checked-in `quality-selection.json` pins all 400 row indices, both parquet SHA256 values and a hash of all selected prompts/golds. Preparation rejects any mismatch. Preparation downloads only those test parquet files, records their SHA256, and saves the exact selected indices and prompts in `labs/data/selection.json` (local cache). Temperature 0, seed 20261122, max_tokens 512, thinking budget 0. GSM8K accepts a bare numeric answer or an explicitly marked final numeric answer, normalized only for commas/decimal representation; it never guesses the last number in prose. MMLU-Pro accepts only a single A–J option letter (optionally `Final answer:`, parentheses or a period). Exact match is applied against the original gold answer. Unfinished completions score incorrect. Reports separate the two datasets, including length-stop counts.

Run the offline tests (the server is a local stdlib fixture with canned OpenAI responses; no live endpoints or dataset downloads):

```bash
"$PYTHON" -m pytest -q benchmarks/inkling/labs/tests
```

The tests run three actual archived question IDs through **all five memory lanes** in each lab (15 checkpoints/lab, preserving any book context skips), three synthetic quality items per dataset at concurrency 3, exact-match negative controls, immutable-manifest checks, resume without additional calls, full archive availability and all-lab short-batch/restart-hook execution. Smoke scores are transport/scoring checks, not Inkling performance measurements. Standalone stub: `python3 benchmarks/inkling/labs/tests/stub_server.py` prints its random loopback URL.

Verified locally: **9 pytest tests passed**. A separate smoke using the real pinned quality subset completed 15 LongMemEval checkpoints (11 scored, 4 original context skips), 15 LoCoMo checkpoints, and 6 quality checkpoints through 110 canned API calls. The retained [smoke-results.json](tests/smoke-results.json) links to local `tests/smoke-output/` raw transcripts (ignored by Git). All 1112 scored archived LongMemEval prompts were also reconstructed and matched exactly. At verification, loopback ports 39850, 39711 and 39700 were unavailable; no real Inkling or judge inference was performed.

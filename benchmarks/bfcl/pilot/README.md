**Archived 40-case pilot.** The expanded experiment is documented one directory above. This archive retains its original code and results; its original commands refer to the pre-archive layout. Do not launch this archive while the expanded task is running.

# BFCL-V4 local subset reproduction

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

BFCL measures whether a model selects the right tools and supplies acceptable arguments. This run uses the official BFCL OpenAI-compatible function-calling handler and its AST and irrelevance evaluators. It is a tool-calling test, not a memory-extraction test. The V4 memory, web-search, live, non-Python and multi-turn categories are excluded. No LLM judge or hosted generation service is used.

## Run

Requirements: Linux for generation/scoring, `uv`, SSH access to an Apple Silicon Mac with `llama-server` installed, and Internet access for public package/model downloads. The Mac only serves a model. All data selection, generation requests and scoring execute on Linux. An SSH alias supplies the model host; no deployment address is embedded in the harness.

From the repository root:

```bash
MODEL_HOST=your-ssh-alias bash benchmarks/bfcl/run.sh
```

This installs the exact Python package versions in `requirements.txt` into `/var/tmp/membench-bfcl/venv`, downloads one pinned GGUF at a time into `~/membench-bfcl-tmp` on the Mac, verifies its SHA-256, serves it on localhost port 39730 and opens an SSH tunnel. It runs 2B, 4B and 0.8B with thinking off and on, saving each request, response and official score in a fresh timestamped directory under `results/`. It stops its own servers, closes the tunnel and removes both scratch directories, retaining results in this directory. It refuses to start unless macOS memory pressure is normal and `memory_pressure` reports at least 40% system-wide memory free. A five-second guard stops its server if either requirement ceases to hold. Do not use either scratch directory for unrelated work.

To score a separately managed localhost endpoint instead, set `BASE_URL` (default `http://localhost:39730/v1`) and run `run.py --model MODEL --thinking off|on --output NEW_DIRECTORY` with the pinned environment. `--rescore` re-runs the official scorer on retained outputs without generating answers. The wrapper refuses to overwrite prior generations. Set `MODEL_SIZES=0.8B` to run only the optional smallest model, or `MODEL_SIZES=2B,4B` for the required pair.

## Pinned method and sampling

- Python 3.11.18; `bfcl-eval==2026.3.23`; all transitive versions in `requirements.txt`, including CPU-only PyTorch. No Linux GPU is used.
- Official repository: <https://github.com/ShishirPatil/gorilla/tree/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard>.
- Official dataset card: the repository's `bfcl_eval/data/README.md`, declaring Apache-2.0. Repository and scorer also use Apache-2.0.
- Primary scoring explanation: <https://gorilla.cs.berkeley.edu/blogs/8_berkeley_function_calling_leaderboard.html#metrics>. V4 composition: <https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html>.
- Installed package data, handler and scorer were compared byte for byte with that repository revision; see `evidence/source-provenance.json`. This records actual source hashes rather than assuming a package version identifies the dataset.
- Ten examples sampled without replacement in each of `simple_python`, `multiple`, `parallel`, `irrelevance`, using `random.Random(f"20261121:{category}").sample(rows, 10)` on original file order. The same 40 IDs are used for every cell. Selection was fixed before generation; see `evidence/sample-manifest.json`.
- Temperature 0, seed 20261121, at most 4,096 output tokens, 8,192-token server context, one request at a time. Per-request `chat_template_kwargs.enable_thinking` controls thinking. The upstream handler builds tools and normalizes dotted function names. No custom system prompt, few-shot examples or schema constraint is added by this wrapper.
- Each correct/incorrect decision comes directly from BFCL's `_evaluate_single_ast_entry` or `_evaluate_single_relevance_entry`. No hand correction or tuning against the published scores. Length-stopped responses stay in the denominator; infrastructure failures abort the cell rather than becoming invented model answers.
- `verify.py` proves the official integration accepts correct arguments and rejects wrong ones, and distinguishes no tool call from an unwanted tool call on an irrelevance item. Evidence: `evidence/scorer-verification.json`.

## Models and hardware

Serving hardware: Apple M3 Ultra, 96 GB unified memory. Scoring hardware: 32-thread x86 CPU. Existing workloads are not stopped or reconfigured. Runtime: llama.cpp build 12359, commit `b1b770d90`, AppleClang 21.0.0 for arm64. The MLX CLI on the initial host could not import; see the report.

| Model | Quantization repository revision | SHA-256 |
|---|---|---|
| Qwen3.5-2B | `unsloth/Qwen3.5-2B-GGUF`, `f6d5376be1edb4d416d56da11e5397a961aca8ae` | `aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223` |
| Qwen3.5-0.8B | `unsloth/Qwen3.5-0.8B-GGUF`, `6ab461498e2023f6e3c1baea90a8f0fe38ab64d0` | `bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517` |
| Qwen3.5-4B | `unsloth/Qwen3.5-4B-GGUF`, `e87f176479d0855a907a41277aca2f8ee7a09523` | `00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4` |

All are Q4_K_M conversions of official Apache-2.0 Qwen weights. The cards do not specify their evaluation precision, and matching it has not been established. The vision projector is not used for these text-only cases.

## Results and interpretation

| Model | Published full BFCL-V4 | Local thinking off | Local thinking on |
|---|---:|---:|---:|
| Qwen3.5-0.8B | 25.3 | 18/40 (45%) | 27/40 (67.5%) |
| Qwen3.5-2B | 43.6 | 29/40 (72.5%) | 37/40 (92.5%) |
| Qwen3.5-4B | 50.3 | 32/40 (80%) | 34/40 (85%) |
| Qwen3.5-9B | 66.1 | Not run | Not run |

These are 240 scored attempts on the same 40 IDs, not 240 independent test questions. Off responses contained no reasoning; all 40 responses in each on cell contained reasoning. There were six length stops: 0.8B off 1, 0.8B on 3, 2B on 1 and 4B on 1. BFCL scored two length-stopped empty irrelevance answers as correct, one in 0.8B on and one in 2B on. If all length stops were instead treated as failures, those two cells would be 26/40 (65.0%) and 36/40 (90.0%); the other cells would be unchanged. The headline table preserves the official evaluator's decisions.

The local four-category percentage is a different metric from the published aggregate. It cannot validate or refute those published figures. It also does not reproduce the 2B-to-4B ordering in thinking mode on this small sample. Both modes must be tested on the intended application; these results do not establish memory-extraction quality.

Pinned primary-source table headers and values are in `evidence/model-card-figures.json`; book locations and replacement wording are in `REPORT.md`. A sampled four-category proportion must never be labeled a reproduced full BFCL-V4 score.

The model-card results for 0.8B and 2B explicitly appear under “General Agent (Thinking).” The 4B/9B table labels the section “General Agent” and their cards describe thinking as the default. The cards do not fully specify BFCL prompts, harness revision, server, quantization, sampling seed, output budget or category-level scores. Our official FC adapter, Q4_K_M conversion, deterministic decoding, finite context/output budget and balanced four-category sample differ from or are not established to match that setup. No result from this subset alone can validate or refute the published aggregate or establish extraction quality.


## Verify retained results

```bash
python3 benchmarks/bfcl/summarize.py --require-complete
python3 benchmarks/bfcl/make_chart.py
```

`results/audit.json` verifies every expected ID, raw-score count, request control and reasoning-mode observation. `results/comparison.html` charts only the local subset. `evidence/scorer-verification.json` contains the fail-capable official-scoring probes. Both required runs and the optional 0.8B run exited successfully. Cleanup is confirmed in an unpublished raw log, an unpublished raw log, the corresponding resource snapshots, and an unpublished raw log. Only this directory is retained; no commit was made by this task.

# 05. Small stock LLMs as the memory model

Research date: 2026-11-20. Every fact carries its source URL. Anything not checked in this pass is marked **UNVERIFIED**.

## How it works

Every memory framework splits the work into a "writer" model call and a retrieval step. The writer model reads raw text and returns structure. Typical jobs:

- **Extract** facts, entities, and relations from a message (retain / add).
- **Decide** whether a new fact is ADD, UPDATE, DELETE, or NOOP against existing memories.
- **Summarise or consolidate** (sleep-time, reflect, community summaries).
- **Answer** a recall or reflect question from retrieved notes.

What each framework asks of this model:

- **mem0 (OSS v3, "new memory algorithm")**: the extraction is now a single LLM call that only adds. The docs say the old design used two calls (extract candidates, then decide ADD/UPDATE/DELETE). The new pipeline retrieves the top-10 related memories for context, makes one call to extract all distinct new facts, then does hash-based dedup and batch insert. Source: https://docs.mem0.ai/migration/oss-v2-to-v3. Its quickstart defaults to OpenAI `gpt-5-mini` for the LLM and `text-embedding-3-small` for embeddings: https://docs.mem0.ai/open-source/configuration.
- **Hindsight (vectorize-io)**: `retain` uses an LLM to pull out key facts, temporal data, entities and relationships, then normalises them into canonical entities, time series and indexes. `recall` runs four strategies in parallel (vector, BM25, graph, temporal) and merges with reciprocal rank fusion plus a cross-encoder. `reflect` does deeper synthesis. Source: https://raw.githubusercontent.com/vectorize-io/hindsight/main/README.md. Hindsight lists 25+ LLM providers, including the local `ollama`, `lmstudio` and `llamacpp`, and any OpenAI-compatible endpoint (same README). On 2026-11-03 it released `hs-decide-1-flash`, a small "decision model" for the small judgments (is this new, does it matter, is it enough), so the main LLM only writes. Apache 2.0 weights on Hugging Face under `hindsight-ai`: https://hindsight.vectorize.io/blog/2026/11/03/hindsight-models.
- **Graphiti (Zep)**: entity and edge extraction plus deduplication, all via structured JSON output. The repo says it "depends on structured (JSON) output... and works best with models and providers that reliably honor it": https://github.com/getzep/graphiti (search snippet). The README example points `OpenAIGenericClient` at Ollama's `http://localhost:11434/v1` with `deepseek-r1:7b` as a placeholder: https://raw.githubusercontent.com/getzep/graphiti/main/README.md. Graphiti's own recommended model list was **not found** in this pass (UNVERIFIED).
- **Letta sleep-time agents**: a second agent edits the primary agent's memory blocks while idle. The memory is "anytime" readable. Source: https://www.letta.com/blog/sleep-time-compute/ (April 2025; paper arXiv:2504.13171). Letta's current docs describe MemFS, a git-backed memory filesystem that agents inspect and edit: https://docs.letta.com/configuration/memory/.
- **LangMem**: `create_memory_manager` gives stateless extraction and update. Models are passed as provider strings such as `"anthropic:claude-3-5-sonnet"`: https://langchain-ai.github.io/langmem/guides/manage_user_profile/ (search snippet). Its API page confirms the function name: https://langchain-ai.github.io/langmem/reference/. The reference page section itself did not render, so per-model guidance is UNVERIFIED.

No framework above publishes a small-model recommendation table in the pages checked. The practical rule is: use a model that reliably returns the schema the framework parses.

## Models table

Sizes, context and licences are from the model cards or vendor pages cited. Memory figures are at 4-bit unless stated.

| Model | Released | Sizes | Context | Licence | Thinking | Memory at 4-bit | Tool calling and JSON notes |
|---|---|---|---|---|---|---|---|
| **Qwen3.5 Small** (Qwen) | Mar 2026 (Unsloth post dated Mar 2, 2026: https://x.com/UnslothAI/status/2028463220063871426) | 0.8B, 2B, 4B, 9B | 262,144 native (4B card: https://huggingface.co/Qwen/Qwen3.5-4B) | Apache 2.0 (9B card: https://huggingface.co/Qwen/Qwen3.5-9B) | Hybrid; Small models **off by default** (Unsloth: https://unsloth.ai/docs/models/qwen3.5.md) | Unsloth table: 0.8B/2B 3.5 GB, 4B 5.5 GB, 9B 6.5 GB (same URL) | Card names vLLM parser `qwen3_coder`. BFCL-V4 0.8B 25.3, 2B 43.6, 4B 50.3, 9B 66.1; TAU2 4B 79.9, 9B 79.1 (figures as cited by VDF: https://vdf.ai/blog/best-small-language-models/) |
| **Qwen3 dense** (Qwen) | Apr 2025 | 0.6B to 8B (sizes beyond 4B **UNVERIFIED** here) | 32K native (**UNVERIFIED**) | Apache 2.0 (**UNVERIFIED** here) | Switchable per turn; confirmed on Qwen3-4B card: https://huggingface.co/Qwen/Qwen3-4B | Not measured here | Older generation; still common for memory extraction in community guides (e.g. `qwen3:8b` in Ollama: https://generativeai.pub/building-local-ai-agents-a-practical-guide-to-models-memory-and-orchestration-12622e9e0269) |
| **Gemma 4 E2B / E4B** (Google) | Jan 2026 (E2B/E4B/26B-A4B/31B on releases page: https://ai.google.dev/gemma/docs/releases); 12B added Jul 2026 | E2B, E4B effective 2.3B and 4.5B | 128K (VDF table) | Apache 2.0 (https://ai.google.dev/gemma/docs/core) | Yes (reasoning page exists) | Google table, Q4_0 incl. 20% overhead: E2B 2.9 GB, E4B 4.5 GB, 12B 6.7 GB (https://ai.google.dev/gemma/docs/core) | Native function calling (VDF). Accepts text, image and audio on small models |
| **Gemma 4 12B** | Jul 2026 | 12B | 256K (VDF) | Apache 2.0 | Yes | 6.7 GB | Native function calling; Tau2 69.0% (VDF) |
| **Ministral 3** (Mistral) | 2025 | 3B, 8B, 14B | 256K | Apache 2.0 | No | 8B fits 12 GB in FP8 (Mistral, via VDF) | Native function calling and JSON output; vLLM parser `mistral` |
| **Granite 4.2** (IBM) | 25 Aug 2026 (card) | 3B, 8B | 128K, to 512K | Apache 2.0 | Reasons before tool calls | Not measured here | BFCL v4: 3B 52.41, 8B 52.39 (VDF) |
| **Phi-4-mini** (Microsoft) | 2025 | 3.8B | 128K | MIT | No | About 2.5 GB (**UNVERIFIED**) | Dedicated function-calling format (VDF) |
| **Llama 3.2** (Meta) | 2024 | 1B, 3B | 128K | Llama 3.2 Community License | No | 3B about 2 GB (**UNVERIFIED**) | BFCL: 3B 21.95%, 1B 10.82% (older leaderboard, VDF) |
| **SmolLM3-3B** (Hugging Face) | 2025 | 3.1B | 64K, 128K with YaRN | Apache 2.0 | Yes | Not measured here | XML or Python-style calls; parser `hermes` (VDF) |
| **LFM2.5** (Liquid AI) | 2026 | 1.2B, 2.6B, 8B-A1B (1.5B active) | 32K for 1.2B, 128K others | LFM Open License 1.0 | Not stated | Under 1 GB for 1.2B (VDF) | Pythonic function calls (VDF) |

**Qwen4 status (checked 2026-11-19, third-party tracker):** Qwen4-Max is API-only (16 Nov 2026). Qwen says smaller open models are "coming", with no sizes, licence or date. No Ollama `qwen4` tag was found: https://www.betterclaw.io/blog/qwen-4-vs-qwen-3-8. The official open Qwen 3.8 weights checked here are 27B and Flash-Next (unsloth collection: https://huggingface.co/collections/unsloth/qwen38). A "Qwen3.8 2B/4B/9B" appears only in community distillations (e.g. https://huggingface.co/empero-ai/Qwen3.8-2B-Distill). Treat those as **not official**. The official small line is still Qwen3.5.

Ollama tags for Qwen3.5 (https://ollama.com/library/qwen3.5): `0.8b` 1.2 to 1.3 GB, `2b` 2.7 to 3.1 GB, `4b` 3.3 to 4.0 GB, `9b` 6.6 to 7.6 GB. All 256K context, text and image, tagged thinking.

## Strengths

- **Cheap, local, private.** Qwen3.5-4B at 4-bit is about 5.5 GB by Unsloth's table, which fits an 8 GB card or a 16 GB Mac with room for context.
- **Long context.** Qwen3.5 has 262K native context, so one model can hold a long session transcript in a single extraction call. The model card notes only some layers keep a growing KV cache, which helps on small hardware (VDF).
- **Mode control.** Qwen3.5 small is non-thinking by default (Unsloth). That suits extraction, which should return JSON quickly. Qwen3.5 general thinking sampling is temp 1.0, top_p 0.95, top_k 20, presence 1.5; non-thinking general is temp 0.7, top_p 0.8 (both: https://huggingface.co/Qwen/Qwen3.5-4B).
- **Tool and schema support in the runtimes.** vLLM has a documented parser for Qwen3.5 (`qwen3_coder`). Ollama exposes JSON-mode format (https://docs.ollama.com/capabilities/structured-outputs).
- **Permissive licences.** Qwen3.5, Gemma 4, Ministral 3, Granite 4.2 and SmolLM3 are Apache 2.0. Phi-4-mini is MIT.

## Limits and failure modes

- **JSON is not guaranteed.** Frameworks like Graphiti assume valid JSON from the extractor. Small models drop fields, add prose around the JSON, or invent entity IDs. Constrained decoding is the fix, not a better prompt. Options: Ollama `format` (JSON or schema), GBNF grammars in llama.cpp (https://raw.githubusercontent.com/ggml-org/llama.cpp/master/grammars/README.md: "force the model to generate valid JSON"), vLLM tool parsers, and `response_format` with `json_schema` on OpenAI-compatible servers (the exact server support matrix is **UNVERIFIED** in this pass).
- **Thinking mode leaks.** Qwen3.5 with thinking on spends many tokens before JSON. Turn thinking off for extraction. Confirm the switch name for your runtime (**UNVERIFIED** for Ollama here).
- **Tool-calling scores drop steeply under 4B.** Qwen3.5 BFCL-V4: 25.3 at 0.8B, 50.3 at 4B. 4B matches 9B on TAU2 (79.9 vs 79.1) but trails clearly on BFCL-V4 (VDF). Test both.
- **Quantization.** Unsloth says its 4-bit GGUFs keep sensitive layers at higher precision (Dynamic 2.0) and has documented MXFP4 sensitivity in some Qwen3.5 tensors (https://unsloth.ai/docs/models/qwen3.5.md). A 2026 paper on a RAG benchmark found 4-bit cut latency 20% with no measurable accuracy loss on that task (https://arxiv.org/html/2609.14762v1). One task is not a general result. Measure extraction F1 at your quant before trusting it.
- **Context is not free.** MLX docs warn that a quantized KV cache does not support batching and that attention on it needs a large score matrix at long context (https://raw.githubusercontent.com/ml-explore/mlx-lm/main/mlx_lm/SERVER.md). Long-context runs on an 8 GB machine slow down sharply.
- **Consolidation drift.** Sleep-time and reflect steps rewrite memory. A small model can overwrite correct facts with worse summaries. Keep the raw episodes (Graphiti keeps episodes as provenance: https://github.com/getzep/graphiti).

## Exact use cases

**Pick a small local model when:**
- The memory is personal or regulated and must not leave the LAN.
- Retain runs on every message and a cloud call per turn is too slow or too costly.
- The extraction schema is narrow (preferences, entities, dates) and you can enforce it with a grammar or JSON schema.
- You are on a Mac with 16 GB or more, or an 8 GB GPU with a 4B model.

**Pick a bigger model (or a hosted one) when:**
- Recall answers need multi-hop reasoning or long synthesis. Hindsight's reflect is the step most likely to need it.
- Graph extraction (Graphiti) produces many invalid edges. Move that one step to a larger model and keep the rest local.
- You need throughput for bulk back-fill (run it overnight, not per message).

**Avoid a small model when:**
- The memory writes must be correct the first time and there is no review step. Mem0's single-pass ADD-only design makes bad extractions stick. Pair it with a review or dedupe step.
- You rely on tool calls inside the memory loop below 4B.

### Per-target guidance

- **Mac, unified memory (MLX / oMLX / LM Studio):** Qwen3.5-4B or 9B 4-bit via `mlx-lm`. 9B at 6.5 GB is comfortable on 16 GB. On 8 GB use 4B with a short context.
- **CPU only:** Qwen3.5-0.8B or 2B, LFM2.5-1.2B, or Llama 3.2 1B. Expect slow retain. Batch it.
- **8 GB GPU:** Qwen3.5-4B 4-bit (5.5 GB weights, leaves room for KV). Qwen3.5-9B at 6.5 GB is tight once the KV cache grows. Gemma 4 E4B (4.5 GB Q4_0) is the safe alternative.

## Setup walkthrough

These commands come from the cited pages. Names marked **UNVERIFIED** were not checked against the live repo.

### 1. Ollama (OpenAI-compatible at `/v1`)

```bash
ollama run qwen3.5:4b          # pulls ~3.3-4.0 GB, Ollama library page above
curl http://localhost:11434/v1/models
```

Graphiti's documented client pattern (https://raw.githubusercontent.com/getzep/graphiti/main/README.md), with Qwen in place of the placeholder:

```python
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient

llm_config = LLMConfig(
    api_key="ollama",
    model="qwen3.5:4b",
    small_model="qwen3.5:4b",
    base_url="http://localhost:11434/v1",
)
llm_client = OpenAIGenericClient(config=llm_config)
```

### 2. llama.cpp (GGUF, Unsloth build)

```bash
llama-server -hf unsloth/Qwen3.5-4B-GGUF:Q4_K_M --ctx-size 8192 --port 8080
# Pattern from https://www.ml4devs.com/articles/llm-local-inference-dev-setup/ (9B example).
# The Q4_K_M tag for the 4B repo is UNVERIFIED.
```

For JSON-constrained output, pass a GBNF grammar with `--grammar-file` (flag per the llama.cpp grammar guide above; **UNVERIFIED** exact flag name for the current build).

### 3. MLX-LM (Apple Silicon)

```bash
pip install mlx-lm
mlx_lm.server --model mlx-community/Qwen3.5-9B-4bit --port 8080
# 9B name from https://blog.dailydoseofds.com/p/karpathys-trick-for-faster-local
# The 4B MLX repo name is UNVERIFIED; check the mlx-community org on Hugging Face.
curl localhost:8080/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Say this is a test!"}],"temperature":0.7}'
```

`mlx_lm.server` is OpenAI-like, defaults to port 8080, and is "not recommended for production" (https://raw.githubusercontent.com/ml-explore/mlx-lm/main/mlx_lm/SERVER.md). Add `--kv-bits 4 --prefill-step-size 512` for long context.

### 4. vLLM (GPU, 8 GB and up)

```bash
vllm serve "Qwen/Qwen3.5-4B" --enable-auto-tool-choice --tool-call-parser qwen3_coder
# Serve command from https://huggingface.co/Qwen/Qwen3.5-4B. The tool flags follow VDF's
# parser table (https://vdf.ai/blog/best-small-language-models/).
```

### 5. Pointing a framework at it

- **Hindsight** runs in Docker and supports local `ollama`, `lmstudio` and `llamacpp` providers (README above). The container command in the README is:

```bash
docker run -it --pull always --name hindsight --restart unless-stopped -p 8888:8888 -p 9999:9999 \
  -e HINDSIGHT_API_LLM_API_KEY=$OPENAI_API_KEY \
  -v hindsight-data:/home/hindsight/.pg0 \
  ghcr.io/vectorize-io/hindsight:latest
```

  Set `HINDSIGHT_API_LLM_PROVIDER=ollama` (provider name verified). The base-URL and model variable names are **UNVERIFIED** here; check the Hindsight models docs at https://hindsight.vectorize.io/developer/models.
- **mem0 OSS** takes an `llm` block with `provider` and `config` (https://docs.mem0.ai/open-source/configuration). Set the provider to the local server. The exact local-provider keys are **UNVERIFIED** here. A community guide used `qwen3:8b` on Ollama for fact extraction (https://generativeai.pub/building-local-ai-agents-a-practical-guide-to-models-memory-and-orchestration-12622e9e0269).
- **Turn thinking off** for extraction calls. The Qwen3.5 small default is already off. Verify on your runtime with a single test request.

## Numbers

- Qwen3.5 memory, 4-bit (Unsloth table): 0.8B and 2B 3.5 GB; 4B 5.5 GB; 9B 6.5 GB. BF16 4B: 14 GB. BF16 9B: 19 GB.
- Qwen3.5 Ollama download sizes: 0.8b 1.2 to 1.3 GB; 2b 2.7 to 3.1 GB; 4b 3.3 to 4.0 GB; 9b 6.6 to 7.6 GB.
- Qwen3.5 BFCL-V4: 25.3 (0.8B), 43.6 (2B), 50.3 (4B), 66.1 (9B). TAU2: 11.6, 48.8, 79.9, 79.1 (VDF, from model cards).
- Gemma 4 Q4_0 incl. 20% overhead: E2B 2.9 GB, E4B 4.5 GB, 12B 6.7 GB, 26B-A4B 14.4 GB, 31B 17.5 GB (Google).
- Gemma 4 mobile LiteRT-LM: E2B 1.1 GB, E4B 2.5 GB (Google).
- Hindsight decision model: 167 ms median per request. A main LLM call takes 1 to 7 s (Hindsight blog). This is the best latency figure found for a memory retain step; it is vendor-reported.
- Qwen3.5 context: 262,144 native, to 1,010,000 with extension (4B card).
- Recommended output length for Qwen3.5: 32,768 tokens for most queries (4B card).
- Tokens per second on Mac or 8 GB GPU: **UNVERIFIED** in this pass. Measure on your box.

## Sources

- mem0 new algorithm (single-pass ADD-only extraction): https://docs.mem0.ai/migration/oss-v2-to-v3
- mem0 OSS configuration (defaults, provider blocks): https://docs.mem0.ai/open-source/configuration
- mem0 Python quickstart: https://docs.mem0.ai/open-source/python-quickstart
- Hindsight README (retain/recall/reflect, providers, docker): https://raw.githubusercontent.com/vectorize-io/hindsight/main/README.md
- Hindsight Models blog (decision model, latency): https://hindsight.vectorize.io/blog/2026/11/03/hindsight-models
- Hindsight decision models docs: https://hindsight.vectorize.io/developer/decision-models
- Hindsight arXiv paper: https://arxiv.org/abs/2512.12818
- Graphiti README: https://raw.githubusercontent.com/getzep/graphiti/main/README.md
- Graphiti repo (structured-output note): https://github.com/getzep/graphiti
- Letta sleep-time compute: https://www.letta.com/blog/sleep-time-compute/ and arXiv:2504.13171 (https://arxiv.org/abs/2504.13171)
- Letta memory docs: https://docs.letta.com/configuration/memory/
- Anthropic, components of agent memory (dreaming, cites Letta): https://www.anthropic.com/research/components-of-agent-memory
- LangMem: https://langchain-ai.github.io/langmem/ and https://langchain-ai.github.io/langmem/guides/manage_user_profile/
- Qwen3.5-4B model card: https://huggingface.co/Qwen/Qwen3.5-4B
- Qwen3.5-9B model card: https://huggingface.co/Qwen/Qwen3.5-9B
- Qwen3.5 collection: https://huggingface.co/collections/unsloth/qwen35
- Qwen3-4B model card: https://huggingface.co/Qwen/Qwen3-4B
- Unsloth Qwen3.5 guide (memory table, thinking default): https://unsloth.ai/docs/models/qwen3.5.md
- Ollama qwen3.5 library: https://ollama.com/library/qwen3.5
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs
- llama.cpp GBNF guide: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/grammars/README.md
- mlx-lm README: https://raw.githubusercontent.com/ml-explore/mlx-lm/main/README.md
- mlx-lm server guide: https://raw.githubusercontent.com/ml-explore/mlx-lm/main/mlx_lm/SERVER.md
- Gemma 4 overview (memory table): https://ai.google.dev/gemma/docs/core
- Gemma releases: https://ai.google.dev/gemma/docs/releases
- Gemma 4 E2B HF card: https://huggingface.co/google/gemma-4-E2B
- VDF, best small language models (Oct 2026 card check, tool-calling table): https://vdf.ai/blog/best-small-language-models/
- BetterClaw, Qwen 4 status (third-party tracker, 19 Nov 2026): https://www.betterclaw.io/blog/qwen-4-vs-qwen-3-8
- TriCalRAG (quantization latency, one task): https://arxiv.org/html/2609.14762v1
- Community guide, mem0 with qwen3:8b: https://generativeai.pub/building-local-ai-agents-a-practical-guide-to-models-memory-and-orchestration-12622e9e0269
- ML4Devs llama-server example: https://www.ml4devs.com/articles/llm-local-inference-dev-setup/

**Not verified in this pass:** Graphiti's own model recommendations; Qwen3 0.6B to 8B details; Phi-4-mini, Llama 3.2 and LFM2.5 memory figures beyond what VDF states; tokens per second on any hardware; the exact Ollama and llama.cpp flags for disabling thinking and passing a schema; mem0 and Hindsight local-provider config keys; the 4B MLX repo name; any official Qwen 3.8 or Qwen 4 small open weights.

# Local open-weight models by hardware tier (state as of 2026-11-20)

Scope: picks for a small business AI assistant with tool calling, grouped by hardware. Every fact carries a source URL. Grades: **[P]** = read from a primary page (model card, vendor page, official docs) in this session. **[S]** = secondary report (news, blog, community benchmark). **UNVERIFIED** = not confirmed; do not publish without checking.

## Method and caveats

- Model cards were read directly on Hugging Face (raw README where the rendered page was too large), on Ollama library pages, and on Google, Mistral, Apple and Microsoft pages.
- Search engines were partly rate-limited, so search results were used only to find candidate URLs, not as facts.
- Tokens per second come from community reports on llamaperf.com [S]. Most rows are one or two runs. Treat them as order-of-magnitude only.
- Ollama "context window" values are the model's maximum, not the default. Ollama's default context is smaller (see Serving).

## Tier A: mini PC or Mac mini, 16 to 32 GB (about 4B to 12B)

| Pick | Publisher, released | Licence | Context | Quant and memory | Tools / JSON / vision | Thinking off | tok/s (reported) | Serve |
|---|---|---|---|---|---|---|---|---|
| **Qwen3.5-9B** (dense, 9B) | Alibaba Qwen, 2026-03-02 (X post) [P] | Apache-2.0 [P: HF card] | 262,144 native [P: HF card] | Ollama `qwen3.5:9b` 6.6-7.6 GB, Q4 class [P: Ollama] | Ollama tags: vision, tools, thinking [P] | Ollama `think` control (see Serving) | Q4: 62.7 on M2 Max 64GB (1 run); 7.9 on RX 9070 XT 16GB (1 run) [S] | `ollama run qwen3.5:9b`; `qwen3.5:9b-mlx` (8.9 GB) [P] |
| **Gemma 4 12B** ("Unified", encoder-free) | Google DeepMind, announced 2026-06-03 [S: analyticsvidhya, digitalapplied]; HF card lists 2026-07-02 [S] | Apache-2.0 [P: HF card and licence link] | 256K [P: HF card] | Ollama `gemma4:12b` 7.7-8.0 GB; Google table: Q4_0 6.7 GB weights, 26.7 GB BF16 [P] | Ollama tags: vision, tools, thinking, audio [P]; native function calling [P: HF card] | Configurable thinking [P]; exact off switch UNVERIFIED | Not measured in this session | `ollama run gemma4:12b`; `gemma4:12b-mlx` 7.7 GB [P] |
| **Ministral 3 8B** | Mistral AI, 2025-12-02 [P: docs.mistral.ai] | Apache-2.0 [P] | 256K [P] | Ollama `ministral-3:8b` 6.0 GB [P] | Structured outputs, function calling, document QnA, vision listed [P: docs.mistral.ai] | Not a reasoning model; no switch needed (UNVERIFIED) | Not measured | `ollama run ministral-3:8b` [P] |

Alternative for the smallest boxes: **Ministral 3 3B** (3.0 GB Ollama, 256K, vision) [P] and **Aion 1.0 Instruct 2.3B** (Microsoft, GA on Hugging Face 2026-11-19, 32K context [S: ModelFit]). Aion is designed for Edge and Windows on-device use; its licence and tool support are UNVERIFIED.

## Tier B: Mac with 64 GB or PC with one 24 GB GPU (about 24B to 32B)

| Pick | Publisher, released | Licence | Context | Quant and memory | Tools / JSON / vision | Thinking off | tok/s (reported) | Serve |
|---|---|---|---|---|---|---|---|---|
| **Qwen3.8-27B** (dense, 27B) | Alibaba Qwen, 2026-08-13 [P: HF listing] | Apache-2.0 [P] | 262,144 native, extensible to 1M with YaRN [P] | Ollama default `qwen3.8` / `27b` 18 GB (Q4_K_M); 30 GB Q8_0; 56 GB BF16 [P: Ollama tags, via secondary Kevin Welter table] | Ollama tags: vision, tools, thinking [P]; native VL [P] | Thinking on by default; `reasoning_effort` (xhigh default, medium, low) and `preserve_thinking` [P]; the exact disable parameter is UNVERIFIED (the card says "configuring the API parameters") | Q4 on RX 7900 XTX 40.0 (7 runs), RTX 3090 37.4 (6 runs) [S: llamaperf] | `ollama run qwen3.8` (Q4 default; 27b-mlx for Apple) [P]; `vllm serve "Qwen/Qwen3.8-27B"` [P] |
| **Gemma 4 26B A4B** (MoE, 25.2B total, 3.8B active) | Google DeepMind, 2026-04-02 [P: Google blog] | Apache-2.0 [P] | 256K [P] | Ollama `gemma4:26b` 16-19 GB; Google table Q4_0 14.4 GB weights [P] | Ollama tags: vision, tools, thinking, audio not on this size [P]; native function calling [P] | Configurable thinking [P]; off switch UNVERIFIED | Q4 57.3 on M4 Pro 64GB (2 runs); 59.1 on DGX Spark (2 runs) [S] | `ollama run gemma4:26b`; `gemma4:26b-mlx` 18 GB [P] |
| **Granite 4.2 30B** (dense, listed as 29B) | IBM, Granite 4.2 family first release 2026-08-25 [P: HF card for 3B]; 30B repo updated 2026-09-04 [P: HF listing] | Apache-2.0 [P: 3B card] | 128K native, long-context extension to 512K [P: 3B card] | GGUF repo exists `ibm-granite/granite-4.2-30b-GGUF`; FP8 and NVFP4 variants exist [P: HF listing]; memory figure UNVERIFIED | Tags: tool-calling, reasoning, thinking [P: HF tags] | Built-in `<think>` trace [P: 3B card] | Not measured | HF GGUF via llama.cpp; vLLM per HF card pattern [P] |

Notes for tier B:
- Qwen3.8-27B is the strongest open model in this tier by the vendor's own tables, but it thinks by default and can spend a long time before answering. Plan a reasoning budget or switch it off for simple tool calls.
- Gemma 4 31B (dense, 30.7B) is the quality alternative: 17.5 GB at Q4_0 per Google's table [P]. It is slower than the 26B A4B.

## Tier C: Mac Studio with 128 GB or more, or a dual-GPU workstation (larger models)

| Pick | Publisher, released | Licence | Context | Memory | Fits | Notes |
|---|---|---|---|---|---|---|
| **gpt-oss-120b** | OpenAI (open weight) | UNVERIFIED this session | 128K [P: Ollama] | 65 GB Ollama tag [P] | 128 GB Mac Studio at Q4 | Tools and thinking tags [P: Ollama]. Release date and licence were not confirmed in this session. |
| **Mistral Small 4** (MoE, 119B) | Mistral AI, announced 2026-03-16 [P: mistral.ai news]; HF repo `Mistral-Small-4-119B-2603` [P] | Apache-2.0 [P: news and docs] | UNVERIFIED | Q4 GGUF by Unsloth exists [P: HF listing]; about 60-70 GB by arithmetic, not measured | 128 GB Mac Studio | Hybrid instruct, reasoning and coding model [P: docs.mistral.ai]. |
| **DeepSeek V4-Flash** (291B) | DeepSeek, 2026-04-26 [P: HF listing]; V4.1-Flash (763B) 2026-10-17 [P] | MIT [P: HF card for V4-Pro, same family] | 1M [P: HF card for V4-Pro] | About 146 GB at 4-bit by arithmetic; does not fit 128 GB | 512 GB M5 Ultra Mac Studio or multi-GPU | Heavy; Qwen3.8 Flash-Next at 2 x RTX 3090 beat it on speed in one community report [S]. |

Too big for these tiers: Kimi K2.6 (1.1T, modified MIT, 2026-02-02) [P: HF listing]; Mistral Large 4 (1T, Mistral Ecosystem Open Weight Licence, not Apache) [P]; Qwen3.8-2.4T-A95B [P: HF collection].

Unresolved: HF lists Qwen3.8-Flash-Next at 180B [P: HF listing], while llamaperf calls it 125B with 6B active [S]. Do not cite either size until the model card is read directly.

## Other roles

**Vision-language (photos, invoices, insurance cards).**
- Qwen3.8-27B: native image and video input [P]. Use it at tier B.
- Gemma 4 E4B: image input and OCR [P]. On the vendor's OmniDocBench 1.5 table (lower edit distance is better), E4B scores 0.181 against 0.164 for the 12B Unified, 0.149 for 26B A4B and 0.131 for 31B [P: Gemma 4 12B HF card]. Use it for tier A document work if 12B is too slow.
- Granite-Docling-258M: a 258M document-conversion VLM for page images [P: litert and GGUF cards]; licence Apache-2.0 [S: Spheron]. Good for forms and invoices as a first pass before the LLM.

**Embedding.**
- EmbeddingGemma 2: released 2026-10-06 [P: Google blog]. 740M parameters total, 8,192-token context, text, image, video and audio inputs, 768-dimensional output, MRL truncation to 128, 256 and 512 [P: model card]. Apache-2.0 [S: RxDB]. Ollama tag `embeddinggemma-2` exists [P: Ollama listing].
- Qwen3-Embedding: 0.6B, 4B and 8B, 32K context, dimensions 32 to 1024 [P: 0.6B card]. Released 2025-06-05 [P]. Licence Apache-2.0 is confirmed on the reranker card of the same series [P]; not fetched for the embedding card itself.
- Qwen3-VL-Embedding-8B (2026-01-08) for mixed image and text retrieval [P: HF listing].

**Reranker.**
- Qwen3-Reranker 0.6B, 4B and 8B, Apache-2.0 [P: 0.6B card]. This is the current Qwen text reranker in the sources read. A Qwen3-VL-Reranker-8B exists (2026-01-08) [P: HF listing].

## Hardware prices (vendor pages)

| Example machine | Tier | Price | Source |
|---|---|---|---|
| Mac mini M6, 16 GB, 256 GB (entry configuration) | A | From $899 [S: PCMag, AppleInsider]. Apple confirmed availability on 2026-09-22 [P: Apple newsroom]. | apple.com/shop/buy-mac/mac-mini lists M6 16 GB and 24 GB configurations [P]; price field not in the cached page. |
| Mac mini M5 Pro, 64 GB, 1 TB | B | UNVERIFIED (M5 Pro base is $1,699 [S]) | Configuration listed [P: apple.com] |
| Mac Studio M5 Max, from | C | From $2,499 [P: Apple newsroom, 2026-08-25] | apple.com/newsroom/2026/08 |
| Mac Studio M5 Ultra, from | C | From $5,499 [P: Apple newsroom, 2026-09-22 snippet] | apple.com/newsroom/2026/09 |
| Workstation GPU (RTX 3090, RTX 5090 or similar) | B/C | UNVERIFIED | Not checked |

## Serving

Commands taken from the sources (verified unless marked):

```bash
# Ollama (library tags, see the Ollama pages cited above)
ollama run qwen3.5:9b              # tier A
ollama run gemma4:12b              # tier A, 256K
ollama run ministral-3:8b          # tier A
ollama run qwen3.8                 # tier B, 27B Q4 default
ollama run gemma4:26b              # tier B
ollama run gpt-oss:120b            # tier C
ollama run qwen3.8:27b-mlx         # Apple Silicon MLX build
ollama run gemma4:26b-mlx          # Apple Silicon MLX build

# Qwen3.8-27B with vLLM (from the Hugging Face card)
pip install vllm
vllm serve "Qwen/Qwen3.8-27B"

# Qwen3.8-27B with SGLang (from the Hugging Face card)
python3 -m sglang.launch_server --model-path "Qwen/Qwen3.8-27B" --host 0.0.0.0 --port 30000

# Google official QAT GGUF naming pattern for llama.cpp (from the Gemma 4 docs)
#   {model-name}-qat-q4_0-gguf
```

Thinking control and context:
- Ollama documents a per-request `think` field. Values can be booleans or model-defined levels, `/api/show` reports the model's own thinking values, and `values: [false]` means no thinking [P: docs.ollama.com/capabilities/thinking]. Send `"think": false` for tier A/B assistants that answer simple tool calls. The exact effect per model is UNVERIFIED for Qwen3.8 and Gemma 4.
- Ollama's default context is small. A 2026 guide says Ollama gives 4K tokens below 24 GB of VRAM [S: kevinwelter.com]. Set the context explicitly for every model. The environment variable name is UNVERIFIED (Ollama's context page did not render in this session).
- Qwen3.8-27B recommends `temperature=1.0, top_p=0.95, top_k=20` for thinking and `temperature=0.7, top_p=0.80, top_k=20, presence_penalty=1.5` for non-thinking [P: HF card].

JSON and structured output: Ollama documents structured outputs and tool calling on its capability pages [P: docs.ollama.com]. Mistral documents structured outputs and function calling for Ministral 3 [P]. The Gemma 4 docs list native function calling [P: HF card]. The exact JSON-schema call for each model is UNVERIFIED in this session.

## Could not verify

- The official Qwen3.8 small models (under 27B). The collection lists 27B, 2.4T-A95B and Flash-Next only. Qwen3.8 9B, 4B and 2B exist only as third-party distills [S: empero-ai]. The official small line is Qwen3.5 (0.8B, 2B, 4B, 9B) [P: Ollama].
- Llama: sources conflict. One says Llama 5 open weights were released in April or June 2026 [S, low-quality sites]. Meta's newest open-weight model in the Meta-controlled sources read is Llama 4 (April 2025) [S]. Muse Spark is closed [S]. Treat Llama as UNVERIFIED.
- Phi-5: only a speculative pre-release guide [S: spheron]. Current Phi in the sources is Phi-4-reasoning-vision-15B (2026-03-04, open weight, multimodal) [P: Microsoft Research blog].
- gpt-oss release date and licence (only the Ollama page was read).
- Tokens per second on the Mac mini M6 and on tier C hardware.
- Vendor price for the tier B Mac and for workstation GPUs.
- The exact non-thinking parameter for Qwen3.8-27B and Gemma 4.

## Sources

- Qwen3.8 collection (HF): https://huggingface.co/collections/Qwen/qwen38 ; API: https://huggingface.co/api/collections/Qwen/qwen38
- Qwen3.8-27B card: https://huggingface.co/Qwen/Qwen3.8-27B ; raw README: https://huggingface.co/Qwen/Qwen3.8-27B/raw/main/README.md
- Qwen3.5 collection: https://huggingface.co/collections/Qwen/qwen35
- Qwen3.5-9B card: https://huggingface.co/Qwen/Qwen3.5-9B
- Qwen3-Embedding-0.6B card: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- Qwen3-Reranker-0.6B raw README: https://huggingface.co/Qwen/Qwen3-Reranker-0.6B/raw/main/README.md
- Qwen3-VL-Reranker-8B: https://huggingface.co/Qwen/Qwen3-VL-Reranker-8B
- Unsloth Qwen3.8-27B GGUF: https://huggingface.co/unsloth/Qwen3.8-27B-GGUF
- Gemma 4 12B card: https://huggingface.co/google/gemma-4-12B ; raw README: https://huggingface.co/google/gemma-4-12B/raw/main/README.md
- Gemma 4 overview (Google): https://ai.google.dev/gemma/docs/core
- Gemma 4 launch (Google blog, 2026-04-02): https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/
- EmbeddingGemma 2 model card: https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2
- EmbeddingGemma 2 launch: https://blog.google/innovation-and-ai/technology/developers-tools/embeddinggemma-2/
- Mistral models overview: https://docs.mistral.ai/models ; Ministral 3 14B: https://docs.mistral.ai/models/ministral-3-14b-25-12
- Mistral Small 4 launch: https://mistral.ai/news/mistral-small-4/ ; HF repo: https://huggingface.co/mistralai/Mistral-Small-4-119B-2603
- Mistral Large 4 weights: https://mistral.ai/news/mistral-large-4-oss/
- IBM Granite 4.2 3B card: https://huggingface.co/ibm-granite/granite-4.2-3b ; collection: https://huggingface.co/collections/ibm-granite/granite-42-language-models
- Granite-Docling GGUF: https://huggingface.co/infil00p/granite-docling-258M-GGUF ; LiteRT: https://huggingface.co/litert-community/granite-docling-258M
- DeepSeek V4-Flash: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash ; V4-Pro (MIT): https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro
- Kimi K2.6: https://huggingface.co/moonshotai/Kimi-K2.6
- Microsoft Aion Instruct (Edge blog, 2026-11-19): https://blogs.windows.com/msedgedev/2026/11/19/hybrid-intelligence-on-the-web-introducing-aion-instruct-and-prompt-api-in-microsoft-edge/
- Microsoft Phi-4-reasoning-vision: https://www.microsoft.com/en-us/research/blog/phi-4-reasoning-vision-and-the-lessons-of-training-a-multimodal-reasoning-model/
- Ollama library: https://ollama.com/library/qwen3.8 , https://ollama.com/library/qwen3.5 , https://ollama.com/library/gemma4 , https://ollama.com/library/ministral-3 , https://ollama.com/library/gpt-oss
- Ollama thinking docs: https://docs.ollama.com/capabilities/thinking
- Apple Mac mini configurations: https://www.apple.com/shop/buy-mac/mac-mini
- Apple Mac Studio configurations: https://www.apple.com/shop/buy-mac/mac-studio
- Apple newsroom, Mac Studio (2026-08-25): https://www.apple.com/newsroom/2026/08/apple-introduces-new-mac-studio-with-m5-max-and-m5-ultra/
- Apple newsroom, Mac mini and Mac Studio availability (2026-09-22): https://www.apple.com/newsroom/2026/09/the-new-mac-mini-and-mac-studio-are-available-today/
- PCMag, Mac mini M6 pricing [S]: https://www.pcmag.com/news/apple-updates-mac-mini-with-m6-m5-pro-processors-and-a-price-hike
- llamaperf community speeds [S]: https://llamaperf.com/model/qwen3-8 , https://llamaperf.com/model/qwen3-5 , https://llamaperf.com/model/gemma-4
- Kevin Welter, Qwen 3.8 with Ollama [S]: https://kevinwelter.com/en/blog/qwen-3-8-ollama
- Edge on-device model notes [S]: https://modelfit.io/blog/microsoft-aion-1-0-instruct-2-3b/

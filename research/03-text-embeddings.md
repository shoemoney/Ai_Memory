# Text Embedding Models for Memory and Retrieval (state as of 2026-11-20)

Scope: the models an agent memory layer would realistically embed with, plus the hosted options. Every fact carries a source URL. Anything I could not check is marked **UNVERIFIED**. The MTEB leaderboard page is a JavaScript app that did not render through my tools, so all MTEB numbers come from model cards, and each one names its own benchmark version. Scores from different benchmark versions are not comparable.

## How it works

- **Dense embedding.** An encoder (or decoder with last-token pooling) maps a text to one fixed-length float vector. Retrieval is nearest-neighbour search on that vector, usually cosine similarity. Almost every model in the table below is dense.
- **Sparse (lexical-weight) embedding.** The model outputs a weight per vocabulary term, so retrieval behaves like a learned BM25. BGE-M3 produces this alongside dense output. Source: https://huggingface.co/BAAI/bge-m3
- **Multi-vector (ColBERT-style).** One vector per token, scored with late interaction (MaxSim). Better recall on long, detailed queries, at roughly token-count times the storage. BGE-M3 also exposes this mode. Source: same BGE-M3 card.
- **Matryoshka (MRL) truncation.** The model is trained so the first k dimensions form a usable embedding on their own. You can store 256 of 1024 dims and keep most of the quality. Evidence: Jina v5 lists dims 32 through 1024 as supported (https://huggingface.co/jinaai/jina-embeddings-v5-text-small), and EmbeddingGemma 2 reports MTEB English falling from 68.46 at 768d to 67.78 at 256d, as cited by a third party (https://rxdb.info/articles/embeddinggemma-2-vector-search.html; the underlying figure is in the model card, https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2).
- **Quantization.** int8 scalar quantization cuts storage by about 4x. Binary (1-bit) cuts it by about 32x and needs rescoring. Jina v5 advertises robustness to binary quantization (its card, same URL as above). Other numbers are UNVERIFIED for this report.
- **Instruction / query prefixes.** Asymmetric retrieval models expect a task instruction on the query side (and often none on the document side). Qwen3 says instructions typically add 1 to 5 points and recommends writing them in English. Source: https://huggingface.co/Qwen/Qwen3-Embedding-8B. EmbeddingGemma has "Task Instruction Prefixes" as a best-practice section (model card_2 URL above). Leaving the prefix out is a silent quality loss, not an error.
- **Why vectors from two models cannot be mixed.** Each model learns its own coordinate system. Two models can have the same dimension count and still be unrelated spaces, so cosine similarity between them is meaningless. Even the same model with a different instruction, pooling choice, quantization, or truncation is a different space for cross-comparison purposes. Store the model ID and version next to every vector, and treat a model change as a full re-index.
- **Re-embedding cost.** Re-indexing means re-running the encoder on every stored chunk, so it costs the same as the original ingest. Hosted, the cost is linear in tokens. Using the verified OpenAI list prices: 1 billion tokens costs about $20 with text-embedding-3-small ($0.02/M) and about $130 with text-embedding-3-large ($0.13/M). Sources: https://developers.openai.com/api/docs/models/text-embedding-3-small and https://www.activepieces.com/blog/openai-embeddings-api-pricing-in-2026-dated-and-checked. Local cost is compute time, not dollars, so the real cost is wall-clock time.

## Models table

Dates are release dates from each source. "Score" is the mean score in the source's stated benchmark.

| Model | Released | Params | Dims | Context | Licence | Score (source benchmark) |
|---|---|---|---|---|---|---|
| Qwen3-Embedding-0.6B | Jun 2025 | 0.6B | 1024 (MRL) | 32K | Apache-2.0 | 64.33 MTEB multilingual mean(task) |
| Qwen3-Embedding-4B | Jun 2025 | 4B | 2560 (MRL) | 32K | Apache-2.0 | 69.45 MTEB multilingual |
| Qwen3-Embedding-8B | Jun 2025 | 8B | 4096 (MRL) | 32K | Apache-2.0 | 70.58 MTEB multilingual (No.1 at release, leaderboard snapshot May 2025) |
| jina-embeddings-v5-text-small | 18 Feb 2026 | 677M | 1024 (MRL 32–1024) | 32K | cc-by-nc-4.0 (non-commercial) | 71.7 MTEB English v2; 67.7 MMTEB |
| jina-embeddings-v5-text-nano | Feb 2026 | 239M | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Harrier-oss-v1-0.6b (Microsoft) | 30 Mar 2026 | 0.6B | 1024 | 32,768 | UNVERIFIED | 69.0 MTEB v2 multilingual |
| Harrier-oss-v1-270m (Microsoft) | 30 Mar 2026 | 270M | 640 | 32,768 | UNVERIFIED | 66.5 MTEB v2 multilingual |
| Harrier-oss-v1-27b (Microsoft) | 30 Mar 2026 | 27B | 5376 | 32,768 | UNVERIFIED | 74.3 MTEB v2 multilingual (too large for CPU) |
| EmbeddingGemma 2 | Oct 2026 | 740M total (270M text backbone always on) | 768 default, MRL | UNVERIFIED | UNVERIFIED | 61.36 MTEB multilingual v2 (768d) |
| EmbeddingGemma 1 | Sep 2025 | 300M class | 768 | UNVERIFIED | UNVERIFIED | 61.15 MTEB multilingual v2 (same table as above) |
| BGE-M3 (BAAI) | 2024 | 0.6B (per Qwen comparison table) | 1024 | 8,192 | UNVERIFIED (MIT per common usage) | 59.56 MTEB multilingual |
| multilingual-e5-large-instruct | 2024 | 0.6B (per Qwen comparison table) | 1024 | UNVERIFIED | UNVERIFIED | 63.22 MTEB multilingual |
| nomic-embed-text-v1.5 | 2024 | 137M (third party) | 768 (MRL) | 8,192 (third party) | Apache-2.0 (UNVERIFIED) | UNVERIFIED |
| nomic-embed-text-v2-moe | Feb 2025 | MoE, UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | ~100 languages (third-party forum summary) |
| snowflake-arctic-embed-l-v2.0 | 2025 | 568M total (third party) | UNVERIFIED | UNVERIFIED | Apache-2.0 (UNVERIFIED) | UNVERIFIED |
| mxbai-embed-large-v1 | 2024 | 335M (third party) | 1024 (MRL 512/256, third party) | 512 (UNVERIFIED) | UNVERIFIED | UNVERIFIED |
| all-MiniLM-L6-v2 | 2021 | 22M class (UNVERIFIED) | 384 (UNVERIFIED) | short, about 256 tokens (UNVERIFIED) | Apache-2.0 (https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Old default; superseded on quality |
| voyage-4-large | 15 Jan 2026 | UNVERIFIED (hosted) | 1024 default; 256, 512, 2048 | 32,000 | Hosted | UNVERIFIED |
| voyage-4 | Jan 2026 | UNVERIFIED | 256, 512, 1024, 2048 | 32,000 | Hosted | UNVERIFIED |
| OpenAI text-embedding-3-small | 2024 | hosted | UNVERIFIED (1536 widely cited) | UNVERIFIED | Hosted | $0.02 per 1M tokens |
| OpenAI text-embedding-3-large | 2024 | hosted | UNVERIFIED (3072 widely cited) | UNVERIFIED | Hosted | $0.13 per 1M tokens |
| Cohere embed-v4.0 | 2025 | hosted | UNVERIFIED | 128,000 | Hosted | $0.12 per 1M tokens (via Bedrock/Vercel gateways) |
| gemini-embedding-001 | Jul 2025 | hosted | UNVERIFIED | 2,048 input tokens | Hosted | $0.15 per 1M text tokens |
| gemini-embedding-2 | 2026 | hosted | UNVERIFIED | UNVERIFIED | Hosted | $0.20 per 1M text (standard), $0.10 (batch); multimodal |

Sources for rows: Qwen spec and score tables https://huggingface.co/Qwen/Qwen3-Embedding-8B; Qwen3 0.6B tag sizes https://ollama.com/library/qwen3-embedding; Jina v5 https://huggingface.co/jinaai/jina-embeddings-v5-text-small; Harrier https://huggingface.co/microsoft/harrier-oss-v1-270m; EmbeddingGemma 2 https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2 and https://blog.google/innovation-and-ai/technology/developers-tools/embeddinggemma-2/; Voyage https://docs.voyageai.com/docs/embeddings and https://blog.voyageai.com/2026/01/15/voyage-4/; Gemini pricing https://ai.google.dev/gemini-api/docs/pricing (mirror: https://aistudio.google.com/docs/pricing) and https://aistudio.google.com/docs/models/gemini-embedding-001; Cohere via https://vercel.com/ai-gateway/models/embed-v4.0; nomic and arctic/mxbai third-party rows from https://ollama.com/library/nomic-embed-text-v2-moe, https://localaimaster.com/models/nomic-embed-text, https://www.morphllm.com/ollama-embedding-models, https://d-central.tech/local-embedding-models/.

**Qwen3 context discrepancy.** The model card says 32K. The Ollama tags say 32K for 0.6b but 40K for 4b and latest. Test before you rely on the larger number.

**Newer Qwen embedding release.** I found none. The family is still 0.6B, 4B and 8B, with later vision-language variants per a third-party guide (https://superlinked.com/blog/qwen3-embedding-reranker-guide). Treat "no newer Qwen text embedding" as a search result, not a proof.

**Leaderboard caveat.** One roundup notes that several major hosted models have no complete MTEB v2 score, so a sorted table cannot rank them (https://www.maximem.ai/blog/best-embedding-models-2026). Current No.1 on MTEB is UNVERIFIED.

## Strengths

- **Qwen3-Embedding:** strongest open multilingual family in its own card's tables, with instruction awareness, MRL, and a 32K window. Ollama, TEI and sentence-transformers all load it.
- **Jina v5 text-small:** best-in-class sub-1B multilingual claim on its own card (71.7 MTEB English v2, 67.7 MMTEB, 119+ languages, 32K tokens). It is a distilled model from Qwen3-Embedding-4B.
- **Harrier-0.6B:** 69.0 on MTEB v2 multilingual at 0.6B with 32K context (card above). Good on CPU if its licence fits.
- **EmbeddingGemma 2:** small and multimodal-capable, with selectively loadable encoders so text-only use pays for 270M, not 740M (Google model card, above).
- **Hosted options:** no GPU, no ops. Voyage-4 shares one embedding space across its family, so you can mix sizes without re-embedding.

## Limits and failure modes

- **Licence traps.** Jina v5 is cc-by-nc-4.0, which blocks commercial use without a separate licence. Check every row before you ship.
- **Wrong or missing prefix.** Asymmetric models lose quality silently when queries and documents are embedded without their instructions.
- **Model-swap corruption.** A changed model, pooling, truncation or quantization makes the old index unusable for new queries. Results still look plausible, which is the dangerous part.
- **Truncation past the trained dimension.** Truncating a non-MRL model, or going below the trained minimum, gives poor vectors without an error. Only use dimensions the card lists.
- **Context overflow.** Text beyond the window is cut or rejected depending on the server. Chunk to the window you actually serve, not the card's maximum. Ollama's default context can be below the card value (UNVERIFIED for your version).
- **Hosted lock-in.** You cannot re-embed without paying again, and provider deprecations force migrations.
- **Benchmark drift.** MTEB versions change, and one roundup says models may have trained on large parts of the benchmark tasks (https://www.rapidfire.ai/learn/best-embedding-models-for-rag). Test on your own memory corpus.

## Exact use cases

- **CPU-only box:** start with a small model: EmbeddingGemma 2 at 256 dims (text path only), Jina v5 nano (if its licence fits), or all-MiniLM-L6-v2 for the cheapest fallback. Quantize to int8. Avoid 4B and 8B on CPU.
- **Mac with MLX:** use `mlx-embeddings` (https://github.com/Blaizzy/mlx-embeddings) for Apple-silicon-native runs, or Ollama's GGUF builds. Qwen3-Embedding-0.6B is the sensible default; move to 4B when memory allows.
- **Multilingual memory:** Qwen3-Embedding-8B or 4B if you have the memory, Harrier-0.6B or Jina v5 small for a lighter multilingual option (check licence), BGE-M3 when you also want sparse or multi-vector output from one model.
- **Long documents:** the 32K-window models (Qwen3, Jina v5, Harrier, Voyage-4) or BGE-M3 at 8,192. Chunk anyway: a whole-document vector averages away detail.
- **Pick it when:** you need one model and one index, the corpus is yours, and you can afford a re-index later.
- **Avoid it when:** the licence is non-commercial and you ship commercially; the box has no GPU and the model is 4B or larger; you cannot store a model ID with each vector.

## Setup walkthrough

**Ollama** (verified against https://docs.ollama.com/capabilities/embeddings and https://ollama.com/library/qwen3-embedding):

```bash
ollama pull qwen3-embedding:0.6b
curl http://localhost:11434/api/embed \
  -d '{"model":"qwen3-embedding:0.6b","input":"Why is the sky blue?"}'
# embeddinggemma is also published; the docs show: ollama run embeddinggemma "Hello world"
```

The response is JSON with an `embeddings` array. Add your own query instruction to the input text. Whether Ollama adds the prefix automatically is UNVERIFIED.

**llama.cpp server** (the `/embedding` and `/v1/embeddings` endpoints are verified against https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md):

```bash
llama-server -m Qwen3-Embedding-0.6B-Q8_0.gguf --embedding -c 8192
curl http://localhost:8080/v1/embeddings -H 'Content-Type: application/json' \
  -d '{"input":"hello world"}'
```

The model file name is a placeholder. The pooling flag for last-token models is UNVERIFIED for your build. The native `/embedding` endpoint is not OpenAI-compatible; use `/v1/embeddings` for clients.

**Hugging Face TEI (Text Embeddings Inference):** I could not render the TEI quick tour or CPU tutorial (https://huggingface.co/docs/text-embeddings-inference/quick_tour and /local_cpu), so no exact Docker command is verified. The pattern is `docker run -p 8080:80 -v $PWD/data:/data ghcr.io/huggingface/text-embeddings-inference:<cpu-tag> --model-id <repo>`. Check the image tag and the `--model-id` flag against the TEI README before you run it (UNVERIFIED).

**sentence-transformers** (verified against the Qwen3-Embedding-8B card):

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
emb = model.encode(["The weather is lovely today.", "He drove to the stadium."])
print(model.similarity(emb, emb).shape)  # (2, 2)
```

Prompt-name handling for queries is UNVERIFIED for this card; read its README section before you rely on it.

**MLX** (install verified against https://github.com/Blaizzy/mlx-embeddings):

```bash
pip install mlx-embeddings
```

The usage API for text models is UNVERIFIED in this report. Read that repo's README for the load and encode calls.

## Numbers

- Qwen3-Embedding MTEB multilingual mean(task): 64.33 (0.6B), 69.45 (4B), 70.58 (8B), all as of the May 2025 leaderboard snapshot (https://huggingface.co/Qwen/Qwen3-Embedding-8B).
- Qwen3-Embedding dims: 1024 / 2560 / 4096. Layers: 28 / 36 / 36. Context 32K (same card).
- Jina v5 text-small: 677M params, 1024 dims, 32K tokens, 71.7 MTEB English v2, 67.7 MMTEB (https://huggingface.co/jinaai/jina-embeddings-v5-text-small).
- Harrier MTEB v2: 66.5 (270M), 69.0 (0.6B), 74.3 (27B), with dims 640 / 1024 / 5376 (https://huggingface.co/microsoft/harrier-oss-v1-270m).
- EmbeddingGemma 2 MTEB multilingual v2: 61.36 at 768d (vs 61.15 for v1). MTEB English at 768d 68.46, at 256d 67.78 (model card, via rxdb).
- Pricing per 1M tokens: OpenAI small $0.02, large $0.13; Cohere embed-v4 $0.12; Gemini embedding-001 $0.15; Gemini Embedding 2 text $0.20 standard, $0.10 batch (Google pages above).
- **CPU and GPU throughput: no verified numbers.** One third-party benchmark reports MiniLM models above 140 queries per second on unstated hardware (https://iam-tsr.github.io/blog/cutting-edge-onnx-embedding-models/). A September 2026 blog says ONNX or OpenVINO with int8 makes CPU embedding practical (https://www.alekseialeinikov.com/en/blog/topics/ai/which-embedding-model-api-vs-self-hosted-2026). Neither gives comparable throughput for a named model on named hardware. Benchmark on your own box before you size anything.

## Sources

- Qwen3-Embedding-8B model card: https://huggingface.co/Qwen/Qwen3-Embedding-8B
- Qwen3-Embedding on Ollama: https://ollama.com/library/qwen3-embedding
- Qwen3 comparison guide (third party): https://superlinked.com/blog/qwen3-embedding-reranker-guide
- Jina v5 text-small: https://huggingface.co/jinaai/jina-embeddings-v5-text-small
- Jina v5 announcement (Elastic blog): https://www.elastic.co/search-labs/blog/jina-embeddings-v5-text
- Microsoft Harrier: https://huggingface.co/microsoft/harrier-oss-v1-270m and https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/now-in-foundry-microsoft-harrier-and-nvidia-egm-8b/4510851
- EmbeddingGemma 2 model card: https://ai.google.dev/gemma/docs/embeddinggemma/model_card_2
- EmbeddingGemma 2 announcement: https://blog.google/innovation-and-ai/technology/developers-tools/embeddinggemma-2/
- Voyage text embeddings docs: https://docs.voyageai.com/docs/embeddings and Voyage 4 blog: https://blog.voyageai.com/2026/01/15/voyage-4/
- Gemini pricing: https://aistudio.google.com/docs/pricing
- OpenAI text-embedding-3-small: https://developers.openai.com/api/docs/models/text-embedding-3-small
- Cohere embed-v4 pricing (gateway): https://vercel.com/ai-gateway/models/embed-v4.0
- BGE-M3: https://huggingface.co/BAAI/bge-m3
- all-MiniLM-L6-v2: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- Ollama embeddings docs: https://docs.ollama.com/capabilities/embeddings
- llama.cpp server: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- TEI (repo, docs unrendered): https://github.com/huggingface/text-embeddings-inference
- mlx-embeddings: https://github.com/Blaizzy/mlx-embeddings
- Leaderboard (JS app, not rendered): https://huggingface.co/spaces/mteb/leaderboard

# 04. Multimodal embedding models for memory and retrieval

Research date: 2026-11-20. Every fact carries its source in the Sources section (numbered [S#]). Anything not verified in this session is marked **UNVERIFIED**.

## How it works

A multimodal embedder maps text, images, screenshots, video and audio into one vector space, so a text query can retrieve an image, and an image can retrieve a caption. Three design choices matter most.

**1. Unified backbone vs. paired encoders.** CLIP-style models encode each modality with a separate tower, trained contrastively to align pairs. Voyage argues that this architecture makes mixed-modality search unreliable because "text and image vectors often align with irrelevant items of the same modality" [S7]. Newer models (Qwen3-VL-Embedding, Gemini Embedding 2, Voyage multimodal-3.5, Cohere Embed v4) run every input through one backbone, so mixed inputs (text + image in one document) produce one vector. Qwen describes its embedder as a dual-tower design where the embedding is the last-layer hidden state of the `[EOS]` token [S2].

**2. The modality gap.** Liang et al. (NeurIPS 2022, "Mind the Gap") show that contrastively trained image and text embeddings occupy separate regions of the sphere, so same-modality neighbours often outrank cross-modal matches [S8]. Practical consequence: when you index screenshots and captions together, measure cross-modal recall on your own data rather than trusting a headline score. (The paper's title and claim come from the arXiv listing; I did not read the full text in this session.)

**3. Single-vector vs. multi-vector.** A single-vector model compresses a page or image to one vector. A late-interaction model (ColPali, ColQwen, Jina v4 multi-vector mode) keeps one vector per visual patch and scores with MaxSim. ColPali's authors describe ColQwen-style models as producing "ColBERT-style multi-vector representations" of page images [S10] and introduced ViDoRe with the claim that embedding page images directly beats OCR-based pipelines [S9].

**Storage cost (my arithmetic, not from a source):**
- One 4096-dim vector in fp16: 8 KB. One million pages: about 8.2 GB.
- ColQwen2 caps a page at 768 patches [S10]. At 128 dims per patch in fp16 (ColBERT convention, not verified for this checkpoint), one page is 768 x 128 x 2 bytes = 196,608 bytes, about 197 KB. One million pages: about 197 GB before any index overhead.
- So multi-vector buys accuracy on visually dense documents at roughly 20 to 25 times the storage of a single vector per page.

## Models table

| Model | Org, date | Size | Dimensions | Inputs | Licence | Notes |
|---|---|---|---|---|---|---|
| Qwen3-VL-Embedding-2B | Alibaba Qwen, 8 Jan 2026 [S1][S2] | 2B, 28 layers | 2048, MRL 64 to 2048 | text, image, screenshots, video, mixed | Apache-2.0 [S1] | 32K context, quantization and instructions supported [S1] |
| Qwen3-VL-Embedding-8B | same [S1] | 8B, 36 layers | 4096, MRL 64 to 4096 | same | Apache-2.0 [S1] | Top MMEB-V2 overall score in its card (77.9) [S1] |
| Qwen3-VL-Reranker-2B / 8B | same [S2] | 2B / 8B | none (scores pairs) | (query, doc) pairs, mixed | Apache-2.0 (repo) [S2] | Single-tower cross-encoder, scores "yes"/"no" tokens [S2] |
| qwen3-vl-embedding (API) | Alibaba Model Studio [S11] | not disclosed | 2560 default; 256 to 2560 | text, up to 5 images, video; fused or independent vectors | Proprietary API | Beijing region only; `enable_fusion=true` gives one fused vector [S11] |
| tongyi-embedding-vision-plus / -flash (API) | Model Studio [S11] | not disclosed | 1152 / 768 default | text, images, video | Proprietary API | Singapore region only; independent vectors only. Whether it is Qwen-lineage is **UNVERIFIED** |
| Gemini Embedding 2 | Google, 10 Mar 2026 [S12][S13] | not disclosed (**UNVERIFIED**) | 3072 default; MRL truncation (768, 1536 recommended by secondary sources) [S14] | text, image, video, audio, PDF | Proprietary API | Input limits in Strengths/Limits [S13] |
| voyage-multimodal-3.5 | Voyage AI (MongoDB), 15 Jan 2026 [S7][S15] | not disclosed | 1024 default; 256, 512, 2048 [S15] | interleaved text, images (screenshots, slides), video | Proprietary API | 32K context [S15] |
| Cohere Embed v4 | Cohere, 15 Apr 2025 [S16] | not disclosed | 256, 512, 1024, 1536 (Matryoshka) [S16] | text, images, interleaved mixed input | Proprietary; also on AWS, Azure, Oracle [S16][S17] | 128K context [S16]; images above 2,458,624 px are downsampled [S17] |
| Jina embeddings v4 | Jina AI, 23 Jun 2025 [S18][S19] | 3.8B, built on Qwen2.5-VL-3B [S18][S19] | 2048 single-vector (MRL to 128); 128 per-patch multi-vector [S19] | text, images, visual documents | **UNVERIFIED** (licence field not seen in fetched card) | Task LoRA adapters: retrieval, text-matching, code [S19] |
| ColPali | ILLUIN, ICLR 2025 [S9] | PaliGemma base (**UNVERIFIED** here) | multi-vector per page | page images | open (repo) [S9] | Introduced ViDoRe [S9] |
| ColQwen2 v1.0 | vidore org [S10] | 2B (Qwen2-VL-2B base) | multi-vector, max 768 patches per page [S10] | page images, text | Apache-2.0 [S10] | Trained with colpali-engine 0.3.1 [S10] |
| Nomic Embed Multimodal 7B | Nomic AI [S20] | 7B (Qwen2.5-VL-7B base, PEFT) [S20] | dense; ColNomic variants are multi-vector [S20] | text, images, interleaved | Apache-2.0 [S20] | 58.8 NDCG@5 on ViDoRe-v2 per its card [S20] |
| SigLIP 2 | Google, Feb 2025 [S21] | ViT (B/16 shown) [S21] | **UNVERIFIED** here | image, text | Apache-2.0 for the timm B/16 build [S21] | Successor to SigLIP for image-text retrieval; not a video or audio model |
| ImageBind | Meta, May 2023 [S22] | not verified | one shared space for six modalities [S22] | six modalities incl. image and audio (full list **UNVERIFIED**) | **UNVERIFIED** | Binds modalities through image-paired data [S22] |
| CLAP | LAION [S23] | **UNVERIFIED** | **UNVERIFIED** | audio, text | **UNVERIFIED** | Repo fetched, navigation only |
| VLM2Vec-V2 / GME | TIGER-Lab; Alibaba NLP [S24][S25][S26] | 2B to 7B | **UNVERIFIED** | text, image, video, visual docs | **UNVERIFIED** | MMEB-V2 benchmark, 78 tasks [S24][S26] |

Not covered in depth this session: OpenCLIP, original CLIP, jina-clip, and Gemini's own MMEB score. Mark them as gaps if the guide needs them.

## Strengths

- **One index, many modalities.** Qwen3-VL-Embedding accepts "text, images, screenshots, and videos, as well as inputs containing a mixture of these modalities" [S1]. Gemini Embedding 2 maps "text, images, video, audio, and documents" into one space [S13].
- **Screenshots and documents without OCR.** Voyage says its models "eliminat[e] the need for complex text extraction or ETL pipelines" for figures, slides and document screenshots [S7]. ViDoRe V3 reports that "visual retrievers outperform textual ones" and that "hybrid or purely visual contexts enhance answer generation quality" [S27].
- **Matryoshka dimensions.** Qwen (64 to 4096), Cohere (256 to 1536), Voyage (256 to 2048) and Gemini (down to 128 per the API docs in its search snippet) let you trade storage for accuracy [S1][S16][S15][S14]. Jina states truncation to 128 "with minimal performance loss" [S19]; this is the vendor's claim.
- **Open weights at 2B.** Qwen 2B and 8B, Jina v4, Nomic 7B and ColQwen2 all run locally [S1][S19][S20][S10].
- **Long inputs.** Qwen 32K, Jina v4 32K, Voyage 32K, Cohere 128K, Gemini text 8,192 tokens [S1][S19][S15][S16][S13].

## Limits and failure modes

- **Modality gap persists in practice.** Even unified backbones can rank same-modality items higher. Measure cross-modal recall at k on your own data before trusting a mixed index [S8].
- **Text-only penalty.** Qwen's own MMTEB table shows the VL embedder trails its text sibling. At 8B the mean task score is 67.88 (VL) vs 70.58 (Qwen3-Embedding-8B), a gap of 2.70. At 2B the VL model scores 63.87 against 64.33 for the 0.6B text model [S1]. The Qwen blog makes this statement too, but the blog did not render in this session, so the card table is the source here.
- **Video sampling loses moments.** Gemini samples at most 32 frames: videos up to 32 s at 1 fps, longer ones uniformly to 32 frames. "Audio tracks are not processed in video files" [S13]. Speech in a video is invisible unless you send the audio separately.
- **Hard input caps.** Gemini: 6 images per request, 180 s audio, 120 s video, one PDF of up to 6 pages per request [S13]. A 40-page deck must be split.
- **Regional lock-in.** The Qwen API models are region-bound (qwen3-vl-embedding Beijing only; tongyi-embedding-vision Singapore only), each with its own key [S11].
- **Partial availability.** A Pinecone integration post (Nov 2026) says Gemini Embedding 2 "is only offered as a text model today" in that integration, despite the model's multimodal API [S28]. Check each vendor's surface before designing around it.
- **Benchmarks shift.** Qwen re-evaluated baselines "on the updated VisDoc OOD split", so MMEB-V2 numbers from different papers are not directly comparable [S1].
- **Multi-vector storage and latency.** See the arithmetic above. Late interaction needs a MaxSim-capable index.
- **Dimension choice is irreversible per index.** Changing model or dimensions means re-embedding everything. This is general engineering knowledge, not sourced here.

## Exact use cases

**Pick a multimodal embedder when:**
- **Screenshot memory for computer-use agents.** Embed each screenshot as an image and retrieve by text intent. Storage at 4096-dim fp16 is about 8 KB per screenshot (arithmetic). Suitability for agent tasks is **UNVERIFIED** (no agent benchmark checked).
- **Photo libraries.** Image-to-text and image-to-image search with a 2B model is the cheapest path. Identity or face search is out of scope for these sources.
- **PDF and slide search.** Use a visual-document model: ColQwen2, Jina v4 multi-vector, or Nomic ColNomic. ViDoRe V3 (10 datasets, about 26,000 pages, 3,099 queries, 6 languages) is the enterprise test bed [S27].
- **Video moments.** Qwen3-VL-Embedding-8B (video retrieval and moment-retrieval tasks are in MMEB-V2) [S1]; Gemini for short clips under 120 s [S13]; Voyage multimodal-3.5 for video [S15].
- **Social posts (image + caption).** Use a single fused vector: Qwen `enable_fusion=true` [S11] or Gemini with image and text in one `contents` list [S13]. For a post with several media items, Google recommends embedding each item and averaging for a post-level vector [S13].

**Avoid a multimodal embedder when:**
- The corpus is text-first and the text is already clean. A text embedder (Qwen3-Embedding, Gemini text) wins on text by the Qwen MMTEB gap above [S1].
- You need a human-readable audit trail. A captioning VLM writes down what it saw; an embedding does not.
- Hardware is small and the corpus is mostly images that a caption already describes well.

**Prefer a captioning VLM plus text embedding when:**
- You want a text reranker on top. ViDoRe V3 finds that "textual reranking substantially improve[s] performance" [S27].
- Captions must be reviewed, edited or logged for compliance.
- Your retrieval budget is text-only and you are indexing many images cheaply. (This is my judgment; cost data for captioning was not gathered.)

## Setup walkthrough

These commands come from the model cards and READMEs. Replace placeholder URLs with your own files.

**Qwen3-VL-Embedding via sentence-transformers** [S1]:
```bash
pip install sentence-transformers
```
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("Qwen/Qwen3-VL-Embedding-8B")
queries = ["A woman playing with her dog on a beach at sunset."]
docs = [
    "A woman shares a joyful moment with her golden retriever on a sunny beach.",
    "https://example.com/screenshot.jpg",  # image by URL (local-path support: UNVERIFIED)
    {"text": "caption text", "image": "https://example.com/screenshot.jpg"},  # mixed input
]
q = model.encode(queries, prompt="Retrieve relevant documents for the query.")
d = model.encode(docs)
print(model.similarity(q, d))
```

**Qwen3-VL-Embedding from the GitHub repo, with a local download** [S2]:
```bash
git clone https://github.com/QwenLM/Qwen3-VL-Embedding.git
cd Qwen3-VL-Embedding && bash scripts/setup_environment.sh && source .venv/bin/activate
huggingface-cli download Qwen/Qwen3-VL-Embedding-2B --local-dir ./models/Qwen3-VL-Embedding-2B
```
Repo requirements for the transformers path: `transformers>=4.57.0`, `qwen-vl-utils>=0.0.14`, `torch==2.8.0`, with flash-attention 2 recommended for speed and memory [S1].

**Qwen3-VL-Embedding via Alibaba Model Studio** [S11]: the API reference names `qwen3-vl-embedding` (Beijing) and `tongyi-embedding-vision-plus` (Singapore). Fusion is `enable_fusion=true`. The full request shape is **UNVERIFIED** here; read the Model Studio page before writing code.

**Gemini Embedding 2** [S12][S13]:
```python
from google import genai
from google.genai import types

client = genai.Client()  # reads GEMINI_API_KEY
img = open("dog.png", "rb").read()
result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=["An image of a dog", types.Part.from_bytes(data=img, mime_type="image/png")],
)
# Multiple parts in one contents list give ONE aggregated embedding.
# Pass separate Content objects to get one embedding each.
```
Raw REST call is `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent` with header `x-goog-api-key` [S12]. Do not use `task_type`; prefix text with a task string such as `task: search result | query: ...` [S12].

**Jina embeddings v4** [S19]:
```bash
pip install -U "transformers>=4.52.0" "torch>=2.6.0" "peft>=0.15.2" torchvision pillow
```
```python
import torch
from transformers import AutoModel

model = AutoModel.from_pretrained("jinaai/jina-embeddings-v4", trust_remote_code=True, torch_dtype=torch.float16).to("cuda")
q = model.encode_text(texts=["Overview of climate change impacts on coastal cities"], task="retrieval", prompt_name="query")
p = model.encode_image(images=["https://example.com/page.png"], task="retrieval")
```
Hosted alternative: `POST https://api.jina.ai/v1/embeddings` with `"model": "jina-embeddings-v4"` and `"task"` set [S19].

**ColQwen2 (multi-vector)** [S10]:
```python
from sentence_transformers import MultiVectorEncoder

model = MultiVectorEncoder("vidore/colqwen2-v1.0")
q = model.encode_query(["Which planet is known as the Red Planet?"])
d = model.encode_document(["Mars, known for its reddish appearance, is often called the Red Planet."])
print(model.similarity(q, d))
```
For page images the card's `colpali-engine` route is the reference [S10]. Image-document encoding via `encode_document` is **UNVERIFIED** in this session.

**Voyage multimodal-3.5** [S7][S15]: install the `voyageai` Python package and set an API key. The request code was not fetched; **UNVERIFIED**.

**Cohere Embed v4** [S16][S17]: model on Cohere Platform, AWS SageMaker and Azure AI Foundry. Request code not fetched; **UNVERIFIED**.

**Hardware sizing (arithmetic, not measured):**
- Weights in bf16 take about 2 bytes per parameter. 2B is about 4 to 5 GB; 8B is about 16 GB; Jina v4 at 3.8B is about 7.6 GB; Nomic 7B is about 14 GB. Add activations and KV for long pages.
- An 8 GB GPU fits the 2B in bf16 on paper. The 8B needs a 16 to 24 GB card or 4-bit quantization. Qwen lists quantization support for the output embedding, not for the model weights [S1].
- CPU inference throughput was not measured. Do not promise a latency number without a benchmark.

Verification commands to run after install: `nvidia-smi` (VRAM use during encode), and an end-to-end check that a text query retrieves a known image in the top 5 of your own 50-item set.

## Numbers

**MMEB-V2 (Qwen's own run, 78 tasks; overall score) [S1]:**

| Model | Image overall | Video overall | VisDoc overall | All |
|---|---|---|---|---|
| Qwen3-VL-Embedding-8B | 80.1 | 66.1 | 83.3 | **77.9** (card table) |
| Qwen3-VL-Embedding-2B | 75.0 | 61.1 | 80.2 | 73.4 |
| Seed-1.6-embedding-1215 | 78.0 | 67.7 | 82.2 | 76.9 |
| IFM-TTE (8B) | 77.9 | 59.2 | 79.5 | 74.1 |
| RzenEmbed (8B) | 75.9 | 55.7 | 81.3 | 72.9 |
| VLM2Vec-V2 (2B) | 64.9 | 34.6 | 69.2 | 59.2 |
| GME-2B | 51.9 | 33.6 | 76.8 | 55.3 |

The 8B score appears as 77.9 in the card table and 77.8 in the arXiv abstract [S1][S4]. The card's abstract line also says "as of January 8, 2025", which is a typo for 2026 [S4]. Quote the table value and note the discrepancy.

**MMTEB (text-only, Qwen's run) [S1]:** Qwen3-VL-Embedding-8B mean (task) 67.88; Qwen3-Embedding-8B 70.58; Qwen3-VL-Embedding-2B 63.87; Qwen3-Embedding-0.6B 64.33.

**ViDoRe:**
- Nomic Embed Multimodal 7B: 58.8 NDCG@5 on ViDoRe-v2 [S20].
- ViDoRe V3 (paper): 10 datasets, about 26,000 pages, 3,099 queries, 6 languages [S27]. The paper's abstract does not give single-model headline scores.
- Secondary sources (not verified against the leaderboard, treat as **UNVERIFIED**): a pure-vision pipeline at 70.01 average nDCG@10 on ViDoRe V3 with reranking [S29]; a 9-model run at 67.0 nDCG@10 [S30]; EVIE-Preview-4.5B at 64.40 on ViDoRe V3 public [S31]. These are pipeline or third-party numbers, not single embedder cards.

**Pricing:**
- Gemini Embedding 2, paid standard: text $0.20 per 1M tokens; image $0.45 per 1M ($0.00012 per image); audio $6.50 per 1M ($0.00016 per second); video $12.00 per 1M ($0.00079 per frame). Batch is half of standard for text ($0.10) [S32].
- Qwen Model Studio: qwen3-vl-embedding image/video $0.258 per 1M tokens, text $0.10; tongyi-embedding-vision-plus $0.09 per 1M; tongyi-embedding-vision-flash image/video $0.03 per 1M [S11].
- Cohere Embed v4: $0.47 per 1M image tokens (third-party pricing page; **UNVERIFIED** against Cohere's price list) [S33].

## Sources

- [S1] Qwen3-VL-Embedding-8B model card, Hugging Face: https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B (model list, MMEB-V2 and MMTEB tables, sentence-transformers usage, licence Apache-2.0)
- [S2] QwenLM/Qwen3-VL-Embedding GitHub README: https://github.com/QwenLM/Qwen3-VL-Embedding and raw README https://raw.githubusercontent.com/QwenLM/Qwen3-VL-Embedding/main/README.md (architecture, download and setup commands, requirements)
- [S3] Qwen3-VL-Embedding technical report (arXiv:2601.04720, submitted 8 Jan 2026, revised 19 Jan 2026): https://arxiv.org/abs/2601.04720
- [S4] Same arXiv abstract, which gives MMEB-V2 overall 77.8: https://arxiv.org/abs/2601.04720
- [S5] Qwen blog, not rendered in this session: https://qwen.ai/blog?id=qwen3-vl-embedding (UNVERIFIED content)
- [S6] Qwen3-VL-Embedding-8B search snippets, Superlinked and learnopencv articles (secondary, not used for numbers): https://superlinked.com/blog/qwen3-embedding-reranker-guide
- [S7] Voyage AI, Multimodal Embeddings docs: https://docs.voyageai.com/docs/multimodal-embeddings
- [S8] Liang et al., "Mind the Gap: Understanding the Modality Gap in Multi-modal Contrastive Representation Learning" (NeurIPS 2022): https://arxiv.org/abs/2203.02053
- [S9] Faysse et al., "ColPali: Efficient Document Retrieval with Vision Language Models" (ICLR 2025): https://arxiv.org/abs/2407.01449
- [S10] vidore/colqwen2-v1.0 model card: https://huggingface.co/vidore/colqwen2-v1.0
- [S11] Alibaba Cloud Model Studio, Multimodal-Embedding API details (last updated 20 Nov 2026): https://www.alibabacloud.com/help/en/model-studio/multimodal-embedding-api-reference and model list https://www.alibabacloud.com/help/en/model-studio/models
- [S12] Gemini API, Embeddings docs (Gemini Embedding 2 code and task prefixes): https://ai.google.dev/gemini-api/docs/embeddings
- [S13] Gemini Embedding 2 multimodal limits and embedding aggregation (same page, "Multimodal embeddings" section): https://ai.google.dev/gemini-api/docs/embeddings#multimodal
- [S14] Gemini Embedding 2 dimensions: Google Cloud docs search snippet (3072-dim output): https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/embedding-2 ; MRL truncation range from secondary source https://tokencost.app/blog/gemini-embedding-2-pricing (secondary)
- [S15] Voyage voyage-multimodal-3.5 model table (in [S7]); launch blog https://blog.voyageai.com/2026/01/15/voyage-multimodal-3-5/
- [S16] Cohere, Announcing Embed Multimodal v4 (15 Apr 2025): https://docs.cohere.com/changelog/embed-multimodal-v4
- [S17] AWS Bedrock, Cohere Embed v4 parameters (image pixel limit): https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-embed-v4.html
- [S18] Jina AI, jina-embeddings-v4 blog reference (URL from model card): https://jina.ai/news/jina-embeddings-v4-universal-embeddings-for-multimodal-multilingual-retrieval
- [S19] jinaai/jina-embeddings-v4 model card and arXiv:2506.18902 (3.8B, 2048 single-vector, 128 multi-vector, adapters): https://huggingface.co/jinaai/jina-embeddings-v4 and https://arxiv.org/abs/2506.18902
- [S20] nomic-ai/nomic-embed-multimodal-7b model card: https://huggingface.co/nomic-ai/nomic-embed-multimodal-7b
- [S21] timm/ViT-B-16-SigLIP2 model card (Apache-2.0; arXiv:2502.14786): https://huggingface.co/timm/ViT-B-16-SigLIP2
- [S22] ImageBind, arXiv:2305.05665: https://arxiv.org/abs/2305.05665
- [S23] LAION-AI/CLAP repository: https://github.com/LAION-AI/CLAP (navigation only in this session; specs UNVERIFIED)
- [S24] TIGER-Lab/VLM2Vec repository (MMEB-V2, 78 tasks): https://github.com/TIGER-AI-Lab/VLM2Vec
- [S25] GME, arXiv:2412.16855 (CVPR 2025): https://arxiv.org/abs/2412.16855
- [S26] VLM2Vec-V2, arXiv:2507.04590 (7 Jul 2025): https://arxiv.org/abs/2507.04590
- [S27] ViDoRe V3, arXiv:2601.08620 (v2 revised 21 Apr 2026): https://arxiv.org/abs/2601.08620 ; ViDoRe org page https://huggingface.co/vidore
- [S28] Pinecone, integrated embedding for Gemini (12 Nov 2026): https://www.pinecone.io/blog/integrated-embedding-google/
- [S29] "Two Pure-Vision Pipelines at the Top of ViDoRe V3" (Hugging Face blog, 23 Oct 2026; pipeline score, UNVERIFIED): https://huggingface.co/blog/Ryenhails/pure-vision-vidore-v3
- [S30] Conare.ai ViDoRe v3 embedding leaderboard (10 Nov 2026; UNVERIFIED): https://conare.ai/evals/vidore-embedding
- [S31] EVIE-Preview-4.5B secondary write-up (UNVERIFIED): https://www.orcarouter.ai/blog/evie-preview-4-5b-quiet-release
- [S32] Gemini API pricing, Gemini Embedding 2 section: https://ai.google.dev/gemini-api/docs/pricing
- [S33] Cohere pricing, third-party summary (UNVERIFIED): https://embeddingcost.com/cohere

**Not verified this session:** jina-clip, OpenCLIP, original CLIP numbers, Gemini MMEB score, Voyage and Cohere request code, Jina v4 licence field, ImageBind and CLAP specs, ColQwen2 per-patch dimension, Qwen blog text.

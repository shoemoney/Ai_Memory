# 06. Uncensored (abliterated) small LLMs as memory models

Research snapshot: 2026-11-20. Neutral technical survey. Every fact carries its source. Anything I could not verify is marked **UNVERIFIED**.

## How it works

**Refusal is a direction.** Arditi et al. showed refusal in chat models is mediated by a single direction in the residual stream: remove it and the model stops refusing; add it and the model refuses harmless prompts too. [arXiv 2406.11717](https://arxiv.org/abs/2406.11717), summarised in [mlabonne's HF blog, 13 Jun 2024](https://huggingface.co/blog/mlabonne/abliteration).

**The recipe** (mlabonne's write-up, [source](https://huggingface.co/blog/mlabonne/abliteration)):
1. Run harmful and harmless prompt sets, record residual activations at the last token.
2. Take the mean difference per layer; normalise; pick the best direction.
3. Ablate it, either at inference (subtract the projection from every component that writes to the stream) or permanently by orthogonalising the weights against it.

**Heretic** ([github.com/p-e-w/heretic](https://github.com/p-e-w/heretic), AGPL-3.0, about 42k stars) automates this. It uses a TPE optimiser (Optuna) over ablation parameters and minimises two scores by default: refusal rate (keyword-based) and KL divergence from the original on harmless prompts. Its default modifier is Arbitrary-Rank Ablation (ARA); classic directional ablation is also available. Install is `pip install -U heretic-llm` then `heretic <model>`, Python 3.10+, PyTorch 2.6+. The README reports about 30-40 minutes for Qwen3-4B on an RTX 3090. Heretic also has a `bnb_4bit` option to lower VRAM during processing.

**Nuance from newer work.** Joad et al. (arXiv 2602.02132, v2 revised 15 Sep 2026, accepted at EMNLP 2026) find that refusal behaviours correspond to geometrically distinct directions, and that steering along any of them mostly changes *how* a model refuses, not whether. Their point is that single-direction abliteration is a simplification, not that it fails. [arXiv 2602.02132](https://arxiv.org/abs/2602.02132)

**Abliterated is not the same as uncensored fine-tuned.** Abliteration edits weights with no training data. Uncensored fine-tunes (Dolphin-style SFT/DPO on compliant data) change behaviour through training. I did not find a measured head-to-head of the two on memory tasks. **UNVERIFIED** for memory work.

## Models and tools (as of 2026-11-20)

| Model / tool | Base | Date / version | Refusals (stock to abliterated) | KL divergence | Source |
|---|---|---|---|---|---|
| huihui-ai/Huihui-Qwen3.8-27B-abliterated | Qwen3.8 27B | HF page dated 8 Nov 2026; tags abliterated, uncensored; Apache-2.0 | not read in the card | not read | [HF](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated) |
| huihui v2 Qwen3.8-Flash-Next | Qwen3.8 Flash Next (MoE, about 158 GB at Q5) | v2 | 99 to 14 (harmful, instruct) | 0.040 on WikiText-2 | [nazeshinjite LoRA card](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA) |
| petruhonk/Qwen3.8-9B-Distill-uncensored-heretic | Qwen3.5-9B distill (per its own description; the name says 3.8) | Apache-2.0 | not read | not read | [HF](https://huggingface.co/petruhonk/Qwen3.8-9B-Distill-uncensored-heretic) |
| mradermacher/Qwen3.8-9B-heretic-uncensored-GGUF | Qwen3.8 9B distill | GGUF quants, Q4_K_M shown | not read | not read | [HF](https://huggingface.co/mradermacher/Qwen3.8-9B-heretic-uncensored-GGUF) |
| Kooten/gemma-4-31b-abliterated-v1.1 | Gemma 4 31B | Heretic, 929 trials | 26/100 | 0.3687 | [HF](https://huggingface.co/Kooten/gemma-4-31b-abliterated-v1.1) |
| Luni/Gemma-4-31B-Heretic | Gemma 4 31B | selected trial 48 | 41.25% (33/80), its own test set | about 1.22 | [HF](https://huggingface.co/Luni/Gemma-4-31B-Heretic) |
| pmarreck/gemma4-heretical | Gemma 4 31B | Ollama packaging, ARA | 98 to 5 | 0.012 | [GitHub](https://github.com/pmarreck/gemma4-heretical) |
| Sabomako/gemma-4-12B-it-heretic | Gemma 4 12B | Heretic v1.3.0, custom method | 98/100 to 0/100 | 0.0545 | [HF](https://huggingface.co/Sabomako/gemma-4-12B-it-heretic) |
| Heretic benchmark row, Gemma 3 12B | Gemma 3 12B | p-e-w/gemma-3-12b-it-heretic | 97 to 3 | 0.16 (huihui's version: 0.45; mlabonne v2: 1.04) | [Kooten card table, citing the Heretic repo](https://huggingface.co/Kooten/gemma-4-31b-abliterated-v1.1) |
| abliterlitics Gemma 4 E2B comparison | Gemma 4 E2B | 13 community variants compared, Sep 2026 | varies | varies; one creator claimed 0.001 and measured 0.187 | [abliterlitics](https://abliterlitics.dev/models/gemma4-e2b/) |
| Tools: Heretic | n/a | heretic-llm on PyPI, v2 configs not compatible with v1 | n/a | n/a | [README](https://raw.githubusercontent.com/p-e-w/heretic/master/README.md) |
| Tools: mlx-heretic | n/a | Apple Silicon port, writes mlx-lm format | n/a | n/a | [GitHub](https://github.com/akaiHuang/mlx-heretic) |
| Tools: OBLITERATUS (NousResearch) | n/a | diff-in-means, CUDA and MLX backends | n/a | n/a | [Hermes docs](https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-obliteratus) |

**Heretic-era naming.** "heretic" on a model name means the weights were produced by Heretic. "abliterated" means a generic abliteration. "uncensored" is a marketing label and often means a fine-tune. Check the model card, not the name.

**Uncensored Gemma and Qwen releases are common, and so are untested claims.** Several cards report "0.0% refusal" with no KL or capability numbers. The abliterlitics E2B study found that one creator's claimed KL of about 0.001 measured 0.187, and that one claimed 0.0% refusal rate was not reproduced. [abliterlitics](https://abliterlitics.dev/models/gemma4-e2b/)

## Strengths

- **Refusal removal is cheap.** Heretic on a small dense model is a one-afternoon job per the README; no fine-tuning data. [README](https://raw.githubusercontent.com/p-e-w/heretic/master/README.md)
- **Capability can be kept.** The best-measured cases show small KL. The Sabomako 12B run shows KL 0.0545 with refusals going from 98 to 0 out of 100; the Gemma 3 12B Heretic row shows 97 to 3 at KL 0.16. [Kooten card](https://huggingface.co/Kooten/gemma-4-31b-abliterated-v1.1), [Sabomako card](https://huggingface.co/Sabomako/gemma-4-12B-it-heretic)
- **Tool calling can survive.** The nazeshinjite LoRA card reports 29/29 valid tool calls on a 35-case suite, the same as the base model, and WikiText perplexity change of +0.0005. These are the author's numbers. [LoRA card](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA)
- **Reversible, with a LoRA form.** The same card packages huihui's v2 edit as a 2.3 MB rank-1 GGUF LoRA. It can be loaded with `--lora-init-without-apply` and switched on per request. [LoRA card](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA)
- **Runs locally on Apple Silicon.** mlx-heretic saves mlx-lm weights, which you can 4-bit with `mlx_lm.convert`. [mlx-heretic](https://github.com/akaiHuang/mlx-heretic)

## Limits and failure modes

- **Multi-step agent degradation.** A llama.cpp discussion titled "Abliterated Qwen3.8-27B loops and falls apart on multi-step agentic..." describes repeated tool calls and loss of instruction-following after several good turns. I only saw the search snippet, not the thread body, so treat this as **partly verified**. [llama.cpp #28430](https://github.com/ggml-org/llama.cpp/discussions/28430)
- **Refusal removal is global, not topic-specific.** Heretic issue #65 notes that abliteration suppresses refusals across topics even if the direction was computed from a few. [Heretic #65](https://github.com/p-e-w/heretic/issues/65)
- **Residual refusal and moralising.** Early community reports say refusals fall but the model may still evade or moralise. This is a 2024 Reddit thread, not a measurement. [r/LocalLLaMA 2024](https://www.reddit.com/r/LocalLLaMA/comments/1da046y/uncensor_any_llm_with_abliteration/)
- **KL is not the whole story.** A KL of 0.3 to 1.2 on the Gemma 4 31B rows is large. The Luni card's selected checkpoint has KL about 1.22 and still refuses 41% of its own test prompts. [Luni card](https://huggingface.co/Luni/Gemma-4-31B-Heretic)
- **Self-reported numbers.** Heretic's README and several cards cite numbers from their own tests; refusal counts depend on the keyword list or LLM judge used. Re-measure on your own prompts.
- **Structured output at low quants.** A general (not abliteration-specific) finding: JSON and tool-call formatting degrade at Q3 and below. Measure at the quant you will run. [Towards Data Science, Mar 2026](https://towardsdatascience.com/self-hosting-your-first-llm/)
- **JSON on abliterated memory extraction: UNVERIFIED.** I found no measured source comparing JSON validity before and after abliteration on extraction tasks. Vendor claims (for example a SmolLM3 heretic card saying it is "excellent at structured JSON") are self-reported. [K0D3IN card](https://huggingface.co/K0D3IN/SmolLM3-3B-Instruct-heretic)

## The memory-extraction claim: what I could and could not verify

The premise is that a stock extractor refuses or sanitises facts from private or adult content, so facts are dropped or rewritten into moral language before storage. **I found no measured source for this.** The community posts I could reach are about the general memory pipeline, not about refusal in extraction:

- A r/SillyTavernAI thread (May 2026) asks which long-term memory setups people are satisfied with. Its snippet shows a short-term layer on local Gemma 3 and a middle layer on built-in summarisation. The thread body was not readable through my tools. [Reddit](https://www.reddit.com/r/SillyTavernAI/comments/1t0fq11/people_who_are_satisfied_with_your_long_term/)
- Arcanum RPGs (22 Sep 2026) reports that SillyTavern's memory systems all look at a narrow window: defaults are scan depth 2, Vector Storage query 2, and Summarize injection depth 2. Summarize can do nothing on default settings without an error. This is a real failure mode for any memory layer, but it is about window size, not refusal. [Arcanum](https://arcanumrpgs.com/blog/sillytavern-memory/)

**So the corruption and silent-drop claims are UNVERIFIED.** Test it yourself: give the same 50 messages to a stock and an abliterated extractor and count dropped facts, altered facts and JSON parse failures.

## Exact use cases

**Pick it when:**
- The memory extractor sees private or adult content as a matter of normal use, and you have measured that the stock model drops or rewrites facts on your own test set.
- You run the model locally and the data never leaves your machine.
- The job is short, structured output with a schema, so you can validate and retry.
- You have measured KL and tool-call validity on your quant.

**Avoid it when:**
- The memory feeds an agent that also takes actions (multi-step tool use; see the degradation reports).
- The store will be shared, published or used by people other than you.
- You cannot pin the exact weights, hash and quant, or you took the weights from an unknown uploader.
- Your licence or employer policy forbids uncensored models.
- A stock model is adequate on your test set. Do not abliterate for convenience.

## Setup walkthrough

**A. Use a prebuilt GGUF (fastest).**
```sh
# Ollama pulls any GGUF on the Hub directly (per HF docs)
ollama run hf.co/mradermacher/Qwen3.8-9B-heretic-uncensored-GGUF:Q4_K_M

# llama.cpp, OpenAI-compatible server (card shows the newer `llama serve` form)
llama-server -hf mradermacher/Qwen3.8-9B-heretic-uncensored-GGUF:Q4_K_M --jinja --port 8080
```
Sources: [HF Ollama docs](https://huggingface.co/docs/hub/en/ollama), [mradermacher card](https://huggingface.co/mradermacher/Qwen3.8-9B-heretic-uncensored-GGUF).

**B. Import your own GGUF into Ollama.** Write a Modelfile with `FROM /abs/path/model.gguf`, then `ollama create memx -f Modelfile`. Ollama documents this flow in its import guide; for split GGUF files, keep the shard names and use a wildcard. [Ollama import docs](https://docs.ollama.com/import)

**C. Apply a LoRA instead of a second model (where the adapter exists).**
```sh
llama-server -m Qwen3.8-Flash-Next-UD-Q5_K_XL-00001-of-00006.gguf \
  --lora HUIHUI-V2-Qwen3.8-Flash-Next-LoRA-F32.gguf --lora-init-without-apply -fa on --jinja
```
Per-request enable via a `lora` field in the body. [nazeshinjite card](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA)

**D. Apple Silicon (MLX).**
```sh
uv tool install mlx-lm
mlx_lm.server --model <mlx-repo-or-local-path> --port 8080
```
The mlx-heretic route: run Heretic-style ablation with mlx-heretic, then `mlx_lm.convert` to 4-bit. [Youssofal MLX card](https://huggingface.co/Youssofal/Qwen3.6-35B-A3B-Abliterated-Heretic-MLX-8bit), [mlx-heretic](https://github.com/akaiHuang/mlx-heretic). Exact flags for `mlx_lm.convert`: **UNVERIFIED** against its help output.

**E. Abliterate your own copy with Heretic (CUDA).**
```sh
python3 -m venv ~/venvs/heretic && . ~/venvs/heretic/bin/activate
pip install -U heretic-llm
heretic Qwen/Qwen3-4B-Instruct-2507        # or your base model
# Config: ./config.toml, or HERETIC_CONFIG_FILE=/abs/path/config.toml
```
Keep the output with the config and the scores. [README](https://raw.githubusercontent.com/p-e-w/heretic/master/README.md)

**F. Point the memory framework at it.** Any framework with an OpenAI-compatible base URL works: `http://localhost:8080/v1` for llama-server, or Ollama's `/v1` route. Use a schema-constrained output for extraction, validate every record, and retry on parse failure. Whether a given memory framework (Mem0, Letta, SillyTavern's Summarize) supports this is **UNVERIFIED** for this survey; check its docs.

**G. Test before you trust it.** Build a fixed set of 50 to 100 messages with known facts. Run the stock and abliterated extractors. Record: facts dropped, facts altered, JSON parse rate, and whether any refusal or moralising text got written into memory.

## SillyTavern memory options

From the [Arcanum guide](https://arcanumrpgs.com/blog/sillytavern-memory/):
- **Summarize:** one rolling summary. Silent no-op on default settings.
- **Vector Storage:** embeddings of past messages, retrieved by similarity to the last messages. Moves history into the vector store rather than adding to it.
- **Data Bank:** attached documents, chunked and retrieved.
- **World Info (lorebooks):** keyword-triggered entries. Exact text, but only when a key appears.

A Reddit guide (28 Mar 2026) covers binding lorebooks to Vector Storage. [Reddit](https://www.reddit.com/r/SillyTavernAI/comments/1s5uvhq/complete_guide_to_setup_and_configure_vector/). TunnelVision (Coneja-Chibi) adds agentic lorebook and summary retrieval. [GitHub](https://github.com/Coneja-Chibi/TunnelVision). Hosted "less filtered" services exist; I did not verify any one's policy or data handling. **UNVERIFIED.**

## Risks

- **No safety layer on stored content.** Whatever the extractor writes becomes permanent memory. Review what it stores.
- **Licence terms differ by base.** Examples: huihui 27B card Apache-2.0; nazeshinjite LoRA card qwen-community-1.0; Heretic repo AGPL-3.0. Read each card and the base licence before redistributing. [huihui](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated), [nazeshinjite](https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA), [Heretic](https://github.com/p-e-w/heretic)
- **Provenance.** Random uploads may carry altered weights or hidden payloads. Verify hashes against the original and prefer repos with a published Heretic config and scores.
- **Legal and policy.** A CISO-oriented guide (6 Sep 2026) treats abliterated models as a policy question. I did not read it in full; treat as **partly verified**. [PlayCISO](https://playciso.com/blog/abliterated-models-refusal-removed-llm-risk-ciso-guide)
- **Privacy.** Local is private; hosted services are not. Check each service's data terms.

## Numbers

- Refusal rates: Gemma 3 12B 97/100 stock to 3/100 under three abliterations; Gemma 4 12B 98/100 to 0/100 (Sabomako); Gemma 4 31B 98 to 5 (pmarreck) and 26/100 remaining (Kooten).
- KL: 0.0545 (Sabomako 12B), 0.012 (pmarreck 31B), 0.16 / 0.45 / 1.04 (Gemma 3 12B Heretic / huihui / mlabonne), 0.3687 (Kooten 31B), about 1.22 (Luni 31B, selected checkpoint), 0.040 (huihui v2 Qwen3.8 Flash Next on WikiText-2).
- Qwen3.8 Flash Next (nazeshinjite card, 100 prompts): harmful instruct 99 to 14; JailbreakBench harmful thinking 93 to 3 with LoRA vs 5 with huihui v2; benign over-refusal 18 to 0.
- Heretic speed: about 30-40 min for Qwen3-4B on an RTX 3090 (README).
- Models with "heretic" on HF: the README says "thousands" (no exact count verified).

## Sources

- Arditi et al., arXiv 2406.11717: https://arxiv.org/abs/2406.11717
- Joad et al., arXiv 2602.02132: https://arxiv.org/abs/2602.02132
- mlabonne, Uncensor any LLM with abliteration (HF blog, 13 Jun 2024): https://huggingface.co/blog/mlabonne/abliteration
- Heretic repo and README: https://github.com/p-e-w/heretic , https://raw.githubusercontent.com/p-e-w/heretic/master/README.md
- Heretic issue #65: https://github.com/p-e-w/heretic/issues/65
- huihui-ai Huihui-Qwen3.8-27B-abliterated: https://huggingface.co/huihui-ai/Huihui-Qwen3.8-27B-abliterated
- nazeshinjite Qwen3.8-Flash-Next LoRA: https://huggingface.co/nazeshinjite/Qwen3.8-Flash-Next-Abliterated-LoRA
- petruhonk Qwen3.8-9B heretic: https://huggingface.co/petruhonk/Qwen3.8-9B-Distill-uncensored-heretic
- mradermacher Qwen3.8-9B heretic GGUF: https://huggingface.co/mradermacher/Qwen3.8-9B-heretic-uncensored-GGUF
- Kooten Gemma 4 31B: https://huggingface.co/Kooten/gemma-4-31b-abliterated-v1.1
- Luni Gemma 4 31B Heretic: https://huggingface.co/Luni/Gemma-4-31B-Heretic
- Sabomako Gemma 4 12B: https://huggingface.co/Sabomako/gemma-4-12B-it-heretic
- pmarreck gemma4-heretical: https://github.com/pmarreck/gemma4-heretical
- abliterlitics Gemma 4 E2B: https://abliterlitics.dev/models/gemma4-e2b/
- mlx-heretic: https://github.com/akaiHuang/mlx-heretic
- Hermes OBLITERATUS docs: https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/mlops/mlops-obliteratus
- llama.cpp discussion 28430 (snippet only): https://github.com/ggml-org/llama.cpp/discussions/28430
- Ollama import docs: https://docs.ollama.com/import ; HF Ollama docs: https://huggingface.co/docs/hub/en/ollama
- Towards Data Science, self-hosting (Mar 2026): https://towardsdatascience.com/self-hosting-your-first-llm/
- Arcanum RPGs, SillyTavern memory (22 Sep 2026): https://arcanumrpgs.com/blog/sillytavern-memory/
- r/SillyTavernAI memory thread (snippet): https://www.reddit.com/r/SillyTavernAI/comments/1t0fq11/people_who_are_satisfied_with_your_long_term/
- r/SillyTavernAI vector storage guide (snippet): https://www.reddit.com/r/SillyTavernAI/comments/1s5uvhq/complete_guide_to_setup_and_configure_vector/
- TunnelVision: https://github.com/Coneja-Chibi/TunnelVision
- PlayCISO legal/risk (partly read): https://playciso.com/blog/abliterated-models-refusal-removed-llm-risk-ciso-guide

**Not verified:** memory-extraction refusal corruption and silent drops (no measured source); JSON validity before vs after abliteration on extraction; mlx_lm.convert flags; per-framework support for abliterated backends; hosted "less filtered" service policies; the llama.cpp thread body; the Qwen3.8 9B heretic base naming (its description says Qwen3.5-9B distill).

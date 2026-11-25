# Agent and LLM memory: the research frontier, 2025 to November 2026

Research notes, 2026-11-20. Maturity labels: **[SHIPPED]** = usable today through a product, API or maintained open-source code. **[PROTO]** = working prototype or open code, not a product. **[PAPER]** = paper result only. **UNVERIFIED** = named in the research question or seen only as a search snippet; the primary page was not read in this session, so no number is given as fact.

## Map of the frontier

The field has split into five camps, and most 2026 work sits on a boundary between two of them.

1. **Offline and sleep-time work.** Spend compute before the query arrives: consolidate, pre-compute, summarise.
2. **Memory in the weights.** Write facts into parameters (self-updatable pools, test-time training, LoRA or "engram" edits, knowledge editing).
3. **Compressed or latent memory.** Replace raw tokens with KV caches, trained cartridges or latent tokens.
4. **Agent-curated text memory.** The agent itself decides what to store, link, revise and retrieve, often trained with RL.
5. **Procedural and skill memory.** Store reusable workflows or playbooks rather than facts.

Two cross-cutting threads matter for a practitioner guide: benchmarks are being rebuilt because LoCoMo is saturating, and memory is now an attack surface.

## Each line of work

### 1. Sleep-time compute and offline consolidation

- **Sleep-time compute: Beyond Inference Scaling at Test-time.** Lin, Snell, Wang, Packer, Wooders, Stoica, Gonzalez (Berkeley, with Letta). arXiv:2504.13171, submitted 17 Apr 2025, https://arxiv.org/abs/2504.13171. Mechanism: the model "thinks" about a context before the query, anticipating questions and pre-computing useful quantities. Results on modified reasoning tasks (Stateful GSM-Symbolic, Stateful AIME): about 5x less test-time compute for the same accuracy; up to +13% and +18% accuracy when sleep-time compute is scaled; Multi-Query GSM-Symbolic cuts average cost per query 2.5x. Gains depend on several queries sharing one context. Maturity: **[PAPER]** with a later Berkeley tech report (EECS-2026-114, May 2026, https://www2.eecs.berkeley.edu/Pubs/TechRpts/2026/EECS-2026-114.pdf, snippet-level only).
- **Letta's productisation.** Letta describes sleep-time agents that edit the memory blocks of a primary agent "anytime", so the primary agent reads updated memory without waiting. https://www.letta.com/blog/sleep-time-compute/ (21 Apr 2025) and https://www.letta.com/blog/memory-blocks/. Maturity: **[SHIPPED]** in Letta's framework, as described by Letta; I did not test it.

### 2. Memory in model weights

- **Test-time memorisation: Titans.** Behrouz et al. (Google Research; full author list not re-checked). arXiv:2501.00663, 31 Dec 2024, https://arxiv.org/abs/2501.00663. Mechanism: attention acts as short-term memory and a neural long-term module is updated during inference, so it memorises the context it sees. Reported: better than Transformers and linear recurrent models on language, reasoning, genomics and time series; scales beyond a 2M context with better needle-in-haystack accuracy than baselines. Maturity: **[PAPER]**. An independent lightweight reimplementation (arXiv:2510.09551, Oct 2025, https://arxiv.org/abs/2510.09551) finds the neural memory helps against attention-only models but that chunking limits the reimplementation's practical performance.
- **Titans successors.** Atlas (arXiv:2505.23735, 29 May 2025, https://arxiv.org/html/2505.23735v1) is a higher-capacity test-time memory. "Nested Learning" (arXiv:2512.24695, 31 Dec 2025, https://arxiv.org/abs/2512.24695) proposes a Continuum Memory System and a self-modifying "Hope" module, and claims a route to continual learning. Maturity: **[PAPER]**; I did not find independent replication of the continual-learning claim. Test-Time Training for Long-Context LLMs (arXiv:2512.13898, https://arxiv.org/abs/2512.13898) argues static attention suffers "score dilution" and proposes targeted gradient updates on the given context. Its headline gains are not verified beyond the abstract.
- **Self-updatable pools: MemoryLLM and M+.** MemoryLLM (arXiv:2402.04624, Feb 2024, https://arxiv.org/abs/2402.04624) keeps a latent memory pool that is overwritten on update. M+ (arXiv:2502.00592, 1 Feb 2025, https://arxiv.org/abs/2502.00592) extends it to scalable long-term memory. Maturity: **[PAPER]**; the memory pool is a fixed-size latent store, so forgetting is by design.
- **Per-user weights.** "Internalizing Per-User Memory as Local Parametric Edits" (arXiv:2606.19172, 17 Jun 2026, https://arxiv.org/html/2606.19172v1) stores each user's facts as edits to a hash-keyed memory table and shares a reasoning adapter. It claims direct recall matches per-user LoRA while giving 5.6x higher indirect-reasoning accuracy, and that edits from different users compose losslessly in one shared table, which a single LoRA cannot do. Maturity: **[PAPER]**, self-reported. A companion probe, "How LoRA Remembers?" (arXiv:2605.30260, https://arxiv.org/html/2605.30260v1), fits a capacity law for LoRA memory.
- **Knowledge editing lineage.** ROME (Meng et al., "Locating and Editing Factual Associations in GPT", arXiv:2202.05262, Feb 2022, https://arxiv.org/abs/2202.05262) edits one fact by a rank-one update to an MLP. MEMIT extends this to mass edits (arXiv:2210.07229; I did not open its page this session, so UNVERIFIED beyond citation by later papers). Maturity: **[PROTO]** in research tooling; editing is brittle for multi-hop and paraphrased queries, which is why it is not a memory product.
- **Cartridges (KV-cache distillation).** Eyuboglu, Ehrlich, Arora, Guha, ..., Ré (Stanford Hazy Research). arXiv:2506.06266, 6 Jun 2025, https://arxiv.org/abs/2506.06266. Mechanism: train a smaller KV cache offline per corpus (a "Cartridge") using self-study, which generates synthetic conversations and trains with a context-distillation loss. Naive next-token training was not competitive with in-context learning. Reported: on challenging long-context benchmarks, Cartridges match in-context-learning quality with 38.6x less memory and are cheaper to serve. Code: https://github.com/HazyResearch/cartridges. Maturity: **[PROTO]** with open code.

### 3. Latent and compressed memory

- **MemGen.** Zhang et al. arXiv:2509.24704, 29 Sep 2025, https://arxiv.org/abs/2509.24704. A reinforcement-learned *memory trigger* watches the reasoning state and decides when to call a *memory weaver* that emits latent tokens into the reasoning. Reported across eight benchmarks: up to 38.22% over ExpeL and AWM (external-memory systems) and up to 13.44% over GRPO, with cross-domain transfer. The authors say planning, procedural and working-memory-like behaviours emerge without supervision. Maturity: **[PAPER]**.
- **Recursive Language Models.** Zhang, Kraska, Khattab. arXiv:2512.24601, 31 Dec 2025 (v3 11 May 2026), https://arxiv.org/abs/2512.24601. Mechanism: the long prompt is an external variable the model inspects and recursively calls itself over, with snippets. Reported: inputs up to two orders of magnitude beyond the window; on GPT-5, a median of +26% over compaction, +130% over CodeAct with sub-calls and +13% over Claude Code at comparable cost; a post-trained RLM-Qwen3-8B beats its base model by 28.3% on average. Code: https://github.com/alexzhang13/rlm. Maturity: **[PROTO]**, open code.

### 4. Agent-curated memory

- **A-MEM.** Xu et al. arXiv:2502.12110, Feb 2025, https://arxiv.org/abs/2502.12110. Zettelkasten-style notes with keywords and tags; new notes link to old ones and can rewrite their attributes ("memory evolution"). Code: https://github.com/agiresearch/a-mem. Maturity: **[PROTO]**. Benchmark numbers UNVERIFIED in this session.
- **Agentic Context Engineering (ACE).** Zhang, Hu, Upasani, ..., Zou, Olukotun. arXiv:2510.04618, 6 Oct 2025 (v3 29 Mar 2026), https://arxiv.org/abs/2510.04618. Mechanism: contexts are *playbooks* updated by generate, reflect and curate steps with structured incremental deltas, which prevents "context collapse" from iterative rewriting. Reported: +10.6% on agent benchmarks and +8.6% on finance, with lower adaptation latency and rollout cost, and no labelled supervision needed. Code: https://github.com/ace-agent/ace. Maturity: **[PROTO]** with open code.
- **ReasoningBank.** Ouyang et al. (Google Research code), arXiv:2509.25140, 29 Sep 2025 (v2 16 Mar 2026), https://arxiv.org/abs/2509.25140. Mechanism: distil transferable reasoning strategies from the agent's own self-judged successes and failures, retrieve them at test time, and write back new ones; MaTTS (memory-aware test-time scaling) generates more contrastive experiences per task. Reported: consistently beats raw-trajectory and success-only memory on web-browsing and software-engineering benchmarks. Numbers UNVERIFIED. Maturity: **[PAPER]/[PROTO]**.
- **Memento.** arXiv:2508.16153, 25 Aug 2025, https://arxiv.org/abs/2508.16153. Frozen LLM; a neural case-selection policy over an episodic memory, updated by memory rewriting and online RL, with no weight updates. Reported on GAIA validation 87.88% Pass@3 and 79.40% on test. Code: https://github.com/Memento-Teams/Memento. Maturity: **[PROTO]**. Follow-ons Memento 2 (arXiv:2512.22716) and Memento 3 (arXiv:2610.11794) appear as snippets only.
- **Mem-alpha.** Yu Wang, Takanobu, Liang, Mao, Hu, McAuley, Wu. arXiv:2509.25911, 30 Sep 2025, https://arxiv.org/abs/2509.25911. RL trains the agent to decide what to store, how to structure it and when to update, with the reward from downstream QA over the full history. Architecture: core, episodic and semantic memory with tools. Trained on instances up to 30k tokens; reported to generalise to over 400k tokens (13x training length). Maturity: **[PAPER]**.
- **Self-organised documents (SoMem).** arXiv:2611.11929, Nov 2026, https://arxiv.org/abs/2611.11929. The agent keeps linked documents, decides what to summarise and revise, and keeps evidence links. Reported: +2.66, +3.10 and +2.00 points over the strongest baseline on LoCoMo, BEAM-100K and LongMemEval-S. Maturity: **[PAPER]**, with code at https://github.com/Qi202/SoMem.
- **Dynamic Cheatsheet.** arXiv:2504.07952, 10 Apr 2025, https://arxiv.org/abs/2504.07952. A black-box LLM keeps an evolving cheatsheet of solutions and strategies. Code: https://github.com/suzgunmirac/dynamic-cheatsheet. Maturity: **[PROTO]**. Numbers UNVERIFIED.
- **Agent Workflow Memory (AWM).** Wang, Mao, Fried, Neubig. arXiv:2409.07429, 11 Sep 2024, https://arxiv.org/abs/2409.07429. Induces reusable workflows from past trajectories. Pre-2025 lineage; numbers UNVERIFIED here because the fetch was rate-limited.
- **Memory systems with a benchmark.** Mem0 (arXiv:2504.19413, 28 Apr 2025, https://arxiv.org/abs/2504.19413) reports 26% relative LLM-as-judge gain over OpenAI's memory on LoCoMo, with a graph variant about 2% higher and lower token cost; it is an open-source library. MemOS (arXiv:2505.22101 and v2 arXiv:2507.03724, https://arxiv.org/abs/2507.03724) treats memory as a schedulable OS resource and claims state of the art on LoCoMo. MemoryOS (arXiv:2506.06326, 30 May 2025, https://arxiv.org/abs/2506.06326) uses short, mid and long-term stores and reports +49.11% F1 and +46.18% BLEU-1 over baselines on LoCoMo with GPT-4o-mini. All three are self-reported. Maturity: Mem0 **[SHIPPED]** as a library; MemOS and MemoryOS **[PROTO]** with open code.

### 5. Context engineering, long context and "context rot"

- **Anthropic's position.** "Effective context engineering for AI agents" (29 Sep 2025, https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) defines context engineering as curating the tokens available at inference and introduces the memory tool and context management as practice. Maturity: **[SHIPPED]** as guidance.
- **Chroma's context rot.** Hong, Troynikov, Huber. Chroma technical report, 14 Jul 2025, https://www.trychroma.com/research/context-rot. 18 LLMs including GPT-4.1, Claude 4, Gemini 2.5 and Qwen3. Finding: models do not use context uniformly; reliability falls as input grows, even on a trivial repeat-the-text task. Secondary blogs quote a degradation point near 113K tokens for conversational memory; I did not verify that figure against the report, so UNVERIFIED.
- **Long context versus RAG.** Earlier head-to-heads still cited: arXiv:2407.16833 (Jul 2024, https://arxiv.org/abs/2407.16833) and arXiv:2501.01880 (Dec 2024, https://arxiv.org/abs/2501.01880), which re-evaluates after filtering questions answerable without context; LaRA (arXiv:2502.09977, https://arxiv.org/abs/2502.09977). The conclusion is workload-dependent: long context wins on accuracy when budget allows, RAG on cost and freshness.

### 6. Anthropic's shipped memory and context features

- **Memory tool.** Tool entry `{"type": "memory_20250818", "name": "memory"}`; the docs describe it as the entire configuration. https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool. Maturity: **[SHIPPED]**.
- **Context editing and compaction.** Context editing clears old tool results and thinking blocks; compaction on demand summarises a conversation. The docs warn about compaction with server-side tools. https://platform.claude.com/docs/en/build-with-claude/context-editing and https://platform.claude.com/docs/en/build-with-claude/compaction. Maturity: **[SHIPPED]**, some parts in beta per the docs. A cookbook page (Mar 2026) covers tool-result clearing: https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools.
- **Agent Skills.** A skill is a folder with a SKILL.md and optional scripts or references (Anthropic, 16 Oct 2025, https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills). On 22 Oct 2026 Anthropic donated the open standard to the Agentic AI Foundation, stating more than 70 agent platforms had integrated it (https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation). Maturity: **[SHIPPED]**.

### 7. Procedural and skill memory

Voyager (Wang et al., arXiv:2305.16291, May 2023, https://arxiv.org/abs/2305.16291) stores executable skills in a library retrieved by similarity; it is the lineage behind skill libraries. CoALA (Sumers, Yao, et al.; arXiv:2309.02427, https://arxiv.org/abs/2309.02427) maps working, episodic, semantic and procedural memory onto language agents and is the usual taxonomy. Skills are now the most widely deployed form of procedural memory, but they are human-authored; ACE, ReasoningBank and AWM are the research answer to auto-authoring them. Maturity: Skills **[SHIPPED]**; auto-authored skill libraries **[PROTO]**.

### 8. Surveys and taxonomies

- "Memory in the Age of AI Agents" (arXiv:2512.13564, 15 Dec 2025, https://arxiv.org/abs/2512.13564) proposes a Forms, Functions and Dynamics taxonomy, arguing long and short-term memory is insufficient.
- "A Survey of Agent Memory in the Second Half" (arXiv:2602.06052, 14 Jan 2026, https://arxiv.org/abs/2602.06052) uses sensory, working, episodic, semantic and procedural categories.
- "Anatomy of Agentic Memory" (arXiv:2602.19320, Feb 2026, https://arxiv.org/html/2602.19320v1) links memory structure to empirical limits.
- Use the Forms, Functions, Dynamics split for the guide; the five-type CoALA split for teaching.

### 9. Benchmarks beyond LoCoMo and LongMemEval

- **MemoryAgentBench** (arXiv:2507.05257, 7 Jul 2025, https://arxiv.org/abs/2507.05257). Multi-turn, incremental. Four competencies: accurate retrieval, test-time learning, long-range understanding and selective forgetting. Finding: no method masters all four; simple context and RAG systems are included as baselines.
- **BEAM** (arXiv:2510.27246, 31 Oct 2025, https://arxiv.org/abs/2510.27246). 100 conversations up to 10M tokens, 2,000 validated questions across memory abilities. Finding: 1M-context models, with and without retrieval, degrade as dialogues lengthen. Its LIGHT baseline (episodic, working and scratchpad memory) gains 3.5% to 12.69% over the strongest baseline.
- **LongMemEval** is used by SoMem and Chroma; I did not re-read its paper this session (UNVERIFIED details).
- Snippet-only 2026 benchmarks: Evo-Memory (test-time learning, May 2026), AgentMemBench (arXiv:2608.00009), multi-party memory benchmark (arXiv:2605.14498). Not verified.

### 10. Memory security

- **MINJA** (arXiv:2503.03704, 5 Mar 2025, https://arxiv.org/abs/2503.03704). Injects malicious records by querying the agent only, with bridging steps and progressive shortening of the indication prompt. Needs no direct write access.
- **AgentPoison** (arXiv:2407.12784, 17 Jul 2024, https://arxiv.org/abs/2407.12784). Backdoor via poisoned memory or RAG knowledge base; reports at least 80% attack success with at most 1% benign-performance loss.
- **Defence study** (arXiv:2601.05504, 9 Jan 2026, https://arxiv.org/abs/2601.05504). Realistic pre-existing legitimate memories sharply reduce MINJA's effect; proposes moderation and trust-aware retrieval with temporal decay. Evaluated in an EHR setting.
- **InjecMEM** (arXiv:2608.23471, Aug 2026, snippet only) reports up to 35.4% retrieval success and 76.6% attack success on MemoryOS. UNVERIFIED beyond the snippet.

## What is usable today

- **[SHIPPED]** Claude memory tool, context editing and compaction (Anthropic docs above). Agent Skills as an open standard across 70+ platforms.
- **[SHIPPED]** Letta sleep-time agents and memory blocks (per Letta's own docs; not tested here).
- **[SHIPPED]** Mem0 as an open-source memory layer, with the caveat that its LoCoMo claims are self-reported.
- **[PROTO, open code]** Cartridges, ACE, Memento, RLM, A-MEM, Dynamic Cheatsheet, MemOS, MemoryOS. Usable in a lab; no SLA.
- **[PAPER only]** Titans-style test-time memory, Atlas, Nested Learning, MemGen, Mem-alpha, ReasoningBank, per-user Engram edits, MemoryLLM and M+. Do not put these in a product plan without replication.

Practical rule the evidence supports: for under about 100K tokens of stable context, use long context plus caching; for large static corpora queried often, a trained cache (Cartridges-style) or RAG; for experience-driven agents, playbooks or reasoning memory (ACE, ReasoningBank) with a write gate against poisoning.

## Open problems

1. **Benchmark saturation and self-reporting.** LoCoMo is saturated and most headline numbers are self-reported. MemoryAgentBench and BEAM are the better current tests, but few papers report on both.
2. **Amortisation depends on workload.** Sleep-time and Cartridge savings need many queries per context. Single-shot agents see no gain.
3. **Weight memory interferes and forgets.** Test-time memorisation, edits and LoRA stores are not shown to hold up under long sequences of conflicting updates. Continual-learning claims need independent replication.
4. **Context rot persists.** Even with large windows, reliability falls with length; RLM-style recursion helps but adds calls and latency.
5. **Memory is an attack surface.** MINJA-style injection needs only chat access; defences are early and evaluated in narrow domains.
6. **Governance.** Who can read, edit and delete a memory, and how a deletion propagates into weights, caches and summaries, is largely unsolved; see the 2026 governance surveys (arXiv:2606.30306, arXiv:2603.11768, snippets only).
7. **Multi-agent shared memory** is moving from pools to governed scopes (arXiv:2606.24535, Jun 2026, snippet), with few shared benchmarks.

## Sources

Primary, read this session:
- https://arxiv.org/abs/2504.13171 (sleep-time compute)
- https://arxiv.org/abs/2510.04618 (ACE)
- https://arxiv.org/abs/2509.25140 (ReasoningBank)
- https://arxiv.org/abs/2509.25911 (Mem-alpha)
- https://arxiv.org/abs/2506.06266 (Cartridges)
- https://arxiv.org/abs/2512.24601 (RLM)
- https://arxiv.org/abs/2501.00663 (Titans)
- https://arxiv.org/abs/2507.05257 (MemoryAgentBench)
- https://arxiv.org/abs/2510.27246 (BEAM)
- https://arxiv.org/abs/2503.03704 (MINJA)
- https://arxiv.org/abs/2508.16153 (Memento)
- https://arxiv.org/abs/2509.24704 (MemGen)
- https://arxiv.org/abs/2502.12110 (A-MEM)
- https://arxiv.org/abs/2506.06326 (MemoryOS)
- https://arxiv.org/abs/2505.22101 (MemOS)
- https://arxiv.org/abs/2504.19413 (Mem0)
- https://arxiv.org/abs/2512.24695 (Nested Learning)
- https://arxiv.org/abs/2510.09551 (Titans Revisited)
- https://arxiv.org/abs/2512.13898 (test-time training for long context)
- https://arxiv.org/abs/2601.05504 (memory poisoning defence)
- https://arxiv.org/abs/2407.12784 (AgentPoison)
- https://arxiv.org/abs/2606.19172 (per-user parametric edits)
- https://arxiv.org/abs/2611.11929 (SoMem)
- https://arxiv.org/abs/2202.05262 (ROME)
- https://arxiv.org/abs/2512.13564 (Memory in the Age of AI Agents)
- https://www.trychroma.com/research/context-rot (context rot)
- https://www.anthropic.com/research/effective-context-engineering-for-ai-agents
- https://www.anthropic.com/news/donating-agent-skills-to-the-agentic-ai-foundation
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- https://www.letta.com/blog/sleep-time-compute/ (search snippet; page not read)

Seen as search snippets only (not read): Letta memory blocks; Berkeley EECS-2026-114; Dynamic Cheatsheet (arXiv:2504.07952); AWM (arXiv:2409.07429); A-MEM and MemOS page bodies; Context editing and compaction docs; MemoryLLM (arXiv:2402.04624); M+ (arXiv:2502.00592); Atlas (arXiv:2505.23735); CoALA (arXiv:2309.02427); Voyager (arXiv:2305.16291); surveys arXiv:2602.06052, 2602.19320, 2603.07670; long-context vs RAG arXiv:2407.16833, 2501.01880, 2502.09977.

Unresolved fetches: the arXiv pages for AWM and Dynamic Cheatsheet, and a second Titans read, returned "Server busy" after one retry. Search engines in this environment were largely rate-limited (brave, duckduckgo and startpage suspended), so coverage relied on Google CSE results.

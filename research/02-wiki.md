# LLM-maintained wiki as agent memory

Research date: 2026-11-20. Sources were read directly unless marked UNVERIFIED. Search went through the local SearXNG tools.

## How it works

Karpathy's gist "LLM Wiki" (created 2026-04-04) is an "idea file" meant to be pasted into an agent such as Claude Code or Codex. [1] It defines three layers:

- **Raw sources.** Articles, papers, notes. Immutable: the LLM reads them and never edits them. [1]
- **The wiki.** LLM-written markdown: summaries, entity and concept pages, cross-references, an overview. The LLM owns it; the human reads it. [1]
- **The schema.** A file such as `CLAUDE.md` or `AGENTS.md` that says how pages are structured and which workflows to run for ingest, query and maintenance. The gist calls this the key configuration file. [1]

Three operations:

- **Ingest.** A new source is read, a summary page is written, the index is updated, and entity and concept pages are revised. The gist says one source may touch 10-15 pages. [1]
- **Query.** The LLM reads the index, drills into pages, and answers with citations. Good answers can be filed back as new pages. [1]
- **Lint.** A periodic health check for contradictions, stale claims, orphan pages, missing concept pages and missing cross-references. [1]

Two special files: `index.md` is a content catalog, one line per page, which the LLM reads first. `log.md` is append-only, and the gist suggests a grep-able prefix such as `## [2026-04-02] ingest | Title`. [1]

The core claim is that the knowledge is compiled once and kept current, not re-derived on each query. [1] Karpathy's own framing: Obsidian is the IDE, the LLM is the programmer, the wiki is the codebase. [1]

## Variants and tools

- **Karpathy gist** (2026-04-04, revision 1 as fetched). Pattern only, no code. More than 5,000 stars at fetch time. [1]
- **Hermes Agent "Llm Wiki" skill**, version 2.1.0, MIT, from Nous Research's Hermes Agent docs. Installed with `hermes skills install official/research/llm-wiki`. Tagged `rag-alternative`. [2]
- **qmd** (tobi/qmd). Not a wiki itself but the search layer the gist recommends. Local BM25 plus vector search, LLM re-rank, run through node-llama-cpp with GGUF models. It ships a CLI and an MCP server. [3]
- **Obsidian-based implementations.** Obsidian is the front end in Karpathy's own setup. [1] One third-party implementation, green-dalii/obsidian-llm-wiki, reportedly refuses embeddings and uses Personalized PageRank over wikilinks; I read only the repo landing page, which did not render its README, so this is UNVERIFIED beyond that claim. [4]
- **DeepWiki (Devin / Cognition).** A different thing: it generates a wiki from code, not a wiki maintained from sources. It auto-generates architecture diagrams, docs and source links for each repo, configured by `.devin/wiki.json`. A free version covers public GitHub repos at deepwiki.com. [5][6]
- **The author's own wiki** is an instance of the pattern. Its `AGENTS.md` names it Karpathy's pattern and uses immutable sources, a `raw/` inbox, compiled pages, `index.md`, `log.md` and a `bin/wiki-lint`. [local: <wiki>/AGENTS.md]
- **Notion, Confluence, Glean.** Only secondary sources. A vendor blog (Falconer) argues they handle one or two of the four properties but not the maintenance loop. [7] A LinkedIn post says the pattern suits small projects, not a whole company. [8] Both are opinion; no head-to-head test found.

## Strengths

- **Compounding.** Cross-references and contradictions are already written when a question arrives. [1]
- **Low retrieval infrastructure.** At a few hundred pages, a catalog file is enough; no embedding store is needed. The gist says this works at about 100 sources and hundreds of pages. [1]
- **Human-readable and diffable.** It is "just a git repo of markdown files": version history and branching for free. [1]
- **Covers several memory types.** Angie Jones (AAIF, 2026-06-08) maps the wiki to semantic, entity, episodic, summary and procedural memory, with the schema as the procedural part. Her example is a conference-data wiki. [9] This is a practitioner mapping, not a benchmark.
- **Human can audit it.** The graph view and the browsable pages make drift visible to a person. [1]

## Limits and failure modes

- **Maintenance is the whole cost.** The gist's argument is that LLMs do the bookkeeping nobody wants to do. [1] The cost moves to the schema and the lint loop, which someone must run and keep honest.
- **Drift and self-corruption.** Microsoft's DELEGATE-52 (arXiv 2604.15597, 17 Apr 2026) ran 19 LLMs through delegated document editing across 52 domains. Frontier models (Gemini 3.1 Pro, Claude 4.6 Opus, GPT 5.4) corrupted on average 25% of document content by the end of long workflows; the paper says agentic tool use did not improve this, and that document size, interaction length and distractor files made it worse. [10] Repeated LLM rewrites of your own notes are therefore a real risk.
- **Summaries replace sources in retrieval.** A welzin.ai write-up reports that neural retrievers prefer LLM-written text over human text, and that human text fell below 10% of top-50 results within about ten write-read cycles. It also says BM25 shows no such bias. [11] I did not read the cited papers; treat the figures as UNVERIFIED until checked.
- **Stale self-description.** The same welzin post describes a roadmap doc that said a feature was "not started" when it had shipped ten days earlier. Its rule: re-derive claims about your own system from the code, not the doc. [11]
- **Scale ceiling.** Falconer (vendor) argues the pattern "breaks at company scale" because it relies on one curator. [7] welzin says to adopt a search layer once `index.md` no longer fits comfortably in context, with a community estimate of 100-200 processed notes where cross-linking starts to pay. [11] The 100-200 figure is a community estimate, not measured.
- **Sync across devices** is a known practical problem. [UNVERIFIED: one blog, Kunal Ganglani, Apr 2026, search snippet only]
- **Flat-file mutation.** A gist comment thread (karpathy/442a6bf, comment 6172613, 29 May 2026) raises the "Flat Markdown Mutation Problem": flat files versus an outliner AST. I did not read the thread; UNVERIFIED as a finding.

## Exact use cases

**Pick it when:**
- One person or a small team is accumulating knowledge on one domain over weeks: a research topic, a codebase's decisions, a book, a due-diligence file.
- The corpus is a few hundred pages or fewer and fits an index in context.
- You want the agent to answer "what do we already know about X" across sessions, and you can review the diffs.
- Every change should be auditable in git.

**Avoid it when:**
- The corpus is large or changes by the minute (ticketing, logs, live customer data). Use retrieval over the raw data.
- Many writers with weak review. Shared writes without a human gate are where drift compounds.
- You need guaranteed exact recall of raw text. The wiki holds synthesis, which is lossy; keep raw sources and cite them.
- The knowledge is only a list of facts per user. A flat memory file or a key-value store is simpler.
- You cannot commit to running lint. Without it the wiki quietly rots.

## Setup walkthrough

This layout follows the gist and the `/data/wiki` instance. The lint script is my sketch, not a sourced tool, and was not run here.

```bash
mkdir -p ~/kb/{raw,wiki} && cd ~/kb && git init
touch wiki/index.md wiki/log.md
```

Layout:

```
kb/
├── AGENTS.md          # schema: page format, ingest/query/lint steps, citation rule
├── raw/               # immutable sources (never edited by the agent)
├── wiki/
│   ├── index.md       # one line per page: [[slug]] - one-sentence summary
│   ├── log.md         # "## [YYYY-MM-DD] ingest | title" lines, append only
│   └── *.md           # one fact, one page; each cites raw/ paths
└── bin/wiki-lint      # the checks below
```

Minimal schema rules to put in `AGENTS.md`:
- Never edit `raw/`. Every claim in a wiki page cites a `raw/...` path or a URL.
- One fact lives on one page; link to it rather than copying it.
- Tag every claim `[src:...]` or `[UNVERIFIED]`.
- Every ingest: write the source page, update `index.md`, update related pages, append to `log.md`, run lint, commit.

Lint sketch (checks that are cheap and deterministic):
1. Every `[[slug]]` resolves to `wiki/slug.md`.
2. Every page in `wiki/` appears in `index.md`.
3. No orphan pages (zero inbound links).
4. Every `.md` page has a `src:` or `UNVERIFIED` tag on claims (grep count).
5. Exit non-zero on failure so the agent cannot commit past it.

Git workflow: one branch per ingest batch, commit the raw source and the wiki change together, run lint in a pre-commit hook, and review the diff before merging. This is the only defence against the silent-drift problem above.

Search when `index.md` stops fitting: install qmd, register the wiki as a collection, and point the agent at its MCP server.

```bash
npm install -g @tobilu/qmd
qmd collection add ~/kb/wiki --name wiki
qmd context add qmd://wiki "Agent-maintained knowledge base"
qmd embed
qmd query "your question"          # hybrid + rerank
qmd search "exact term"            # BM25 only
qmd mcp                            # stdio MCP server
```

Claude Code MCP config from the qmd README:

```json
{ "mcpServers": { "qmd": { "command": "qmd", "args": ["mcp"] } } }
```

## Numbers

- Gist: about 100 sources and hundreds of pages as the scale where a plain index works. [1]
- Gist: one ingest may touch 10-15 pages. [1]
- Community estimate: cross-linking pays at about 100-200 processed notes. Not measured. [11]
- DELEGATE-52: frontier models corrupt about 25% of document content by end of long workflows. [10]
- DELEGATE-52 scope: 19 models, 52 domains. [10]
- qmd defaults (README): `limit` 10, `candidateLimit` 40, `minScore` 0, reranking on by default; embedding and rerank contexts unload after 5 minutes idle, roughly 1 s to recreate. [3]
- Gist star count: 5,000+ at fetch. [1]
- Hermes skill version: 2.1.0. [2]
- DeepWiki: no published cost figures in the part I read. The effort table was truncated. [6]

## Sources

1. Karpathy, "LLM Wiki" gist, created 2026-04-04. https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f (raw: https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md)
2. Hermes Agent docs, "Llm Wiki" skill v2.1.0. https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/research/research-llm-wiki
3. tobi/qmd README. https://github.com/tobi/qmd (raw README: https://raw.githubusercontent.com/tobi/qmd/main/README.md)
4. green-dalii/obsidian-llm-wiki, repo page (README not rendered). https://github.com/green-dalii/obsidian-llm-wiki
5. Devin Docs, DeepWiki repository wikis. https://docs.devin.ai/work-with-devin/deepwiki
6. DeepWiki. https://deepwiki.com/ and https://cognition.com/blog/deepwiki (May 5, 2025)
7. Falconer, "The enterprise LLM wiki", 2026-04-28 (vendor). https://falconer.com/guides/enterprise-llm-wiki-karpathy/
8. LinkedIn post, 2026-04-19 (search snippet only). https://www.linkedin.com/posts/aagupta_how-pms-can-take-advantage-of-karpathys-activity-7451795168040603648-2Pm2
9. Angie Jones, "Karpathy's LLM Wiki as Agent Memory," AAIF, 2026-06-08. https://aaif.io/blog/karpathys-llm-wiki-as-agent-memory
10. Laban, Schnabel, Neville, "LLMs Corrupt Your Documents When You Delegate" (DELEGATE-52), arXiv:2604.15597, submitted 2026-04-17. https://arxiv.org/abs/2604.15597
11. welzin.ai, "Build a Karpathy-style LLM wiki in Obsidian," 2026-07-16 (vendor; cites papers I did not read). https://welzin.ai/blogs/build-an-llm-wiki-in-obsidian
12. Sanity, "Taking Karpathy's wiki to work," 2026-09-03 (vendor). https://www.sanity.io/blog/taking-karpathys-wiki-to-work
13. Local: <wiki>/AGENTS.md (the author's instance of the pattern).

## Could not verify

- DELEGATE-52 figures that welzin attributes to the paper but the abstract does not state: "within 20 interactions," "average near 50%," and "agentic harness worse by about 6%." Only the 25% figure is in the abstract.
- Pasquale Pillitteri's RAG vs wiki cost comparison: the body did not load, so no cost numbers from it.
- Notion and Confluence as agent memory: no primary evidence found, only opinion posts.
- Multi-agent shared wiki: a gist (redmizt, 2026-04-10) exists in search results; I did not read its body.
- The "5 weeks in daily production, without vector search" writeup surfaced only as a search snippet attached to Karpathy's gist; I could not find its author or URL.

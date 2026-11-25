# Flat-file markdown memory for agents (state as of 2026-11-20)

## How it works

Flat-file memory means the agent's long-term state is plain text files on disk, usually Markdown, that the harness either injects into the prompt or lets the agent open on demand.

Two loading models dominate:

- **Always-in-context.** The file (or its first N lines) is concatenated into the system prompt every session. Claude Code's CLAUDE.md files work this way: "Both are loaded at the start of every conversation" ([Claude Code memory docs](https://code.claude.com/docs/en/memory)).
- **On-demand.** Only an index or file tree is always visible; the agent reads or greps the rest when needed. Anthropic's memory tool is this model: "Claude automatically checks its memory directory before starting a task" and then views files under `/memories` ([Anthropic memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)).

The Letta Code "Context Repositories" design combines both: the file tree is always in the system prompt, each file carries a frontmatter description, and a `system/` directory marks files that are always fully loaded ([Letta, 2026-02-12](https://www.letta.com/blog/context-repositories/)).

## Variants and tools (dated)

| Variant | What it is | Loading | Source |
|---|---|---|---|
| CLAUDE.md / CLAUDE.local.md | Hand-written instructions, project/user/org scopes | Always; ancestor dirs at launch, subdirs on demand | [code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory) |
| `.claude/rules/*.md` | Topic files; optional `paths:` frontmatter | Always, or when a matching file is read | same |
| Claude Code auto memory | Claude writes `MEMORY.md` index plus topic files | First 200 lines or 25KB of the index, every session | same |
| AGENTS.md | Open cross-tool format, "a README for agents" | Read by Claude Code in place of CLAUDE.md | [agents.md](https://agents.md/) (site says used by 60k+ OSS projects) |
| Anthropic memory tool | `memory_20250818` client-side tool, `/memories` directory | On demand; your app serves storage | [docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool) |
| Cursor rules | `.cursor/rules/*.mdc` with `alwaysApply`, `globs`, `description` | Four modes: always, auto-attached by glob, agent-selected, manual `@` | [cursor.com/docs/rules](https://cursor.com/docs/rules) |
| Windsurf rules | `.windsurf/rules/` plus `global_rules.md` | Per-file and total caps | [markdific guide, 2026-09-30](https://markdific.com/guides/windsurf-rules/) (secondary) |
| Letta memory blocks | Labeled, size-limited core memory in context | Always in context; agent edits via tools | [docs.letta.com](https://docs.letta.com/v1-sdk/memory/memory-blocks/) |
| Letta Filesystem | Folders of parsed docs with `grep`, `open`, `semantic_search` tools | On demand | [Letta, 2025-07-24](https://www.letta.com/blog/letta-filesystem/) |
| Letta Context Repositories | Git-backed memory repo cloned locally | Tree always visible; `system/` always loaded | [Letta, 2026-02-12](https://www.letta.com/blog/context-repositories/) |
| Obsidian vault as memory | Vault with CLAUDE.md schema plus notes | Whatever the agent is pointed at | community guides, e.g. [aident.ai, 2026-08-29](https://aident.ai/blog/second-brain-without-obsidian-plain-markdown) (secondary, unverified benchmarks) |

Note: Claude Code's auto memory and Anthropic's memory tool are different products. The first is a local harness feature; the second is an API tool your code must back.

## Strengths

- **Human-editable and diffable.** Anyone can open, fix, or delete a line. Letta's blog calls files "simple, universal primitives that both humans and agents can work with using familiar tools" ([Letta](https://www.letta.com/blog/context-repositories/)).
- **Grep is a real retriever.** Boris Cherny, creator of Claude Code, said in a 2026 interview that Claude Code's "agentic search" is "really just glob and grep, and it outperformed RAG" ([Pragmatic Engineer, 2026-03-04](https://newsletter.pragmaticengineer.com/p/building-claude-code-with-boris-cherny), quoted via secondary posts; the primary podcast is not verified here).
- **Git history for free.** Context Repositories "are git-backed, so every change to memory is automatically versioned" and concurrent subagents can work in worktrees and merge ([Letta](https://www.letta.com/blog/context-repositories/)).
- **Zero infrastructure.** No embeddings, no service. The memory tool's own docs describe it as "a directory of memory files" your application stores however it likes ([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)).
- **Tool-agnostic with AGENTS.md.** One file can be read by many agents.

## Limits and failure modes

- **Hard caps that truncate silently.** Auto memory loads "first 200 lines or 25KB" ([Claude Code docs](https://code.claude.com/docs/en/memory)). A third-party reading of the leaked Claude Code source says overflow is truncated with only a warning appended to the file ([Mem0, 2026-09-24](https://mem0.ai/library/coding-agents/how-memory-works-in-claude-code)). The silent-truncation detail is from that secondary read, not from Anthropic's docs.
- **Windsurf caps.** 6,000 characters per global rule, 12,000 characters total across active rules ([design.dev guide](https://design.dev/guides/windsurf-rules/); also cited in [evanca/flutter-ai-rules](https://github.com/evanca/flutter-ai-rules)).
- **Letta blocks** are size-limited; the docs example sets `"limit": 5000` on a block ([Letta docs](https://docs.letta.com/v1-sdk/memory/memory-blocks/)). Third-party posts cite other limits (a 50k-character guidance and a 20K-character issue example); not verified against Letta's source.
- **Adherence drops with length.** Anthropic: "Longer files consume more context and reduce adherence." Target under 200 lines per CLAUDE.md ([docs](https://code.claude.com/docs/en/memory)). Cursor: "Keep rules under 500 lines" ([Cursor docs](https://cursor.com/docs/rules)).
- **Contradictions.** "If two instructions contradict each other, Claude may pick one arbitrarily" ([docs](https://code.claude.com/docs/en/memory)). Auto memory has no conflict resolution.
- **Concurrency.** Two writers on one file can lose data. Git (Letta) or worktrees mitigate it; plain shared files do not.
- **Scale.** Mem0 (a vendor, so biased) argues files work for "roughly 200 stable memories, single user, no concurrency" and cites "15K tokens versus 2K" for files loaded wholesale ([Mem0, 2026-09-11](https://mem0.ai/library/agent-memory/your-ai-agents-memory-is-just-a-file-thats-the-problem)). Treat the numbers as vendor claims; UNVERIFIED as general facts.
- **Stale memory.** Anthropic's "Auto Dream" consolidation is reported by third parties (first around 2026-03-24 to 26) as a background pass that merges and prunes memory files ([implicator.ai, 2026-03-25](https://www.implicator.ai/anthropic-adds-auto-dream-to-claude-code-fixing-memory-decay-between-sessions/)). Not in the official docs I could read; UNVERIFIED as shipped behavior.
- **Context editing does not replace memory.** Anthropic's server-side clearing removes old tool results from the prompt; it does not store anything. Its default config example uses `trigger` 30000 input tokens and `keep` 3 tool uses, but those are example values, not defaults ([context editing docs](https://platform.claude.com/docs/en/build-with-claude/context-editing)).

## Exact use cases

**Pick it when:**
- One developer or one small team, one repo or one agent.
- Facts are stable, short, and worth reading by humans (build commands, conventions, preferences).
- You want to review and revert memory in git.
- You need portability across agents: AGENTS.md, Cursor rules, memory-tool directories.
- Total memory fits in roughly a few thousand lines, with the index under the harness cap.

**Avoid it when:**
- Many users or agents write concurrently and need isolation (use a DB with ACLs).
- You need time-aware facts ("was true until March") or contradiction resolution.
- Memory grows past what a grep plus an index can navigate, or past the always-loaded cap.
- You need semantic recall over large corpora (use archival or vector memory, e.g. Letta archival memory, which is "semantically searchable" per [Letta docs](https://docs.letta.com/v1-sdk/memory/archival-memory/)).

## Setup walkthrough (minimal, Claude Code)

Layout:

```
repo/
├── CLAUDE.md                  # always loaded, <200 lines, team-shared
├── CLAUDE.local.md            # personal, gitignored
├── .claude/rules/
│   ├── testing.md             # always loaded
│   └── api.md                 # paths: scoped
└── docs/memory/
    ├── INDEX.md               # one line per note
    └── decisions/2026-11-20-flat-files.md
```

Scoped rule example (`.claude/rules/api.md`):

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API rules
- All endpoints validate input.
- Error shape: { "code": string, "message": string }.
```

Note file with frontmatter (the description is what an on-demand reader sees first, following the Letta pattern):

```markdown
---
description: Why we chose flat files over a vector DB for agent memory (2026-11-20)
type: decision
---

Decision: flat files until >200 stable notes or >1 writer. Reason: grep beat RAG for our repo size.
```

Index (`docs/memory/INDEX.md`), kept under 200 lines:

```markdown
# Memory index
- [flat-files decision](decisions/2026-11-20-flat-files.md) - why files, not a DB
```

Add a line to the root CLAUDE.md pointing at the index:

```markdown
## Memory
Before a design decision, read docs/memory/INDEX.md and grep docs/memory for the topic.
```

Check what loaded: run `/context all` in a session and read the **Memory files** list ([docs](https://code.claude.com/docs/en/memory)). Audit for stale or conflicting lines with `/doctor prompt-audit` ([docs](https://code.claude.com/docs/en/memory)).

Git as history: `git add CLAUDE.md docs/memory && git commit -m "docs: record flat-file memory decision"`. Use commit messages as the changelog for memory; Letta does the same automatically ([Letta](https://www.letta.com/blog/context-repositories/)).

For the Anthropic memory tool, the minimal request is `tools=[{"type": "memory_20250818", "name": "memory"}]` plus a handler that rejects paths outside `/memories` ([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)). The Python SDK ships `BetaLocalFilesystemMemoryTool(base_path="./memory")` ([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)).

## Numbers

- 200 lines or 25KB: Claude Code auto memory load cap ([docs](https://code.claude.com/docs/en/memory)).
- 200 lines: CLAUDE.md target, "longer files ... reduce adherence" ([docs](https://code.claude.com/docs/en/memory)).
- 500 lines: Cursor rule guidance ([docs](https://cursor.com/docs/rules)).
- 6,000 / 12,000 characters: Windsurf global / total caps (secondary source).
- 30k tokens: Letta default context limit, recommended 100k-200k for file-heavy work ([Letta Filesystem](https://www.letta.com/blog/letta-filesystem/)).
- 5,000 characters: example Letta block `limit` ([docs](https://docs.letta.com/v1-sdk/memory/memory-blocks/)).
- 60k+ projects using AGENTS.md ([agents.md](https://agents.md/)).
- 15K vs 2K tokens and "~200 memories": vendor claim, UNVERIFIED.
- 3 keep / 30k trigger: example values only ([context editing docs](https://platform.claude.com/docs/en/build-with-claude/context-editing)).

## Sources

- Claude Code memory docs: https://code.claude.com/docs/en/memory
- Anthropic memory tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- Anthropic context editing: https://platform.claude.com/docs/en/build-with-claude/context-editing
- Letta memory blocks: https://docs.letta.com/v1-sdk/memory/memory-blocks/
- Letta Filesystem (2025-07-24): https://www.letta.com/blog/letta-filesystem/
- Letta Context Repositories (2026-02-12): https://www.letta.com/blog/context-repositories/
- Letta archival memory: https://docs.letta.com/v1-sdk/memory/archival-memory/
- Cursor rules: https://cursor.com/docs/rules
- AGENTS.md: https://agents.md/
- Mem0, Claude Code memory (2026-09-24, source-read claims): https://mem0.ai/library/coding-agents/how-memory-works-in-claude-code
- Mem0, file memory limits (2026-09-11, vendor): https://mem0.ai/library/agent-memory/your-ai-agents-memory-is-just-a-file-thats-the-problem
- Pragmatic Engineer, Boris Cherny interview (2026-03-04): https://newsletter.pragmaticengineer.com/p/building-claude-code-with-boris-cherny
- Windsurf limits, secondary: https://design.dev/guides/windsurf-rules/ and https://markdific.com/guides/windsurf-rules/
- Auto Dream, secondary: https://www.implicator.ai/anthropic-adds-auto-dream-to-claude-code-fixing-memory-decay-between-sessions/
- Local observation: this session's memory directory follows the `~/.claude/projects/<repo>/memory/MEMORY.md` pattern described by Mem0.

## Could not verify

- Official Claude Code docs for the auto memory storage path and any consolidation pass (the "Storage location" and "How it works" sections did not come back in my reads).
- Boris Cherny's quote from the primary podcast or post; I read it via a secondary report and an X post excerpt.
- Letta's exact unit and default for block `limit`, and the 50k/20K figures from third-party posts.
- Windsurf limits from Windsurf's own docs (only secondary guides read).
- Any benchmark comparing grep against RAG with numbers.

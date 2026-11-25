# gap-reruns: three inventory rows that had no local run

Three rows of `reviews/benchmark-inventory.md` were judged runnable in principle but had never been run locally. This
folder runs them or says why they cannot be run. The book's rule: when it cites someone else's number, it reruns the number
on local hardware with local open-weight models and prints both figures.

| Folder | Row | Chapter sentence | What was run |
|---|---|---|---|
| `g39-hindsight-latency/` | G39 | `06-small-memory-models.html:159` (167 ms median) | Task-owned Hindsight 1.2.3 plus the 0.8B `hs-decide-1-flash`, 242 timed decision-model requests |
| `g44-sleep-time/` | G44 | `16-frontier.html:120` (2.5 times lower cost per query) | Sleep-time step and two answering arms, 32 contexts, 160 questions, 960 answer calls, local 7B |
| `g10-beam-light/` | G10 | `16-frontier.html:250` (LIGHT gains of 3.5% to 12.69%) | BEAM's own RAG baseline and LIGHT on the smallest scale, 5 conversations, 100 questions, local 3B reader, local 7B judge |

Results, differences from the sources, limits and suggested replacement sentences: `REPORT.md`. Each subfolder has its own
README with the one-command run, versions, data sources and licences, and its raw per-item outputs.

## Hardware class and shared pieces

- Harness host: 28 GB x86 development machine, CPU only (its 8 GB GPU was not used).
- Model host: Apple M1 Ultra, 64 GB, running llama.cpp (`serve.sh`) and a small embedding server
  (`g10-beam-light/embed_server.py`), reached through an SSH tunnel to a localhost-only port. The harness defaults to
  `http://127.0.0.1:39980/v1`; every endpoint is a setting.
- Models: Qwen2.5-7B-Instruct Q4_K_M and Qwen2.5-3B-Instruct Q4_K_M (GGUF), `hs-decide-1-flash`, `hs-embed-1`, `hs-rerank-1`,
  `BAAI/bge-small/base/large-en-v1.5`, `all-MiniLM-L6-v2`.
- Data is fetched by script into scratch and never stored here: LoCoMo (CC BY-NC 4.0), Stateful GSM-Symbolic P2 (licence not
  stated on the card), BEAM (code MIT, data CC BY-SA 4.0, commit b2da22e).
- Cleanup: `cleanup.py` stops everything, removes the container, the pulled image, the scratch folders on both machines,
  and writes `results/cleanup.json` with before and after listings.

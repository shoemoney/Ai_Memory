# Small local benchmark reruns

Three book claims are tracked here (all three finished): Game of 24 (chapter 16), Deep Memory Retrieval (chapter 14), and the uploader's Qwen3.8 9B refusal count (chapter 06). These are local checks with smaller open-weight models, not replications with the original hosted models.

## Reproduce

With the local OpenAI-compatible model server and SSH tunnel already running on port 39900:

```sh
bash benchmarks/small-reruns/run.sh
```

`ENDPOINT` defaults to `http://127.0.0.1:39900/v1`. It may point to another localhost tunnel. `SCRATCH` defaults to `/data/scratch/membench/small-reruns`. Dependencies install into a scratch virtual environment, never globally. Requirements and the complete installed lock are included. Checkpoints are append-only per completed item and rerunning resumes them. Remove results intentionally to start a fresh run.

`run.sh` also runs the refusal arms (two 9B 4-bit models, one at a time, 100 prompts each). `serve.sh` runs on the assigned Apple M3 Ultra model host from `~/membench-small-reruns-tmp/` with a local `model.gguf`. It checks at least 40% free memory before loading and stops its own model process on warn or critical kernel pressure. It never stops another service. Copy or download the specified model into that scratch directory before invoking it. Model transport and host addresses are deployment settings and are deliberately not stored here.

Hardware: Apple M3 Ultra, 96 GB unified memory, shared with other benchmark workloads; a 32-thread x86 CPU host runs the harness and scoring. No host GPU use. Game of 24 and the DMR reader use Qwen2.5-3B-Instruct Q4_K_M (Qwen Research license); the DMR judge is Qwen2.5-7B-Instruct Q4_K_M (Apache-2.0); the refusal arms use two Qwen3.8 9B Q4_K_M builds (Apache-2.0, see refusal/PROTOCOL.md). Weight digest and server version are in [Game of 24 protocol](game24/PROTOCOL.md).

## Results

| Benchmark / setup | Published | Local (exact 95% CI) | N |
|---|---|---|---|
| Game of 24, direct | GPT-4o 10% | Qwen2.5 3B Q4: 2.0% (0.24% to 7.04%) | 100 |
| Game of 24, memory + tools | GPT-4o DC-RS 99% | Qwen2.5 3B Q4 DC-Cumulative: 5.0% (1.64% to 11.28%) | same 100 |

Paired change +3 points, conservative exact 95% interval -6.51 to +12.11 points; exact McNemar p=0.453125. This is not a clear improvement. The local DC arm hit the token cap on 82/100 final answers and 17/100 curations. It attempted Python on eight puzzles. It cannot verify or refute the published GPT-4o/DC-RS figure. See [the full protocol](game24/PROTOCOL.md), [raw checkpoints](game24/results.jsonl), [summary](game24/summary.json), and [editor report](REPORT.md).

| DMR, full conversation in context | MemGPT/Zep protocol, GPT-4-turbo: 94.4% | Qwen2.5 3B reader, 7B local judge: 66.7% (58.5% to 74.1%) | 150 |
| DMR, plain dense retrieval, top 5 pairs | MemGPT 93.4%, Zep 94.8% (hosted systems, not this baseline) | same reader and judge: 61.3% (53.0% to 69.2%) | same 150 |
| Refusals, uploader's build, Heretic keyword rule | 6/100 (card) | Q4_K_M: 14/100 (7.9% to 22.4%) | 100 |
| Refusals, uploader's build, hand labels | not published | 43/100 (33.1% to 53.3%) | same 100 |
| Refusals, stock model, keyword rule / hand labels | 100/100 (original, card) | 98/100 / 98/100 (93.0% to 99.8%) | same 100 |

DMR paired difference (dense minus full) -5.3 points, conservative exact 95% interval -19.8 to +9.4, exact McNemar p=0.341: no clear difference at this size. The 40-item judge audit found 33 of 40 agreements with the tester's labels (82.5%, 67.2% to 92.7%); headline rates keep the judge's labels. The Zep and MemGPT systems were not run (existing framework adapters could not be reused without touching running jobs). The local reader is far smaller than GPT-4-turbo, so these figures cannot confirm or refute the published ones. See [dmr/PROTOCOL.md](dmr/PROTOCOL.md) and [dmr/summary.json](dmr/summary.json).

Refusals: the keyword rule gives 14/100, not the card's 6/100, on the same prompt set (inferred from Heretic defaults) with different weights precision and decoding. Reading the responses shows the keyword rule misses most refusals in this build: it often answers a harmful request by writing the safe opposite (a prevention guide for "how to commit fraud"), which contains no marker, and 8 of the 14 keyword hits were compliant answers with a disclaimer. Under the written rule 43/100 were refused, and the stock model refuses 98/100 under either rule (paired difference -55 points, interval -66.3 to -39.1, p<1e-16). Only prompt indices, labels and timings are stored. See [refusal/PROTOCOL.md](refusal/PROTOCOL.md), [refusal/summary.json](refusal/summary.json) and [editor report](REPORT.md).

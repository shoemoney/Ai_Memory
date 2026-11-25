# Editorial report: published-paper reruns

Both items ran to completion and passed their independent verifiers (`hipporag2/verify.py`, `spiral-of-silence/verify.py`). Hardware class: generation on an Apple M3 Ultra, 96 GB (llama.cpp, Qwen2.5-3B-Instruct Q4_K_M); retrieval, embedding and scoring on a 32-thread x86 CPU (at most 8 threads, no GPU). The tester ran everything; no LLM judge was used.

## G46: HippoRAG 2

Book location: `build/chapters/14-knowledge-graphs.html`, line 250: "+7% ... HippoRAG 2 on associative memory tasks against the best embedding model."

Published: abstract claims a 7% associative-memory gain over the best embedding model. The 2Wiki tables (1,000 questions) give QA F1 71.0 versus 61.5 and recall@5 90.4 versus 76.5 (HippoRAG 2 versus NV-Embed-v2).

Local (150 seeded 2Wiki questions, 1,117 context passages including distractors, same questions and corpus for both systems, paired, 95% bootstrap intervals over questions, 10,000 resamples):

| Metric | HippoRAG 2 | Dense (all-MPNet) | Difference |
|---|---|---|---|
| Recall@1 | 35.2 [32.0, 38.3] | 30.5 [27.0, 34.0] | +4.7 [1.0, 8.5] |
| Recall@5 | 78.5 [74.0, 83.0] | 53.8 [49.5, 58.3] | +24.7 [19.5, 30.0] |
| Recall@10 | 87.0 [83.5, 90.3] | 67.8 [63.2, 72.3] | +19.2 [14.8, 23.7] |
| Recall@20 | 91.0 [88.0, 93.8] | 74.8 [70.7, 79.0] | +16.2 [12.7, 20.0] |
| Exact match | 33.3 [26.0, 40.7] | 25.3 [18.7, 32.7] | +8.0 [0.0, 15.3] |
| QA F1 | 46.3 [39.5, 53.3] | 32.5 [25.8, 39.6] | +13.8 [6.6, 21.2] |

Verdict: supports the direction of the claim. HippoRAG 2 beat the dense baseline on every metric, and the F1 and recall differences exclude zero (exact match touches zero). The size is not comparable: local F1 gain is 13.8 points against 9.5 published, but the local setup differs a great deal, and the abstract's 7% is an aggregate over several datasets, not a 2Wiki figure, so this cannot validate "+7%".

Setup differences: Qwen2.5-3B Q4 replaces Llama-3.3-70B (extraction, fact filter, reading); all-MPNet-base-v2 replaces NV-Embed-v2 (and the baseline is a weaker embedder); 1,117-passage reduced corpus instead of 6,119; 150 questions instead of 1,000; author code at a pinned maintained revision, not the exact paper-release environment. The dense baseline is the author's StandardRAG with the same embedder and reader, not "the best embedding model" of the paper.

Extraction repairs (all audited in `hipporag2/results/format-guard-events.jsonl`): the 3B model sometimes returned malformed triples, so the harness requests JSON-object output and retries rejected responses with a typed schema. The retry budget was first 3 seeds, then raised to 10 after two passages kept failing, which finished the earlier accepted responses unchanged. Two passages (runaway repetition cut at the token limit on all attempts) received zero triples and stay indexed as passages; 10 of 1,117 passages ended with no triples in total (`index-diagnostics.json`). Schema validity does not establish that extracted facts are accurate.

Interrupted and resumed: a first operator started the pass; it was stopped at about 435 of 1,117 extraction items and again at about 648 (the evaluator and its tunnel exited without a logged cause). Both restarts reused the author's persistent LLM cache with identical prompts, model and seeds. No finished item was rerun and no scoring changed.

Suggested replacement: "In a reduced rerun on 150 two-hop questions with a small local model, HippoRAG 2 beat a plain dense retriever by 13.8 F1 points (95% interval 6.6 to 21.2) and by 24.7 recall@5 points. The published 7% is an average over several datasets that this book could not reproduce at full scale."

Evidence: `hipporag2/results/summary.json`, `hipporag2.jsonl`, `dense.jsonl`, `cohort.json`, `provenance.json`, `index-diagnostics.json`.

## G16: Spiral of Silence

Book location: `build/chapters/02-wiki.html`, line 181: "Under 10% of top-50 ... Share of human-written text in retrieval results after ten write and read iterations, in a simulation on question-answering datasets."

Published: under 10% human-written in the top results after ten iterations (paper Figure 4, which uses about 4,000 new documents per round across several generators and datasets).

Local (183 NQ questions, 3,632 human passages, Contriever-msmarco retriever, Qwen2.5-3B generator adding 183 documents per round, 10 rounds, top-50 share, 95% question-bootstrap intervals):

| Round | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Human share (%) | 100 | 94.7 | 89.7 | 85.1 | 80.7 | 77.0 | 73.5 | 70.5 | 67.9 | 65.3 | 62.9 |
| Interval low | 100 | 94.4 | 89.1 | 84.3 | 79.8 | 75.8 | 72.2 | 69.2 | 66.5 | 63.9 | 61.4 |
| Interval high | 100 | 95.0 | 90.2 | 85.8 | 81.7 | 78.1 | 74.7 | 71.8 | 69.3 | 66.8 | 64.5 |

Verdict: reproduces the direction (a steady monotonic decline, with generated text taking a growing share of top results), but does not reproduce the magnitude: 62.9% human at round 10, not under 10%. The local run wrote about 4% as much text per round (183 versus roughly 4,000 documents), from one small generator, into a 3,632-passage corpus, so it tests the trend at low write volume and cannot confirm or refute the paper's threshold. Setup differences are listed in README.md.

Suggested replacement: "In a small local rerun, where only 183 generated documents were added per round, the human-written share of the top 50 results fell from 100% to 63% over ten rounds (95% interval 61% to 64%). The paper's under-10% figure used about 20 times as much generated text per round, and this book could not test that scale."

Evidence: `spiral-of-silence/results/summary.json`, `round-00.json` to `round-10.json`, `generated.jsonl`, `cohort.json`, `provenance.json`, `retriever-runtime.json`; chart in `comparison.png`, `comparison.svg`, `comparison.html`.

## What did not work

An initial 7B extraction attempt (23 cached requests) was dropped for throughput; an early start before the embedding download finished failed; an unconstrained 3B extraction produced malformed output; two evaluator/tunnel exits mid-extraction; two passages exhausted the retry budget. All are described above or in README.md.

## Cleanup

Before: workstation scratch 3.0 GB, small files 4.1 MB, own model folder on the Mac 6.4 GB (model server, its watcher script and an ssh tunnel on port 39950 were this task's own). After: the tunnel, the model server and its watcher are stopped (no listener on the port on either machine); the Mac folder and the workstation scratch and small-file folders are deleted. Mac free memory 80% afterwards; Mac disk used 13 GiB (about 6 GB freed, 118 to 124 GiB available); workstation /data unchanged at 149 GB used since the scratch was mostly cached and small. No containers, images or volumes were ever created. Only this territory folder remains. Nothing was committed.

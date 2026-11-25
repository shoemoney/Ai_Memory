# Chapter 07, round 14 lab

> The raw resource, process and cleanup logs mentioned in this document are not published; the summaries and figures derived from them are kept.

The named scripts mirror the chapter's printed listings. The lab uses the pinned
stock and edited Qwen2.5-Coder GGUF files, Ollama 0.40.16, CPU inference with eight
threads, and jsonschema 4.25.1 on the local Ryzen 9 8945HX machine.

`harness-tests.txt` records synthetic regression checks for invalid review answers,
malformed tuple edits, disputed totals, interrupted-review journaling, stale notes,
and wrong-city rejection. `test-harness.py` drives those checks against the lab's
extracted `memtest.py`.

`tensors.txt` summarizes the GGUF header inspection. The complete tensor name,
shape and type lists are in `stock-tensors.json` and `edited-tensors.json`.
No model weights, credentials or runtime caches belong in this folder.

The final twenty-response run is in `responses.jsonl`; `reviewed.jsonl` and
`reviewed.json` preserve the decisions and canonical tuples. `review.txt` records
zero errors for stock and two residence reversals for edited, with no disputes.
Only the edited medication's trailing period was canonicalized. The closed enum
made the new stock debt predicate `owes`.

`free.jsonl` records the unconstrained stock debt response. `sensitive.jsonl`
contains eight responses: two synthetic adult cases, both models, both decoding
modes. None explicitly declines. Both constrained quote responses invent a friend
relationship and omit denied regret; both constrained health responses treat
sexual context as another medication value. Stock's unconstrained health response
uses an out-of-enum predicate. Its exact-count scorer normalizes I/me to user;
these literal counts are separate from the main suite's reviewed counts.

`warm.txt` records a single resident stock call of 5.416 seconds, after a preload;
the warm command unloads in a finally block. `readback.txt` records a fresh-process
read/parse of the two-fact note in 0.064 ms. These are anecdotal timings.

`cleanup.txt`, `cleanup.json`, an unpublished raw log and `print-preview.txt` record
resource cleanup and the private print build. The chapter remains nine pages
(pages 6 through 14 in the isolated preview), with at least three spare lines.
All downloaded GGUFs, imports, caches, anonymous container volumes and task
containers were removed. The Ollama image was already present and was retained.

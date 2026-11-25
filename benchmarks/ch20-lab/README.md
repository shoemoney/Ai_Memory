# Chapter 20 lab, 23 November 2026

The six chapter listings are copied verbatim here. The chapter retains the original
21 November measurements for stages 0 to 3 and the 2B writer. This pass reran the
cache probe, default stage 4, both larger writers and the variants below on CPU.

- Default stage 4: 23/24. `stage-4-default.json` preserves this baseline.
- `lab.py 4 --all-rows`: 24/24; 16 current rows use 358 memory tokens.
- `lab.py 4 --or-keywords`: 24/24.
- Default 4B and 9B writers: 12/24 each, three ingestions each.
- `writers.py 4 --key-bodies --sentences --single-ingestion`: 13/24,
  one ingestion, 11 accepted extractions, 13 fact inserts.

Only the first question sweep generates answers; subsequent sweeps use cache.
The combined writer variant does not isolate its component changes. Scores use
literal answer checks; no automated semantic grounding count was added.

`checks.py` tests real Memcached identity and before/after SQL deletion eligibility,
including historical recall. `retrieval_trials.py` measures the complete valid-row
budget and both retrieval options. These require the running owned lab and its
Python environment. `cleanup_trials.py` requires no existing lab; it constructs
partial setup states and tests refusal without deleting mismatched resources.
Run serving and inference while holding `/var/tmp/memlab-gpu.lock`.

Raw request audits, accepted/rejected writes, answer contexts, timing logs and
summaries are in `results/`. No weights, caches, database files or owner tokens
are retained. Cleanup and final private print checks are recorded in the lab response.

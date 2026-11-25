# DELEGATE-52 and ACE finance: reduced local reruns

Two published results reproduced at small scale with one open-weight model on local hardware. Everything here ran on the same model, **Qwen2.5-7B-Instruct, Q4_K_M** (GGUF from bartowski, repository revision 8911e8a, Apache-2.0), served by llama.cpp (build 12359) on an **Apple M3 Ultra, 96 GB** shared with other jobs. Code and scoring ran on a 32-thread x86 box and reached the model over an SSH tunnel. The endpoint is a setting (`ENDPOINT`, `ACE_BASE_URL`), default localhost.

| Folder | What | One command |
|---|---|---|
| `delegate52/` | G13: official DELEGATE-52 round-trip relay and domain evaluators | `bash delegate52/run.sh` |
| `ace-finance/` | G21: official ACE code, XBRL Formula, baseline vs ACE playbook | `bash ace-finance/run.sh` |

Both scripts pin the upstream commit, clone it into scratch, and write results into their `results/` folder. Nothing from the upstream repositories or datasets is stored here. The ACE patch (`ace-finance/ace-local.patch`, small) only adds a `local` provider whose base URL comes from an environment variable. DELEGATE-52 needed no code change: the official client reads `OPENAI_BASE_URL`.

## Results

| Claim | Published | Local | N | Interval |
|---|---|---|---|---|
| DELEGATE-52: content corrupted at the end of a long chain | about 25% (frontier models, 20 interactions) | **71.2%** after 4 interactions (54.3% after 2) | 40 environments, 40 domains | bootstrap 95%: 59.9% to 82.1% (41.9% to 66.6% after 2) |
| ACE finance: gain over baseline | +8.6% average (FiNER and Formula, 671B model) | **+10.5 points** on XBRL Formula (46.5% to 57.0%) | 200 test items, paired | bootstrap 95%: +3.5 to +18.0; exact McNemar p = 0.0065 (38 gains, 17 losses) |

### DELEGATE-52 setup
- Data: `microsoft/delegate52` revision 9d32564 (234 redistributable environments, 48 domains, cdla-permissive-2.0). Code: `microsoft/DELEGATE52` commit b896b80 (MIT).
- Protocol: official `run_relay.py`, single-shot (not agentic), distractor files included, default sampling (temperature 1.0), forward then backward edit per round trip. Score = official per-domain reconstruction score of the document after each backward edit against the original. Corruption = 1 minus score.
- Sample fixed before any score: environments whose seed document is at most 3,600 tokens; one environment per domain drawn with seed 20261122; 40 of 42 eligible domains drawn with the same seed (`selected.json`).
- Throughput check on two environments before fixing the length: one environment alone took 3 min 57 s for one round trip (two interactions); four runs in parallel took 17 min for four round trips, and 3 of 4 first-step outputs ran away to the 8,000-token cap. With roughly 3,000 output tokens per step at about 60 tokens per second aggregate, 40 environments by 2 round trips (four interactions) was the longest chain that fit in about three hours.
- Length is **4 interactions, not 20**. Output cap 6,000 tokens (the official default of 20,000 does not fit the 32K slot).
- Swap: `python1` could not be scored because the official repository lacks `utils_eval.py`, which the python evaluator imports. It was replaced by `recipe1` (rule in `selected.json`), run once with identical flags after the batch.
- By step (interaction 2 and 4 only; the forward edit has no official score): see `delegate52/results/summary.json`. Sensitivity: dropping the 4 steps per interaction that had no score (model dropped a file or broke the format) gives 49.2% (36.9% to 61.5%) and 68.0% (55.9% to 79.5%) instead of counting them as full loss.

### ACE finance setup
- Code: `ace-agent/ace` commit 82709de (Apache-2.0). Data: the repository's own `eval/finance/data` (XBRL Formula; 200 test items used whole).
- Same model for generator, reflector and curator. Offline mode: baseline test with an empty playbook, training on the first 60 training items (one epoch), validation on the first 40 validation items at steps 30 and 60 (0.525 then 0.600), then the final test with the best-validation playbook (the step-60 one). Baseline and final run in the same job on the same 200 items, temperature 0, 2,048 output tokens. Scoring is the repository's deterministic numeric check; no LLM judge.
- Playbook grew to about 2,700 tokens. 6 of 60 curator calls returned invalid JSON and were skipped by the code.

## Limits
- DELEGATE-52: one 7B quantized model against 19 frontier models; 4 interactions against 20; one sample per environment; temperature 1.0 and the 6,000-token cap are my settings or the official default and may add noise; 39 of 40 environments come from the pre-drawn list and 1 is a documented swap; domains with larger seed documents were excluded by the size rule, so documents are small. Per-environment scores are noisy (one run each). The paper's headline and this result are different quantities (different models, lengths, document sizes).
- ACE: one small model, 60 training items, 40 validation items; the paper used a 671B model and the full training sets; 164 of the 200 test items use a formula that also appears in the 60 training items (`results/formula_overlap.json`), so the gain may reflect memorizing formula templates and rounding rules rather than general strategy. Only the finance half of the ACE claim was run; the AppWorld agent half (+10.6%) was not.
- No independent human checked any item; scoring is deterministic in both runs.
- Evidence of failures: raw model text was not kept (size); per-step scores, token counts and latencies are in `delegate52/results/steps.jsonl`, per-item correctness in `ace-finance/results/items.jsonl`.

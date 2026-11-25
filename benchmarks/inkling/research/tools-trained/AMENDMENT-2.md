# Amendment 2: native tool declaration, lean schemas, out-of-template requests

Dated 2026-11-25, post hoc, written after the independent review (`../REVIEW-tinker.md`) and **before any v3 sampling**. The evaluation code, the out-of-template request file and a dry-run cost estimate are committed first; the sampling run's `runs/v3/provenance.json` records the repository HEAD at launch and refuses to start if the `v3/` folder has uncommitted changes. PREREG.md and AMENDMENT-1.md, and every file under `runs/main` and `runs/v2`, are untouched.

## Why

The review reproduced every number in RESULTS.md and found that the comparison still flatters the adapter:

1. 29 of arm B's 33 first-command misses in v2 are malformed call JSON, and in 27 of those the model had chosen the right command. B put JSON schemas into system text instead of declaring tools through the renderer, which is the likely cause.
2. The 3.58% prompt-token ratio is against a schema padded by one ~90-word paragraph repeated in all eight schemas (2,812 first-turn tokens against about 940 without it).
3. The test set is in-template: the same intent phrases as training with new wrappers and numbers.
4. RESULTS.md cited a provenance file that does not exist, and said the v2 evaluation code was committed before sampling when it was committed about three minutes after.

This amendment adds arms and a test set that answer 1 to 3 and records provenance properly for 4. It does not change what A is.

## Arms (all start from the same user request, effort 0.0, temperature 1.0, 512 completion tokens, four turns, 4,096 prompt tokens)

| Arm | Model | Prompt |
| --- | --- | --- |
| A | adapter (the unchanged final checkpoint from `runs/main`) | shared instruction plus the fixture sentence; no tool text |
| B-native | stock | shared instruction plus the fixture sentence, then the eight commands declared natively through the renderer's own path (`create_conversation_prefix_with_tools`, which emits a `tool_declare` message). One `text` string argument each, the one-line command description from `commands.TOOLS`, and a one-line argument note that mentions `-h`. No bash transport schema, no repeated boilerplate |
| B-lean | stock | the v2 arm B text (bash transport plus eight schemas serialised into system text, `indent=2`) with only the repeated ~90-word description paragraph removed. The repeated per-argument description and the indentation stay, so this is the v2 form minus the padding, not a minimal schema |
| C | stock | the v2 cheat-sheet arm unchanged (shared instruction, fixture sentence, bash transport schema, ten cheat-sheet lines) |

The renderer does support native declaration for this model; the first-turn prompt for `Find a web page about cobalt gardens.` is 903 tokens for B-native (the v2 B was 2,812, B-lean is 1,996, C is 421, A is 58 under the v2 fixture sentence).

Parsing is the v2 amended parser: a bash call with a one-line command, or a native call to one of the eight commands with exactly one nonempty string argument (rewritten into a safely quoted command line), is executed against the fake reference tools; anything else ends the episode and is counted. A call to an undeclared `bash` is accepted for the stock arms, which is lenient toward the baselines.

## Test sets

1. **In-template**: the existing 400-request test split (sha256 recorded in `provenance.json`; it must equal `data-manifest.json`). Arms A, B-native, B-lean, C. A and C are sampled again in the same run so every arm shares conditions; the v2 numbers stay in the record unchanged.
2. **Out-of-template**: 100 hand-authored requests in `v3/ood.py`, written to `v3/data/ood.jsonl`. 70 need a tool and 30 do not. The 70 are 52 single-command requests (6 or 7 per command, covering all eight) and 18 two-step requests (web_search then read_url, image_search then ask_model, remember then recall, calc then remember, web_search then ask_model, read_url then ask_model, image_gen then image_search). The 30 no-tool requests include six near misses that mention search, URLs or remembering without needing a tool. Every request comes from its own template with new verbs and sentence shapes, and arguments are natural phrases, not the training `cobalt garden N` pattern; so this test changes phrasing and argument style together. `test_v3.py` proves zero overlap with training: against the regenerated training requests it checks that no OOD template equals a training frame, shares any three-word sequence with one (placeholders included), or uses a training head verb or wrapper word. Arms A, B-native and C. No retraining and no checkpoint selection.

Scoring on the OOD set uses command names only (arguments are free). The expected name sequence for a two-step request is the pair in the order given.

## Metrics, per arm and test set

- First command right: the first parsed call names the expected first command, over tool-needed episodes.
- Well-formed call rate: parsed calls over call attempts, where an attempt is a call that parsed, a call the parser rejected, or a malformed or truncated turn containing a tool-call marker. Malformed first turns are reported as their own row with the count in which the intended command was nonetheless right. "Intended" is a heuristic: the first of the eight command names after the call marker in the raw text of the malformed turn. It is descriptive and is not folded into first-command accuracy.
- Exact sequence: command names equal to the expected sequence and the episode ended in a clean final answer (the v2 strict criterion on names; no fixture-answer matching).
- Extra calls: parsed calls not consumed by a greedy ordered match to the expected names, including calls on no-tool requests.
- No-tool specificity: no-tool requests answered cleanly with no call.
- Prompt and completion tokens per episode, and list-price cost from the repo's cost utility at the published rates (uncached prefill).

Paired bootstrap, A minus B-native on first command, 10,000 episode-paired draws, seed 0, `numpy.percentile` at 2.5 and 97.5, for the in-template test (280 tool-needed) and the out-of-template test (70). These are the only inferential statements; everything else is descriptive. There is no success gate. Possible outcomes include A ahead, A equal to B-native, and B-native ahead, and all will be reported as found.

## Cost and budget

The dry run (`runs/v3/preflight.json`) bounds the sampling cost by taking every episode to four turns with 512 completion tokens each and prompt growth of 500 tokens per turn, at $0.15 per million prefill tokens and $0.50 per million sampled tokens: ceiling about $3.71, expected about $0.81. The budget is $5; sampling stops before starting if the ceiling is above it. Actual spend goes in COST.md after the run. The key is passed to a user systemd unit as an environment variable and is not written anywhere.

## Provenance

`runs/v3/provenance.json` is written by the runner before the first sample and records: the research repository HEAD and the sha256 of every `v3/*.py` file, the recipe snapshot commit (branch `recipe-trained-tools` at 08876d4, extracted with `git archive` into a frozen directory so later branch changes cannot alter the sampled code), the sha256 of both test files, a hash of the checkpoint path, package versions and the start time. The runner refuses to sample if `git status` shows changes under `v3/`.

## Known limits

- B-native shares its argument note across all eight tools and mentions `-h`; a different note could move its numbers. B-lean still repeats a per-argument description and is not as short as a hand-minimised schema (its first turn is 1,996 tokens against 903 for B-native).
- The OOD set is 100 requests written once by one author; intervals on 70 tool-needed episodes are wide.
- Two-step OOD chains reuse command pairs that appear in training (image_search then ask_model, remember then recall) in new phrasing, alongside pairs that do not.
- The fake backend, one model, one adapter, one seed.

## Addendum, 2026-11-25 (after the first v3 sampling, before the second)

The first v3 run (`runs/v3`, provenance in `runs/v3/provenance.json`, research HEAD dfca642b) finished before this addendum was written. Reading its traces showed a harness effect that the amendment did not anticipate. B-native sometimes answers a first turn with **several tool calls at once** (parallel calls, for example `read_url` on two different URLs). The harness, like v2's, accepts one call per turn and ends the episode on anything else, so those turns are recorded as non-well-formed and the episode scores as a miss even when the first call named the right command. That penalises native declaration for behaviour that the cheat-sheet arm discourages in writing ("one call per turn") and that A never learned.

Two additions, both labelled post hoc:

1. **Descriptive re-read of the saved traces, no new sampling.** `report_v3.py` now also counts first turns that issued several calls and reports first-command accuracy if such a turn is read by its first call. This is reported next to, never instead of, the registered first-command number.
2. **One follow-up arm, B-native-1call.** B-native with a single added sentence in the system instruction, `Call one command per turn.` (the cheat-sheet arm already says this). Everything else is identical: same declared tools, same parser, same two test sets, same 10,000-draw seed-0 bootstrap for A minus B-native-1call. It is sampled once, in `runs/v3b`, and both B-native variants stay in the tables. The follow-up has the same $5 budget; its ceiling is checked by a dry run before sampling and spend is added to COST.md.

The code change is additive (a new arm name in `tools_v3.py`, a `--followup` flag in `run_v3.py`, extra report columns); no earlier arm's prompt changed, which `test_v3.py` checks. It is committed before the follow-up sampling, and `runs/v3b/provenance.json` records that commit.

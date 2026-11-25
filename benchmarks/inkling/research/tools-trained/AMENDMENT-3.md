# Amendment 3: adapter v2 (A2) trained for specificity, with a blind test

Dated 2026-11-25, written **before** the blind out-of-template set (OOT-2) was opened and before any A2 training or sampling. AMENDMENT-2 showed that with tools declared natively the adapter's first-command lead disappears out-of-template, and that the adapter invents commands for unfamiliar no-tool requests (7 of 30 handled correctly on OOT-1). That weakness looks like a data problem, so this round retrains with broader data and tests the result on requests written by someone else.

## Blind protocol

- OOT-2 is a 120-request file (80 need a command, 40 need none) written by a separate author from the command descriptions alone, committed at the original blind file (v1, not published) before this amendment. It was **not opened** by the author of this amendment, nor was its folder listed, until the v2 training data had been generated, hashed and committed.
- The v2 data commit is `d2476f3ac0963afd9f7dfd84570de8b580772d46` (research repository). The files, by sha256:

| File | sha256 |
| --- | --- |
| `v4/data/train.jsonl` (4,000 rows) | `e94d196c03fce7a0e1b2274b0ad0e7af6991d6e2ffbe77c42f40c2066e1fc713` |
| `v4/data/valid.jsonl` (400 rows) | `3b71e304c9bd3db289c0e5472d79c49d965e4d51baebe8a8a528d4cfe97ad755` |
| `v4/data/plan.jsonl` (requests sent to the stock model) | `b8e61ae288ec47b7a5eadfd3e14f44902d599d972423d507584be216046ae125` |
| `v4/data/answers.jsonl` (the stock model's answers) | `47af9c47e9745c8f7d2d4ade8a48779b5ae54f5abc9427bb4aa0d48434dd47e7` |
| `v4/gen_v2.py`, `shapes.py`, `pools.py` | `b32b8751...`, `a54a9cf2...`, `9c631d3e...` |

- OOT-1 (the 100 requests of AMENDMENT-2) is **no longer blind**: its failures informed this data. It is reported as a development set. Training data was built so that no OOT-1 item is copied or paraphrased; `v4/test_v4.py` proves zero shared content three-grams between training request frames and OOT-1 frames and no near-duplicate request (token Jaccard 0.6 or higher).
- After this amendment is committed the same check is run against OOT-2, **before training**. If it finds any overlap, the overlapping training items are removed and replaced, the new hashes are recorded in an addendum to this file, and the overlap is reported.

## The v2 curriculum

Same eight commands, same fake backend, same JSONL schema and system prompt as v1, 4,000 train and 400 validation rows (v1: 4,000 and 400), so the comparison is about content. Per 4,000 training rows:

| Part | Rows | What |
| --- | ---: | --- |
| Single commands | 1,540 | 14 to 18 independent sentence shapes per command (questions, imperatives, fragments, statements), arguments from pools of 40 to 100 phrases, an optional independent prefix and suffix on 40% |
| Two-step chains | 400 | eight chain types, four to six shapes each, second argument derived from the first result |
| Help first / unsupported flag | 320 | help-then-operation and "decline an unsupported flag" with six flags |
| Follow-ups about a shown result | 240 | 192 need no command (parity, half, digits, domain, file type, "was anything stored"), 48 need a second command |
| Mental arithmetic | 200 | small sums, differences, products to 12 by 12, exact small divisions; answer computed |
| Word games | 200 | reverse, upper-case, count letters or vowels, first or last letter, sort letters; answer computed |
| Sampled no-tool answers | 1,100 | definitions 160, translation 120, rewording 120, small talk 100, opinions 100, explanations 120, brainstorming 100, factual 80, and concept questions 200 |

Near-miss pairs: the same arithmetic shapes with small operands (answered directly) and with three- or four-digit operands (calc); 24 concepts about the tools themselves ("what is a URL", "what is a search engine", "how does AI image generation work") asked as explanations (no command) alongside the commands' own request shapes. Two-digit by two-digit products are deliberately absent, so the boundary between "do it in your head" and "use calc" is not taught there.

**Sampled answers.** For requests whose good answer needs a model, the stock model (Inkling 2 Mini, effort 0.0, temperature 0.7, at most 220 completion tokens, up to three tries, reply kept only if cleanly ended and at most 700 characters) answered once. 1,473 requests were planned (15% over quota); 1,430 answers were kept in the main pass, and 40 more were sampled incrementally after wording changes made to remove overlap with OOT-1. List-price spend: $0.111 for a first pass that was discarded when the generator changed, $0.133 for the second, about $0.01 for the incremental passes; total about **$0.26**. Answers are the stock model's, so the adapter learns to answer like the stock model, with its errors.

**Training system prompt.** As in v1, training uses the short instruction alone, while every evaluation arm also receives the one-sentence fixture note. This mismatch exists in v1 and is kept so only the data differs.

## A2 training

Recipe `recipe-trained-tools-pr` at commit `60cb705` (frozen copy), `train.py` with v1's settings: LoRA rank 32, batch 32, one epoch (125 updates), the default learning rate for the model (0.00054), effort 0.0, max length 4,096, seed 0, fresh optimizer, loss on every assistant turn. Only the final checkpoint is saved (`save_every` is set above the step count). Periodic closed-loop validation on `valid.jsonl` runs as in v1. Estimated training cost about $0.35 plus the periodic validation.

## Evaluation

Arms: **A** (the v1 adapter, unchanged), **A2**, **B-native-1call** and **C** (both as in AMENDMENT-2). Test sets: the in-template test (400 requests), OOT-1 (100, development) and OOT-2 (120, blind). Parsing, scoring, temperature, token limits and turn limits are those of AMENDMENT-2 (`v3/tools_v3.py`), and the new runner `v4/run_v4.py` imports them. Metrics per arm and set: first command right; well-formed call rate with malformed first turns as their own row; exact sequence; extra calls; no-tool specificity with a Wilson 95% interval; the names of invented commands (command names outside the eight, with counts); prompt and completion tokens per episode.

Paired bootstrap (10,000 episode-paired draws, seed 0, percentiles 2.5 and 97.5) on first command (tool-needed episodes) and on no-tool specificity (no-tool episodes), for **A2 minus B-native-1call** and **A2 minus A**, on each test set. No success threshold is set. OOT-2 scoring uses the file's own expected command names; any mapping needed to read its format is described in an addendum, not by editing the file.

## Budget and provenance

Budget $6 for this round (training about $0.35, sampling about $1, data answers about $0.26). The evaluation runner refuses to start with uncommitted changes under `v3/` or `v4/` and records the repository commit and file hashes in `runs/v4/provenance.json`; it also records the data hashes above, the OOT-2 file hash, and a hash of the A2 checkpoint path. Units run through `systemd-run --user`; the key is supplied as an environment variable and is never printed or stored.

## Known limits

OOT-2's author saw only the command descriptions, but may have shared habits with the author of OOT-1; the mental-arithmetic boundary in this curriculum is a design choice that a blind author may draw elsewhere (for example labelling "15 times 4" as needing calc), which would count as an error for A2. One adapter per version, one seed, one sample per request.

## Addendum 1, 2026-11-25: OOT-2 overlap found and removed (before training)

After the data commit above and AMENDMENT-3's own commit (`f32ec5f7`), OOT-2 was opened (sha256 `cf13fa71d5c824e5dda2d421a596f16fbc655d84696b1cfb903e81de27c4041e`, matching its README) and the same overlap check was run against the first v2 data. It found **32 shared content three-grams** (for example "pull up what", "ask another AI", "find me a", "search the web", "second opinion from") **and 6 near-duplicate requests**: three trivia questions I had written independently of OOT-2 that match it almost word for word ("What language is spoken in Brazil", the boiling point of water in Fahrenheit, the chemical symbol for gold), plus a small-talk request, a recall request and a brainstorming request. Natural English phrasing overlaps, so this was expected for some shapes; the protocol above said to remove and replace.

What was done. The generator gained an `--exclude` option: while drawing requests it rejects any candidate that shares a content three-gram with, or has token Jaccard 0.6 or higher against, any request in OOT-1 or OOT-2. The blind file is used only as a filter. No OOT-2 text was added to training or used to choose or write shapes; the effect is to remove phrasings the blind author happened to use, which makes the test harder, not easier. Replacement rows come from the remaining shapes and pools, so some shapes lost most of their draws. Data sizes and the composition table are unchanged. The superseded first data (`train.jsonl` sha256 `e94d196c...`) is in commit `d2476f3a` and was never trained on.

Final v2 data (this commit; the commit hash is in `runs/v4/provenance.json`):

| File | sha256 |
| --- | --- |
| `v4/data/train.jsonl` | `e42456da79d48b485f2c4e968250e520f975369e2607d467550eb43062e280c1` |
| `v4/data/valid.jsonl` | `92e1180c41a4a98c68dd587cbbf978515545cb987d3696270da67ec935198bdd` |
| `v4/data/plan.jsonl` | `5d8ca10ad6daebddebd899c93b1c088f024ece3f68274c16ae09ab89fbed63af` |
| `v4/data/answers.jsonl` | `214f1a08b6d2a02325f60bb20eda0f1a5cbcfca8b240041de7bb7dd844d46f56` |

`v4/test_v4.py` now proves zero overlap with OOT-1 and with OOT-2 on these files. Answer-sampling spend rose to about **$0.27** (an extra 133 requests, $0.013). OOT-2's format needs no mapping: each row's `commands` list is the expected command names, empty when none is needed.

## Addendum 2, 2026-11-25: a v2-template test set (t2), written before A2 sampling

The recipe being prepared for upstream generates its test split from the v2 generator, so the evaluation also scores every arm on a **v2-template test** (`t2`, 400 requests from the v2 generator's `test` split, a third seed, drawn after train and validation, with the same OOT-1 and OOT-2 overlap filter). For A2 this is the in-template test; the v1 test is now called the v1-template test and is out-of-template for A2's phrasing, though it shares the eight commands.

- `v4/data/train.jsonl` and `valid.jsonl` are byte-identical to the files A2 trains on (hashes in Addendum 1). `v4/data/test.jsonl` sha256 `b51aaed70859dafd12257205d531f45981b6b4511feb2d75d0283a8ffbf5cbf1`. Its sampled no-tool answers (167 more requests, $0.017) are in `v4/data/answers_test.jsonl`, sha256 `587136080995d06feb1f493f99ff195b0d2f4df6fcbff45604154c8ddf28cb42`, and are used by the test split only, so adding them did not change train or valid. `plan.jsonl` was regenerated to include the test requests (sha256 `93d2f081b98841b09989811ace4d8c2274e8d4b5b1230d1d50ebd10c3077e1f4`); `answers.jsonl` is unchanged.
- `test_v4.py` proves the test split shares no request with train or valid and has zero overlap with OOT-1 and OOT-2.
- Four test sets now: v1-template (400), t2 (400), OOT-1 (100, development), OOT-2 (120, blind). Four arms each: 4 x 1,020 = 4,080 episodes. The dry run's worst-case ceiling (every episode to four 512-token turns) is $6.92 and its expected cost $1.10; as that ceiling is far above anything the earlier runs did (about a sixth of it), the runner gates on twice the expected cost against the $6 budget and I will stop if actual spend approaches it. Spend so far this round: answers about $0.28, training about $0.35 to be confirmed.
- Training data note: because the training answers include 167 requests sampled for the test split after the fact, "answers.jsonl hash" above refers to the training answers only.

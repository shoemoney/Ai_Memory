# [Recipe] Add trained-tools recipe: eight commands without tool text

Adds `recipes/trained_tools`: LoRA SFT that teaches Inkling-2-Mini eight one-line commands (`web_search`, `image_search`, `image_gen`, `ask_model`, `read_url`, `calc`, `remember`, `recall`) with no tool text in its prompt, including when not to call one.

- `prepare` builds a CC0 curriculum (4,000 / 400 / 400) over a deterministic fake backend and samples about 1,600 short answers from the stock model once (about $0.15). It prints the upper-bound cost before spending, `--dry-run` stops there, `--budget-usd` caps it, and answers are appended to the cache as they arrive.
- `train` is a standard supervised run; its estimate covers training and the periodic validation, and `budget_usd` gates the total.
- `eval` runs the adapter, the stock model with the commands declared natively, and a stock-model cheat sheet in a closed loop, on the generated test and on a 120-request blind file written from the command descriptions alone. It reports first-turn malformed turns, invented command names and parallel calls per arm, and the paired bootstrap of adapter minus native.
- The blind file is v1.1 of the author's original: real place names, local organisations, teams and retailers were replaced by invented ones and every domain moved under `.example`, by a substitution table committed before it was applied. No request was reworded and no label changed.

**What it shows.** Two complete runs of the recipe, about $0.95 each at list prices, one adapter and one seed per run:

| First command, adapter minus native | Run 1 | Run 2 |
| --- | ---: | ---: |
| Generated test (250 tool requests) | +4.4 points [+1.6, +7.2] | +2.0 [-1.2, +5.6] |
| Blind test v1.1 (80 tool requests) | -7.5 [-15.0, 0.0] | -10.0 [-18.8, -2.5] |

So the adapter matches native declaration on requests built from its own templates and trails it on unfamiliar phrasing. What it buys is about 8 to 9% of native's uncached prompt tokens and far fewer extra calls (3 to 11 against 48 to 67). What it costs is over-calling on casual no-tool requests (4 and 5 of 40 on the blind test against 1 for native) and a few invented command names (up to 4 per 120 requests; native cannot invent one). The cheat-sheet arm mostly shows a stock model writing the call as plain text; read it as a baseline, not as command choice. The README table has every column for both runs, and says that two runs of identical code move by a few points in each cell.

This is a recipe about what moving a tiny, fixed interface into the weights buys and costs, not about a better tool-using model. It does not teach tool discovery, and new commands need retraining.

Tests need no API key (`pytest tinker_cookbook/recipes/trained_tools`); pyright and pre-commit are clean.

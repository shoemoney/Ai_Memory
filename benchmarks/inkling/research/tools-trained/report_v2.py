"""Rebuild the post hoc report and PNG from saved traces; makes no service calls."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tinker_cookbook.recipes.trained_tools.analyze import analyze, analyze_amended

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "runs/main"
V2 = ROOT / "runs/v2"
main_paths = sorted(MAIN.glob("test_tools-*.jsonl"))
v2_paths = sorted(V2.glob("test_tools-*.jsonl"))
original = analyze(main_paths)
amended = analyze_amended(v2_paths)
(V2 / "main-analysis.json").write_text(json.dumps(original, indent=2) + "\n")
(V2 / "analysis.json").write_text(json.dumps(amended, indent=2) + "\n")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |", *["| " + " | ".join(map(str, row)) + " |" for row in rows]])


def fraction(n, d):
    return f"{int(n)}/{d} ({100*n/d:.2f}%)"


raw_main = {}
for path in main_paths:
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    a = rows[0]["arm"]
    counts = {key: sum(r["scores"][key] for r in rows) for key in rows[0]["scores"]}
    turns = [t for r in rows for t in r["turns"]]
    raw_main[a] = {"counts": counts, "turns": len(turns), "prompt_tokens": sum(t["prompt_tokens"] for t in turns), "completion_tokens": sum(t["completion_tokens"] for t in turns)}
main_rows, token_rows = [], []
for a in "ABC":
    d = raw_main[a]
    c = d["counts"]
    main_rows.append([a, fraction(c["tool_correct"], 280), fraction(c["arguments_valid"], int(c["calls"])), fraction(c["no_tool_correct"], int(c["predicted_no_tool"])), fraction(c["no_tool_correct"], 120), fraction(c["final_correct"], 400), fraction(c["episode_correct"], 400)])
    token_rows.append(["Main", a, f'{d["prompt_tokens"]:,}', f'{d["completion_tokens"]:,}', d["turns"], f'${(d["prompt_tokens"]*.15+d["completion_tokens"]*.5)/1e6:.8f}'])
amend_rows = []
for a, d in amended["arms"].items():
    c = d["counts"]
    amend_rows.append([a, fraction(c["tool_correct"], 280), fraction(c["first_command_correct"], 280), fraction(c["sequence_contained"], 280), f'{int(c["extra_calls"])}/400 = {d["extra_calls_per_episode"]:.3f}', fraction(c["actual_final_correct"], 400), d["native_mapped_calls"]])
    token_rows.append(["Amended v2", a, f'{d["prompt_tokens"]:,}', f'{d["completion_tokens"]:,}', d["turns"], f'${d["list_price_usd"]:.8f}'])
spend = sum(d["list_price_usd"] for d in amended["arms"].values())
main_spend = sum((d["prompt_tokens"]*.15+d["completion_tokens"]*.5)/1e6 for d in raw_main.values())
paired_rows = []
for metric, label in [("tool_correct", "Strict sequence"), ("first_command_correct", "First command"), ("sequence_contained", "Ordered containment")]:
    d = amended["paired"][metric]
    lo, hi = d["paired_bootstrap_95pct_interval"]
    paired_rows.append([label, f'{100*d["A_minus_B"]:.2f}', f'[{100*lo:.2f}, {100*hi:.2f}]'])

fig, ax = plt.subplots(figsize=(10, 5.8), layout="constrained")
colors = {"A": "#176b48", "B": "#245aa8", "C": "#b26705", "C0": "#795598"}
for a, d in raw_main.items():
    x, y = d["prompt_tokens"], d["counts"]["tool_correct"] / 280 * 100
    ax.scatter(x, y, s=90, facecolors="none", edgecolors=colors[a], linewidth=2)
    ax.annotate(f"{a} main: {y:.1f}%", (x, y), xytext=(-4, -22 if a == "A" else 12), textcoords="offset points", ha="left" if a != "B" else "right", fontsize=11)
for a, d in amended["arms"].items():
    x, y = d["prompt_tokens"], d["tool_accuracy"] * 100
    ax.scatter(x, y, s=90, c=colors[a])
    ax.annotate(f"{a} v2: {y:.1f}%", (x, y), xytext=(10 if a != "B" else -10, 10), textcoords="offset points", ha="left" if a != "B" else "right", fontsize=11)
ax.set(xscale="log", xlim=(50000, 4000000), ylim=(0, 112), xlabel="Total rendered prompt tokens across 400 episodes (log scale)", ylabel="Strict tool sequence accuracy on 280 tool-needed episodes (%)", title="Adapter: 279/280 in both runs; stock improves after post hoc repair")
ax.set_xticks([100000, 300000, 1000000, 3000000], ["100,000", "300,000", "1,000,000", "3,000,000"])
ax.grid(alpha=.22)
ax.text(.02, .96, "Hollow: original main run    Filled: post hoc amendment v2", transform=ax.transAxes, va="top", fontsize=10)
fig.savefig(ROOT / "tool-accuracy-vs-prompt-tokens.png", dpi=180)
plt.close(fig)

extra_rows=[]
for a,d in amended["arms"].items():
    c=d["counts"]
    extra_rows.append([a, fraction(c["arguments_valid"], int(c["calls"])), fraction(c["no_tool_correct"], int(c["predicted_no_tool"])), fraction(c["no_tool_correct"],120), fraction(c["final_correct"],400), fraction(c["episode_correct"],400)])
cohort_rows=[]
for a,d in amended["arms"].items():
    for skill,c in d["cohorts"].items():
        if skill == "direct": continue
        cohort_rows.append([a,skill,c['episodes'],int(c['tool_correct']),int(c['first_command_correct']),int(c['sequence_contained']),int(c['actual_final_correct'])])

text = f'''# An adapter keeps 279/280 strict tool sequences with 3.58% of the schema arm's prompt tokens

The adapter retained 279/280 strict command sequences in the post hoc rerun and used 82,990 prompt tokens versus the stock schema arm's 2,318,037 (3.58%). Repairing the evaluation raised stock strict sequence accuracy from 173/280 to 208/280 with full schemas and from 16/280 to 172/280 with a cheat sheet plus a bash schema. The original stock scores understate command choice: they mix transport failures, probing of artificial results and final-answer matching. The amendment narrows that problem; it does not establish broad tool-use superiority or latency gains.

![Strict tool accuracy against actual prompt tokens](tool-accuracy-vs-prompt-tokens.png)

Reproduce the offline report from the cookbook worktree: `PYTHONPATH=. .venv/bin/python {ROOT / 'report_v2.py'}`. Plotting additionally requires matplotlib (this report used 3.11.2).

## What was compared

A is the saved low-rank adaptation (LoRA) checkpoint with no tool catalog. B is the stock model with full JavaScript Object Notation (JSON) command schemas and a bash function schema serialized in its system prompt. C in the main run is stock with ten cheat-sheet lines; C in amendment version 2 (v2) also receives B's bash schema. C0 is stock with the original C prompt. Every amended arm also receives “Tool results come from a test fixture; report them as given.” C0 therefore preserves the original prompt treatment, not all original evaluation conditions. B is schema text in the system message, not an MCP server benchmark or native schema API.

The [preregistration](PREREG.md) and [main traces/configuration](runs/main/) are unchanged. The [post hoc amendment](AMENDMENT-1.md) was written and committed before new sampling. The [v2 dry run](runs/v2/preflight.json), [configuration](runs/v2/run-config.json), [metrics](runs/v2/comparison.json) and [paired analysis](runs/v2/analysis.json) specify the repair. Complete traces contain each exact inference prompt, generated response and tool result. Command/result fixtures remain unchanged to match A's training. Stock native calls to known commands are mapped to safely quoted command lines; free prose is not interpreted as shell.

## Pre-registered main-run table (unchanged)

Strict tool accuracy requires a clean completion and exact full command-name sequence on 280 tool-needed episodes. Valid execution is successful executions per parsed call. No-tool precision is correct direct requests per clean no-call prediction; no-tool specificity is clean no-call predictions per 120 direct requests. Reference final accuracy is whitespace-normalized exact match to the original target over all 400 episodes. Episode accuracy additionally requires the expected sequence and valid executions.

{table(['Arm','Strict tool accuracy','Valid execution','No-tool precision','No-tool specificity','Reference final accuracy','Episode accuracy'], main_rows)}

[Original analysis](runs/v2/main-analysis.json): A minus B strict accuracy is {100*original['A_minus_B_tool_accuracy']:.2f} percentage points, with a paired 95% interval [{100*original['paired_bootstrap_95pct_interval'][0]:.2f}, {100*original['paired_bootstrap_95pct_interval'][1]:.2f}]. The numerical registered success gates pass, but the baseline defects limit that result's interpretation. This table is not retroactively rescored.

## Post hoc amendment table

First command accuracy counts a correct first parsed command even if later steps fail. Ordered containment means all reference command names occur in order among parsed calls. Extra calls are parsed calls not consumed by a greedy ordered reference match, including wrong commands and calls on direct requests; the mean uses all 400 episodes. Selection diagnostics do not require a clean final completion. Actual-result final accuracy compares the final answer to the last successful result the model received, retaining the direct-answer and unsupported-flag targets. It measures faithful reporting separately from task success and can pass a wrong tool or rewritten argument. Mapped calls count stock native calls converted by the parser.

{table(['Arm','Strict tool accuracy','First command','Ordered containment','Extra calls / episode','Actual-result final accuracy','Mapped calls'], amend_rows)}

All arms saw the same 400 requests: 280 tool-needed and 120 direct. The bash-only parser remains for A. For stock arms, exactly one known native function with one nonempty text argument is mapped; ambiguous/multiple calls and malformed arguments still fail. Retain the other original metrics for transparency:

{table(['Arm','Valid execution','No-tool precision','No-tool specificity','Reference final accuracy','Episode accuracy'],extra_rows)}

The stock final-answer scores remain low after grading against received results (B 149/400 rather than 146/400 against references). Exact output matching penalizes explanations and natural paraphrases; this is not a semantic answer-quality metric. C0's 240 mapped calls show the transport issue mattered. Its first parsed command score still excludes prose that cannot be mapped and should not be confused with the earlier manual intended-command audit (85.7%). The shared fixture sentence reduced one source of distrust but does not prove the synthetic content is on-topic or all distrust is eliminated. No further tuning or rerun followed these outcomes.

Paired intervals resample the same 280 tool-needed episode IDs, 10,000 draws, seed 0; the random generator resets for each metric. Differences and two-sided percentile 95% intervals below are in percentage points. They describe this post hoc evaluation, not a new registered success test.

{table(['Metric','A minus B (points)','Paired 95% interval (points)'], paired_rows)}

## Exact token accounting and spend

Prompt tokens are the rendered input on every actual inference turn, including repeated history. Completion tokens include the model's generated thinking, calls and final answers. Counts below are measured, not character estimates. Costs use actual token counts at $0.15 per million uncached prompt tokens and $0.50 per million completion tokens, verified 2026-11-25 against the [published pricing table](https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/). No cache discount is assumed.

{table(['Run','Arm','Prompt tokens','Completion tokens','Turns','List-price token cost'],token_rows)}

Amended sampling cost **${spend:.8f}** from actual tokens, under the $10 budget and $5.57056 worst-case compute ceiling. Main test sampling cost **${main_spend:.8f}** at the same uncached list prices. These are token-accounted charges, not a provider invoice; actual cash billing/cache discounts and checkpoint storage charges are unavailable. No new training occurred. See [COST.md](COST.md). The four-arm unit exited successfully; no paid retry or partial rerun occurred.

## Reproduction

The frozen evaluation uses effort 0.0, temperature 1.0, 512 completion tokens per turn, at most four turns and 4096 prompt tokens per turn, with no test-based checkpoint selection. The v2 rerun was `eval` with `amended=True` on the `recipe-trained-tools` branch (commit `08876d4`): a dry run with `dry_run=True budget_usd=10`, then the same command without `dry_run`, launched as a user systemd unit with the Tinker key supplied through the unit's environment. The checkpoint is `checkpoint` in `runs/main/final_tools_metrics.json`. `analyze --amended` rebuilds the paired analysis from the traces; this script rebuilds the tables and chart.

The sampling command spends money. Use a fresh output directory for a replication; the analyzer rejects duplicated IDs. The published run used `runs/v2` as its log directory. Exact arm prompts are in every trace's first system message.

## Behavior cohorts

Counts are descriptive, with no subgroup selection. Help includes help-before-operation requests; unsupported means a request to check help and decline the unsupported --turbo flag. The 60 web_search+read_url tasks use a combination withheld from training and validation. All other command compositions were known. Final counts here use actual-result grading.

{table(['Arm','Cohort','Episodes','Strict correct','First correct','Contained','Final correct'],cohort_rows)}

## Limits

Eight fixed commands, deterministic fake fixtures and templated requests make this a narrow interface experiment. Train/test wrapper families and argument IDs are disjoint, but intent paraphrases are shared. One training/data-order seed and one rollout per arm do not characterize run-to-run variance; the hosted API exposes no sampling seed here. Bootstrap intervals reflect episode resampling, not training or sampling-seed uncertainty. The post hoc repair followed inspection of the original failures and changes several factors together, so it cannot isolate their causal effects.

Command-name metrics do not establish argument relevance, real retrieval quality, generated-image quality or safety of arbitrary shell/URL access. Actual-result final matching measures literal reporting, not semantic answer quality. The stock schemas are verbose; token savings against them should be read alongside the shorter cheat-sheet arm. No first-token timing is available, and there is no latency, local speed, energy, or general intelligence claim.
'''
(V2 / "report-v2.md").write_text(text)
print(f"Wrote runs/v2/report-v2.md and chart; v2 list-price sampling ${spend:.8f}")

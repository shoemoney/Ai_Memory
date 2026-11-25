"""Rebuild the v3 tables, JSON and chart from saved traces. Makes no service calls.

    python report_v3.py runs/v3        # writes results-v3.json, tables-v3.md, first-command-vs-prompt-tokens.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import tools_v3 as t  # noqa: E402
from tinker_cookbook.utils.cost_estimation import TokenCostRates, TokenUsage  # noqa: E402

RATES = TokenCostRates(0.15, 0.15, 0.50, 0.75)  # per-million rates, as in v2 and the dry run
DRAWS, SEED = 10_000, 0


def load(run: Path, split: str, arm: str) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in (run / f"{split}_{arm}.jsonl").read_text().splitlines()]
    for r in rows:  # rescore from the raw turns; never trust stored scores
        r["scores"] = t.score_record(r)
    return rows


def first_call_name(record: dict[str, Any]) -> str | None:
    """Name of the first call in the first turn, even when that turn issued several calls."""
    calls = (record["turns"][0]["response"].get("tool_calls") or []) if record["turns"] else []
    if not calls:
        return None
    function = calls[0]["function"]
    name = function["name"].removeprefix("functions.")
    if name in t.TOOLS:
        return name
    try:
        return t.command_name(json.loads(function["arguments"])["command"])
    except (ValueError, KeyError, TypeError):
        return None


def multi_call_first_turn(record: dict[str, Any]) -> bool:
    return bool(record["turns"]) and len(record["turns"][0]["response"].get("tool_calls") or []) > 1


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    s = [r["scores"] for r in rows]
    needed = [x for x in s if x["needed"]]
    direct = [x for x in s if not x["needed"]]
    prompt = sum(x["prompt_tokens"] for x in s)
    completion = sum(x["completion_tokens"] for x in s)
    first_malformed = sum(x["first_turn_malformed"] for x in needed)
    attempts, ok = sum(x["call_attempts"] for x in s), sum(x["call_ok"] for x in s)
    return {
        "episodes": len(s),
        "tool_needed": len(needed),
        "no_tool_needed": len(direct),
        "first_command_right": sum(x["first_command_right"] for x in needed),
        "first_turn_malformed": first_malformed,
        "first_malformed_intended_right": sum(x["first_malformed_intended_right"] for x in needed),
        "first_turn_other_failure": sum(x["first_turn_other_failure"] for x in needed),
        "first_turn_multi_call": sum(multi_call_first_turn(r) for r in rows if r["scores"]["needed"]),
        "first_right_by_first_call": sum(
            bool(r["expected"]) and first_call_name(r) == r["expected"][0] for r in rows
        ),
        "call_attempts": attempts,
        "call_well_formed": ok,
        "malformed_turns": sum(x["malformed_turns"] for x in s),
        "exact_sequence": sum(x["exact_sequence"] for x in needed),
        "extra_calls": sum(x["extra_calls"] for x in s),
        "no_tool_ok": sum(x["no_tool_ok"] for x in direct),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "prompt_per_episode": prompt / len(s),
        "completion_per_episode": completion / len(s),
        "turns": sum(x["turns"] for x in s),
        "list_price_usd": RATES.estimate_usd(TokenUsage(sampled=completion, prefill_uncached=prompt)),
    }


def paired_bootstrap(a: list[bool], b: list[bool]) -> dict[str, float]:
    """A minus B in percentage points; episode-paired resampling, numpy percentiles."""
    x, y = np.asarray(a, float), np.asarray(b, float)
    idx = np.random.default_rng(SEED).integers(0, len(x), size=(DRAWS, len(x)))
    diffs = 100 * (x[idx].mean(1) - y[idx].mean(1))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {"diff_pp": float(100 * (x.mean() - y.mean())), "lo": float(lo), "hi": float(hi), "n": len(x)}


def paired_first(rows_a: list[dict], rows_b: list[dict]) -> dict[str, float]:
    by_b = {r["id"]: r for r in rows_b}
    pairs = [(r, by_b[r["id"]]) for r in rows_a if r["scores"]["needed"]]
    return paired_bootstrap(
        [p[0]["scores"]["first_command_right"] for p in pairs],
        [p[1]["scores"]["first_command_right"] for p in pairs],
    )


def build(runs: list[Path]) -> dict[str, Any]:
    data: dict[str, dict[str, list[dict[str, Any]]]] = {"in": {}, "ood": {}}
    for run in runs:
        for path in sorted(run.glob("*_*.jsonl")):
            split, arm = path.stem.split("_", 1)
            if split in data:
                data[split][arm] = load(run, split, arm)
    order = [*t.ARMS_IN, *t.ARMS_FOLLOWUP]
    data = {s: {a: data[s][a] for a in order if a in data[s]} for s in data}
    out: dict[str, Any] = {split: {a: summarize(r) for a, r in arms.items()} for split, arms in data.items()}
    out["paired_A_minus_Bnative_first_command"] = {
        split: paired_first(data[split]["A"], data[split]["B-native"]) for split in ("in", "ood")
    }
    out["paired_A_minus_Bnative1call_first_command"] = {
        split: paired_first(data[split]["A"], data[split]["B-native-1call"])
        for split in ("in", "ood")
        if "B-native-1call" in data[split]
    }
    out["draws"], out["seed"] = DRAWS, SEED
    return out


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else "n/a"


def tables(res: dict[str, Any]) -> str:
    lines: list[str] = []
    for split, title in (("in", "In-template test (400 episodes: 280 need a tool, 120 do not)"),
                         ("ood", "Out-of-template test (100 episodes: 70 need a tool, 30 do not)")):
        lines += [f"**{title}**", "",
                  "| Arm | First command right | First turn malformed (intended command right) | Well-formed calls | Exact sequence | Extra calls | No-tool specificity | Prompt tok / episode | Completion tok / episode |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for arm, d in res[split].items():
            lines.append(
                f"| {arm} | {pct(d['first_command_right'], d['tool_needed'])} "
                f"| {d['first_turn_malformed']} ({d['first_malformed_intended_right']}) "
                f"| {pct(d['call_well_formed'], d['call_attempts'])} "
                f"| {pct(d['exact_sequence'], d['tool_needed'])} "
                f"| {d['extra_calls']} "
                f"| {pct(d['no_tool_ok'], d['no_tool_needed'])} "
                f"| {d['prompt_per_episode']:,.0f} | {d['completion_per_episode']:,.0f} |"
            )
        lines.append("")
    lines += ["**Paired bootstrap, first command, A minus B-native** (tool-needed episodes, "
              f"{res['draws']:,} draws, seed {res['seed']}, percentile 2.5 / 97.5)", "",
              "| Test | A minus comparator (points) | 95% interval | n |", "| --- | ---: | ---: | ---: |"]
    for split, label in (("in", "In-template"), ("ood", "Out-of-template")):
        p = res["paired_A_minus_Bnative_first_command"][split]
        lines.append(f"| {label} | {p['diff_pp']:+.2f} | [{p['lo']:+.2f}, {p['hi']:+.2f}] | {p['n']} |")
    for key, name in (("paired_A_minus_Bnative1call_first_command", "B-native-1call"),):
        for split, label in (("in", "In-template"), ("ood", "Out-of-template")):
            if split in res.get(key, {}):
                p = res[key][split]
                lines.append(
                    f"| {label}, vs {name} (follow-up) | {p['diff_pp']:+.2f} | [{p['lo']:+.2f}, {p['hi']:+.2f}] | {p['n']} |"
                )
    lines += ["", "**Multi-call first turns** (tool-needed episodes; the harness accepts one call per turn)", "",
              "| Test | Arm | First turn issued several calls | First command right if such a turn is read by its first call |",
              "| --- | --- | ---: | ---: |"]
    for split in ("in", "ood"):
        for arm, d in res[split].items():
            lines.append(
                f"| {split} | {arm} | {d['first_turn_multi_call']} | {pct(d['first_right_by_first_call'], d['tool_needed'])} |"
            )
    lines += ["", "**Prompt-token ratio, A over each arm** (total prompt tokens over the whole test)", "",
              "| Test | vs B-native | vs B-lean | vs C |", "| --- | ---: | ---: | ---: |"]
    for split, label in (("in", "In-template"), ("ood", "Out-of-template")):
        a = res[split]["A"]["prompt_tokens"]
        r = lambda arm: f"{100 * a / res[split][arm]['prompt_tokens']:.1f}%" if arm in res[split] else "not run"  # noqa: E731
        lines.append(f"| {label} | {r('B-native')} | {r('B-lean')} | {r('C')} |")
    lines.append("")
    return "\n".join(lines)


def chart(res: dict[str, Any], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"A": "#176b48", "B-native": "#245aa8", "B-lean": "#6f7f99", "C": "#b26705",
              "B-native-1call": "#7a3fa0"}
    fig, ax = plt.subplots(figsize=(9, 5.4), layout="constrained")
    for arm in (*t.ARMS_IN, *t.ARMS_FOLLOWUP):
        pts = []
        for split, filled in (("in", True), ("ood", False)):
            if arm in res[split]:
                d = res[split][arm]
                x, y = d["prompt_per_episode"], 100 * d["first_command_right"] / d["tool_needed"]
                ax.scatter(x, y, s=90, color=colors[arm], facecolors=colors[arm] if filled else "white", linewidths=2, zorder=3)
                pts.append((x, y))
        if len(pts) == 2:
            ax.plot(*zip(*pts, strict=True), color=colors[arm], alpha=0.35, zorder=2)
        ax.annotate(arm, pts[0], xytext=(8, 6), textcoords="offset points", color=colors[arm], fontsize=11)
    ax.set_xscale("log")
    ax.set_xlabel("Prompt tokens per episode (log scale)")
    ax.set_ylabel("First command right, % of tool-needed episodes")
    ax.set_ylim(0, 102)
    ax.set_title("First-command accuracy against prompt cost; filled = in-template, open = out-of-template")
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=150)


def main() -> None:
    runs = [Path(p) for p in sys.argv[1:]]
    run = runs[0]
    res = build(runs)
    (run / "results-v3.json").write_text(json.dumps(res, indent=2) + "\n")
    (run / "tables-v3.md").write_text(tables(res))
    chart(res, run / "first-command-vs-prompt-tokens.png")
    print(tables(res))


if __name__ == "__main__":
    main()

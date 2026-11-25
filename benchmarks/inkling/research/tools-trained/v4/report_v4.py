"""Tables, JSON and chart for the A2 evaluation, rebuilt from saved traces (no service calls).

    python report_v4.py runs/v4
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v3"))
import report_v3 as r3  # noqa: E402
import tools_v3 as t  # noqa: E402

ARMS = ("A", "A2", "B-native-1call", "C")
SPLITS = {"in": "v1-template test", "t2": "v2-template test (in-template for A2)", "oot1": "OOT-1 (development set)", "oot2": "OOT-2 (blind)"}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def invented(rows: list[dict[str, Any]]) -> Counter:
    names: Counter = Counter()
    for r in rows:
        for c in r["commands"]:
            n = t.command_name(c)
            if n not in t.TOOLS:
                names[n] += 1
    return names


def paired_spec(a: list[dict], b: list[dict]) -> dict[str, float]:
    by_b = {r["id"]: r for r in b}
    pairs = [(r, by_b[r["id"]]) for r in a if not r["scores"]["needed"]]
    return r3.paired_bootstrap(
        [p[0]["scores"]["no_tool_ok"] for p in pairs], [p[1]["scores"]["no_tool_ok"] for p in pairs]
    )


def build(run: Path) -> dict[str, Any]:
    data = {s: {a: r3.load(run, s, a) for a in ARMS} for s in SPLITS}
    out: dict[str, Any] = {"summary": {}, "invented": {}, "paired": {}}
    for s, arms in data.items():
        out["summary"][s] = {a: r3.summarize(rows) for a, rows in arms.items()}
        out["invented"][s] = {a: dict(invented(rows)) for a, rows in arms.items()}
        out["paired"][s] = {
            f"A2-{b}": {
                "first_command": r3.paired_first(arms["A2"], arms[b]),
                "no_tool_specificity": paired_spec(arms["A2"], arms[b]),
            }
            for b in ("B-native-1call", "A")
        }
    out["draws"], out["seed"] = r3.DRAWS, r3.SEED
    return out


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else "n/a"


def tables(res: dict[str, Any]) -> str:
    lines: list[str] = []
    for s, title in SPLITS.items():
        first = next(iter(res["summary"][s].values()))
        lines += [f"**{title}** ({first['episodes']} requests: {first['tool_needed']} need a command, {first['no_tool_needed']} do not)", "",
                  "| Arm | First command right | First turn malformed | Well-formed calls | Exact sequence | Extra calls | No-tool specificity (Wilson 95%) | Prompt tok / episode |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
        for a, d in res["summary"][s].items():
            lo, hi = wilson(d["no_tool_ok"], d["no_tool_needed"])
            lines.append(
                f"| {a} | {pct(d['first_command_right'], d['tool_needed'])} | {d['first_turn_malformed']} "
                f"| {pct(d['call_well_formed'], d['call_attempts'])} | {pct(d['exact_sequence'], d['tool_needed'])} | {d['extra_calls']} "
                f"| {pct(d['no_tool_ok'], d['no_tool_needed'])} [{100 * lo:.0f}, {100 * hi:.0f}] | {d['prompt_per_episode']:,.0f} |"
            )
        lines.append("")
    lines += [f"**Paired bootstrap** ({res['draws']:,} draws, seed {res['seed']}, percentile 2.5 / 97.5; points)", "",
              "| Test | Comparison | First command | No-tool specificity |", "| --- | --- | ---: | ---: |"]
    for s, title in SPLITS.items():
        for k, v in res["paired"][s].items():
            f, p = v["first_command"], v["no_tool_specificity"]
            lines.append(f"| {title} | {k} | {f['diff_pp']:+.1f} [{f['lo']:+.1f}, {f['hi']:+.1f}] (n={f['n']}) | {p['diff_pp']:+.1f} [{p['lo']:+.1f}, {p['hi']:+.1f}] (n={p['n']}) |")
    lines += ["", "**Invented command names** (calls to names outside the eight; count of calls)", "", "| Test | Arm | Calls | Names |", "| --- | --- | ---: | --- |"]
    for s, title in SPLITS.items():
        for a, names in res["invented"][s].items():
            top = ", ".join(f"`{n}` x{c}" for n, c in sorted(names.items(), key=lambda x: -x[1])) or "none"
            lines.append(f"| {title} | {a} | {sum(names.values())} | {top} |")
    return "\n".join(lines) + "\n"


def chart(res: dict[str, Any], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"A": "#6f7f99", "A2": "#176b48", "B-native-1call": "#245aa8", "C": "#b26705"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), layout="constrained", sharey=True)
    for ax, key, title in ((axes[0], "first", "First command right (tool-needed requests)"), (axes[1], "spec", "No-tool requests answered without a call")):
        for j, a in enumerate(ARMS):
            for i, s in enumerate(SPLITS):
                d = res["summary"][s][a]
                k, n = (d["first_command_right"], d["tool_needed"]) if key == "first" else (d["no_tool_ok"], d["no_tool_needed"])
                lo, hi = wilson(k, n)
                x = i + (j - 1.5) * 0.2
                ax.bar(x, 100 * k / n, 0.19, color=colors[a], label=a if i == 0 else None)
                ax.errorbar(x, 100 * k / n, yerr=[[100 * k / n - 100 * lo], [100 * hi - 100 * k / n]], color="black", lw=1)
        ax.set_xticks(range(4), ["v1 template", "v2 template", "OOT-1 (dev)", "OOT-2 (blind)"], fontsize=9)
        ax.set_title(title, fontsize=11)
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("%")
    axes[0].legend(loc="lower left", fontsize=9)
    fig.savefig(path, dpi=150)


def main() -> None:
    run = Path(sys.argv[1])
    res = build(run)
    (run / "results-v4.json").write_text(json.dumps(res, indent=2) + "\n")
    (run / "tables-v4.md").write_text(tables(res))
    chart(res, run / "a2-first-command-and-specificity.png")
    print(tables(res))


if __name__ == "__main__":
    main()

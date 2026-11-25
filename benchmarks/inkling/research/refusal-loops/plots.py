"""Matplotlib SVG plots from analysis.json / refusal.json / ablation.json (no model needed)."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.rcParams["svg.fonttype"] = "none"


def heatmaps(analysis, out, metric="val_score", core=(6, 18)):
    """One layer x pass heatmap per pass count N, shared colour scale."""
    ns = sorted(analysis["by_n"], key=int)
    grids = {}
    for n in ns:
        g = np.full((24, int(n)), np.nan)
        for v in analysis["by_n"][n]["visits"]:
            g[v["layer"], v["pass_number"] - 1] = v[metric]
        grids[n] = g
    vmax = np.nanmax([np.nanmax(g) for g in grids.values()])
    vmin = min(0, np.nanmin([np.nanmin(g) for g in grids.values()]))
    fig, axes = plt.subplots(1, len(ns), figsize=(2.6 * len(ns) + 1.2, 6), squeeze=False,
                             gridspec_kw=dict(width_ratios=[int(n) for n in ns]))
    for ax, n in zip(axes[0], ns):
        im = ax.imshow(grids[n], aspect="auto", vmin=vmin, vmax=vmax, cmap="viridis", origin="lower")
        ax.set_title(f"N = {n} passes")
        ax.set_xticks(range(int(n)))
        ax.set_xticklabels(range(1, int(n) + 1))
        ax.set_xlabel("loop pass")
        ax.axhline(core[0] - 0.5, color="w", lw=0.6)
        ax.axhline(core[1] - 0.5, color="w", lw=0.6)
    axes[0][0].set_ylabel("layer (0-based; core 6-17)")
    fig.colorbar(im, ax=axes[0].tolist(), label="validation separation (gap / pooled std)")
    fig.savefig(out, format="svg", bbox_inches="tight")
    plt.close(fig)


def refusal_vs_n(refusal, out):
    ns = sorted(refusal, key=int)
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for group, color in (("harmful", "#c0392b"), ("benign", "#2980b9")):
        xs, ys, lo, hi = [], [], [], []
        for n in ns:
            r = refusal[n][group]
            if r["refusal_rate"] is None:
                continue
            xs.append(int(n)); ys.append(r["refusal_rate"])
            lo.append(r["refusal_rate"] - r["wilson_95"][0]); hi.append(r["wilson_95"][1] - r["refusal_rate"])
        ax.errorbar(xs, ys, yerr=[lo, hi], marker="o", capsize=3, color=color, label=f"{group} (held-out)")
    ax.set_xlabel("loop passes N"); ax.set_ylabel("refusal rate (heuristic, 95% Wilson)")
    ax.set_ylim(0, 1); ax.set_xticks([int(n) for n in ns]); ax.legend()
    fig.savefig(out, format="svg", bbox_inches="tight")
    plt.close(fig)


def ablation_effect(ablation, out):
    """Refusal rate on held-out harmful prompts when the direction is removed at one pass."""
    ns = sorted(ablation, key=int)
    fig, axes = plt.subplots(1, len(ns), figsize=(5.5 * len(ns), 4), squeeze=False)
    for ax, n in zip(axes[0], ns):
        data = ablation[n]
        names = ["baseline"] + sorted(data["conditions"], key=lambda c: (c.startswith("p1dir"), c.startswith("random"), c == "all", c))
        rates, lo, hi = [], [], []
        for name in names:
            r = data["baseline"] if name == "baseline" else data["conditions"][name]
            if r is None or r["refusal_rate"] is None:
                rates.append(np.nan); lo.append(0); hi.append(0); continue
            rates.append(r["refusal_rate"]); lo.append(r["refusal_rate"] - r["wilson_95"][0])
            hi.append(r["wilson_95"][1] - r["refusal_rate"])
        colors = ["#7f8c8d" if nm == "baseline" else "#8e44ad" if nm.startswith(("random", "p1dir")) else "#27ae60" if nm == "all" else "#e67e22" for nm in names]
        ax.bar(range(len(names)), rates, yerr=[lo, hi], capsize=3, color=colors)
        ax.set_xticks(range(len(names))); ax.set_xticklabels(names, rotation=60, ha="right")
        ax.set_ylim(0, 1); ax.set_title(f"N = {n}: direction removed at one pass"); ax.set_ylabel("refusal rate, harmful")
    fig.savefig(out, format="svg", bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path, help="directory holding analysis/refusal/ablation json")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    out = a.out or a.results / "plots"
    out.mkdir(parents=True, exist_ok=True)
    load = lambda n: json.loads((a.results / n).read_text()) if (a.results / n).exists() else None
    if (an := load("analysis.json")) and an["by_n"]:
        heatmaps(an, out / "separation-heatmap.svg")
    if (rf := load("refusal.json")) and any(v["harmful"]["n"] for v in rf.values()):
        refusal_vs_n({k: v for k, v in rf.items() if v["harmful"]["n"]}, out / "refusal-vs-passes.svg")
    if ab := load("ablation.json"):
        ablation_effect(ab, out / "single-pass-ablation.svg")


if __name__ == "__main__":
    main()

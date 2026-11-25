"""Counts, paired bootstrap and spend for one pr-live run, from its saved traces.

    python summarize.py final            # or first-run
"""

import glob
import json
import sys
from pathlib import Path

import numpy as np

run = Path(__file__).parent / sys.argv[1]
RATES = (0.15, 0.50)  # list price per million prefill / sampled tokens


def load(test: str, arm: str) -> dict[str, dict]:
    path = glob.glob(str(run / "comparison" / f"{test}_tools-{arm}-*.jsonl"))[0]
    return {r["id"]: r for r in map(json.loads, Path(path).read_text().splitlines())}


def paired(a: dict, b: dict, key: str, need: bool) -> dict[str, float]:
    ids = [i for i, r in a.items() if bool(r["expected"]) == need]
    x = np.array([a[i]["scores"][key] for i in ids], float)
    y = np.array([b[i]["scores"][key] for i in ids], float)
    idx = np.random.default_rng(0).integers(0, len(ids), size=(10_000, len(ids)))
    d = 100 * (x[idx].mean(1) - y[idx].mean(1))
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"diff_pp": float(100 * (x.mean() - y.mean())), "lo": float(lo), "hi": float(hi), "n": len(ids)}


summary: dict = {}
for test in ("test", "blind_test"):
    arms = {a: load(test, a) for a in ("adapter", "native", "sheet")}
    summary[test] = {}
    for arm, rows in arms.items():
        total = lambda k: int(sum(r["scores"][k] for r in rows.values()))  # noqa: E731
        summary[test][arm] = {
            "episodes": len(rows), "tool_needed": total("tool_needed"), "no_tool_needed": total("no_tool_needed"),
            "first_command": total("first_command_correct"), "first_turn_malformed": total("first_turn_malformed"),
            "calls_well_formed": total("calls_well_formed"), "call_attempts": total("call_attempts"),
            "exact_sequence": total("exact_sequence"), "extra_calls": total("extra_calls"),
            "no_tool_correct": total("no_tool_correct"),
            "prompt_tokens": total("prompt_tokens"), "completion_tokens": total("completion_tokens"),
            "prompt_tokens_per_episode": total("prompt_tokens") / len(rows),
            "list_price_usd": (total("prompt_tokens") * RATES[0] + total("completion_tokens") * RATES[1]) / 1e6,
        }
    summary[test]["adapter_minus_native"] = {
        "first_command": paired(arms["adapter"], arms["native"], "first_command_correct", True),
        "no_tool_specificity": paired(arms["adapter"], arms["native"], "no_tool_correct", False),
    }
(run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({t: {a: (d["first_command"], d["no_tool_correct"], d["extra_calls"]) for a, d in v.items() if a != "adapter_minus_native"} for t, v in summary.items()}))

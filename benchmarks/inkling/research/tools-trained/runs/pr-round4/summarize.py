"""Rescore every saved trace with the shipped scoring code and print the README tables.

Old pr-live traces (adapter, native) are rescored offline: follow-up rows expect only their first
command, and turns that issued several calls count as ``parallel``. New traces already carry both.

    PYTHONPATH=<recipe checkout> python summarize.py
"""

import glob
import json
import re
from pathlib import Path

from tinker_cookbook.recipes.trained_tools.data import Task
from tinker_cookbook.recipes.trained_tools.eval import (
    Episode,
    first_command_scores,
    paired_bootstrap,
    summarize,
)

HERE = Path(__file__).parent
LIVE = HERE.parent / "pr-live"
FOLLOW_IDS = {"test-00037", "test-00147", "test-00204", "test-00298", "test-00360"}
RATES = (0.15, 0.50)


def episodes(path: str, fix_follow: bool) -> list[Episode]:
    out = []
    for line in Path(path).read_text().splitlines():
        r = json.loads(line)
        request = next(m["content"] for m in r["messages"] if m["role"] == "user")
        expected = r["expected"][:1] if fix_follow and r["id"] in FOLLOW_IDS else r["expected"]
        assistant = [m for m in r["messages"] if m["role"] == "assistant"]
        kinds = [
            "parallel" if k == "invalid" and len(a.get("tool_calls") or []) > 1 else k
            for k, a in zip(r["kinds"], assistant, strict=False)
        ]
        s = r["scores"]
        out.append(
            Episode(
                Task(r["id"], request, expected),
                r["arm"],
                r["commands"],
                kinds,
                int(s["call_attempts"]),
                int(s["prompt_tokens"]),
                int(s["completion_tokens"]),
                r["end"] == "answered",
                r["end"],
            )
        )
    return out


NAMES = re.compile(r"\b(web_search|image_search|image_gen|ask_model|read_url|calc|remember|recall)\b")


def intended_right(path: str) -> int:
    """Descriptive: first-turn malformed episodes whose visible text names the expected command first."""
    n = 0
    for line in Path(path).read_text().splitlines():
        r = json.loads(line)
        if r["kinds"][:1] != ["malformed"] or not r["expected"]:
            continue
        text = next(m["content"] for m in r["messages"] if m["role"] == "assistant")
        visible = text.split("<|end_message|>", 1)[-1]  # after the thinking block
        found = NAMES.search(visible)
        n += bool(found) and found.group(1) == r["expected"][0]
    return n


def find(folder: Path, test: str, arm: str) -> str:
    return glob.glob(str(folder / f"{test}_tools-{arm}-*.jsonl"))[0]


RUNS = {
    "generated": {
        "final": {
            "adapter": (LIVE / "final/comparison", "test", True),
            "native": (LIVE / "final/comparison", "test", True),
            "sheet": (HERE / "sheet-final", "tasks-final", False),
        },
        "first": {
            "adapter": (LIVE / "first-run/comparison", "test", True),
            "native": (LIVE / "first-run/comparison", "test", True),
            "sheet": (HERE / "sheet-first", "tasks-first-run", False),
        },
    },
    "blind v1.1": {
        "a": {a: (HERE / "blind-a", "blind_test", False) for a in ("adapter", "native", "sheet")},
        "b": {a: (HERE / "blind-b", "blind_test", False) for a in ("adapter", "native", "sheet")},
    },
}

if __name__ == "__main__":
    summary: dict = {}
    for test, runs in RUNS.items():
        summary[test] = {}
        for run, arms in runs.items():
            eps, paths = {}, {}
            for arm, (folder, stem, fix) in arms.items():
                try:
                    paths[arm] = find(folder, stem, arm)
                    eps[arm] = episodes(paths[arm], fix)
                except IndexError:
                    continue
            summary[test][run] = {}
            for arm, e in eps.items():
                m = summarize(e)
                n = len(e)
                tool = sum(bool(x.task.expected) for x in e)
                direct = n - tool
                usd = (m["prompt_tokens_per_episode"] * RATES[0] + m["completion_tokens_per_episode"] * RATES[1]) * n / 1e6
                summary[test][run][arm] = {
                    "first_malformed_intended_right": intended_right(paths[arm]),
                    "episodes": n, "tool_needed": tool, "no_tool_needed": direct,
                    "first_command": round(m["first_command_accuracy"] * tool),
                    "first_turn_malformed": int(m["first_turn_malformed"]),
                    "parsed_calls": int(m["parsed_calls"]), "call_attempts": int(m["call_attempts"]),
                    "invented_names": int(m["invented_names"]), "parallel_episodes": int(m["parallel_episodes"]),
                    "exact_sequence": round(m["exact_sequence_accuracy"] * tool),
                    "extra_calls": round(m["extra_calls_per_episode"] * n),
                    "no_tool_ok": round(m["no_tool_specificity"] * direct),
                    "prompt_tok_per_episode": round(m["prompt_tokens_per_episode"]),
                    "list_price_usd": round(usd, 4),
                }
            if {"adapter", "native"} <= set(eps):
                summary[test][run]["adapter_minus_native_first_command"] = paired_bootstrap(
                    first_command_scores(eps["adapter"]), first_command_scores(eps["native"])
                )
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=1))

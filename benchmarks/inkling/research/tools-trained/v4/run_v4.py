"""Dry run and sampling for the A2 evaluation (AMENDMENT-3).

    python run_v4.py --dry-run ...   # estimate only; no service client
    python run_v4.py ...             # refuses a dirty v3/ or v4/ folder or an estimate over budget
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v3"))
import tools_v3 as t  # noqa: E402
from tinker_cookbook.recipes.trained_tools.data import make_renderer  # noqa: E402
from tinker_cookbook.utils.cost_estimation import TokenCostRates, TokenUsage, fetch_model_pricing  # noqa: E402

ARMS = ("A", "A2", "B-native-1call", "C")
FALLBACK = TokenCostRates(0.15, 0.15, 0.50, 0.75)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()


def items_oot2(path: Path) -> list[t.Item]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    return [t.Item(r["id"], "+".join(r["commands"]) or "direct", r["request"], r["commands"], "oot2") for r in rows]


def sets(args: argparse.Namespace) -> dict[str, list[t.Item]]:
    return {
        "in": t.items_in_template(Path(args.test)),
        "t2": t.items_in_template(Path(args.data_dir) / "test.jsonl"),
        "oot1": t.items_ood(Path(args.oot1)),
        "oot2": items_oot2(Path(args.oot2)),
    }


def estimate(sets_: dict[str, list[t.Item]], rates: TokenCostRates) -> dict:
    renderer = make_renderer(t.MODEL_NAME)
    ceiling = expected = TokenUsage()
    per = {}
    for split, items in sets_.items():
        for arm in ARMS:
            prompt_arm = "A" if arm == "A2" else arm
            first = [renderer.build_generation_prompt(t.arm_messages(i.request, prompt_arm, renderer), effort=0.0).length for i in items]
            c = TokenUsage(sampled=len(items) * t.MAX_TURNS * 512, prefill_uncached=sum(min(t.MAX_PROMPT, f + 500 * k) for f in first for k in range(t.MAX_TURNS)))
            e = TokenUsage(sampled=int(len(items) * 2 * 130), prefill_uncached=int(sum(first) * 2 * 1.25))
            per[f"{split}/{arm}"] = {"episodes": len(items), "first_turn_mean": sum(first) / len(first), "ceiling_usd": rates.estimate_usd(c)}
            ceiling, expected = ceiling + c, expected + e
    return {"per_arm": per, "ceiling_usd": rates.estimate_usd(ceiling), "expected_usd": rates.estimate_usd(expected)}


async def sample_all(args, sets_, ckpt_a: str, ckpt_a2: str, out: Path) -> None:
    import tinker

    service = tinker.ServiceClient()
    a, a2, stock = await asyncio.gather(
        service.create_sampling_client_async(base_model=t.MODEL_NAME, model_path=ckpt_a),
        service.create_sampling_client_async(base_model=t.MODEL_NAME, model_path=ckpt_a2),
        service.create_sampling_client_async(base_model=t.MODEL_NAME),
    )
    clients = {"A": a, "A2": a2, "B-native-1call": stock, "C": stock}
    renderer = make_renderer(t.MODEL_NAME)
    sem = asyncio.Semaphore(args.concurrency)
    jobs = [(split, arm, [t.run_episode(i, "A" if arm == "A2" else arm, clients[arm], renderer, tinker, sem) for i in items])
            for split, items in sets_.items() for arm in ARMS]
    results = await asyncio.gather(*(asyncio.gather(*c) for _, _, c in jobs))
    for (split, arm, _), records in zip(jobs, results, strict=True):
        for r in records:
            r["arm"] = arm
            r["scores"] = t.score_record(r)
        path = out / f"{split}_{arm}.jsonl"
        path.write_text("".join(json.dumps(r, default=lambda x: x.model_dump()) + "\n" for r in records))
        print(f"wrote {path.name}: {len(records)}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True)
    ap.add_argument("--oot1", required=True)
    ap.add_argument("--oot2", required=True)
    ap.add_argument("--ckpt-v1", required=True, help="runs/main/checkpoints.jsonl")
    ap.add_argument("--ckpt-a2", required=True, help="runs/v4/train/checkpoints.jsonl")
    ap.add_argument("--data-dir", required=True, help="v4/data")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--budget", type=float, default=3.0)
    ap.add_argument("--concurrency", type=int, default=256)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sets_ = sets(args)
    rates = fetch_model_pricing(t.MODEL_NAME) or FALLBACK
    est = estimate(sets_, rates)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / ("preflight.json" if args.dry_run else "run-config.json")).write_text(json.dumps({"arms": ARMS, "rates": rates.__dict__, "budget_usd": args.budget, **est}, indent=2) + "\n")
    print(json.dumps({k: est[k] for k in ("ceiling_usd", "expected_usd")}))
    # The ceiling takes every episode to four 512-token turns; the gate uses twice the expected cost.
    if est["expected_usd"] * 2 > args.budget:
        sys.exit("twice the expected cost is above budget")
    if args.dry_run:
        return
    dirty = git("status", "--porcelain", "--", str(HERE), str(HERE.parent / "v3"))
    if dirty:
        sys.exit("v3/ or v4/ has uncommitted changes; commit before sampling")
    last = lambda p: json.loads(Path(p).read_text().splitlines()[-1])["sampler_path"]  # noqa: E731
    ckpt_a, ckpt_a2 = last(args.ckpt_v1), last(args.ckpt_a2)
    data = Path(args.data_dir)
    prov = {
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "research_repo_head": git("rev-parse", "HEAD"),
        "v3_v4_files_sha256": {f"{d.name}/{p.name}": sha(p) for d in (HERE.parent / "v3", HERE) for p in sorted(d.glob("*.py"))},
        "recipe_snapshot_commit": (Path(args.snapshot) / "COMMIT").read_text().strip(),
        "data_sha256": {n: sha(data / n) for n in ("train.jsonl", "valid.jsonl", "plan.jsonl", "answers.jsonl")},
        "test_sha256": {"in_template_v1": sha(Path(args.test)), "t2": sha(data / "test.jsonl"), "oot1": sha(Path(args.oot1)), "oot2": sha(Path(args.oot2))},
        "checkpoint_sha256": {"A": hashlib.sha256(ckpt_a.encode()).hexdigest(), "A2": hashlib.sha256(ckpt_a2.encode()).hexdigest()},
        "package_versions": {n: importlib.metadata.version(n) for n in ("tinker", "tml-renderers")},
    }
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    asyncio.run(sample_all(args, sets_, ckpt_a, ckpt_a2, out))
    (out / "finished.json").write_text(json.dumps({"finished_utc": datetime.now(UTC).isoformat(timespec="seconds")}) + "\n")


if __name__ == "__main__":
    main()

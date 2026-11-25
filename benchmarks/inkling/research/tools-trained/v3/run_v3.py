"""Dry-run cost estimate and sampling for the v3 evaluation.

    python run_v3.py --dry-run ...     # no service client, no key; writes preflight.json
    python run_v3.py ...               # samples; refuses a dirty v3 folder or an estimate over budget

The API key is read from the environment by the tinker client and is never printed or stored.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import tools_v3 as t
from tinker_cookbook.recipes.trained_tools.data import make_renderer
from tinker_cookbook.utils.cost_estimation import TokenCostRates, TokenUsage, fetch_model_pricing

HERE = Path(__file__).resolve().parent
FALLBACK_RATES = TokenCostRates(0.15, 0.15, 0.50, 0.75)  # per-million rates used in v2
V2_TURNS_PER_EPISODE = 2.0  # observed in v2 for the stock arms
V2_COMPLETION_PER_TURN = 130  # observed in v2, rounded up


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str, cwd: Path = HERE) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


FOLLOWUP = False


def plan(in_items: list[t.Item], ood_items: list[t.Item]) -> list[tuple[str, list[t.Item], str]]:
    if FOLLOWUP:
        return [(arm, items, split) for arm in t.ARMS_FOLLOWUP
                for items, split in ((in_items, "in"), (ood_items, "ood"))]
    return [(arm, in_items, "in") for arm in t.ARMS_IN] + [
        (arm, ood_items, "ood") for arm in t.ARMS_OOD
    ]


def estimate(
    in_items: list[t.Item], ood_items: list[t.Item], rates: TokenCostRates
) -> dict[str, object]:
    renderer = make_renderer(t.MODEL_NAME)
    per_arm: dict[str, dict[str, float]] = {}
    ceiling = TokenUsage()
    expected = TokenUsage()
    for arm, items, split in plan(in_items, ood_items):
        first = [
            renderer.build_generation_prompt(t.arm_messages(i.request, arm, renderer), effort=0.0).length
            for i in items
        ]
        prefill_ceiling = sum(
            min(t.MAX_PROMPT, f + 500 * k) for f in first for k in range(t.MAX_TURNS)
        )
        sampled_ceiling = len(items) * t.MAX_TURNS * 512
        prefill_expected = int(sum(first) * V2_TURNS_PER_EPISODE * 1.25)
        sampled_expected = int(len(items) * V2_TURNS_PER_EPISODE * V2_COMPLETION_PER_TURN)
        per_arm[f"{split}/{arm}"] = {
            "episodes": len(items),
            "first_turn_tokens_mean": sum(first) / len(first),
            "ceiling_usd": rates.estimate_usd(
                TokenUsage(sampled=sampled_ceiling, prefill_uncached=prefill_ceiling)
            ),
        }
        ceiling += TokenUsage(sampled=sampled_ceiling, prefill_uncached=prefill_ceiling)
        expected += TokenUsage(sampled=sampled_expected, prefill_uncached=prefill_expected)
    return {
        "per_arm": per_arm,
        "ceiling_usd": rates.estimate_usd(ceiling),
        "expected_usd": rates.estimate_usd(expected),
        "ceiling_tokens": ceiling.__dict__,
        "expected_tokens": expected.__dict__,
    }


def provenance(args: argparse.Namespace, checkpoint: str) -> dict[str, object]:
    import tinker_cookbook

    status = git("status", "--porcelain", "--", str(HERE))
    return {
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "research_repo_head": git("rev-parse", "HEAD"),
        "v3_folder_dirty": bool(status),
        "v3_files_sha256": {p.name: sha256(p) for p in sorted(HERE.glob("*.py"))},
        "recipe_snapshot_commit": (Path(args.snapshot) / "COMMIT").read_text().strip(),
        "recipe_imported_from": str(Path(tinker_cookbook.__file__).parent.parent),
        "ood_sha256": sha256(Path(args.ood)),
        "in_template_test_sha256": sha256(Path(args.test)),
        "checkpoint_sha256": hashlib.sha256(checkpoint.encode()).hexdigest(),
        "package_versions": {
            name: importlib.metadata.version(name) for name in ("tinker", "tml-renderers")
        },
        "python": platform.python_version(),
    }


async def sample_all(args: argparse.Namespace, in_items, ood_items, checkpoint: str, out: Path):
    import tinker

    service = tinker.ServiceClient()
    trained, stock = await asyncio.gather(
        service.create_sampling_client_async(base_model=t.MODEL_NAME, model_path=checkpoint),
        service.create_sampling_client_async(base_model=t.MODEL_NAME),
    )
    renderer = make_renderer(t.MODEL_NAME)
    sem = asyncio.Semaphore(args.concurrency)
    jobs = []
    for arm, items, split in plan(in_items, ood_items):
        client = trained if arm == "A" else stock
        jobs.append((arm, split, [t.run_episode(i, arm, client, renderer, tinker, sem) for i in items]))
    results = await asyncio.gather(*(asyncio.gather(*coros) for _, _, coros in jobs))
    for (arm, split, _), records in zip(jobs, results, strict=True):
        for r in records:
            r["scores"] = t.score_record(r)
        path = out / f"{split}_{arm}.jsonl"
        path.write_text("".join(json.dumps(r, default=lambda x: x.model_dump()) + "\n" for r in records))
        print(f"wrote {path.name}: {len(records)} episodes", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True, help="in-template test.jsonl")
    ap.add_argument("--ood", required=True, help="v3/data/ood.jsonl")
    ap.add_argument("--checkpoints", required=True, help="runs/main/checkpoints.jsonl")
    ap.add_argument("--snapshot", required=True, help="frozen recipe checkout (has a COMMIT file)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--budget", type=float, default=5.0)
    ap.add_argument("--concurrency", type=int, default=256)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--followup", action="store_true", help="run the addendum arm only")
    args = ap.parse_args()
    global FOLLOWUP
    FOLLOWUP = args.followup

    in_items = t.items_in_template(Path(args.test))
    ood_items = t.items_ood(Path(args.ood))
    rates = fetch_model_pricing(t.MODEL_NAME)
    pricing = "tinker models.json via cost_estimation.fetch_model_pricing"
    if rates is None:
        rates, pricing = FALLBACK_RATES, "fallback: the per-million rates used in v2 ($0.15 prefill, $0.50 sample)"
    est = estimate(in_items, ood_items, rates)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    record = {"followup": FOLLOWUP, "arms": sorted({p[0] for p in plan(in_items, ood_items)}), "rates": rates.__dict__,
              "pricing_source": pricing, "budget_usd": args.budget, **est}
    (out / ("preflight.json" if args.dry_run else "run-config.json")).write_text(
        json.dumps(record, indent=2) + "\n"
    )
    print(json.dumps({k: record[k] for k in ("ceiling_usd", "expected_usd", "pricing_source")}, indent=2))
    if est["ceiling_usd"] > args.budget:  # type: ignore[operator]
        sys.exit(f"estimated ceiling ${est['ceiling_usd']:.2f} exceeds budget ${args.budget:.2f}")
    if args.dry_run:
        return
    prov = provenance(args, "")
    if prov["v3_folder_dirty"]:
        sys.exit("v3 folder has uncommitted changes; commit before sampling")
    checkpoint = json.loads(Path(args.checkpoints).read_text().splitlines()[-1])["sampler_path"]
    prov = provenance(args, checkpoint)
    (out / "provenance.json").write_text(json.dumps(prov, indent=2) + "\n")
    asyncio.run(sample_all(args, in_items, ood_items, checkpoint, out))
    (out / "finished.json").write_text(
        json.dumps({"finished_utc": datetime.now(UTC).isoformat(timespec="seconds")}) + "\n"
    )


if __name__ == "__main__":
    main()

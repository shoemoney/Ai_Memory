"""Offline tests for the v2 data (AMENDMENT-3). Run from the recipe snapshot directory:

    cd <snapshot> && PYTHONPATH=<snapshot>:<v4>:<v3> python -m pytest -q <v4>/test_v4.py
"""

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "v3"))
import ood  # noqa: E402
import overlap  # noqa: E402

from tools_v3 import command_name  # noqa: E402
from tinker_cookbook.recipes.trained_tools.commands import TOOLS  # noqa: E402
from tinker_cookbook.recipes.trained_tools.data import load_samples  # noqa: E402

DATA = HERE / "data"


@pytest.fixture(scope="module")
def rows() -> dict[str, list[dict]]:
    return {s: [json.loads(line) for line in (DATA / f"{s}.jsonl").read_text().splitlines()] for s in ("train", "valid", "test")}


def test_files_load_with_the_recipe_validator():
    for split in ("train", "valid", "test"):
        samples = load_samples(DATA / f"{split}.jsonl")
        assert len(samples) == {"train": 4000, "valid": 400, "test": 400}[split]
    manifest = json.loads((DATA / "manifest.json").read_text())
    import hashlib

    for name, digest in manifest["files"].items():
        assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == digest


def test_composition_and_executions(rows):
    train = rows["train"]
    names = {command_name(c) for r in train for c in r["commands"]}
    assert names == set(TOOLS)
    assert 0.36 < sum(not r["commands"] for r in train) / len(train) < 0.46
    assert len({r["messages"][1]["content"] for r in train}) == len(train)
    assert len({r["phrase_family"] for r in train}) > 150  # many independent shapes
    train_valid = {r["messages"][1]["content"] for r in train + rows["valid"]}
    assert not train_valid & {r["messages"][1]["content"] for r in rows["test"]}
    assert not {r["messages"][1]["content"] for r in train} & {r["messages"][1]["content"] for r in rows["valid"]}


def test_near_miss_pairs_exist(rows):
    train = rows["train"]
    small = [r for r in train if r["skill"] == "direct:arith"]
    big = [r for r in train if r["skill"] == "calc" and r["commands"]]
    assert small and big and all(not r["commands"] for r in small)
    concept = [r for r in train if r["skill"] == "direct:concept"]
    assert concept and all(not r["commands"] for r in concept)


def test_zero_overlap_with_oot1_development_set(rows):
    train_requests = [r["messages"][1]["content"] for r in rows["train"] + rows["valid"] + rows["test"]]
    oot1 = ood.build()
    result = overlap.report(train_requests, [r["request"] for r in oot1], [r["template"] for r in oot1])
    assert not result["frame_3gram_hits"], result["frame_3gram_hits"][:5]
    assert not result["near_duplicates"], result["near_duplicates"][:5]


def test_zero_overlap_with_oot2_blind_set(rows):
    path = HERE.parent.parent / "tools-blind" / "oot2.jsonl"
    oot2 = [json.loads(line)["request"] for line in path.read_text().splitlines()]
    assert len(oot2) == 120
    train_requests = [r["messages"][1]["content"] for r in rows["train"] + rows["valid"] + rows["test"]]
    result = overlap.report(train_requests, oot2)
    assert not result["frame_3gram_hits"], result["frame_3gram_hits"][:5]
    assert not result["near_duplicates"], result["near_duplicates"][:5]


def test_report_helpers_and_oot2_loader():
    import report_v4
    import run_v4

    lo, hi = report_v4.wilson(7, 30)
    assert 0.11 < lo < 0.13 and 0.40 < hi < 0.42  # known interval for 7/30
    assert report_v4.wilson(0, 0) == (0.0, 0.0)
    rows = [{"commands": ["translate 'x'", "calc 1+1", "web_search q"]}, {"commands": ["synonym a"]}]
    assert dict(report_v4.invented(rows)) == {"translate": 1, "synonym": 1}
    items = run_v4.items_oot2(HERE.parent.parent / "tools-blind" / "oot2.jsonl")
    assert len(items) == 120 and sum(bool(i.expected) for i in items) == 80
    assert all(i.split == "oot2" for i in items)

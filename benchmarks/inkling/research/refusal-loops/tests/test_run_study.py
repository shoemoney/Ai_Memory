import argparse
import json

import numpy as np

import run_study


def fake_acts(path, n, seed=0):
    rng = np.random.default_rng(seed)
    layers = [0] * 1 + [l for p in range(n) for l in range(6, 18)] + [20]
    passes = [1] + [p for p in range(1, n + 1) for _ in range(12)] + [1]
    labels = np.array([1, 0] * 10)
    splits = np.repeat(np.array(["train", "validation", "eval"]), [12, 4, 4])
    acts = rng.standard_normal((20, len(layers), 8))
    acts[labels == 1, :, 0] += 3
    np.savez(path, activations=acts, labels=labels, splits=splits, layers=np.array(layers),
             passes=np.array(passes))


def test_ablation_conditions_and_report(tmp_path):
    fake_acts(tmp_path / "acts-N3.npz", 3)
    args = argparse.Namespace(out=tmp_path, passes=[3], ablate_passes=[3], ablate_mode="per_layer",
                              seed=1, model="m", n=10)
    d = run_study.load_acts(args, 3)
    conds = run_study.ablation_conditions(args, 3, d)
    assert set(conds) == {"pass1", "pass2", "pass3", "p1dir_at_pass2", "p1dir_at_pass3", "all", "random_all",
                          "all_layers", "all_layers_single", "random_all_layers"}
    assert {k[1] for k in conds["pass2"]} == {2} and len(conds["pass2"]) == 12
    assert len(conds["all"]) == 36
    assert len(conds["all_layers"]) == 38 and {k[0] for k in conds["all_layers"]} >= {0, 20}
    assert len({tuple(v) for v in conds["all_layers_single"].values()}) == 1
    assert len({tuple(v) for v in conds["random_all_layers"].values()}) == 14
    assert all(abs(np.linalg.norm(v) - 1) < 1e-9 for v in conds["all"].values())
    args.ablate_mode = "single"
    single = run_study.ablation_conditions(args, 3, d)["all"]
    assert len({tuple(v) for v in single.values()}) == 1
    gen = tmp_path / "gen"
    gen.mkdir()
    for name, labels in (("refusal-N3-harmful", ["refused"] * 3 + ["complied"]),
                         ("refusal-N3-benign", ["complied"] * 4), ("ablate-N3-pass2", ["complied"] * 4)):
        (gen / f"{name}.jsonl").write_text("".join(json.dumps(dict(id=str(i), label=l)) + "\n" for i, l in enumerate(labels)))
    run_study.report(args, [])
    ab = json.loads((tmp_path / "ablation.json").read_text())
    assert ab["3"]["baseline"]["refusal_rate"] == 0.75
    assert ab["3"]["conditions"]["pass2"]["refusal_rate"] == 0
    an = json.loads((tmp_path / "analysis.json").read_text())
    assert 6 <= an["by_n"]["3"]["best_core_visit"]["layer"] < 18

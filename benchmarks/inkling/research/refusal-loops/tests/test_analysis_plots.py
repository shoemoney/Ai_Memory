import json

import numpy as np

import analysis
import plots


def synthetic(visits=6, hidden=8, seed=1):
    rng = np.random.default_rng(seed)
    splits = np.repeat(np.array(["train", "validation", "eval"]), [12, 4, 4])
    labels = np.array([1, 0] * 10)
    acts = rng.standard_normal((len(labels), visits, hidden))
    acts[labels == 1, :, 0] += 4.0
    return acts, labels, splits


def test_direction_recovers_planted_axis_and_cosine():
    acts, labels, splits = synthetic()
    dirs, val, ev = analysis.per_visit_directions(acts, labels, splits)
    assert all(d[0] > 0.8 for d in dirs)
    assert all(v["score"] > 2 for v in val)
    layers, passes = [6, 7, 6, 7, 6, 7], [1, 1, 2, 2, 3, 3]
    pc = analysis.pass_cosines(dirs, layers, passes)
    assert pc[6]["passes"] == [1, 2, 3] and abs(pc[6]["matrix"][0][0] - 1) < 1e-9
    assert pc[6]["matrix"][0][1] > 0.6
    cn = analysis.cross_n_cosines({1: dirs[:2], 3: dirs}, {1: [(6, 1), (7, 1)], 3: list(zip(layers, passes))})
    assert set(cn["1v3"]) == {"6:1", "7:1"}


def test_plots_write_svgs(tmp_path):
    acts, labels, splits = synthetic()
    dirs, val, ev = analysis.per_visit_directions(acts, labels, splits)
    layers = [6, 7, 6, 7, 6, 7]
    passes = [1, 1, 2, 2, 3, 3]
    table, best = analysis.summarize(dirs, layers, passes, val, ev)
    an = {"by_n": {"3": dict(visits=table), "1": dict(visits=table[:2])}}
    r = dict(n=12, refused=6, partial=0, complied=6, refusal_rate=0.5, wilson_95=[0.25, 0.75])
    rf = {"1": dict(harmful=r, benign=r), "3": dict(harmful=r, benign=r)}
    ab = {"3": dict(baseline=r, conditions={"pass1": r, "pass2": r, "all": r, "random_all": r, "p1dir_at_pass2": r})}
    (tmp_path / "analysis.json").write_text(json.dumps(an))
    (tmp_path / "refusal.json").write_text(json.dumps(rf))
    (tmp_path / "ablation.json").write_text(json.dumps(ab))
    import sys
    sys.argv = ["plots", str(tmp_path)]
    plots.main()
    for name in ("separation-heatmap", "refusal-vs-passes", "single-pass-ablation"):
        assert (tmp_path / "plots" / f"{name}.svg").read_text().startswith("<?xml")

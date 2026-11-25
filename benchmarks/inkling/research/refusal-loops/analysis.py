"""Pure numpy analysis of per-(layer, pass) activations; no model needed."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from direction.direction import separation, unit_direction


def split_arrays(acts, labels, splits):
    def get(split, label):
        return acts[(splits == split) & (labels == label)]
    return get


def per_visit_directions(acts, labels, splits):
    """Train-only difference-of-means direction for each visit, plus validation/eval separation."""
    get = split_arrays(acts, labels, splits)
    x = np.asarray(acts, dtype=np.float64)
    dirs, val, ev = [], [], []
    for j in range(x.shape[1]):
        r = unit_direction(get("train", 1)[:, j].astype(np.float64), get("train", 0)[:, j].astype(np.float64))
        dirs.append(r)
        val.append(separation(get("validation", 1)[:, j], get("validation", 0)[:, j], r))
        ev.append(separation(get("eval", 1)[:, j], get("eval", 0)[:, j], r))
    return np.stack(dirs), val, ev


def cosine(a, b):
    return float(a @ b / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-12))


def separation_grid(layers, passes, scores, n_layers=24, max_pass=5):
    """Fill a [layer, pass] grid (NaN where the layer has no such pass)."""
    grid = np.full((n_layers, max_pass), np.nan)
    for layer, p, s in zip(layers, passes, scores):
        grid[int(layer), int(p) - 1] = s
    return grid


def pass_cosines(dirs, layers, passes):
    """For each core layer, the cosine matrix of its direction across the passes it has."""
    out = {}
    for layer in sorted(set(int(l) for l in layers)):
        idx = [j for j, l in enumerate(layers) if int(l) == layer]
        if len(idx) < 2:
            continue
        ps = [int(passes[j]) for j in idx]
        out[layer] = dict(passes=ps, matrix=[[cosine(dirs[a], dirs[b]) for b in idx] for a in idx])
    return out


def cross_n_cosines(dirs_by_n, keys_by_n):
    """Cosine of the direction at the same (layer, pass) between every pair of pass counts."""
    out = {}
    ns = sorted(dirs_by_n)
    for a in ns:
        for b in ns:
            if a >= b:
                continue
            ia = {k: j for j, k in enumerate(keys_by_n[a])}
            ib = {k: j for j, k in enumerate(keys_by_n[b])}
            out[f"{a}v{b}"] = {f"{k[0]}:{k[1]}": cosine(dirs_by_n[a][ia[k]], dirs_by_n[b][ib[k]])
                               for k in ia if k in ib}
    return out


def summarize(dirs, layers, passes, val, ev, core=(6, 18)):
    """Per-visit table plus best validation visit among core layers."""
    rows = [dict(layer=int(l), pass_number=int(p), val_score=v["score"], val_auc=v["auc"],
                 eval_score=e["score"], eval_auc=e["auc"])
            for l, p, v, e in zip(layers, passes, val, ev)]
    best = max((r for r in rows if core[0] <= r["layer"] < core[1]), key=lambda r: r["val_score"])
    return rows, best

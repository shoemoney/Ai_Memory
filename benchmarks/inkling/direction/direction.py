"""Fit train-only directions and select a layer/pass on validation separation."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def unit_direction(harmful, harmless):
    delta = np.mean(harmful, axis=0, dtype=np.float64) - np.mean(harmless, axis=0, dtype=np.float64)
    norm = np.linalg.norm(delta)
    if not np.isfinite(norm) or norm < 1e-12:
        raise ValueError("Degenerate or nonfinite difference of means")
    return delta / norm


def separation(harmful, harmless, direction):
    a, b = harmful @ direction, harmless @ direction
    gap = float(a.mean() - b.mean())
    # Population variance permits a single held-out item per class on tiny tests.
    std = float(np.sqrt((a.var() + b.var()) / 2))
    auc = float(((a[:, None] > b).sum() + 0.5 * (a[:, None] == b).sum()) / (len(a) * len(b)))
    return dict(score=gap / max(std, 1e-8), mean_gap=gap, pooled_std=std, auc=auc)


def fit(activations, labels, splits, layers, passes, layer_range=None):
    x = np.asarray(activations, dtype=np.float64)
    labels, splits = np.asarray(labels), np.asarray(splits)
    if x.ndim != 3 or len(labels) != len(x) or len(splits) != len(x):
        raise ValueError("Expected activations [prompts, visits, hidden_size]")
    if len(layers) != x.shape[1] or len(passes) != x.shape[1] or not np.isfinite(x).all():
        raise ValueError("Invalid visit metadata or nonfinite activations")
    if set(labels) != {0, 1} or set(splits) != {"train", "validation", "eval"}:
        raise ValueError("Expected two labels and train/validation/eval splits")
    for split in ("train", "validation", "eval"):
        for label in (0, 1):
            if not np.any((labels == label) & (splits == split)):
                raise ValueError(f"Missing class {label} in {split}")
    def subset(split, label, visit):
        return x[(splits == split) & (labels == label), visit]
    directions, candidates = [], []
    for j, (layer, loop_pass) in enumerate(zip(layers, passes)):
        try:
            r = unit_direction(subset("train", 1, j), subset("train", 0, j))
        except ValueError:
            directions.append(np.zeros(x.shape[-1]))
            candidates.append(dict(layer=int(layer), pass_number=int(loop_pass), valid=False))
            continue
        directions.append(r)
        candidates.append(dict(layer=int(layer), pass_number=int(loop_pass), valid=True,
                               validation=separation(subset("validation", 1, j), subset("validation", 0, j), r)))
    valid = [j for j, c in enumerate(candidates) if c["valid"]
             and (layer_range is None or layer_range[0] <= c["layer"] <= layer_range[1])]
    if not valid:
        raise ValueError("No nondegenerate training directions")
    best = max(valid, key=lambda j: candidates[j]["validation"]["score"])
    # Eval is measured only for the fixed winner, never for candidate ranking.
    report = dict(candidates=candidates, selected_index=best,
                  layer_range=layer_range,
                  selection_metric="signed validation mean gap / pooled population std",
                  selected=candidates[best],
                  selected_eval=separation(subset("eval", 1, best), subset("eval", 0, best), directions[best]),
                  counts={s: {str(l): int(np.sum((splits == s) & (labels == l))) for l in (0, 1)}
                          for s in ("train", "validation", "eval")})
    return np.stack(directions), best, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("activations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--layer-range", help="Inclusive zero-based LO-HI; restricts selection only, e.g. 6-17 for the loop core")
    args = parser.parse_args()
    layer_range = tuple(int(x) for x in args.layer_range.split("-")) if args.layer_range else None
    with np.load(args.activations, allow_pickle=False) as data:
        directions, best, report = fit(data["activations"], data["labels"], data["splits"], data["layers"], data["passes"], layer_range)
        provenance = dict(activation_sha256=hashlib.sha256(args.activations.read_bytes()).hexdigest(),
                          collection=json.loads(str(data["metadata"])))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        np.savez(args.output, directions=directions.astype(np.float32),
                 direction=directions[best].astype(np.float32),
                 layers=data["layers"], passes=data["passes"], selected_index=best,
                 selected_layer=data["layers"][best], selected_pass=data["passes"][best],
                 metadata=json.dumps(provenance))
    report["provenance"] = provenance
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report["selected"], indent=2))


if __name__ == "__main__":
    main()

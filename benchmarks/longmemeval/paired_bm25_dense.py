"""Paired BM25 versus dense comparison on the 300 sampled questions.

Reads results/full/items/*.json, prints the discordant counts, the exact
McNemar p value and a bootstrap interval for the accuracy difference, and
writes results/full/paired-bm25-dense.json.
"""
import glob
import json
import math
import pathlib
import random

ROOT = pathlib.Path(__file__).parent / "results" / "full"


def main():
    scores = {}
    for path in glob.glob(str(ROOT / "items" / "*.json")):
        item = json.load(open(path))
        if "correct" in item:
            scores.setdefault(item["method"], {})[item["question_id"]] = bool(item["correct"])
    bm25, dense = scores["bm25-standard"], scores["dense-standard"]
    ids = sorted(set(bm25) & set(dense))
    a = sum(bm25[i] and not dense[i] for i in ids)
    b = sum(dense[i] and not bm25[i] for i in ids)
    n = a + b
    p = min(1.0, 2 * sum(math.comb(n, x) for x in range(min(a, b) + 1)) / 2 ** n)
    rng = random.Random(1)
    diffs = sorted(sum(bm25[i] - dense[i] for i in (rng.choice(ids) for _ in ids)) / len(ids) for _ in range(10000))
    out = {"n": len(ids), "bm25_only": a, "dense_only": b, "exact_p": round(p, 4),
           "difference_points": round(100 * (a - b) / len(ids), 1),
           "bootstrap95": [round(100 * diffs[250], 1), round(100 * diffs[9750], 1)]}
    (ROOT / "paired-bm25-dense.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()

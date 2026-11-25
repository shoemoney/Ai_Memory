"""Matched comparison for the systems that completed four conversations.

Reads results/full/items/<backend>/*.json and prints, for every backend except
Cognee, the score on the question IDs all of them completed, with Wilson
intervals and exact paired (McNemar) tests against Graphiti.
Writes results/full/four-system-matched.json.
"""
import collections
import glob
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).parent / "results" / "full"


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


def main():
    scores = collections.defaultdict(dict)
    for path in glob.glob(str(ROOT / "items" / "*" / "*.json")):
        item = json.load(open(path))
        if item.get("complete") and item.get("correct") is not None:
            scores[item["backend"]][item["item_id"]] = bool(item["correct"])
    systems = sorted(k for k in scores if k != "cognee")
    ids = sorted(set.intersection(*[set(scores[k]) for k in systems]))
    out = {"n": len(ids), "conversations": sorted({i[:3] for i in ids}), "systems": {}, "paired_vs_graphiti": {}}
    for k in systems:
        correct = sum(scores[k][i] for i in ids)
        out["systems"][k] = {"correct": correct, "accuracy": round(100 * correct / len(ids), 1), "wilson95": wilson(correct, len(ids))}
    for k in systems:
        if k == "graphiti":
            continue
        a = sum(scores[k][i] and not scores["graphiti"][i] for i in ids)
        b = sum(scores["graphiti"][i] and not scores[k][i] for i in ids)
        n = a + b
        p = min(1.0, 2 * sum(math.comb(n, x) for x in range(min(a, b) + 1)) / 2 ** n)
        out["paired_vs_graphiti"][k] = {"only_this": a, "only_graphiti": b, "exact_p": round(p, 4)}
    (ROOT / "four-system-matched.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

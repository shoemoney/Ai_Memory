"""Paired comparison of the empty-playbook baseline and the ACE playbook on the same test items."""
import json, sys, os, glob, random
from math import comb

def per_item(path, n):
    d = json.load(open(path))
    wrong = {e["index"] for e in d["error_log"]["errors"]}
    t = d["test_results"]
    assert t["total"] == n, (path, t["total"])
    return [0 if i in wrong else 1 for i in range(n)], t

def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)

def main(run_root, out):
    run = sorted(glob.glob(os.path.join(run_root, "ace_run_*")))[-1]
    n = 200
    base, tb = per_item(os.path.join(run, "initial_test_results.json"), n)
    ace, ta = per_item(os.path.join(run, "final_test_results.json"), n)
    b = sum(1 for x, y in zip(base, ace) if x == 1 and y == 0)
    c = sum(1 for x, y in zip(base, ace) if x == 0 and y == 1)
    diffs = [y - x for x, y in zip(base, ace)]
    rng = random.Random(11)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(10000))
    def wilson(k, m, z=1.96):
        p = k / m; den = 1 + z * z / m
        ctr = (p + z * z / (2 * m)) / den; h = z * ((p * (1 - p) / m + z * z / (4 * m * m)) ** .5) / den
        return ctr - h, ctr + h
    tr = json.load(open(os.path.join(run, "train_results.json")))
    res = {"n_items": n,
           "baseline": {"correct": sum(base), "acc": sum(base) / n, "wilson95": wilson(sum(base), n)},
           "ace": {"correct": sum(ace), "acc": sum(ace) / n, "wilson95": wilson(sum(ace), n)},
           "paired_diff_points": 100 * sum(diffs) / n,
           "paired_diff_bootstrap95_points": [100 * means[250], 100 * means[9749]],
           "gains": c, "losses": b, "mcnemar_exact_p": mcnemar_exact(b, c),
           "best_validation_accuracy": tr.get("best_accuracy"),
           "validation_checkpoints": [{"step": r["step"], "val_acc": r["val_result"].get("accuracy"),
                                       "playbook_tokens": r["playbook_num_tokens"]} for r in tr["results"]],
           "no_answer_baseline": tb.get("no_answer"), "no_answer_ace": ta.get("no_answer")}
    os.makedirs(out, exist_ok=True)
    json.dump(res, open(os.path.join(out, "summary.json"), "w"), indent=1)
    with open(os.path.join(out, "items.jsonl"), "w") as f:
        for i in range(n):
            f.write(json.dumps({"test_index": i, "baseline_correct": base[i], "ace_correct": ace[i]}) + "\n")
    for name in ("best_playbook.txt", "final_playbook.txt"):
        p = os.path.join(run, name)
        if os.path.exists(p):
            open(os.path.join(out, name), "w").write(open(p).read())
    print(json.dumps(res, indent=1))

if __name__ == "__main__":
    main(*sys.argv[1:3])

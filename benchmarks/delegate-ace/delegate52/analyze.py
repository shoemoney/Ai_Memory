"""Score the relay runs: corruption by step and at the end of the chain, bootstrap over environments.

Corruption = 1 - reconstruction score of the document recovered after the backward edit of
round trip k (interaction 2k) against the original seed, using the official domain evaluators.
A step with no score (the model dropped a required file, or the format check failed) counts as
corruption 1.0 (document lost); the sensitivity table drops such steps instead.
"""
import json, glob, sys, os, random, collections, statistics

def load(raw):
    chains = {}
    for fp in sorted(glob.glob(os.path.join(raw, "results_*.jsonl"))):
        for line in open(fp):
            r = json.loads(line)
            chains.setdefault((r["sample_id"], r["rid_chain"][0]), []).append(r)
    return chains

def boot(vals, n=10000, seed=7):
    rng = random.Random(seed)
    k = len(vals)
    means = sorted(sum(vals[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]

def main(raw, selected, out):
    sel = json.load(open(selected))["environments"]
    want = {e["sample_id"]: e["domain"] for e in sel}
    chains = load(raw)
    per_env, steps_rows, rows = {}, [], []
    for (sid, rid), recs in chains.items():
        if sid not in want:
            continue
        recs.sort(key=lambda r: len(r["rid_chain"]))
        rts = max(r["round_trip_num"] for r in recs)
        if len(recs) < 4 or rts < 2 or len(recs) != 2 * rts:
            continue
        per_env[sid] = recs
    n_planned = len(want)
    steps = sorted({r["round_trip_num"] for recs in per_env.values() for r in recs})
    result = {"environments_planned": n_planned, "environments_complete": len(per_env),
              "incomplete": sorted(set(want) - set(per_env)), "steps": {}, "rows": []}
    maxrt = max(steps) if steps else 0
    by_step = collections.defaultdict(dict)
    sens = collections.defaultdict(dict)
    stats = collections.defaultdict(list)
    for sid, recs in per_env.items():
        for r in recs:
            stats["latency"].append(r["llm_latency"] or 0)
            stats["completion_tokens"].append(r["completion_tokens"] or 0)
            stats["prompt_tokens"].append(r["prompt_tokens"] or 0)
            ev = r["evaluation"]
            stats["errors"].append(1 if (r["round_trip_direction"] == "backward" and "score" not in ev) else 0)
            stats["truncated"].append(1 if (r["completion_tokens"] or 0) >= 6000 else 0)
            if r["round_trip_direction"] == "backward":
                k = r["round_trip_num"]
                sc = ev.get("score")
                by_step[k][sid] = 1.0 - float(sc) if sc is not None else 1.0
                if sc is not None:
                    sens[k][sid] = 1.0 - float(sc)
    for k in sorted(by_step):
        v = list(by_step[k].values())
        lo, hi = boot(v)
        sv = list(sens[k].values())
        slo, shi = boot(sv) if sv else (None, None)
        result["steps"][f"interaction_{2*k}"] = {
            "n_env": len(v), "corruption_mean": sum(v) / len(v), "ci95": [lo, hi],
            "median": statistics.median(v),
            "frac_env_corruption_ge_0.5": sum(x >= 0.5 for x in v) / len(v),
            "sensitivity_drop_unscored": {"n": len(sv), "mean": sum(sv) / len(sv) if sv else None, "ci95": [slo, shi]},
            "unscored_steps": len(v) - len(sv)}
    final = by_step[maxrt] if maxrt else {}
    result["end_of_chain_interaction"] = 2 * maxrt
    result["per_env"] = [{"sample_id": s, "domain": want[s],
                          **{f"corruption_at_{2*k}": round(by_step[k].get(s, float('nan')), 4) for k in sorted(by_step)}}
                         for s in sorted(per_env)]
    for key in ("latency", "completion_tokens", "prompt_tokens"):
        result[f"mean_{key}"] = sum(stats[key]) / len(stats[key]) if stats[key] else None
    result["steps_without_score"] = sum(stats["errors"])
    result["steps_at_token_cap"] = sum(stats["truncated"])
    os.makedirs(out, exist_ok=True)
    json.dump(result, open(os.path.join(out, "summary.json"), "w"), indent=1)
    with open(os.path.join(out, "steps.jsonl"), "w") as f:
        for sid, recs in sorted(per_env.items()):
            for r in recs:
                ev = r["evaluation"]
                f.write(json.dumps({"sample_id": sid, "domain": want[sid], "round_trip": r["round_trip_num"],
                    "direction": r["round_trip_direction"], "score": ev.get("score"), "error": ev.get("error"),
                    "completion_tokens": r["completion_tokens"], "prompt_tokens": r["prompt_tokens"],
                    "latency_s": r["llm_latency"]}) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "per_env"}, indent=1))

if __name__ == "__main__":
    main(*sys.argv[1:4])

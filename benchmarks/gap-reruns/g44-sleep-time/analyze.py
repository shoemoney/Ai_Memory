"""Paired analysis over contexts for the sleep-time rerun (bootstrap over contexts, 10,000 resamples, seed 20261122).
Reads raw/answers.jsonl, raw/sleep.jsonl, raw/verify.jsonl. Cost per query follows the paper: tokens generated at test time
weigh t=10 against sleep-time tokens; the sleep arm adds (sleep tokens of the context) / (questions of the context).
Two item sets, same for every arm:
  all       every question (original + up to 4 generated per context); accuracy is against model-generated gold for generated items
  verified  original questions (dataset gold) plus generated questions whose gold an independent expression-based solve reproduced"""
import json, random, collections, math, sys
T = 10; B = 10000
ans = [json.loads(l) for l in open("raw/answers.jsonl")]
slp = {json.loads(l)["key"]: json.loads(l) for l in open("raw/sleep.jsonl")}
ver = {json.loads(l)["key"]: json.loads(l)["match"] for l in open("raw/verify.jsonl")}

def num(x):
    try: return float(str(x).replace("$", "").replace(",", ""))
    except ValueError: return None
def ok(r):
    p, g = num(r["pred"]), num(r["gold"])
    return p is not None and g is not None and abs(p - g) < 1e-6 * max(1, abs(g))
for r in ans: r["ok"] = ok(r)
VS = sorted({r["verbosity"] for r in ans})

def build(keep):
    rows = [r for r in ans if keep(r)]
    cell = collections.defaultdict(lambda: [0, 0, 0, 0])  # n, correct, completion tokens, prompt tokens
    for r in rows:
        c = cell[(r["ctx"], r["arm"], r["verbosity"])]; c[0] += 1; c[1] += r["ok"]; c[2] += r["completion_tokens"]; c[3] += r["prompt_tokens"]
    ctxs = sorted({r["ctx"] for r in rows}); return cell, ctxs

def stats(cell, sample):
    out = {}
    for arm in ("base", "sleep"):
        for v in VS:
            n = sum(cell[(c, arm, v)][0] for c in sample); k = sum(cell[(c, arm, v)][1] for c in sample)
            tok = sum(cell[(c, arm, v)][2] for c in sample) / n; pt = sum(cell[(c, arm, v)][3] for c in sample) / n
            s = sum(slp[c]["completion_tokens"] for c in sample) / n if arm == "sleep" else 0.0
            sc = sum(slp[c]["completion_tokens"] for c in sample) / len(sample) if arm == "sleep" else 0.0
            out[(arm, v)] = {"acc": k / n, "tok": tok, "prompt_tok": pt, "sleep_per_q": s, "sleep_per_context": sc, "qbar": n / len(sample), "cost": T * tok + s}
    return out

def match_tokens(s, acc):
    pts = sorted((s[("base", v)]["tok"], s[("base", v)]["acc"]) for v in VS)
    if acc <= pts[0][1]: return pts[0][0]
    for (t0, a0), (t1, a1) in zip(pts, pts[1:]):
        if a0 < acc <= a1: return t0 + (t1 - t0) * (acc - a0) / (a1 - a0)
    return None

def derived(s):
    d = {}
    for v in VS:
        b, sl = s[("base", v)], s[("sleep", v)]
        d[f"acc_diff_sleep_minus_base_v{v}"] = sl["acc"] - b["acc"]
        d[f"test_token_ratio_base_over_sleep_v{v}"] = b["tok"] / sl["tok"]
        d[f"cost_ratio_base_over_sleep_v{v}"] = b["cost"] / sl["cost"]
        one = T * sl["tok"] + sl["sleep_per_context"]  # sleep arm if each context had one question
        d[f"amortization_ratio_1_vs_measured_v{v}"] = one / sl["cost"]
        d[f"amortization_ratio_1_vs_10_modeled_v{v}"] = one / (T * sl["tok"] + sl["sleep_per_context"] / 10)
        m = match_tokens(s, sl["acc"])
        d[f"matched_base_tokens_v{v}"] = m
        d[f"matched_cost_ratio_base_over_sleep_v{v}"] = (T * m / sl["cost"]) if m else None
    return d

def ci(vals):
    v = sorted(x for x in vals if x is not None and not math.isnan(x))
    return [v[int(0.025 * len(v))], v[int(0.975 * len(v)) - 1]] if len(v) >= B * 0.9 else None

result = {}
for name, keep in (("all", lambda r: True), ("verified", lambda r: r["origin"] == "original" or ver.get(f'{r["ctx"]}|{r["qid"]}', False))):
    cell, ctxs = build(keep); rnd = random.Random(20261122)
    pt = stats(cell, ctxs); dp = derived(pt)
    boots = [derived(stats(cell, [rnd.choice(ctxs) for _ in ctxs])) for _ in range(B)]
    accs = collections.defaultdict(list)
    r2 = random.Random(7)
    for _ in range(B):
        smp = [r2.choice(ctxs) for _ in ctxs]
        for arm in ("base", "sleep"):
            for v in VS:
                accs[f"{arm}_v{v}"].append(sum(cell[(c, arm, v)][1] for c in smp) / sum(cell[(c, arm, v)][0] for c in smp))
    nq = {c: cell[(c, "base", VS[0])][0] for c in ctxs}
    result[name] = {"contexts": len(ctxs), "queries": sum(nq.values()), "questions_per_context_mean": sum(nq.values()) / len(ctxs),
                    "cells": {f"{a}_v{v}": {**pt[(a, v)], "acc_ci95": ci(accs[f"{a}_v{v}"])} for (a, v) in pt},
                    "paired": {k: {"point": dp[k], "ci95": ci([b[k] for b in boots]), "share_of_resamples_defined": sum(b[k] is not None for b in boots) / B} for k in dp}}
result["sleep_tokens_per_context_mean"] = sum(slp[c]["completion_tokens"] for c in {r["ctx"] for r in ans}) / len({r["ctx"] for r in ans})
result["verifier"] = {"generated_items": len(ver), "verified": sum(ver.values())}
json.dump(result, open("results.json", "w"), indent=1)
for name in ("all", "verified"):
    R = result[name]; print(f"== {name}: contexts={R['contexts']} queries={R['queries']} q/ctx={R['questions_per_context_mean']:.2f}")
    for k, c in R["cells"].items(): print(" ", k, f"acc={c['acc']:.3f} {c['acc_ci95'] and [round(x,3) for x in c['acc_ci95']]} tok={c['tok']:.1f} cost={c['cost']:.0f}")
    for k, p in R["paired"].items(): print(" ", k, None if p["point"] is None else round(p["point"], 3), p["ci95"] and [round(x, 3) for x in p["ci95"]], round(p["share_of_resamples_defined"], 3))
print(result["verifier"], result["sleep_tokens_per_context_mean"])

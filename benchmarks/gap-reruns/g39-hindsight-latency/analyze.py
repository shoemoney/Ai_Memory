"""Summarize decision-model request timings (raw/decider-timing.jsonl) from the recall phase.
The first START lines are retain-phase warm-up traffic and are excluded."""
import json, sys, statistics as st, random
START = int(sys.argv[1]) if len(sys.argv) > 1 else 4
rows = [json.loads(l) for l in open("raw/decider-timing.jsonl")][START:]
def pct(v, p):
    v = sorted(v); k = (len(v) - 1) * p; f = int(k); c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)
def summ(name, rs):
    c = [r["compute_s"] * 1000 for r in rs]; w = [r["wall_s"] * 1000 for r in rs]; t = [r["input_tokens"] for r in rs]
    rnd = random.Random(20261122)
    meds = sorted(st.median(rnd.choices(c, k=len(c))) for _ in range(5000))
    print(f"{name}: n={len(rs)} compute_ms median={st.median(c):.0f} (95% CI {meds[125]:.0f}-{meds[4874]:.0f}) p90={pct(c,.9):.0f} p95={pct(c,.95):.0f} | wall_ms median={st.median(w):.0f} p95={pct(w,.95):.0f} | input_tokens median={st.median(t):.0f} p95={pct(t,.95):.0f}")
    return {"n": len(rs), "compute_median_ms": st.median(c), "compute_ci": [meds[125], meds[4874]], "compute_p90_ms": pct(c, .9), "compute_p95_ms": pct(c, .95), "wall_median_ms": st.median(w), "wall_p95_ms": pct(w, .95), "tokens_median": st.median(t), "tokens_p95": pct(t, .95)}
ok = [r for r in rows if r["status"] == 200]
out = {"all": summ("all", ok), "dropped_non200": len(rows) - len(ok)}
out["small_lt1000tok"] = summ("small <1000 tok", [r for r in ok if r["input_tokens"] < 1000])
out["large_ge1000tok"] = summ("large >=1000 tok", [r for r in ok if r["input_tokens"] >= 1000])
out["excluding_first_5"] = summ("excl. first 5 (warm-up)", ok[5:])
json.dump(out, open("results.json", "w"), indent=1)

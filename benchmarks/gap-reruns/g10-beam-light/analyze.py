"""Paired analysis of BEAM scores (llm_judge_score per question, rubric-based) for the baseline RAG and LIGHT on the same questions.
Bootstrap over questions (10,000 resamples, seed 20261122) and, as a coarser check, over the 5 conversations."""
import json, random, glob, statistics as st, collections
rnd = random.Random(20261122)
fixed = json.load(open("raw/questions_fixed.json"))
rows = {"rag": {}, "light": {}}
for f in glob.glob("raw/scores-*-conv*.jsonl"):
    for l in open(f):
        r = json.loads(l); rows[r["system"]][r["key"]] = r
keys = sorted(set(rows["rag"]) & set(rows["light"]))
ok = [k for k in keys if rows["rag"][k]["score"] is not None and rows["light"][k]["score"] is not None]
print("fixed questions", fixed["n_questions"], "scored in both", len(ok), "judge errors", sum(1 for s in rows for k in rows[s] if rows[s][k]["score"] is None))
def pct(v, p): v = sorted(v); return v[int(p * (len(v) - 1))]
def mean(x): return sum(x) / len(x)
sc = {s: [rows[s][k]["score"] for k in ok] for s in rows}
diff = [l - r for l, r in zip(sc["light"], sc["rag"])]
def bci(vals, f):
    b = sorted(f([rnd.choice(vals) for _ in vals]) for _ in range(10000)); return [b[250], b[9749]]
res = {"n": len(ok), "rag_mean": mean(sc["rag"]), "light_mean": mean(sc["light"]), "diff_light_minus_rag": mean(diff),
       "rag_ci": bci(sc["rag"], mean), "light_ci": bci(sc["light"], mean), "diff_ci": bci(diff, mean),
       "light_wins": sum(d > 0 for d in diff), "rag_wins": sum(d < 0 for d in diff), "ties": sum(d == 0 for d in diff)}
by_conv = collections.defaultdict(list)
for k, d in zip(ok, diff): by_conv[k.split("|")[0]].append(d)
cm = {c: mean(v) for c, v in by_conv.items()}
res["per_conversation_diff"] = cm
res["relative_gain_percent_of_rag_mean"] = 100 * res["diff_light_minus_rag"] / res["rag_mean"] if res["rag_mean"] else None
by_ab = collections.defaultdict(lambda: {"rag": [], "light": []})
for k in ok:
    ab = rows["rag"][k]["ability"]
    by_ab[ab]["rag"].append(rows["rag"][k]["score"]); by_ab[ab]["light"].append(rows["light"][k]["score"])
res["per_ability"] = {a: {"n": len(v["rag"]), "rag": mean(v["rag"]), "light": mean(v["light"])} for a, v in by_ab.items()}
json.dump(res, open("results.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "per_ability"}, indent=1))
for a, v in res["per_ability"].items(): print(a, v)
# fixed-seed sample of 40 judged answers for the tester's hand check (20 per system)
rs = random.Random(5); pick = rs.sample(ok, 20)
with open("raw/hand_check_sample.jsonl", "w") as f:
    for k in pick:
        for s in ("rag", "light"):
            r = rows[s][k]; f.write(json.dumps({"key": k, "system": s, "ability": r["ability"], "question": r["question"], "response": r["response"][:1500], "judge_score": r["score"], "judge": r["judge"]}) + "\n")

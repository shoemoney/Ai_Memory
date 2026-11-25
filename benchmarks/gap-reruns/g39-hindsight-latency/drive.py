"""Drive a task-owned Hindsight 1.2.3 with LoCoMo conversation 0 and issue decision-model traffic.

Phases (each checkpointed in OUT/*.jsonl, rerunning resumes):
  retain  : session_1..K of conversation 0 as documents (LLM extraction + consolidation, which also
            sends decision-model requests when the decision model is configured)
  recall  : one recall per LoCoMo question with rerank prune+dedup (decision-model ranking + dedup)
  reflect : a handful of reflect calls (LLM query + decision-model evidence trimming)
Data: LoCoMo locomo10.json (CC BY-NC 4.0), fetched by script into scratch, never stored here.
"""
import argparse, json, os, sys, time
from pathlib import Path
from hindsight_client import Hindsight

p = argparse.ArgumentParser()
p.add_argument("phase", choices=["retain", "recall", "reflect"])
p.add_argument("--data", default="/data/scratch/membench/gap-reruns/locomo10.json")
p.add_argument("--base", default="http://127.0.0.1:39983")
p.add_argument("--bank", default="gap-locomo0")
p.add_argument("--sessions", type=int, default=6)
p.add_argument("--n", type=int, default=120)
p.add_argument("--out", default=str(Path(__file__).resolve().parent / "raw"))
a = p.parse_args()
out = Path(a.out); out.mkdir(exist_ok=True)
conv = json.load(open(a.data))[0]
c = conv["conversation"]

def done(path):
    return {json.loads(l)["key"] for l in open(path)} if path.exists() else set()

def log(path, rec):
    with open(path, "a") as f: f.write(json.dumps(rec) + "\n")

with Hindsight(base_url=a.base, timeout=1800) as client:
    if a.phase == "retain":
        path = out / "retain.jsonl"; seen = done(path)
        for i in range(1, a.sessions + 1):
            key = f"session_{i}"
            if key in seen: continue
            text = "\n".join(f'{t["speaker"]}: {t["text"]}' for t in c[key])
            t0 = time.perf_counter()
            r = client.retain(bank_id=a.bank, content=text, document_id=key, timestamp=None,
                              context=f'Conversation between {c["speaker_a"]} and {c["speaker_b"]}, {c.get(key+"_date_time","")}')
            log(path, {"key": key, "seconds": time.perf_counter() - t0, "chars": len(text), "ok": getattr(r, "success", None), "items": getattr(r, "items_count", None)})
            print(key, time.perf_counter() - t0, flush=True)
    elif a.phase == "recall":
        path = out / "recall.jsonl"; seen = done(path)
        qs = [q for q in conv["qa"] if "question" in q][: a.n]
        for j, q in enumerate(qs):
            key = f"q{j}"
            if key in seen: continue
            t0 = time.perf_counter()
            r = client.recall(bank_id=a.bank, query=q["question"], budget="mid", rerank={"prune": True, "dedup": True})
            log(path, {"key": key, "seconds": time.perf_counter() - t0, "results": len(r.results)})
            if j % 10 == 0: print(key, flush=True)
    else:
        path = out / "reflect.jsonl"; seen = done(path)
        qs = [q for q in conv["qa"] if "question" in q][: a.n]
        for j, q in enumerate(qs):
            key = f"q{j}"
            if key in seen: continue
            t0 = time.perf_counter()
            r = client.reflect(bank_id=a.bank, query=q["question"], budget="low")
            log(path, {"key": key, "seconds": time.perf_counter() - t0})
            print(key, flush=True)

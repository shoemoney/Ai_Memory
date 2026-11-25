"""Local rerun of the sleep-time compute multi-query cost claim (arXiv 2504.13171, Stateful GSM-Symbolic P2).

Stages (each checkpointed as JSONL in raw/, rerunning resumes):
  genq   : extra question/answer pairs per context with the paper's Appendix C prompt (local model, not o3-mini)
  sleep  : one offline "rethink" generation per context (paper's sleep_time_base prompt, no tools)
  answer : every question, with and without the rethink notes, at paper verbosity levels 0, 2, 4
Endpoint: any OpenAI-compatible server (default http://127.0.0.1:39980/v1), temperature 0.
"""
import argparse, json, os, random, re, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"; RAW.mkdir(exist_ok=True)
ap = argparse.ArgumentParser()
ap.add_argument("stage", choices=["select", "genq", "sleep", "answer", "verify"])
ap.add_argument("--data", default="/data/scratch/membench/gap-reruns/g44/stateful_gsm_symbolic_p2.jsonl")
ap.add_argument("--endpoint", default=os.environ.get("ENDPOINT", "http://127.0.0.1:39980/v1"))
ap.add_argument("--model", default="gap-qwen2.5-7b")
ap.add_argument("--contexts", type=int, default=32)
ap.add_argument("--pool", type=int, default=44)
ap.add_argument("--verbosities", default="0,2,4")
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--seed", type=int, default=20261122)
a = ap.parse_args()
lock = threading.Lock()

def chat(system, user, max_tokens):
    body = json.dumps({"model": a.model, "temperature": 0, "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(a.endpoint + "/chat/completions", body, {"Content-Type": "application/json"})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=1200) as r:
        d = json.load(r)
    return d["choices"][0]["message"]["content"], d["usage"]["prompt_tokens"], d["usage"]["completion_tokens"], time.perf_counter() - t

def done(path, key="key"):
    return {json.loads(l)[key] for l in open(path)} if path.exists() else set()

def emit(path, rec):
    with lock, open(path, "a") as f: f.write(json.dumps(rec) + "\n")

def gold(ans): return re.sub(r"(?s).*#### ", "", ans).replace("$", "").replace(",", "").strip(".").strip()

def prompt(name): return (HERE / "prompts" / name).read_text().strip()

GENQ = ("You are given a template that can generate grade school math problems, and an instantiation of that template.\n"
        "You will be given a context, and a example question answer pair. Your task is to generate a list of questions and answers about the context "
        "at the same difficult level that could plausibly be asked about that context. Make sure that the newly generated questions have the same number "
        "of reasoning steps required as the example question. The goal is to have many question and answer pairs about the same context. "
        "Generate questions and answers in the same format as the example, where the answer first contains reasoning and then is the final answer comes after")

def run_pool(items, fn):
    with ThreadPoolExecutor(a.workers) as ex: list(ex.map(fn, items))

ctxs_path = RAW / "contexts.jsonl"
if a.stage == "select":
    rows = [json.loads(l) for l in open(a.data)]
    seen, pool = set(), []
    rnd = random.Random(a.seed); rnd.shuffle(rows)
    for r in rows:
        c = r["stateful_gsm_symbolic_context"]
        if c in seen: continue
        seen.add(c); pool.append({"key": f"c{len(pool)}", "row_id": r["id"], "instance": r["instance"], "context": c, "question": r["stateful_gsm_symbolic_question"],
                                  "answer": gold(r["answer"]), "full_answer": r["answer"]})
        if len(pool) == a.pool: break
    ctxs_path.write_text("".join(json.dumps(p) + "\n" for p in pool)); print("selected", len(pool)); sys.exit()

ctxs = [json.loads(l) for l in open(ctxs_path)]

if a.stage == "genq":
    out = RAW / "genq.jsonl"; seen = done(out)
    def work(c):
        if c["key"] in seen: return
        user = (f'Context: {c["context"]}\n\nExample question: {c["question"]}\nExample answer: {c["full_answer"]}\n\n'
                'Now write 6 new question and answer pairs about the same context. Use exactly this layout for each pair:\n'
                'Question: <question>\nAnswer: <reasoning> #### <number>\n')
        text, pt, ct, dt = chat(GENQ, user, 1400)
        pairs = []
        for m in re.finditer(r"Question:\s*(.+?)\s*Answer:\s*(.+?####\s*([-$0-9.,]+))", text, re.S):
            q, full, g = m.group(1).strip(), m.group(2).strip(), gold(m.group(3))
            if g and q and q != c["question"]: pairs.append({"question": q, "answer": g, "full_answer": full})
        emit(out, {"key": c["key"], "pairs": pairs, "prompt_tokens": pt, "completion_tokens": ct, "seconds": dt, "raw": text})
    run_pool(ctxs, work)

def questions():
    gen = {json.loads(l)["key"]: json.loads(l)["pairs"] for l in open(RAW / "genq.jsonl")}
    sel = []
    for c in ctxs:
        pairs = gen.get(c["key"], [])[:4]
        if len(pairs) < 3: continue
        sel.append({**c, "qs": [{"qid": "orig", "question": c["question"], "gold": c["answer"], "origin": "original"}] +
                    [{"qid": f"g{i}", "question": p["question"], "gold": p["answer"], "origin": "generated"} for i, p in enumerate(pairs)]})
        if len(sel) == a.contexts: break
    return sel

if a.stage == "sleep":
    out = RAW / "sleep.jsonl"; seen = done(out)
    base = prompt("system/sleep_time_base.txt") + "\n\nNo tools are available here: write your calculations and inferences directly as your reply. Your whole reply is stored as the rethink_memory_block."
    persona = ("I am an expert reasoning agent. When given a new context, I make calculations and inferences that can be useful for future questions. "
               "I am verbose and brainstorm many different types of possible questions and answers.")
    def work(c):
        if c["key"] in seen: return
        text, pt, ct, dt = chat(base + "\n\nPersona: " + persona, "[trigger_rethink_memory] New situation: " + c["context"], 1500)
        emit(out, {"key": c["key"], "notes": text, "prompt_tokens": pt, "completion_tokens": ct, "seconds": dt})
    run_pool(questions(), work)

if a.stage == "answer":
    out = RAW / "answers.jsonl"; seen = done(out)
    notes = {json.loads(l)["key"]: json.loads(l)["notes"] for l in open(RAW / "sleep.jsonl")}
    vs = [int(v) for v in a.verbosities.split(",")]
    jobs = [(c, q, arm, v) for c in questions() for q in c["qs"] for arm in ("base", "sleep") for v in vs]
    def final_number(t):
        m = re.findall(r"(-?[$0-9.,]{2,})|(-?[0-9]+)", t)
        return "".join(m[-1]).replace("$", "").replace(",", "").strip(".") if m else ""
    def work(j):
        c, q, arm, v = j; key = f'{c["key"]}|{q["qid"]}|{arm}|{v}'
        if key in seen: return
        system = (prompt(f"system/convo_verbosity_{v}.txt") + "\nReply with plain text; no tools are available.\n\nPersona: " + prompt(f"persona/persona_verbosity_{v}.txt")
                  + "\nHuman: " + prompt(f"human/human_verbosity_{v}.txt"))
        if arm == "sleep": system += "\n\nrethink_memory_block:\n" + notes[c["key"]]
        text, pt, ct, dt = chat(system, c["context"] + " " + q["question"], 800)
        pred = final_number(text)
        emit(out, {"key": key, "ctx": c["key"], "qid": q["qid"], "origin": q["origin"], "arm": arm, "verbosity": v, "gold": q["gold"], "pred": pred,
                   "correct": pred == q["gold"], "prompt_tokens": pt, "completion_tokens": ct, "seconds": dt, "text": text})
    run_pool(jobs, work)
if a.stage == "verify":
    import ast, operator
    out = RAW / "verify.jsonl"; seen = done(out)
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.USub: operator.neg, ast.Pow: operator.pow}
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in ops: return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in ops: return ops[type(n.op)](ev(n.operand))
        raise ValueError("unsafe")
    jobs = [(c, q) for c in questions() for q in c["qs"] if q["origin"] == "generated"]
    def work(j):
        c, q = j; key = f'{c["key"]}|{q["qid"]}'
        if key in seen: return
        text, pt, ct, dt = chat("You turn word problems into one arithmetic expression.", c["context"] + " " + q["question"] +
                                "\n\nWrite the final answer as ONE arithmetic expression that uses only numbers and + - * / ( ), with every intermediate step inlined "
                                "(percentages as decimals, no units, no dollar signs). Output exactly one line: ANSWER = <expression>", 200)
        m = re.search(r"ANSWER\s*=\s*([-+*/().0-9 eE]+)", text.replace(",", ""))
        val = None
        try:
            if m: val = float(ev(ast.parse(m.group(1).strip(), mode="eval")))
        except Exception: val = None
        try: g = float(q["gold"])
        except ValueError: g = None
        emit(out, {"key": key, "ctx": c["key"], "qid": q["qid"], "expr": m.group(1).strip() if m else None, "value": val, "gold": q["gold"],
                   "match": val is not None and g is not None and abs(val - g) < 1e-6 * max(1, abs(g)), "completion_tokens": ct})
    run_pool(jobs, work)
print("stage done", a.stage)

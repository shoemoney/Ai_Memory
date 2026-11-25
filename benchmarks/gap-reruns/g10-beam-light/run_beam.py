"""Run BEAM's own baseline (pair-chunk dense RAG, k=5) and LIGHT on the smallest BEAM scale, with one local model.

Uses the BEAM repository's code unchanged (cloned to scratch, pinned commit); this runner only
  - points every LLM slot (index builder, scratchpad summarizer, reader, judge) at one local OpenAI-compatible server,
  - sends sentence-transformer encodes to the model host (remote_st.py) instead of loading encoders on this machine.
Stages: select | answer | judge. Per-conversation outputs go to WORK/<conv>/ (scratch); small result files go to raw/.
"""
import argparse, json, os, random, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BEAM = os.environ.get("BEAM_DIR", "/data/scratch/membench/gap-reruns/g10/BEAM")
WORK = Path(os.environ.get("WORK_DIR", "/data/scratch/membench/gap-reruns/g10/work"))
RAW = HERE / "raw"; RAW.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE)); sys.path.insert(0, BEAM)
os.environ.setdefault("OPENAI_API_KEY", "local")

ap = argparse.ArgumentParser()
ap.add_argument("stage", choices=["select", "answer", "judge"])
ap.add_argument("--system", choices=["rag", "light"])
ap.add_argument("--conv", help="single conversation id (default: all selected)")
ap.add_argument("--n-conv", type=int, default=5)
ap.add_argument("--seed", type=int, default=20261122)
ap.add_argument("--endpoint", default=os.environ.get("ENDPOINT", "http://127.0.0.1:39980/v1"))
ap.add_argument("--model", default="gap-qwen2.5-7b")
ap.add_argument("--index-max-tokens", type=int, default=1200)
ap.add_argument("--reader-max-tokens", type=int, default=600)
a = ap.parse_args()
SIZE = "100K"

if a.stage == "select":
    ids = sorted([d for d in os.listdir(f"{BEAM}/chats/{SIZE}") if d.isdigit() and os.path.exists(f"{BEAM}/chats/{SIZE}/{d}/probing_questions/probing_questions.json")], key=int)
    pick = sorted(random.Random(a.seed).sample(ids, a.n_conv), key=int)
    qs = []
    for c in pick:
        d = json.load(open(f"{BEAM}/chats/{SIZE}/{c}/probing_questions/probing_questions.json"))
        for ability, items in d.items():
            for i, it in enumerate(items): qs.append({"conv": c, "ability": ability, "index": i, "question": it["question"]})
    json.dump({"scale": SIZE, "seed": a.seed, "conversations": pick, "n_questions": len(qs), "questions": qs}, open(RAW / "questions_fixed.json", "w"), indent=1)
    print("selected", pick, len(qs)); sys.exit()

import sentence_transformers
from remote_st import RemoteST
sentence_transformers.SentenceTransformer = RemoteST
from langchain_openai import ChatOpenAI
import src.answer_probing_questions.long_term_memory_methods as lm
lm._get_st_client = lambda name, device=None: RemoteST(name)

# Two changes to BEAM code, both applied at import time (the cloned files stay untouched).
# 1) Public-code bug fix: light.py passes the int 14000 to str.replace, which raises TypeError the
# first time the scratchpad exceeds ~28k tokens and the iterative summarizer runs. Re-exec the module with str(tokens_limit).
import inspect
import src.answer_probing_questions.light as light
# Speed-only change: the per-chunk yes/no filter calls in noise_filtering are independent (temperature 0), so they run in a thread
# pool instead of one after another. Prompts, outputs and the order of kept chunks are identical.
_src2 = inspect.getsource(light)
_loop = _src2[_src2.index("        for doc in docs:"):_src2.index("    elif noise_handling_type == 2:")]
_par = '''        from concurrent.futures import ThreadPoolExecutor as _TPE
        def _keep(doc):
            doc_text = doc.page_content
            prompt = filter_chunk_context_prompt.replace("<query>", query) \\
                                                .replace("<doc_text>", doc_text)
            return doc_text, qwen_llm.invoke(prompt).content.strip().lower()
        with _TPE(8) as _ex:
            for doc_text, response in _ex.map(_keep, docs):
                if response == "yes":
                    selected_docs.append(doc_text)

'''
_src2 = _src2.replace(_loop, _par).replace('.replace("<tokens_limit>", tokens_limit)', '.replace("<tokens_limit>", str(tokens_limit))')
exec(compile(_src2, light.__file__, "exec"), light.__dict__)
for _n in ("create_scratch_pad", "create_episodic_memory", "create_working_memory", "create_memory_chunks", "noise_filtering"):
    setattr(lm, _n, getattr(light, _n))

def llm(max_tokens):
    return ChatOpenAI(model=a.model, base_url=a.endpoint, api_key="local", temperature=0, max_tokens=max_tokens, timeout=1800, max_retries=3)

fixed = json.load(open(RAW / "questions_fixed.json"))
convs = [a.conv] if a.conv else fixed["conversations"]

if a.stage == "answer":
    from src.answer_probing_questions.answer_generation import answer_generation
    method = {"rag": "pair_chunk", "light": "light"}[a.system]
    for c in convs:
        out = WORK / c / a.system; out.mkdir(parents=True, exist_ok=True)
        if (out / "answers.json").exists(): print("skip", c); continue
        # BEAM keeps the scratchpad and episodic index next to the answers; LIGHT index is shared between reruns of one conversation
        idx = WORK / c / "index"; idx.mkdir(exist_ok=True)
        t = time.time()
        answer_generation(probing_questions_address=f"{BEAM}/chats/{SIZE}/{c}/probing_questions/probing_questions.json",
                          evaluation_type="rag", chat_address=f"{BEAM}/chats/{SIZE}/{c}/chat.json", chat_size=SIZE,
                          gpt_llm=llm(a.index_max_tokens * 3), qwen_llm=llm(a.index_max_tokens), model=llm(a.reader_max_tokens),
                          result_save_address=str(idx), result_save_file_name=f"{a.system}-answers.json",
                          retrieval_config={"retrieval_method": method, "retriever": "dense", "k": 5})
        os.replace(idx / f"{a.system}-answers.json", out / "answers.json")
        (out / "seconds.txt").write_text(str(time.time() - t)); print("done", c, time.time() - t)

if a.stage == "judge":
    import src.evaluation.compute_metrics as cm
    cm.SentenceTransformer = RemoteST
    # BEAM's report uses llm_judge_score for every ability; the event-ordering alignment/Kendall extras are not needed for it.
    cm.event_ordering_score = lambda **kw: {}
    judge = llm(1500)
    for c in convs:
        ans = WORK / c / a.system / "answers.json"; out = RAW / f"scores-{a.system}-conv{c}.jsonl"
        if not ans.exists(): continue
        seen = {json.loads(l)["key"] for l in open(out)} if out.exists() else set()
        rub = json.load(open(f"{BEAM}/chats/{SIZE}/{c}/probing_questions/probing_questions.json"))
        for ability, items in json.load(open(ans)).items():
            for i, q in enumerate(items):
                key = f"{c}|{ability}|{i}"
                if key in seen: continue
                resp = q["llm_response"]; err = None; res = {}
                for attempt in range(3):
                    try:
                        res = getattr(cm, "evaluate_" + ability)(rubric=rub[ability][i]["rubric"], llm_response=resp, probing_question=q["question"], model=judge)
                        err = None; break
                    except Exception as e:
                        err = repr(e)[:200]
                with open(out, "a") as f:
                    f.write(json.dumps({"key": key, "system": a.system, "conv": c, "ability": ability, "index": i, "question": q["question"],
                                        "response": resp, "score": res.get("llm_judge_score"), "judge": res.get("llm_judge_responses"), "error": err}) + "\n")
        print("judged", c, a.system)

#!/usr/bin/env python3
"""Reduced LoCoMo comparison. All inference is sent to a loopback endpoint."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import time
import urllib.parse
import urllib.request

DATA_REV = "3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376"
EMBED_REV = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
SEED = 20261121
ROOT = Path(__file__).resolve().parent
JUDGE = """Grade whether the generated answer matches the reference answer to a question
about a conversation. Be generous: matching the reference topic is sufficient even
when the generated answer is longer. For dates, require the same absolute date or
time period, allowing different date formats. Return only a JSON object with
keys reasoning (a short explanation) and label (exactly CORRECT or WRONG).
Question: {question}
Reference: {gold}
Generated answer: {answer}"""
ANSWER_SYSTEM = """Answer questions about the supplied conversation using its evidence.
You may reason from the evidence and resolve relative dates using each session's
timestamp. Open-domain questions may use general knowledge together with the
conversation. Give a concise answer, including all requested list items.
If evidence is insufficient, say: I don't know based on the given context."""


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def append(path, value):
    with path.open("a") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")


def pseudonymize(text):
    mapping = json.loads((ROOT / "name-hashes.json").read_text())
    def token(match):
        word = match.group()
        return mapping.get(hashlib.sha256(word.lower().encode()).hexdigest(), word)
    return re.sub(r"\b[A-Za-z]+\b", token, str(text))


def wilson(k, n):
    z = 1.959963984540054
    p = k / n
    den = 1 + z*z/n
    center = (p + z*z/(2*n))/den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [center-half, center+half]


def parse_json(text):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end+1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "local")
    args = parser.parse_args()
    lab, out = args.lab, args.out
    lab.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "summary.json").exists() or (out / "items.jsonl").exists():
        raise SystemExit("Use a fresh output directory; completed runs are never overwritten.")
    base = os.environ.get("BASE_URL", "http://localhost:39700/v1")
    if urllib.parse.urlparse(base).hostname not in {"localhost"}:
        raise SystemExit("Only a loopback model endpoint is permitted; tunnel remote servers.")
    model = os.environ.get("MODEL", "qwen2.5-14b-instruct")
    os.environ["MEM0_TELEMETRY"] = "false"
    os.environ["MEM0_DIR"] = str(lab / "mem0-home")
    os.environ["HF_HOME"] = str(lab / "hf")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ.pop("OPENROUTER_API_KEY", None)
    import numpy as np
    import torch
    from openai import OpenAI
    from sentence_transformers import SentenceTransformer
    from mem0 import Memory
    import mem0.configs.prompts as prompts
    torch.set_num_threads(8)
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    client = OpenAI(base_url=base, api_key="local-unused", timeout=600, max_retries=0)
    trace = out / "model-calls.jsonl"

    def chat(messages, max_tokens, kind, response_format=None):
        messages = [dict(m, content=pseudonymize(m["content"])) for m in messages]
        t0 = time.monotonic()
        kwargs = dict(model=model, messages=messages, temperature=0, seed=SEED,
                      max_tokens=max_tokens)
        if response_format:
            kwargs["response_format"] = response_format
        result = client.chat.completions.create(**kwargs)
        response = result.model_dump()
        append(trace, {"kind": kind, "messages": messages, "max_tokens": max_tokens,
                       "temperature": 0, "seed": SEED,
                       "response": response, "seconds": time.monotonic()-t0})
        choice = result.choices[0]
        if choice.finish_reason != "stop":
            raise RuntimeError(f"Truncated or invalid completion in {kind}: {choice.finish_reason}")
        return choice.message.content

    data_path = lab / "locomo10.json"
    url = f"https://raw.githubusercontent.com/snap-research/locomo/{DATA_REV}/data/locomo10.json"
    if not data_path.exists():
        urllib.request.urlretrieve(url, data_path)
    raw = data_path.read_bytes()
    sample = json.loads(raw)[0]
    conv = sample["conversation"]
    rng = random.Random(SEED)
    selected = []
    for category in (1, 2, 3, 4):
        pool = [i for i, q in enumerate(sample["qa"]) if q["category"] == category]
        selected.extend(rng.sample(pool, 10))
    selected.sort()
    questions = [{"item_id": f"c0-q{i}", "original_question_sha256": hashlib.sha256(
        sample["qa"][i]["question"].encode()).hexdigest(),
        "question": pseudonymize(sample["qa"][i]["question"]),
        "gold": pseudonymize(sample["qa"][i]["answer"]),
        "category": sample["qa"][i]["category"],
        "evidence": sample["qa"][i].get("evidence", [])} for i in selected]
    sessions, turns = [], []
    for key in sorted((k for k, v in conv.items() if re.fullmatch(r"session_\d+", k)
                       and isinstance(v, list)), key=lambda k: int(k.split("_")[1])):
        date = conv[key + "_date_time"]
        session_turns = []
        for turn in conv[key]:
            text = f"[{date}] {turn['dia_id']} {turn['speaker']}: {turn.get('text', '')}"
            for field in ("query", "blip_caption"):
                if turn.get(field):
                    text += f" [Image {field}: {turn[field]}]"
            text = pseudonymize(text)
            session_turns.append(text)
            turns.append(text)
        sessions.append({"key": key, "date": date, "turns": session_turns})
    dump(out / "selection.json", questions)
    dump(out / "manifest.json", {"seed": SEED, "conversation_index": 0,
        "categories": [1, 2, 3, 4], "per_category": 10, "n": len(questions),
        "data_revision": DATA_REV, "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_license": "CC-BY-NC-4.0", "model": model,
        "embedder": "sentence-transformers/all-MiniLM-L6-v2", "embedder_revision": EMBED_REV,
        "sessions": len(sessions), "turns": len(turns), "retrieval_k": 20,
        "mem0_chunk_turns": 8, "judge_calls_per_answer": 1,
        "pseudonymized": True})
    # No reference answers, summaries, observations or evidence IDs enter indexing.
    dump(out / "indexed-conversation.json", sessions)
    embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2",
                                  revision=EMBED_REV, device="cpu")
    matrix = embedder.encode(turns, normalize_embeddings=True, show_progress_bar=False)
    query_vectors = embedder.encode([q["question"] for q in questions],
                                   normalize_embeddings=True, show_progress_bar=False)
    full_context = "\n".join(turns)
    all_rows = []

    def evaluate(backend, contexts):
        pending = []
        for item, context in zip(questions, contexts):
            answer = chat([{"role": "system", "content": ANSWER_SYSTEM},
                {"role": "user", "content": f"Conversation evidence:\n{context}\n\nQuestion: {item['question']}"}],
                256, f"{backend}:{item['item_id']}:answer")
            pending.append((item, context, answer))
            print(backend, item["item_id"], "answered", flush=True)
        for item, context, answer in pending:
            judge_raw = chat([{"role": "user", "content": JUDGE.format(
                question=item["question"], gold=item["gold"], answer=answer)}],
                256, f"{backend}:{item['item_id']}:judge", {"type": "json_object"})
            judge = parse_json(judge_raw)
            if judge.get("label") not in {"CORRECT", "WRONG"}:
                raise RuntimeError(f"Unparseable judge label: {judge_raw}")
            row = dict(item, backend=backend, context=context, answer=answer,
                       judge_raw=judge_raw, correct=judge["label"] == "CORRECT")
            append(out / "items.jsonl", row)
            all_rows.append(row)
            print(backend, item["item_id"], judge["label"], flush=True)

    evaluate("full-context", [full_context] * len(questions))
    rag_contexts = []
    for vector in query_vectors:
        ids = np.argsort(-(matrix @ vector), kind="stable")[:20]
        rag_contexts.append("\n".join(turns[i] for i in ids))
    evaluate("rag", rag_contexts)
    memory = Memory.from_config({
        "llm": {"provider": "openai", "config": {"model": model, "temperature": 0,
            "max_tokens": 2048, "api_key": "local-unused", "openai_base_url": base}},
        "embedder": {"provider": "huggingface", "config": {
            "model": "sentence-transformers/all-MiniLM-L6-v2", "embedding_dims": 384,
            "model_kwargs": {"revision": EMBED_REV, "device": "cpu"}}},
        "vector_store": {"provider": "qdrant", "config": {
            "path": str(lab / "qdrant"), "embedding_model_dims": 384,
            "collection_name": "locomo", "on_disk": True}},
        "history_db_path": str(lab / "history.db"),
        "custom_instructions": "Extract facts about BOTH named speakers. Preserve their identities and dates. Resolve relative dates using the message timestamp. Ignore the machine date."})
    # Keep Mem0's extraction pipeline, but record the exact local calls and reject truncation.
    def mem0_generate(messages, response_format=None, **kwargs):
        return chat(messages, 2048, "mem0:extract", response_format)
    memory.llm.generate_response = mem0_generate
    original_resolve = prompts._resolve_dates
    current_date = None
    def resolve_dates(current_date_arg=None, observation_date=None, **kwargs):
        return original_resolve(current_date_arg or current_date, observation_date)
    prompts._resolve_dates = resolve_dates
    try:
        from datetime import datetime
        for session in sessions:
            current_date = datetime.strptime(session["date"], "%I:%M %p on %d %B, %Y").date().isoformat()
            for start in range(0, len(session["turns"]), 8):
                result = memory.add([{"role": "user", "content": "\n".join(
                    session["turns"][start:start+8])}], user_id="conversation-0", infer=True,
                    metadata={"session": session["key"], "reference_date": current_date})
                append(out / "ingest.jsonl", {"session": session["key"], "start": start,
                    "result": result})
                print("mem0 ingest", session["key"], start, len(result.get("results", [])), flush=True)
    finally:
        prompts._resolve_dates = original_resolve
    memories = memory.get_all(filters={"user_id": "conversation-0"}, limit=10000)
    dump(out / "extracted-memories.json", memories)
    if not memories.get("results"):
        raise RuntimeError("Mem0 extracted zero memories; no misleading empty-store score is reported.")
    contexts = []
    for question in questions:
        hits = memory.search(question["question"], top_k=20,
                             filters={"user_id": "conversation-0"})
        contexts.append("\n".join(hit["memory"] for hit in hits["results"]))
    evaluate("mem0", contexts)
    summary = {}
    for backend in ("full-context", "rag", "mem0"):
        rows = [row for row in all_rows if row["backend"] == backend]
        k = sum(row["correct"] for row in rows)
        summary[backend] = {"correct": k, "n": len(rows), "accuracy": k/len(rows),
                            "wilson_95": wilson(k, len(rows)),
                            "by_category": {str(c): {"correct": sum(r["correct"] for r in rows if r["category"] == c),
                                "n": sum(r["category"] == c for r in rows)} for c in (1,2,3,4)}}
    dump(out / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

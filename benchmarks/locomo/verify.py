#!/usr/bin/env python3
"""Recompute reported counts from raw local responses without making model calls."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from run import parse_json, wilson


def read_jsonl(path):
    return [json.loads(line) for line in path.open()]


def verify(out):
    if not __debug__:
        raise RuntimeError("Verification requires Python without optimization flags.")
    selection = json.loads((out / "selection.json").read_text())
    assert len(selection) == 40
    assert Counter(q["category"] for q in selection) == {1: 10, 2: 10, 3: 10, 4: 10}
    selected = {q["item_id"]: q for q in selection}
    assert len(selected) == 40
    sessions = json.loads((out / "indexed-conversation.json").read_text())
    assert len(sessions) == 19 and sum(len(s["turns"]) for s in sessions) == 419
    assert all(set(s) == {"key", "date", "turns"} for s in sessions)
    rows = read_jsonl(out / "items.jsonl")
    calls = read_jsonl(out / "model-calls.jsonl")
    assert len(rows) == 120
    assert all(r["response"]["choices"][0]["finish_reason"] == "stop" for r in calls)
    answer_calls = {r["kind"]: r for r in calls if r["kind"].endswith(":answer")}
    judge_calls = {r["kind"]: r for r in calls if r["kind"].endswith(":judge")}
    assert len(answer_calls) == len(judge_calls) == 120
    counts = {}
    summary = json.loads((out / "summary.json").read_text())
    for backend in ("full-context", "rag", "mem0"):
        subset = [r for r in rows if r["backend"] == backend]
        assert len(subset) == 40 and {r["item_id"] for r in subset} == set(selected)
        for row in subset:
            original = selected[row["item_id"]]
            assert all(row[k] == original[k] for k in original)
            kind = f"{backend}:{row['item_id']}"
            answer = answer_calls[kind + ":answer"]["response"]["choices"][0]["message"]["content"]
            judge = judge_calls[kind + ":judge"]["response"]["choices"][0]["message"]["content"]
            assert row["answer"] == answer and row["judge_raw"] == judge
            verdict = parse_json(judge)["label"]
            assert verdict in {"CORRECT", "WRONG"}
            assert row["correct"] == (verdict == "CORRECT")
        k = sum(r["correct"] for r in subset)
        assert summary[backend]["correct"] == k and summary[backend]["n"] == 40
        assert summary[backend]["accuracy"] == k / 40
        assert summary[backend]["wilson_95"] == wilson(k, 40)
        assert sum(v["correct"] for v in summary[backend]["by_category"].values()) == k
        assert all(v["n"] == 10 for v in summary[backend]["by_category"].values())
        counts[backend] = {"correct": k, "n": 40}
    full = "\n".join(turn for s in sessions for turn in s["turns"])
    assert all(r["context"] == full for r in rows if r["backend"] == "full-context")
    ingests = read_jsonl(out / "ingest.jsonl")
    extracted = json.loads((out / "extracted-memories.json").read_text())["results"]
    assert len(ingests) == 61 and len(extracted) > 0
    added = {m["id"]: m["memory"] for row in ingests for m in row["result"].get("results", [])}
    assert {m["id"]: m["memory"] for m in extracted} == added
    extraction_calls = [c for c in calls if c["kind"] == "mem0:extract"]
    assert len(extraction_calls) == 61
    empty_extractions = 0
    for call in extraction_calls:
        data = parse_json(call["response"]["choices"][0]["message"]["content"])
        assert isinstance(data["memory"], list)
        empty_extractions += not data["memory"]
    proof = {"counts_recomputed_from_raw_judgments": counts,
             "question_alignment_verified": True, "same_sample_all_systems": True,
             "all_completions_stopped_normally": True, "answer_calls": len(answer_calls),
             "judge_calls": len(judge_calls), "extraction_calls": len(ingests),
             "empty_extraction_responses": empty_extractions,
             "retained_memories": len(extracted),
             "run_py_sha256": hashlib.sha256(Path(__file__).with_name("run.py").read_bytes()).hexdigest()}
    (out / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    verify(parser.parse_args().out)

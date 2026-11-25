"""Rescore saved refusal-loops generations (gen/*.jsonl) with the heuristic and an LLM judge.

The judge is an OpenAI-compatible endpoint (default: the pinned Qwen judge on 127.0.0.1:39700, via the
the workstation tunnel). Prompt, rubric and JSON contract are the ones in refusal/score.py. Output:
<study>/rescore.json with per-condition heuristic and judge counts plus per-row labels.
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loops  # noqa: E402,F401  (puts benchmarks/inkling on sys.path)

sys.path.insert(0, str(loops.INKLING / "refusal"))
import score  # noqa: E402
from run import post_chat, response_text  # noqa: E402


def judge_row(prompt, text, args):
    body = dict(model=args.judge_model, temperature=0, seed=7, thinking_budget=0, max_tokens=512,
                messages=[{"role": "system", "content": score.JUDGE_SYSTEM},
                          {"role": "user", "content": json.dumps(dict(request=prompt["prompt"], group=prompt["group"],
                                                                      response=text))}])
    return score.parse_judge(response_text(post_chat(args.judge_base_url, body)))


def tally(labels):
    n = len(labels)
    k = sum(l == "refused" for l in labels)
    return dict(n=n, refused=k, partial=sum(l == "partial" for l in labels),
                complied=sum(l == "complied" for l in labels),
                refusal_rate=k / n if n else None, wilson_95=score.wilson(k, n))


def rescore_file(path, prompts, args, pool):
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

    def one(row):
        out = dict(id=row["id"], heuristic=row["label"])
        try:
            out["judge"] = judge_row(prompts[row["id"]], row["text"], args)["label"]
        except Exception as exc:  # recorded, never counted as a refusal
            out["judge_error"] = f"{type(exc).__name__}: {exc}"
        return out

    scored = list(pool.map(one, rows))
    ok = [r for r in scored if "judge" in r]
    return dict(heuristic=tally([r["heuristic"] for r in scored]), judge=tally([r["judge"] for r in ok]),
                judge_errors=len(scored) - len(ok), rows=scored)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("study", type=Path)
    ap.add_argument("--prompts", type=Path, default=loops.INKLING / "refusal/prompts.jsonl")
    ap.add_argument("--judge-base-url", default="http://127.0.0.1:39700/v1")
    ap.add_argument("--judge-model", default="qwen2.5-14b-instruct")
    ap.add_argument("--concurrency", type=int, default=3)
    args = ap.parse_args()
    prompts = {p["id"]: p for p in score.read_jsonl(args.prompts)}
    out = {}
    with ThreadPoolExecutor(args.concurrency) as pool:
        for path in sorted((args.study / "gen").glob("*.jsonl")):
            out[path.stem] = rescore_file(path, prompts, args, pool)
            r = out[path.stem]
            print(path.stem, "heur", r["heuristic"]["refused"], "judge", r["judge"]["refused"], "of", r["judge"]["n"],
                  "errors", r["judge_errors"], flush=True)
    (args.study / "rescore.json").write_text(json.dumps(dict(judge_model=args.judge_model, conditions=out), indent=2))


if __name__ == "__main__":
    main()

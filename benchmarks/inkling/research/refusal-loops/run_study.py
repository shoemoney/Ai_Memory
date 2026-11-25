"""Refusal direction per loop pass and per pass count (run on the Mac Studio; see README.md).

Stages (comma separated, default all): collect, refusal, ablate, report.
  collect  one forward per prompt at each pass count N, last-instruction-token activations
           at every (layer, pass) -> acts-N{n}.npz
  refusal  greedy generation on held-out prompts at each N, no edit -> gen/refusal-N{n}-{group}.jsonl
  ablate   greedy generation on held-out harmful prompts at N with the direction projected out
           at ONE pass (or all, or random control) -> gen/ablate-N{n}-{cond}.jsonl
  report   analysis.json, refusal.json, ablation.json from the files above (no model needed)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import loops  # noqa: E402  (also puts benchmarks/inkling on sys.path)
import analysis  # noqa: E402
from direction import collect  # noqa: E402

CORE = (6, 18)


def read_jsonl(path):
    p = Path(path)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def refusal_scorer():
    sys.path.insert(0, str(loops.INKLING / "refusal"))
    import score
    return score


def generation_tokens(tok, prompt, effort):
    rendered = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                                       add_generation_prompt=True, reasoning_effort=effort)
    return tok(rendered, add_special_tokens=False)["input_ids"]


def select(rows, group, split):
    return [r for r in rows if r["split"] in split and r["label"] == group]


def run_condition(model, tok, rows, out_path, args, eos, context):
    """Greedy-generate each row once under ``context`` (a context manager factory); resumable."""
    score = refusal_scorer()
    done = {r["id"] for r in read_jsonl(out_path)}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a") as fh:
        for row in rows:
            if row["id"] in done:
                continue
            ids = generation_tokens(tok, row["prompt"], args.reasoning_effort)
            with context():
                gen, truncated = loops.greedy_generate(model, ids, args.max_tokens, eos)
            text = tok.decode(gen, skip_special_tokens=True)
            label, why = score.classify(text, "length" if truncated else "stop")
            fh.write(json.dumps(dict(id=row["id"], group=row["group"], label=label, why=why,
                                     tokens=len(gen), text=text)) + "\n")
            fh.flush()


def stage_collect(args, model, tok, config, rows):
    import mlx.core as mx
    for n in args.passes:
        path = args.out / f"acts-N{n}.npz"
        if path.exists():
            continue
        tcfg = loops.text_config_at(config["text_config"], n)
        keys = collect.visit_keys(tcfg)
        acts, positions = [], []
        with loops.pass_count(model, n):
            for i, row in enumerate(rows):
                ids, last = collect.instruction_tokens(tok, row["prompt"], args.reasoning_effort)
                with collect.capture_layers(model, last, tcfg) as records:
                    out = model.model.language_model(mx.array([ids]))
                    mx.eval(out)
                acts.append(np.stack([v for _, v in records]))
                positions.append(last)
                print(f"collect N={n} {i+1}/{len(rows)}", flush=True)
                if hasattr(mx, "clear_cache"):
                    mx.clear_cache()
        np.savez(path, activations=np.stack(acts), labels=np.array([r["label"] for r in rows]),
                 splits=np.array([r["split"] for r in rows]), ids=np.array([r["id"] for r in rows]),
                 layers=np.array([k[0] for k in keys]), passes=np.array([k[1] for k in keys]),
                 token_positions=np.array(positions), num_passes=n,
                 metadata=json.dumps(dict(model=str(args.model), seed=args.seed, n=args.n,
                                          reasoning_effort=args.reasoning_effort,
                                          site="post_decoder_partial_block_residual",
                                          token="last_user_instruction_content_token")))


def load_acts(args, n):
    with np.load(args.out / f"acts-N{n}.npz", allow_pickle=False) as d:
        return {k: d[k] for k in d.files}


def ablation_conditions(args, n, d):
    """{name: {(layer, pass): unit vector}} built from train-only directions at pass count n."""
    dirs, val, _ = analysis.per_visit_directions(d["activations"], d["labels"], d["splits"])
    layers, passes = d["layers"], d["passes"]
    index = {(int(l), int(p)): j for j, (l, p) in enumerate(zip(layers, passes))}
    core = range(*CORE)
    if args.ablate_mode == "single":
        best = max((j for (l, p), j in index.items() if l in core), key=lambda j: val[j]["score"])
        vec = lambda l, p: dirs[best]
    else:
        vec = lambda l, p: dirs[index[(l, p)]]
    conds = {}
    for p in range(1, n + 1):
        conds[f"pass{p}"] = {(l, p): vec(l, p) for l in core}
        if p > 1:
            conds[f"p1dir_at_pass{p}"] = {(l, p): dirs[index[(l, 1)]] for l in core}
    conds["all"] = {(l, p): vec(l, p) for l in core for p in range(1, n + 1)}
    rng = np.random.default_rng(args.seed)
    rand = {}
    for l in core:
        r = rng.standard_normal(dirs.shape[1])
        rand[l] = r / np.linalg.norm(r)
    conds["random_all"] = {(l, p): rand[l] for l in core for p in range(1, n + 1)}
    # Whole-network controls: every recorded decoder visit (all layers, all passes).
    conds["all_layers"] = {k: dirs[j] for k, j in index.items()}
    best_core = max((j for (l, p), j in index.items() if l in core), key=lambda j: val[j]["score"])
    conds["all_layers_single"] = {k: dirs[best_core] for k in index}
    rand_all = {}
    for l in sorted({k[0] for k in index}):
        r = rng.standard_normal(dirs.shape[1])
        rand_all[l] = r / np.linalg.norm(r)
    conds["random_all_layers"] = {k: rand_all[k[0]] for k in index}
    return conds


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", type=Path, help="local checkpoint directory (HF layout)")
    ap.add_argument("--mlx-lm", type=Path, help="PR #2086 checkout, if not installed")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--prompts", type=Path, default=loops.INKLING / "refusal/prompts.jsonl")
    ap.add_argument("--passes", default="1,2,3,5")
    ap.add_argument("--ablate-passes", default="3,5", help="pass counts to run single-pass ablation at")
    ap.add_argument("--ablate-mode", choices=("per_layer", "single"), default="per_layer",
                    help="per_layer: each layer's own direction at the ablated pass; "
                         "single: the best validation direction everywhere (Arditi style)")
    ap.add_argument("--stages", default="collect,refusal,ablate,report")
    ap.add_argument("--n", type=int, default=60, help="prompts per class (max 60 in the shipped file)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-tokens", type=int, default=192)
    ap.add_argument("--reasoning-effort", default="none")
    args = ap.parse_args()
    args.passes = [int(x) for x in args.passes.split(",")]
    args.ablate_passes = [int(x) for x in args.ablate_passes.split(",") if x]
    stages = set(args.stages.split(","))
    args.out.mkdir(parents=True, exist_ok=True)
    rows = collect.prepare_prompts(args.prompts, args.n, args.seed)

    if stages & {"collect", "refusal", "ablate"}:
        if args.mlx_lm:
            sys.path.insert(0, str(args.mlx_lm.resolve()))
        import mlx_lm
        config = json.loads((args.model / "config.json").read_text())
        if config.get("model_type") != "inkling2_loop":
            raise SystemExit("Expected an inkling2_loop checkpoint")
        model, tok = mlx_lm.load(str(args.model), lazy=True)
        tok = collect.unwrap_tokenizer(tok)
        model.eval()
        allowed = loops.trained_passes(config["text_config"])
        bad = [n for n in args.passes if n not in allowed]
        if bad:
            raise SystemExit(f"Pass counts {bad} not allowed for this checkpoint (allowed {allowed})")
        eos = {config["eos_token_id"]}
        heldout = {"eval"}
        if "collect" in stages:
            stage_collect(args, model, tok, config, rows)
        if "refusal" in stages:
            for n in args.passes:
                for label, name in ((1, "harmful"), (0, "benign")):
                    run_condition(model, tok, select(rows, label, heldout),
                                  args.out / f"gen/refusal-N{n}-{name}.jsonl", args, eos,
                                  lambda n=n: loops.pass_count(model, n))
        if "ablate" in stages:
            for n in [p for p in args.ablate_passes if p in args.passes]:
                conds = ablation_conditions(args, n, load_acts(args, n))
                for name, spec in conds.items():
                    from contextlib import ExitStack

                    def ctx(n=n, spec=spec):
                        stack = ExitStack()
                        stack.enter_context(loops.pass_count(model, n))
                        stack.enter_context(loops.ablate_at_pass(model, spec))
                        return stack
                    run_condition(model, tok, select(rows, 1, heldout),
                                  args.out / f"gen/ablate-N{n}-{name}.jsonl", args, eos, ctx)
    if "report" in stages:
        report(args, rows)


def rate(path, score):
    rs = read_jsonl(path)
    k = sum(r["label"] == "refused" for r in rs)
    partial = sum(r["label"] == "partial" for r in rs)
    return dict(n=len(rs), refused=k, partial=partial, complied=len(rs) - k - partial,
                refusal_rate=k / len(rs) if rs else None, wilson_95=score.wilson(k, len(rs)))


def report(args, rows):
    score = refusal_scorer()
    ana, dirs_by_n, keys_by_n = {}, {}, {}
    for n in args.passes:
        f = args.out / f"acts-N{n}.npz"
        if not f.exists():
            continue
        d = load_acts(args, n)
        dirs, val, ev = analysis.per_visit_directions(d["activations"], d["labels"], d["splits"])
        table, best = analysis.summarize(dirs, d["layers"], d["passes"], val, ev, CORE)
        keys = [(int(l), int(p)) for l, p in zip(d["layers"], d["passes"])]
        dirs_by_n[n], keys_by_n[n] = dirs, keys
        ana[str(n)] = dict(visits=table, best_core_visit=best,
                           pass_cosines=analysis.pass_cosines(dirs, d["layers"], d["passes"]))
    out = dict(model=str(args.model), counts=dict(prompts_per_class=args.n), by_n=ana,
               cross_n_cosines=analysis.cross_n_cosines(dirs_by_n, keys_by_n) if len(dirs_by_n) > 1 else {})
    (args.out / "analysis.json").write_text(json.dumps(out, indent=2))
    refusal = {str(n): {g: rate(args.out / f"gen/refusal-N{n}-{g}.jsonl", score)
                        for g in ("harmful", "benign")} for n in args.passes}
    (args.out / "refusal.json").write_text(json.dumps(refusal, indent=2))
    abl = {}
    for n in args.ablate_passes:
        conds = {p.stem.split(f"ablate-N{n}-")[1]: rate(p, score)
                 for p in sorted((args.out / "gen").glob(f"ablate-N{n}-*.jsonl"))}
        if conds:
            abl[str(n)] = dict(baseline=refusal.get(str(n), {}).get("harmful"), conditions=conds)
    (args.out / "ablation.json").write_text(json.dumps(abl, indent=2))
    print("wrote analysis.json refusal.json ablation.json")


if __name__ == "__main__":
    main()

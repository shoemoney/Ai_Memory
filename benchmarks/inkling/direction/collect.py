"""Collect post-decoder partial-block residuals, with explicit loop visits."""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def visit_keys(text_config):
    n = text_config["num_hidden_layers"]
    loop = text_config.get("loop_config")
    if not loop:
        return [(i, 1) for i in range(n)]
    a, b, passes = (loop[k] for k in ("core_start", "core_end", "num_passes"))
    if not 0 < a < b <= n or passes < 1:
        raise ValueError("Invalid loop_config")
    return ([(i, 1) for i in range(a)]
            + [(i, p) for p in range(1, passes + 1) for i in range(a, b)]
            + [(i, 1) for i in range(b, n)])


def prepare_prompts(path, n=50, seed=42):
    """N items per class. Eval never contributes to fitting or selection."""
    groups = {0: [], 1: []}
    seen = set()
    aliases = {"train": "train", "validation": "validation", "val": "validation",
               "eval": "eval", "test": "eval", "heldout": "eval"}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        group = row.get("group", row.get("label"))
        if group == "memory_assistant":
            # The sibling suite's capability controls are not either refusal class.
            continue
        if group in ("harmful", 1):
            label = 1
        elif group in ("harmless", "benign", "benign_edgy", "safe", 0):
            label = 0
        else:
            raise ValueError(f"Unknown prompt group: {group!r}")
        prompt = row.get("prompt", row.get("instruction"))
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Each row needs a nonempty prompt")
        digest = hashlib.sha256(prompt.strip().encode()).hexdigest()
        if digest in seen:
            raise ValueError("Duplicate prompt content: could leak between splits")
        seen.add(digest)
        split = row.get("split")
        if split is not None and split not in aliases:
            raise ValueError(f"Unknown split: {split}")
        item = dict(row)
        item.update(id=str(row.get("id", digest)), prompt=prompt, label=label,
                    group=row.get("group", "harmful" if label else "harmless"),
                    split=aliases.get(split), sha256=digest)
        groups[label].append(item)
    if n < 5 or any(len(rows) < n for rows in groups.values()):
        raise ValueError("Need --n >= 5 and at least N distinct prompts per class")
    supplied = [r["split"] is not None for rows in groups.values() for r in rows]
    if any(supplied) and not all(supplied):
        raise ValueError("Supply splits for every row or none")
    result = []
    for label, rows in groups.items():
        # Sorting keyed by prompt content makes row ordering irrelevant.
        rows.sort(key=lambda r: hashlib.sha256(f'{seed}:{r["sha256"]}'.encode()).digest())
        if all(supplied):
            # Preserve the provided split and sample each split proportionally.
            quotas = {"validation": max(1, n // 5), "eval": max(1, n // 5)}
            quotas["train"] = n - sum(quotas.values())
            chosen = []
            for split, count in quotas.items():
                subset = [r for r in rows if r["split"] == split]
                if len(subset) < count:
                    raise ValueError(f"Insufficient class {label} rows in {split}")
                chosen.extend(subset[:count])
        else:
            chosen = rows[:n]
            hold = max(1, n // 5)
            for i, row in enumerate(chosen):
                row["split"] = ("eval" if i < hold else
                                "validation" if i < 2 * hold else "train")
        result.extend(chosen)
    if len({r["id"] for r in result}) != len(result):
        raise ValueError("Prompt IDs must be unique")
    return result


def unwrap_tokenizer(tokenizer):
    """mlx-lm returns a TokenizerWrapper, which is not callable; offsets need the HF fast tokenizer."""
    return tokenizer if callable(tokenizer) else tokenizer._tokenizer


def instruction_tokens(tokenizer, prompt, reasoning_effort="none"):
    """Locate the last instruction-content token, excluding end-message tokens."""
    rendered = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], tokenize=False,
        add_generation_prompt=False, reasoning_effort=reasoning_effort)
    marker = "<|message_user|><|content_text|>"
    start = rendered.find(marker)
    if start < 0 or rendered[start + len(marker):][:len(prompt)] != prompt:
        raise ValueError("Unexpected Inkling chat template: cannot locate instruction")
    start += len(marker)
    end = start + len(prompt)
    encoded = tokenizer(rendered, add_special_tokens=False, return_offsets_mapping=True)
    offsets = encoded["offset_mapping"]
    positions = [i for i, (a, b) in enumerate(offsets) if b > start and a < end]
    if not positions:
        raise ValueError("Tokenizer returned no instruction offsets; use a fast tokenizer")
    pos = positions[-1]
    if offsets[pos][1] > end:
        raise ValueError("Last instruction token overlaps the message terminator")
    # Causal prefill only through this token: no response/generation token capture.
    return encoded["input_ids"][:pos + 1], pos


@contextmanager
def capture_layers(model, last_token, text_config):
    """Patch the common decoder base temporarily; don't replace shared modules."""
    import mlx.core as mx
    from mlx_lm.models.inkling2.layers import DecoderLayer

    layers = model.model.language_model.layers
    indices = {id(layer): i for i, layer in enumerate(layers)}
    original = DecoderLayer.__call__
    counts, records = Counter(), []

    def wrapped(layer, *args, **kwargs):
        output = original(layer, *args, **kwargs)
        if id(layer) in indices:
            i = indices[id(layer)]
            counts[i] += 1
            vector = output[0][0, last_token, :].astype(mx.float32)
            mx.eval(vector)
            records.append(((i, counts[i]), np.array(vector).copy()))
        return output

    DecoderLayer.__call__ = wrapped
    try:
        yield records
        if [key for key, _ in records] != visit_keys(text_config):
            raise RuntimeError("Observed decoder visits differ from configured loop schedule")
    finally:
        DecoderLayer.__call__ = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--mlx-lm", type=Path, help="PR #2086 checkout (optional if installed)")
    parser.add_argument("--prompts", type=Path, default=Path(__file__).resolve().parents[1] / "refusal/prompts.jsonl")
    parser.add_argument("--n", type=int, default=50, help="Total prompts per class, including holdouts")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--reasoning-effort", default="none")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = prepare_prompts(args.prompts, args.n, args.seed)
    if args.mlx_lm:
        sys.path.insert(0, str(args.mlx_lm.resolve()))
    import mlx.core as mx
    import mlx_lm

    config = json.loads((args.model / "config.json").read_text())
    if config.get("model_type") != "inkling2_loop":
        raise ValueError("Expected Inkling 2 loop architecture")
    model, tokenizer = mlx_lm.load(str(args.model), lazy=True)
    tokenizer = unwrap_tokenizer(tokenizer)
    model.eval()
    keys = visit_keys(config["text_config"])
    activations, token_positions = [], []
    for i, row in enumerate(rows):
        tokens, last = instruction_tokens(tokenizer, row["prompt"], args.reasoning_effort)
        if len(tokens) > args.max_tokens:
            raise ValueError(f'{row["id"]} exceeds --max-tokens; do not silently truncate')
        with capture_layers(model, last, config["text_config"]) as records:
            # Skip lm_head: only residual states are needed, no vocabulary logits.
            out = model.model.language_model(mx.array([tokens]))
            mx.eval(out)
        activations.append(np.stack([v for _, v in records]))
        token_positions.append(last)
        print(f'{i+1}/{len(rows)} {row["id"]} {row["split"]}', flush=True)
        if hasattr(mx, "clear_cache"):
            mx.clear_cache()
    metadata = dict(schema_version=1, seed=args.seed, model=str(args.model.resolve()),
                    config=config, mlx_lm_path=mlx_lm.__file__,
                    prompts_sha256=hashlib.sha256(args.prompts.read_bytes()).hexdigest(),
                    rows=rows, reasoning_effort=args.reasoning_effort,
                    activation_site="post_decoder_partial_block_residual",
                    token_site="last_user_instruction_content_token")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output, activations=np.stack(activations),
             labels=np.array([r["label"] for r in rows]),
             splits=np.array([r["split"] for r in rows]),
             layers=np.array([k[0] for k in keys]), passes=np.array([k[1] for k in keys]),
             token_positions=np.array(token_positions), metadata=json.dumps(metadata))
    args.output.with_suffix(".splits.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows))
    args.output.with_suffix(".eval.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows if row["split"] == "eval"))


if __name__ == "__main__":
    main()

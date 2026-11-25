"""Runtime pass-count override and per-pass activation hooks for inkling2_loop.

No fork and no monkeypatch of the PR is needed to change the pass count: the
PR reads ``args.loop_config["num_passes"]`` on every call (``TextModel._run_loop``,
``layer_visits``, ``Model.make_cache``), so ``pass_count`` just sets that value
temporarily. Only the single-pass ablation needs a (temporary, restored)
patch of ``DecoderLayer.__call__``, the same hook point direction/collect.py uses.
"""
from collections import Counter
from contextlib import contextmanager
import importlib
import sys
from pathlib import Path

import numpy as np

INKLING = Path(__file__).resolve().parents[2]
if str(INKLING) not in sys.path:
    sys.path.insert(0, str(INKLING))


def text_model(model):
    return model.model.language_model


def trained_passes(text_config):
    """Pass counts the checkpoint may be run at: any 1..5 for varloop, else only the trained count."""
    loop = text_config.get("loop_config")
    if not loop:
        raise ValueError("Not a looped model")
    return (1, 2, 3, 4, 5) if loop.get("is_varloop") else (loop["num_passes"],)


@contextmanager
def pass_count(model, n, allow_untrained=False):
    """Run the model at ``n`` loop passes inside the block; restores the original value."""
    loop = text_model(model).args.loop_config
    if loop is None:
        raise ValueError("Model has no loop_config")
    if not isinstance(n, int) or n < 1:
        raise ValueError("Pass count must be a positive integer")
    if n != loop["num_passes"] and not loop.get("is_varloop") and not allow_untrained:
        raise ValueError(f"Checkpoint is not a varloop model (is_varloop false): it was trained at "
                         f"{loop['num_passes']} passes, refusing {n}. Pass allow_untrained=True to force.")
    old = loop["num_passes"]
    loop["num_passes"] = n
    try:
        yield n
    finally:
        loop["num_passes"] = old


def text_config_at(text_config, n):
    """Copy of the HF text_config with num_passes=n (for collect.visit_keys / capture_layers)."""
    out = dict(text_config)
    out["loop_config"] = dict(text_config["loop_config"], num_passes=n)
    return out


@contextmanager
def visit_hook(model, fn):
    """Call ``fn(layer_index, loop_pass, output) -> output`` after every decoder visit.

    ``loop_pass`` is one-based. Visit counters reset whenever layer 0 runs, which is once per
    forward (it is in the prelude), so the numbering stays right across decode steps.
    """
    layers_mod = importlib.import_module("mlx_lm.models.inkling2.layers")
    DecoderLayer = layers_mod.DecoderLayer
    layers = text_model(model).layers
    indices = {id(layer): i for i, layer in enumerate(layers)}
    original = DecoderLayer.__call__
    counts = Counter()

    def wrapped(layer, *args, **kwargs):
        output = original(layer, *args, **kwargs)
        i = indices.get(id(layer))
        if i is None:
            return output
        if i == 0:
            counts.clear()
        counts[i] += 1
        return fn(i, counts[i], output)

    DecoderLayer.__call__ = wrapped
    try:
        yield
    finally:
        DecoderLayer.__call__ = original


def project_out(hidden, direction):
    """h - (h . r) r in float32, cast back; direction is unit norm, applied at every position."""
    import mlx.core as mx
    r = mx.array(np.asarray(direction, dtype=np.float32))
    h = hidden.astype(mx.float32)
    return (h - mx.sum(h * r, axis=-1, keepdims=True) * r).astype(hidden.dtype)


@contextmanager
def ablate_at_pass(model, directions):
    """Inference-time activation ablation, no weight edit.

    directions: {(layer_index, loop_pass): unit vector}, loop_pass one-based. A decoder visit is
    edited only if its (layer, pass) key is present, so a single pass is ablated by listing only
    that pass's keys. The direction is projected out of the layer's output hidden state at every
    token position. Non-core layers always count as pass 1.
    """
    def fn(layer, loop_pass, output):
        r = directions.get((layer, loop_pass))
        if r is None:
            return output
        return project_out(output[0], r), output[1]

    with visit_hook(model, fn):
        yield


def greedy_generate(model, tokens, max_tokens, eos_ids=()):
    """Greedy decode from a token id list; returns generated ids and whether it hit max_tokens."""
    import mlx.core as mx
    gen = importlib.import_module("mlx_lm.generate")
    out = []
    for token, _ in gen.generate_step(mx.array(tokens), model, max_tokens=max_tokens):
        token = int(token)
        out.append(token)
        if token in eos_ids:
            break
    return out, len(out) >= max_tokens and (not out or out[-1] not in eos_ids)

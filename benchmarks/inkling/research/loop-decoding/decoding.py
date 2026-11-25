"""Greedy loop-depth experiments for the unmodified mlx-lm Inkling PR.

Single request, text only, unsharded inference. No sampling or quantized KV caches.
"""
from copy import deepcopy
from dataclasses import dataclass, field
import sys
from pathlib import Path

import mlx.core as mx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'refusal-loops'))
from loops import pass_count, text_model


@dataclass
class Result:
    tokens: list = field(default_factory=list)
    accepted: list = field(default_factory=list)
    passes: list = field(default_factory=list)
    kls: list = field(default_factory=list)
    loop_work: int = 0


def forward(model, ids, n, cache):
    with pass_count(model, n):
        logits = model(mx.array([ids]), cache=cache)
    mx.eval(logits)
    return logits[0]


def new_cache(model, n):
    with pass_count(model, n):
        return model.make_cache()


def greedy(model, prompt, max_tokens, n=3, eos_ids=()):
    if not prompt or max_tokens < 0:
        raise ValueError('Nonempty prompt and nonnegative max_tokens required')
    cache = new_cache(model, n)
    logits = forward(model, prompt, n, cache)[-1]
    result = Result()
    for _ in range(max_tokens):
        token = int(mx.argmax(logits))
        result.tokens.append(token)
        result.passes.append(n)
        if token in eos_ids:
            break
        logits = forward(model, [token], n, cache)[-1]
    return result


def speculative(model, prompt, max_tokens, k=4, n_draft=1, n_verify=3, eos_ids=(),
                draft_transform=None):
    """Independent depth-specific caches; K-position target verification.

    Snapshot + replay is intentional: CacheList includes nontrimmable convolution
    states, and rotating caches may have overwritten history. Never trim just KV.
    draft_transform is an optional candidate perturbation hook for rollback tests.
    """
    if k < 1 or not prompt or max_tokens < 0:
        raise ValueError('Positive k, nonempty prompt, nonnegative max_tokens required')
    dc, vc = new_cache(model, n_draft), new_cache(model, n_verify)
    dl = forward(model, prompt, n_draft, dc)[-1]
    vl = forward(model, prompt, n_verify, vc)[-1]
    result = Result()
    while len(result.tokens) < max_tokens:
        ds, vs = deepcopy(dc), deepcopy(vc)
        draft = []
        for i in range(min(k, max_tokens - len(result.tokens))):
            token = int(mx.argmax(dl))
            if draft_transform:
                token = draft_transform(token, i)
            draft.append(token)
            dl = forward(model, [token], n_draft, dc)[-1]
            result.loop_work += n_draft
        verified = forward(model, draft, n_verify, vc)
        result.loop_work += n_verify * len(draft)
        predictions = [int(mx.argmax(vl))]
        if len(draft) > 1:
            predictions += mx.argmax(verified[:-1], axis=-1).tolist()
        accepted = 0
        for token, expected in zip(draft, predictions):
            if token != expected:
                break
            accepted += 1
        result.accepted.append(accepted)
        emitted = draft[:accepted]
        if accepted < len(draft):
            emitted.append(predictions[accepted])
            # Restore ALL cache metadata and arrays, including convolution tails.
            dc, vc = ds, vs
            result.loop_work += len(emitted) * (n_draft + n_verify)
            dl = forward(model, emitted, n_draft, dc)[-1]
            vl = forward(model, emitted, n_verify, vc)[-1]
        else:
            vl = verified[-1]
        for token in emitted:
            result.tokens.append(token)
            if token in eos_ids:
                return result
    return result


def kl(previous, current):
    """KL(previous || current), distributions represented by logits."""
    lp = previous - mx.logsumexp(previous, axis=-1)
    lq = current - mx.logsumexp(current, axis=-1)
    return max(0.0, float(mx.sum(mx.exp(lp) * (lp - lq))))


def adaptive_logits(model, ids, threshold, max_passes=3):
    """Cache-free reference exit: staged core, final block evaluated at each pass.

    Recompute the complete prefix per token. Thus skipped deeper KV entries never
    exist and never silently acquire the wrong positional offset. This provides
    a safe semantic reference, not a production cached adaptive decoder.
    """
    from mlx_lm.models.inkling2.layers import unweighted_rms_norm
    tm = text_model(model)
    core = tm.args.loop_core
    if max_passes < 1 or threshold < 0:
        raise ValueError('Positive max_passes and nonnegative threshold required')
    with pass_count(model, max_passes):
        h = tm.embed(mx.array([ids]))
        def run(layers, h, blocks, bank=None):
            for i, layer in enumerate(layers):
                messages = None if bank is None else tm.message_input(bank, i)
                h, blocks = layer(h, blocks, cache=None, conv_mask=None, messages=messages)
            return h, blocks
        prelude = run(tm.layers[:core.start], h, None)
        h, blocks = prelude
        previous, divergences = None, []
        for depth in range(1, max_passes + 1):
            bank = None
            if depth > 1:
                bank = (blocks[prelude[1].shape[0] + 1:],
                        unweighted_rms_norm(h.astype(mx.float32)))
                h, blocks = prelude
            h, blocks = run(tm.layers[core.start:core.stop], h, blocks, bank)
            tail, tail_blocks = run(tm.layers[core.stop:], h, blocks)
            normed = unweighted_rms_norm(tail.astype(mx.float32))
            tail = tm.norm(tm.final_input(tail_blocks, normed)[..., 0, :]).astype(h.dtype)
            logits = model.lm_head(tail).astype(mx.float32)
            cap = tm.args.final_logit_softcapping
            logits = (mx.tanh(logits / cap) * cap)[0, -1, :tm.args.unpadded_vocab_size]
            mx.eval(logits)
            if previous is not None:
                divergence = kl(previous, logits)
                divergences.append(divergence)
                if divergence < threshold:
                    return logits, depth, divergences
            previous = logits
        return logits, depth, divergences


def adaptive(model, prompt, max_tokens, threshold=5e-4, max_passes=3, eos_ids=()):
    if not prompt or max_tokens < 0:
        raise ValueError('Nonempty prompt and nonnegative max_tokens required')
    result = Result()
    for _ in range(max_tokens):
        logits, depth, divergences = adaptive_logits(
            model, prompt + result.tokens, threshold, max_passes)
        token = int(mx.argmax(logits))
        result.tokens.append(token)
        result.passes.append(depth)
        result.kls.append(divergences)
        if token in eos_ids:
            break
    return result

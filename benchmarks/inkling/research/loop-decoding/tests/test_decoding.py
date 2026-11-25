import mlx.core as mx
import pytest
from decoding import (adaptive, adaptive_logits, forward, greedy, new_cache,
                      speculative, text_model)
from loops import visit_hook

@pytest.mark.parametrize('k', [2, 4, 8])
@pytest.mark.parametrize('n', [1, 2])
def test_lossless(model, k, n):
    prompt = [1, 5, 2, 9, 4, 3, 7, 8, 6]
    expected = greedy(model, prompt, 12).tokens
    assert speculative(model, prompt, 12, k, n).tokens == expected


def test_rollback_all_states(model):
    prompt = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    expected = greedy(model, prompt, 12).tokens
    # First candidate correct; second deliberately wrong even at equal depth.
    def corrupt(token, i):
        return (token + 1) % 32 if i == 1 else token
    result = speculative(model, prompt, 12, k=4, n_draft=3, draft_transform=corrupt)
    assert result.tokens == expected
    assert 1 in result.accepted
    # Equal-depth drafts force the all-accepted path, beyond sliding window.
    result = speculative(model, prompt, 12, k=4, n_draft=3)
    assert result.tokens == expected
    assert result.accepted == [4, 4, 4]


def test_eos_and_lengths(model):
    first = greedy(model, [1, 2], 1).tokens[0]
    assert speculative(model, [1, 2], 10, eos_ids=[first]).tokens == [first]
    assert speculative(model, [1, 2], 0).tokens == []
    with pytest.raises(ValueError):
        speculative(model, [1], 3, k=0)


def test_pass_one_independent_of_total(model):
    captures = []
    for n in [1, 3, 5]:
        states = {}
        def hook(layer, loop_pass, output):
            if loop_pass == 1 and layer < 18:
                states[layer] = output[0]
            return output
        with visit_hook(model, hook):
            cache = new_cache(model, n)
            forward(model, [1, 2, 3, 4], n, cache)
            # Compare a subsequent cached visit as well as prompt prefill.
            prefill = dict(states)
            forward(model, [5], n, cache)
            states = {**{('prefill', i): h for i, h in prefill.items()},
                      **{('decode', i): h for i, h in states.items()}}
        captures.append(states)
    for states in captures[1:]:
        for layer, hidden in captures[0].items():
            assert float(mx.max(mx.abs(hidden - states[layer]))) == 0.0


def test_adaptive_exit(model):
    ids = [1, 2, 3, 4]
    full, depth, _ = adaptive_logits(model, ids, threshold=0)
    expected = forward(model, ids, 3, None)[-1]
    assert depth == 3
    assert float(mx.max(mx.abs(full - expected))) < 1e-5
    _, depth, divergences = adaptive_logits(model, ids, threshold=float('inf'))
    assert depth == 2 and len(divergences) == 1
    result = adaptive(model, ids, 5, threshold=float('inf'))
    assert result.passes == [2] * 5
    assert adaptive(model, ids, 5, threshold=0).tokens == greedy(model, ids, 5).tokens

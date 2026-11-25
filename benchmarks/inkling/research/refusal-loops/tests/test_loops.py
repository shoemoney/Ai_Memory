import numpy as np
import pytest

import loops
from direction.collect import capture_layers, visit_keys

TOKENS = [1, 2, 3, 4, 5]


def forward(model):
    import mlx.core as mx
    out = model.model.language_model(mx.array([TOKENS]))
    mx.eval(out)
    return np.array(out)


@pytest.mark.parametrize("n", [1, 2, 3, 5])
def test_pass_count_override_runs_n_passes(varloop, n):
    import mlx.core as mx
    model, config = varloop
    tcfg = loops.text_config_at(config["text_config"], n)
    with loops.pass_count(model, n):
        assert len(loops.text_model(model).layer_visits) == 12 + 12 * n
        assert len(model.make_cache()) == 12 + 12 * n
        with capture_layers(model, 3, tcfg) as records:
            mx.eval(model.model.language_model(mx.array([TOKENS])))
    assert [k for k, _ in records] == visit_keys(tcfg)
    assert {p for (i, p), _ in records if i == 6} == set(range(1, n + 1))


def test_override_restores_and_changes_output(varloop):
    model, _ = varloop
    base = forward(model)
    with loops.pass_count(model, 5):
        five = forward(model)
        with loops.pass_count(model, 1):
            one = forward(model)
        assert loops.text_model(model).args.loop_config["num_passes"] == 5
    assert loops.text_model(model).args.loop_config["num_passes"] == 3
    np.testing.assert_array_equal(forward(model), base)
    assert not np.allclose(five, base) and not np.allclose(one, base) and not np.allclose(one, five)
    with loops.pass_count(model, 3):
        np.testing.assert_array_equal(forward(model), base)


def test_override_restored_on_error(varloop):
    model, _ = varloop
    with pytest.raises(RuntimeError):
        with loops.pass_count(model, 2):
            raise RuntimeError("x")
    assert loops.text_model(model).args.loop_config["num_passes"] == 3


def test_non_varloop_refuses_other_counts(fixedloop):
    model, config = fixedloop
    assert loops.trained_passes(config["text_config"]) == (3,)
    with pytest.raises(ValueError, match="not a varloop"):
        with loops.pass_count(model, 5):
            pass
    with loops.pass_count(model, 3):
        pass
    with loops.pass_count(model, 2, allow_untrained=True):
        assert len(loops.text_model(model).layer_visits) == 36


def test_varloop_allows_one_to_five(varloop):
    assert loops.trained_passes(varloop[1]["text_config"]) == (1, 2, 3, 4, 5)


def record(model):
    """Run a forward under a recording hook; returns {(layer, pass): last-position vector}."""
    import mlx.core as mx
    seen = {}

    def fn(layer, p, output):
        seen[(layer, p)] = np.array(output[0][0, -1].astype(mx.float32))
        return output
    return seen, fn


def test_single_pass_ablation_only_touches_that_pass(varloop):
    import mlx.core as mx
    model, _ = varloop
    rng = np.random.default_rng(0)
    r = rng.standard_normal(8)
    r /= np.linalg.norm(r)
    base, fn = record(model)
    with loops.visit_hook(model, fn):
        mx.eval(model.model.language_model(mx.array([TOKENS])))
    abl, fn2 = record(model)
    with loops.ablate_at_pass(model, {(8, 2): r}):
        with loops.visit_hook(model, fn2):  # inner hook sees the edited output
            mx.eval(model.model.language_model(mx.array([TOKENS])))
    # Everything strictly before the edited visit is untouched, including pass 1 of layer 8.
    for key in [(i, 1) for i in range(8)] + [(6, 2), (7, 2), (8, 1)]:
        np.testing.assert_array_equal(abl[key], base[key])
    assert abs(abl[(8, 2)] @ r) < 1e-4 < abs(base[(8, 2)] @ r)
    # The edit propagates forward (pass 2 later layers, and pass 3 via messages) but pass-1 visits do not move.
    assert not np.allclose(abl[(9, 2)], base[(9, 2)])
    assert not np.allclose(abl[(17, 3)], base[(17, 3)])
    assert all(np.array_equal(abl[(i, 1)], base[(i, 1)]) for i in range(6, 18))


def test_ablating_last_pass_leaves_earlier_passes_identical(varloop):
    import mlx.core as mx
    model, _ = varloop
    r = np.ones(8) / np.sqrt(8)
    base, fn = record(model)
    with loops.visit_hook(model, fn):
        mx.eval(model.model.language_model(mx.array([TOKENS])))
    abl, fn2 = record(model)
    with loops.ablate_at_pass(model, {(l, 3): r for l in range(6, 18)}):
        with loops.visit_hook(model, fn2):
            mx.eval(model.model.language_model(mx.array([TOKENS])))
    for (l, p), v in base.items():
        if p < 3 and l < 18:
            np.testing.assert_array_equal(abl[(l, p)], v)
    assert abs(abl[(17, 3)] @ r) < 1e-4


def test_hooks_restored_and_no_hook_is_identity(varloop):
    from mlx_lm.models.inkling2.layers import DecoderLayer
    model, _ = varloop
    before = DecoderLayer.__call__
    base = forward(model)
    with loops.ablate_at_pass(model, {}):
        np.testing.assert_array_equal(forward(model), base)
    assert DecoderLayer.__call__ is before
    with pytest.raises(RuntimeError):
        with loops.ablate_at_pass(model, {(7, 1): np.ones(8) / np.sqrt(8)}):
            raise RuntimeError("x")
    assert DecoderLayer.__call__ is before


def test_pass_counter_resets_across_decode_steps(varloop):
    """Greedy generation does one forward per token; pass numbering must restart each step."""
    model, _ = varloop
    log = []
    with loops.pass_count(model, 2):
        with loops.visit_hook(model, lambda l, p, o: (log.append((l, p)), o)[1]):
            ids, _ = loops.greedy_generate(model, TOKENS, 3)
    assert len(ids) == 3
    assert max(p for _, p in log) == 2
    assert log.count((6, 2)) == log.count((6, 1)) >= 3  # prefill plus decode forwards


def test_generation_with_single_pass_ablation_runs(varloop):
    model, _ = varloop
    r = np.ones(8) / np.sqrt(8)
    with loops.pass_count(model, 3), loops.ablate_at_pass(model, {(l, 2): r for l in range(6, 18)}):
        ids, truncated = loops.greedy_generate(model, TOKENS, 4)
    assert len(ids) == 4 and truncated

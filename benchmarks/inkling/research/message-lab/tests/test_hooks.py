import numpy as np
import pytest
from hooks import MessageHook, pass_count
from run_message import run_forward
from hooks import visit_hook

TOKENS = [1, 2, 3, 4, 5]


def forward(model):
    import mlx.core as mx
    x = model(mx.array([TOKENS]))
    mx.eval(x)
    return np.array(x)


def visit_records(model):
    seen = {}
    def record(i, p, out):
        seen[(i, p)] = np.array(out[0])
        return out
    return seen, record


def test_capture_sham_and_restore(tiny):
    from mlx_lm.models.inkling2.layers import DecoderLayer, MessageGate
    decoder, gate = DecoderLayer.__call__, MessageGate.__call__
    base = forward(tiny)
    with MessageHook(tiny, 1, [6], [1, 2]) as capture:
        np.testing.assert_array_equal(forward(tiny), base)
        capture.assert_touched()
    assert capture.records[6]['message_before'].shape == (1, 2, 4, 8)
    assert set(capture.records[6]['gates']) == {'q', 'k', 'v', 'mlp'}
    with MessageHook(tiny, 1, [6], [1, 2], 'replace', {6: capture.records[6]['message_before']}):
        np.testing.assert_array_equal(forward(tiny), base)
    with pytest.raises(RuntimeError, match='planted'):
        with MessageHook(tiny, 1, [6], [1], 'zero'):
            raise RuntimeError('planted')
    assert DecoderLayer.__call__ is decoder and MessageGate.__call__ is gate
    np.testing.assert_array_equal(forward(tiny), base)


@pytest.mark.parametrize('mode', ['zero', 'replace', 'random', 'shuffle'])
def test_edit_only_selected_message_positions_and_norm(tiny, mode):
    import mlx.core as mx
    message = mx.arange(1*5*4*8, dtype=mx.float32).reshape(1, 5, 4, 8) + 1
    supplied = np.full((1, 2, 4, 8), 123., np.float32)
    hook = MessageHook(tiny, 1, [6], [1, 3], mode, {6: supplied})
    changed, _ = hook.edit(6, message)
    changed, raw = np.array(changed), np.array(message)
    np.testing.assert_array_equal(changed[:, [0, 2, 4]], raw[:, [0, 2, 4]])
    if mode == 'replace':
        np.testing.assert_array_equal(changed[:, [1, 3]], supplied)
    if mode == 'zero':
        assert not changed[:, [1, 3]].any()
    if mode == 'random':
        np.testing.assert_allclose(np.linalg.norm(changed[:, [1, 3]], axis=-1),
                                   np.linalg.norm(raw[:, [1, 3]], axis=-1), rtol=1e-6)
    if mode == 'shuffle':
        np.testing.assert_array_equal(changed[:, [1, 3]], raw[:, [3, 1]])


def test_boundary_scoping_and_signal_swap(tiny):
    base, fn = visit_records(tiny)
    with visit_hook(tiny, fn):
        forward(tiny)
    # A planted donor tensor passes unchanged into exactly the chosen message.
    signal = np.zeros((1, 1, 4, 8), np.float32)
    signal[..., 3] = 11.
    edited, fn = visit_records(tiny)
    with MessageHook(tiny, 1, [8], [2], 'replace', {8: signal}) as h, visit_hook(tiny, fn):
        forward(tiny)
        h.assert_touched()
    np.testing.assert_array_equal(h.records[8]['message_after'], signal)
    for key in [(i, 1) for i in range(18)] + [(6, 2), (7, 2)]:
        np.testing.assert_array_equal(base[key], edited[key])
    assert not np.allclose(base[(8, 2)], edited[(8, 2)])
    np.testing.assert_array_equal(base[(8, 2)][:, :2], edited[(8, 2)][:, :2])
    # Compare the actual captured donor from a different prompt as well.
    with MessageHook(tiny, 2, [8], [2]) as donor:
        import mlx.core as mx
        mx.eval(tiny(mx.array([[5, 4, 3, 2, 1]])))
    with MessageHook(tiny, 2, [8], [2], 'replace', {8: donor.records[8]['message_before']}) as recipient:
        forward(tiny)
    np.testing.assert_array_equal(recipient.records[8]['message_after'], donor.records[8]['message_before'])


def test_first_pass_injection_and_zero_all(tiny):
    with MessageHook(tiny, 2, [6], [2]) as cap:
        forward(tiny)
    with pass_count(tiny, 1):
        base = forward(tiny)
        with MessageHook(tiny, 0, [6], [2], 'replace', {6: cap.records[6]['message_before']}) as h:
            changed = forward(tiny)
            h.assert_touched()
        np.testing.assert_array_equal(base[:, :2], changed[:, :2])
        assert not np.allclose(base, changed)
    with MessageHook(tiny, -1, range(6, 18), None, 'zero') as h:
        changed = forward(tiny)
        h.assert_touched()
        assert all(v == 2 for v in h.events.values())
        assert all(not r['message_after'].any() for r in h.records.values())


def test_multiple_forwards_reset_visits_and_scope_other_models(tiny):
    with MessageHook(tiny, 2, [17], [0]) as h:
        forward(tiny)
        raw = h.records[17]['message_before'].copy()
        forward(tiny)
        np.testing.assert_array_equal(raw, h.records[17]['message_before'])
        assert h.events[17] == 2


def test_forward_scores_lm_head_and_pass_override(tiny):
    base = run_forward(tiny, TOKENS, [1, 2])
    changed = run_forward(tiny, TOKENS, [1, 2], 1)
    assert base['margin'] == pytest.approx(base['logits'][0] - base['logits'][1])
    assert changed['margin'] != pytest.approx(base['margin'])
    assert tiny.model.language_model.args.loop_config['num_passes'] == 3


def test_invalid_positions_and_nested_restore(tiny):
    with pytest.raises(ValueError):
        with MessageHook(tiny, 1, [6], [100]):
            forward(tiny)
    with MessageHook(tiny, 1, [6], [1]):
        with pytest.raises(RuntimeError, match='non-nestable'):
            with MessageHook(tiny, 2, [6], [1]):
                pass
        forward(tiny)


def test_class_hook_does_not_touch_another_model(tiny):
    from mlx_lm.models.inkling2.model import Model
    other = Model(tiny.args)
    other.eval()
    base = forward(other)
    with MessageHook(tiny, 1, [6], [1], 'zero') as hook:
        np.testing.assert_array_equal(forward(other), base)
        assert not hook.events
        forward(tiny)
        hook.assert_touched()

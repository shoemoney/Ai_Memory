"""Read-only capture; patches are scoped and restored, including on exceptions.

No public message-lab API existed when this adapter was written. All vectors use
only the final sequence position. Gate values are available DURING the receiving
pass, not at the end of the sending pass.
"""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import numpy as np

spec = importlib.util.spec_from_file_location('flip17_loops', Path(__file__).parents[1] / 'refusal-loops/loops.py')
loops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loops)
# Reuse the shared exact gate equation when the sibling implementation is available.
shared_path = Path(__file__).parents[1] / 'message-lab/hooks.py'
shared_gate_values = None
if shared_path.exists():
    shared_spec = importlib.util.spec_from_file_location('flip17_message_hooks', shared_path)
    shared = importlib.util.module_from_spec(shared_spec)
    shared_spec.loader.exec_module(shared)
    shared_gate_values = shared.gate_values

pass_count = loops.pass_count
text_model = loops.text_model


def to_numpy(x):
    """float32 NumPy copy of an MLX array; bfloat16 has no NumPy buffer format, so cast in MLX first."""
    import mlx.core as mx
    x = x.astype(mx.float32)
    mx.eval(x)
    return np.array(x).copy()


@contextmanager
def capture(model, layers):
    import mlx.core as mx
    from mlx_lm.models.inkling2.layers import MessageInput, MessageGate, unweighted_rms_norm
    tm = text_model(model)
    core = tm.args.loop_core
    gates = {id(getattr(tm.layers[i], f'{kind}_message_gate')): (i, kind)
             for i in core for kind in ('q', 'k', 'v', 'mlp')}
    out = dict(residual={}, message={}, gate={}, forget={})
    original_input, original_gate = MessageInput.__call__, MessageGate.__call__
    counts = {}

    def copy(x):
        return to_numpy(x)

    def visit(i, p, output):
        if i in layers and p == 1:
            out['residual'][i] = copy(output[0][0, -1])
        return output

    message_calls = {}
    def message(module, bank, i):
        result = original_input(module, bank, i)
        if module is tm.message_input:
            message_calls[i] = message_calls.get(i, 1) + 1
            p = message_calls[i]  # receiving pass (2 then 3)
            out['message'][p, i + core.start] = copy(result[0, -1])
        return result

    def gate(module, hidden, msg):
        result = original_gate(module, hidden, msg)
        key = gates.get(id(module))
        if key is not None:
            counts[key] = counts.get(key, 1) + 1
            p = counts[key]
            # Exact gate formula from PR #2086, no changes to forward output.
            if shared_gate_values is not None:
                forget, gain = shared_gate_values(module, hidden, msg)
            else:
                states = mx.concatenate([unweighted_rms_norm(hidden), unweighted_rms_norm(msg)], axis=-1)
                states = module.down_proj(states.astype(module.down_proj.weight.dtype)).astype(mx.float32)
                forget, gain = mx.tanh(module.forget_gate_proj(states)), mx.tanh(module.message_gate_proj(states))
            out['gate'][p, *key] = copy(gain[0, -1])
            out['forget'][p, *key] = copy(forget[0, -1])
        return result

    MessageInput.__call__, MessageGate.__call__ = message, gate
    try:
        with loops.visit_hook(model, visit):
            yield out
    finally:
        MessageInput.__call__, MessageGate.__call__ = original_input, original_gate


def flatten(mapping, pass_id=None):
    values = [v.reshape(-1) for k, v in sorted(mapping.items()) if pass_id is None or k[0] == pass_id]
    if not values:
        raise ValueError('Capture was empty; check architecture and selected layers')
    return np.concatenate(values)

"""Scoped, cache-free prefill interventions on PR #2086's inter-pass messages.

boundary b means pass b -> b+1; boundary 0 is explicit first-pass injection.
Class patches are scoped to model identities, serial only, and restored on error.
"""
from collections import Counter
from contextlib import contextmanager
import importlib
import importlib.util
from pathlib import Path
import numpy as np

REFUSAL = Path(__file__).resolve().parents[1] / 'refusal-loops'
_spec = importlib.util.spec_from_file_location('message_lab_loops', REFUSAL / 'loops.py')
_loops = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_loops)
pass_count, text_model, visit_hook = _loops.pass_count, _loops.text_model, _loops.visit_hook

_ACTIVE = False
ROLES = ('q', 'k', 'v', 'mlp')


def _numpy(x):
    import mlx.core as mx
    return np.array(x.astype(mx.float32))


def gate_values(gate, hidden, message):
    """Exact unmodified gate equations; returns (forget, gain), both signed tanh."""
    import mlx.core as mx
    from mlx_lm.models.inkling2.layers import unweighted_rms_norm
    x = mx.concatenate([unweighted_rms_norm(hidden), unweighted_rms_norm(message)], axis=-1)
    x = gate.down_proj(x.astype(gate.down_proj.weight.dtype)).astype(mx.float32)
    return mx.tanh(gate.forget_gate_proj(x)), mx.tanh(gate.message_gate_proj(x))


class MessageHook:
    def __init__(self, model, boundary, layers, positions=None, mode='capture', replacements=None, seed=16):
        if boundary < -1 or mode not in ('capture', 'zero', 'replace', 'random', 'shuffle'):
            raise ValueError('Invalid boundary or mode')
        if boundary == 0 and mode != 'replace':
            raise ValueError('Boundary 0 only supports explicit first-pass replacement')
        core = text_model(model).args.loop_core
        self.layers = set(layers)
        if not self.layers or not self.layers <= set(core):
            raise ValueError('Select nonempty subset of loop core layers')
        self.positions = None if positions is None else tuple(positions)
        if self.positions is not None and (not self.positions or len(set(self.positions)) != len(self.positions) or min(self.positions) < 0):
            raise ValueError('Positions must be unique nonnegative indices')
        self.model, self.boundary, self.mode = model, boundary, mode
        self.replacements = replacements or {}
        self.rng = np.random.default_rng(seed)
        self.records = {}
        self.events = Counter()
        self.history = {}

    def assert_touched(self):
        expected = text_model(self.model).args.loop_config['num_passes'] - 1 if self.boundary == -1 else 1
        if set(self.events) != self.layers or any(v != expected for v in self.events.values()):
            raise RuntimeError(f'Expected one cache-free prefill visit per selected layer; got {self.events}')

    def edit(self, layer, message):
        import mlx.core as mx
        positions = self.positions if self.positions is not None else tuple(range(message.shape[1]))
        if max(positions) >= message.shape[1]:
            raise ValueError('Position out of bounds (use full prefill, no KV cache)')
        idx = mx.array(positions)
        selected = message[:, idx, :, :]
        raw = _numpy(selected)
        if self.mode == 'zero':
            changed = mx.zeros_like(selected)
        elif self.mode == 'replace':
            changed = mx.array(self.replacements[layer]).astype(message.dtype)
            if changed.shape != selected.shape:
                raise ValueError(f'Replacement shape {changed.shape} != {selected.shape}')
        elif self.mode == 'random':
            noise = self.rng.standard_normal(raw.shape).astype(np.float32)
            noise *= np.linalg.norm(raw, axis=-1, keepdims=True) / np.maximum(np.linalg.norm(noise, axis=-1, keepdims=True), 1e-12)
            changed = mx.array(noise).astype(message.dtype)
        elif self.mode == 'shuffle':
            if len(positions) < 2:
                raise ValueError('Shuffle needs at least two positions')
            order = self.rng.permutation(len(positions))
            if np.array_equal(order, np.arange(len(positions))):
                order = np.roll(order, 1)
            changed = selected[:, mx.array(order), :, :]
        else:
            changed = selected
        self.records[layer] = dict(message_before=raw, message_after=_numpy(changed), gates={})
        self.events[layer] += 1
        updated = mx.array(message)
        updated[:, idx, :, :] = changed
        return updated, positions

    @contextmanager
    def context(self):
        global _ACTIVE
        if _ACTIVE:
            raise RuntimeError('MessageHook contexts are serial and non-nestable')
        import mlx.core as mx
        mod = importlib.import_module('mlx_lm.models.inkling2.layers')
        decoder_original, gate_original = mod.DecoderLayer.__call__, mod.MessageGate.__call__
        tm = text_model(self.model)
        indices = {id(l): i for i, l in enumerate(tm.layers)}
        gates = {id(getattr(tm.layers[i], role + '_message_gate')): (i, j, role)
                 for i in self.layers for j, role in enumerate(ROLES)}
        counts = Counter()
        active = {}

        def decoder(layer, *args, **kwargs):
            i = indices.get(id(layer))
            if i is None:
                return decoder_original(layer, *args, **kwargs)
            if i == 0:
                counts.clear()
            counts[i] += 1
            if i not in self.layers or not (counts[i] > 1 if self.boundary == -1 else counts[i] == self.boundary + 1):
                return decoder_original(layer, *args, **kwargs)
            raw = kwargs.get('messages')
            if self.boundary == 0:
                hidden = args[0]
                raw = mx.zeros((*hidden.shape[:-1], 4, hidden.shape[-1]), mx.float32)
            if raw is None:
                raise RuntimeError('No incoming message at requested boundary')
            changed, positions = self.edit(i, raw)
            active[i] = (raw, positions)
            kwargs['messages'] = changed
            try:
                return decoder_original(layer, *args, **kwargs)
            finally:
                self.history[(counts[i] - 1, i)] = self.records[i]
                active.pop(i, None)

        def gate(g, hidden, message):
            loc = gates.get(id(g))
            if loc is None or loc[0] not in active:
                return gate_original(g, hidden, message)
            i, channel, role = loc
            raw, positions = active[i]
            idx = mx.array(positions)
            # Local pre-intervention gate, evaluated on the recipient hidden state.
            # Later selected layers may already include upstream intervention effects.
            f, gain = gate_values(g, hidden[:, idx], raw[:, idx, channel, :])
            ef, eg = gate_values(g, hidden[:, idx], message[:, idx])
            self.records[i]['gates'][role] = dict(forget_before=_numpy(f), gain_before=_numpy(gain),
                forget_after=_numpy(ef), gain_after=_numpy(eg),
                contribution_norm_before=_numpy(mx.linalg.norm(gain * raw[:, idx, channel, :], axis=-1)))
            out = gate_original(g, hidden, message)
            if self.boundary == 0:
                # The native first pass skips gates. Preserve that outside selected positions.
                injected = mx.array(hidden)
                injected[:, idx, :] = out[:, idx, :]
                out = injected
            return out

        _ACTIVE = True
        mod.DecoderLayer.__call__, mod.MessageGate.__call__ = decoder, gate
        try:
            yield self
        finally:
            mod.DecoderLayer.__call__, mod.MessageGate.__call__ = decoder_original, gate_original
            _ACTIVE = False

    def __enter__(self):
        self._context = self.context()
        return self._context.__enter__()

    def __exit__(self, *exc):
        return self._context.__exit__(*exc)


def diagnostics(records):
    """Small JSON summary; full selected tensors remain available in hook.records."""
    return {str(i): dict(message_norm_mean=float(np.linalg.norm(r['message_before'], axis=-1).mean()),
        message_norm_max=float(np.linalg.norm(r['message_before'], axis=-1).max()),
        gates={role: {key + '_mean': float(value.mean()) for key, value in vals.items()} |
               {key + '_abs_mean': float(np.abs(value).mean()) for key, value in vals.items()}
               for role, vals in r['gates'].items()}) for i, r in records.items()}

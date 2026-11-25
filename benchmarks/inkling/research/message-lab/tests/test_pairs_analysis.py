import json
from pathlib import Path
import re
import numpy as np
import pytest
import pairs
import analysis
from run_message import Journal, read_rows


class ToyTokenizer:
    """Lossless tokens; objects single-token, synthetic identifiers character-tokenized."""
    def __init__(self):
        self.vocab = {}

    def encode(self, text, add_special_tokens=False):
        chunks = re.findall('|'.join(pairs.ITEMS) + r'|[\s\S]', text)
        return [self.vocab.setdefault(c, len(self.vocab)) for c in chunks]

    def apply_chat_template(self, messages, **kwargs):
        return '<user>' + messages[0]['content'] + '</user>'


def test_generate_300_aligned_balanced_and_deterministic():
    data = pairs.build(ToyTokenizer())
    assert data['n'] == len(data['pairs']) == 300
    assert [sum(p['template'] == t for p in data['pairs']) for t in range(3)] == [100]*3
    assert sum(p['split'] == 'heldout' for p in data['pairs']) == 100
    assert data == pairs.build(ToyTokenizer())
    for p in data['pairs']:
        a, b = p['tokens']
        assert len(a) == len(b)
        assert {i for i, (x, y) in enumerate(zip(a, b)) if x != y} <= set(p['bridge_positions'])
        assert len(p['irrelevant_positions']) == len(p['bridge_positions'])
        assert not set(p['irrelevant_positions']) & set(p['bridge_positions'])
        assert p['prompts'][0].split('Session 2')[1] == p['prompts'][1].split('Session 2')[1]
        ca, cb = p['control_tokens']
        assert len(ca) == len(cb)
        assert {i for i, (x, y) in enumerate(zip(ca, cb)) if x != y} <= set(p['control_bridge_positions'])
        assert p['controls'][0]['answer'] == p['controls'][1]['answer'] == p['answers'][0]


def test_reject_unaligned_or_more_than_bridge_change():
    tok = ToyTokenizer()
    original = pairs.build(tok, 3)['pairs'][0]
    prompts = original['prompts'].copy()
    prompts[1] += 'x'
    assert pairs.align(tok, prompts, original['bridge_character_spans'], original['irrelevant_character_spans']) is None


def test_official_shipped_pairs_alignment_offline():
    # No network: tokenizer is optional, but the shipped token arrays are always checked.
    data = json.loads((Path(__file__).resolve().parents[1] / 'pairs300.json').read_text())
    assert len(data['pairs']) == 300
    for p in data['pairs']:
        assert len(p['tokens'][0]) == len(p['tokens'][1])
        assert len(p['bridge_positions']) >= 2
        assert len(p['bridge_positions']) == len(p['irrelevant_positions'])
        assert {i for i, (a, b) in enumerate(zip(*p['tokens'])) if a != b} <= set(p['bridge_positions'])
    payload = dict(data)
    fp = payload.pop('fingerprint')
    assert fp == pairs.fingerprint(payload)


def test_bootstrap_pairs_not_directions_and_recovery():
    rows = [dict(pair=f'p{i}', x=float(i)) for i in range(5) for _ in range(2)]
    interval = analysis.cluster_interval(rows, lambda r: r['x'], 500)
    assert interval['n_pairs'] == 5 and interval['n_observations'] == 10
    assert interval['mean'] == 2 and interval['low'] <= 2 <= interval['high']
    ratio = analysis.ratio_interval([dict(pair=str(i), gain=1, gap=2) for i in range(5)], 500)
    assert ratio['ratio'] == ratio['low'] == ratio['high'] == .5
    null = analysis.ratio_interval([dict(pair=str(i), gain=1, gap=0) for i in range(5)], 500)
    assert null['ratio'] is None


def test_resume_tail_recovery_and_no_duplicates(tmp_path):
    path = tmp_path / 'rows.jsonl'
    path.write_bytes(b'{"key":"a"}\n{"key":')
    journal = Journal(path)
    journal.add(dict(key='a'))
    journal.add(dict(key='b'))
    assert [r['key'] for r in read_rows(path)] == ['a', 'b']
    path.write_text('{"key":"a"}')
    Journal(path).add(dict(key='b'))
    assert [r['key'] for r in read_rows(path)] == ['a', 'b']
    path.write_text('bad\n{"key":"a"}\n')
    with pytest.raises(ValueError):
        read_rows(path)


def test_analysis_and_svg_pipeline(tmp_path):
    from plots import draw
    rows = []
    for i in range(4):
        for side in range(2):
            meta = dict(pair=str(i), side=side, split='heldout', template=2, task='two_hop', block='6-11', boundary=1)
            for c, shift in [('swap', 1.), ('sham', 0.)]:
                rows.append(dict(**meta, experiment='swap', condition=c, margin=1-shift, donor_shift=shift,
                                 flip=False, recipient_initially_correct=True, argmax_to_donor=False))
            rows.append(dict(**meta, experiment='zero', condition='zero_all', margin=.5, baseline1=0, baseline3=1))
            rows.append(dict(**meta, experiment='injection', condition='inject', margin=.5, gain=.5, gap=1, recovery=.5))
    report = analysis.summarize(rows, 200)
    assert report['contrasts'][0]['swap_minus_control']['mean'] == 1
    assert 'sham' in analysis.control_table(report)
    draw(report, tmp_path)
    for name in ('swap', 'zero', 'injection'):
        assert '<svg' in (tmp_path / (name + '.svg')).read_text()


def test_runner_complete_matrix_and_resume_without_forwards(monkeypatch, tmp_path):
    """Condition planner coverage with fake forwards; causal execution is tested separately."""
    import run_message as runner
    from types import SimpleNamespace
    # The causal model/hook paths are covered above; this test checks the full scheduler,
    # diagnostics consumption, direction labels and idempotent journal separately.
    pair = pairs.build(ToyTokenizer(), 3)['pairs'][0]
    calls = []
    def fake_forward(model, tokens, answers, passes=3, hook=None, allow_untrained=False):
        calls.append((passes, None if hook is None else hook.mode))
        if hook is not None:
            raw = np.ones((1, len(hook.positions or [0]), 4, 8), np.float32)
            for i in hook.layers:
                hook.records[i] = dict(message_before=raw, message_after=raw, gates={})
                hook.history[(hook.boundary, i)] = hook.records[i]
        return dict(margin=float(passes), choice=1, argmax=answers[0], logits=[float(passes), 0.])
    monkeypatch.setattr(runner, 'run_forward', fake_forward)
    class FakeHook:
        def __init__(self, model, boundary, layers, positions=None, mode='capture', *args, **kwargs):
            self.boundary, self.layers, self.positions, self.mode = boundary, set(layers), positions, mode
            self.records, self.history = {}, {}
    monkeypatch.setattr(runner, 'MessageHook', FakeHook)
    journal = runner.Journal(tmp_path / 'results.jsonl')
    args = SimpleNamespace(allow_untrained=False, boundaries=[1, 2], seed=16)
    runner.run_pair(None, ToyTokenizer(), pair, journal, args)
    rows = runner.read_rows(journal.path)
    assert len(rows) == 60
    assert len(calls) == 76
    assert sum(r['experiment'] == 'swap' for r in rows) == 40
    assert sum(r['experiment'] == 'injection' for r in rows) == 8
    analysis.validate_complete(rows, dict(planned_pairs=[pair['id']], boundaries=[1, 2]))
    with pytest.raises(ValueError, match='missing'):
        analysis.validate_complete(rows[:-1], dict(planned_pairs=[pair['id']], boundaries=[1, 2]))
    runner.run_pair(None, ToyTokenizer(), pair, journal, args)
    assert len(calls) == 76 and len(runner.read_rows(journal.path)) == 60

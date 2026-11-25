"""Study 16: serial cache-free paired message interventions, append-only JSONL."""
import argparse
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import pairs
from hooks import MessageHook, diagnostics, pass_count, text_model, REFUSAL

HERE = Path(__file__).resolve().parent
BLOCKS = {'6-11': list(range(6, 12)), '12-17': list(range(12, 18))}


def run_forward(model, tokens, answer_tokens, passes=3, hook=None, allow_untrained=False):
    import mlx.core as mx
    with pass_count(model, passes, allow_untrained=allow_untrained), hook if hook is not None else nullcontext():
        logits = model(mx.array([tokens]))
        mx.eval(logits)
        scores = np.array(logits[0, -1].astype(mx.float32))
        if hook is not None:
            hook.assert_touched()
    # Own answer minus paired foil; donor-directed changes negate this margin.
    a, b = answer_tokens
    return dict(margin=float(scores[a] - scores[b]), choice=int(scores[a] > scores[b]),
                argmax=int(scores.argmax()), logits=[float(scores[a]), float(scores[b])])


def stable_seed(key, seed):
    return int.from_bytes(hashlib.sha256(f'{seed}:{key}'.encode()).digest()[:4], 'big')


def read_rows(path):
    """Recover only an interrupted final append; malformed interior rows are errors."""
    if not path.exists():
        return []
    raw = path.read_bytes()
    rows, consumed = [], 0
    for i, line in enumerate(raw.splitlines(keepends=True)):
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            if consumed + len(line) != len(raw):
                raise ValueError(f'Corrupt interior JSON row {i}')
            with path.open('r+b') as fh:
                fh.truncate(consumed)
            break
        rows.append(row)
        consumed += len(line)
    # A complete but newline-less final row must not merge with the next append.
    if rows and path.stat().st_size and not path.read_bytes().endswith(b'\n'):
        with path.open('ab') as fh:
            fh.write(b'\n')
    return rows


class Journal:
    def __init__(self, path):
        self.path = path
        self.done = {r['key'] for r in read_rows(path)}

    def add(self, row):
        if row['key'] in self.done:
            return
        with self.path.open('a') as fh:
            fh.write(json.dumps(row, allow_nan=False) + '\n')
            fh.flush()
            os.fsync(fh.fileno())
        self.done.add(row['key'])
        print(row['key'], flush=True)


def item_meta(pair, side, task='two_hop'):
    return dict(pair=pair['id'], side=side, template=pair['template'], split=pair['split'], task=task)


def cell_key(meta, experiment, block, boundary, condition):
    return f"{meta['pair']}/{meta['task']}/{meta['side']}/{experiment}/{block}/{boundary}/{condition}"


def run_pair(model, tok, pair, journal, args):
    expected = []
    for task in ('two_hop', 'single_hop'):
        for side in range(2):
            meta = item_meta(pair, side, task)
            expected.extend(cell_key(meta, 'zero', 'all', -1, c) for c in ('intact1', 'intact3', 'zero_all'))
    for boundary in args.boundaries:
        for block in BLOCKS:
            for side in range(2):
                meta = item_meta(pair, side)
                expected.extend(cell_key(meta, 'swap', block, boundary, c)
                                for c in ('swap', 'sham', 'irrelevant', 'random', 'shuffle'))
                expected.append(cell_key(meta, 'injection', block, boundary, 'inject'))
    if all(key in journal.done for key in expected):
        return
    aligned = pairs.align(tok, pair['prompts'], pair['bridge_character_spans'], pair['irrelevant_character_spans'])
    if aligned is None or aligned['tokens'] != pair['tokens'] or aligned['bridge_positions'] != pair['bridge_positions']:
        raise ValueError('Tokenizer mismatch or corrupt alignment')
    baselines = {}
    for task in ('two_hop', 'single_hop'):
        prompts = pair['prompts'] if task == 'two_hop' else [x['prompt'] for x in pair['controls']]
        for side in range(2):
            meta = item_meta(pair, side, task)
            tokens = pairs.encode(tok, pairs.render(tok, prompts[side]))
            if task == 'single_hop' and tokens != pair['control_tokens'][side]:
                raise ValueError('Single-hop tokenizer mismatch')
            own = side if task == 'two_hop' else 0
            answer_ids = [pair['answer_tokens'][own], pair['answer_tokens'][1-own]]
            for n in (1, 3):
                key = cell_key(meta, 'zero', 'all', -1, f'intact{n}')
                # Recompute small intact baselines for unfinished dependent cells, even on resume.
                baseline_hook = MessageHook(model, -1, range(6, 18), None) if n == 3 else None
                result = run_forward(model, tokens, answer_ids, n, baseline_hook, args.allow_untrained)
                if baseline_hook is not None:
                    result['diagnostics'] = diagnostics(baseline_hook.history)
                    del baseline_hook
                baselines[(task, side, n)] = result
                journal.add(dict(key=key, experiment='zero', condition=f'intact{n}', block='all', boundary=-1,
                                 **meta, **result))
            key = cell_key(meta, 'zero', 'all', -1, 'zero_all')
            if key not in journal.done:
                hook = MessageHook(model, -1, range(6, 18), None, 'zero', seed=args.seed)
                result = run_forward(model, tokens, answer_ids, hook=hook, allow_untrained=args.allow_untrained)
                journal.add(dict(key=key, experiment='zero', condition='zero_all', block='all', boundary=-1,
                    **meta, **result, baseline3=baselines[(task, side, 3)]['margin'],
                    baseline1=baselines[(task, side, 1)]['margin'], diagnostics=diagnostics(hook.history),
                    baseline_diagnostics=baselines[(task, side, 3)]['diagnostics'],
                    diagnostic_scope='all boundaries; local gate inputs can include earlier intervention effects'))

    for boundary in args.boundaries:
        for block, layers in BLOCKS.items():
            conditions = ('swap', 'sham', 'irrelevant', 'random', 'shuffle')
            todo = [cell_key(item_meta(pair, side), expt, block, boundary, c)
                    for side in range(2) for expt, cs in [('swap', conditions), ('injection', ('inject',))] for c in cs]
            if all(key in journal.done for key in todo):
                continue
            captured = {}
            for side in range(2):
                answer_ids = [pair['answer_tokens'][side], pair['answer_tokens'][1-side]]
                for site in ('bridge', 'irrelevant'):
                    hook = MessageHook(model, boundary, layers, pair[f'{site}_positions'])
                    base = run_forward(model, pair['tokens'][side], answer_ids, hook=hook,
                                       allow_untrained=args.allow_untrained)
                    captured[(side, site)] = (hook.records, base)
            for side in range(2):
                meta = item_meta(pair, side)
                answer_ids = [pair['answer_tokens'][side], pair['answer_tokens'][1-side]]
                for condition in conditions:
                    key = cell_key(meta, 'swap', block, boundary, condition)
                    if key in journal.done:
                        continue
                    site = 'irrelevant' if condition == 'irrelevant' else 'bridge'
                    donor = side if condition in ('sham', 'random', 'shuffle') else 1-side
                    records, base = captured[(side, site)]
                    source = {i: r['message_before'] for i, r in captured[(donor, site)][0].items()}
                    mode = condition if condition in ('random', 'shuffle') else 'replace'
                    hook = MessageHook(model, boundary, layers, pair[f'{site}_positions'], mode, source,
                                       stable_seed(key, args.seed))
                    result = run_forward(model, pair['tokens'][side], answer_ids, hook=hook,
                                         allow_untrained=args.allow_untrained)
                    # Donor margin = -recipient margin for the two alternatives.
                    journal.add(dict(key=key, experiment='swap', condition=condition, block=block, boundary=boundary,
                        **meta, **result, baseline_margin=base['margin'], donor_shift=base['margin']-result['margin'],
                        flip=bool(base['margin'] > 0 and result['margin'] < 0),
                        recipient_initially_correct=base['margin'] > 0,
                        argmax_to_donor=bool(base['argmax'] != answer_ids[1] and result['argmax'] == answer_ids[1]),
                        baseline_diagnostics=diagnostics(records), diagnostics=diagnostics(hook.records)))
                key = cell_key(meta, 'injection', block, boundary, 'inject')
                if key not in journal.done:
                    source = {i: r['message_before'] for i, r in captured[(side, 'bridge')][0].items()}
                    hook = MessageHook(model, 0, layers, pair['bridge_positions'], 'replace', source)
                    result = run_forward(model, pair['tokens'][side], answer_ids, 1, hook, args.allow_untrained)
                    m1, m3 = (baselines[('two_hop', side, n)]['margin'] for n in (1, 3))
                    gap = m3 - m1
                    journal.add(dict(key=key, experiment='injection', condition='inject', block=block, boundary=boundary,
                        **meta, **result, baseline1=m1, baseline3=m3, gap=gap, gain=result['margin']-m1,
                        recovery=(result['margin']-m1)/gap if abs(gap) > 1e-6 else None,
                        source_diagnostics=diagnostics(captured[(side, 'bridge')][0]), diagnostics=diagnostics(hook.records)))
    import mlx.core as mx
    if hasattr(mx, 'clear_cache'):
        mx.clear_cache()


def manifest(args, data):
    config = json.loads((args.model / 'config.json').read_text())
    source_hashes = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                     for name in ('hooks.py', 'pairs.py', 'run_message.py')}
    source_hashes['refusal-loops/loops.py'] = hashlib.sha256((REFUSAL / 'loops.py').read_bytes()).hexdigest()
    import inspect
    from mlx_lm.models.inkling2 import layers as model_layers, model as model_module
    for name, module in (('pr_layers.py', model_layers), ('pr_model.py', model_module)):
        source_hashes[name] = hashlib.sha256(Path(inspect.getfile(module)).read_bytes()).hexdigest()
    from importlib.metadata import version, PackageNotFoundError
    versions = {}
    for name in ('mlx', 'mlx-lm', 'numpy', 'transformers'):
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = 'unavailable'
    files = {p.name: dict(bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns)
             for p in args.model.glob('*.safetensors')}
    planned = [p['id'] for p in data['pairs'] if args.split == 'all' or p['split'] == args.split]
    if args.limit:
        planned = planned[:args.limit]
    return dict(schema=1, model=str(args.model.resolve()), config=config, weights=files, planned_pairs=planned, versions=versions,
                dataset=pairs.fingerprint(data), sources=source_hashes, seed=args.seed,
                limit=args.limit, split=args.split, boundaries=args.boundaries, allow_untrained=args.allow_untrained,
                estimand='immediate next-token forced-choice logit margin; no generated reasoning')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--pairs', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--mlx-lm', type=Path)
    ap.add_argument('--split', choices=('discovery', 'heldout', 'all'), default='discovery')
    ap.add_argument('--boundaries', default='1,2')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--seed', type=int, default=16)
    ap.add_argument('--allow-untrained', action='store_true', help='Explicitly allow Mini one-pass ablations')
    args = ap.parse_args()
    args.boundaries = [int(x) for x in args.boundaries.split(',')]
    if not args.boundaries or not set(args.boundaries) <= {1, 2}:
        ap.error('The registered three-pass study has boundaries 1 and 2')
    if args.mlx_lm:
        sys.path.insert(0, str(args.mlx_lm.resolve()))
    import mlx_lm
    model, tok = mlx_lm.load(str(args.model), lazy=True)
    # Processor wrappers delegate inconsistently across installed transformers versions.
    while hasattr(tok, 'tokenizer'):
        tok = tok.tokenizer
    model.eval()
    if list(text_model(model).args.loop_core) != list(range(6, 18)):
        raise ValueError('Study requires 24-layer Inkling with core 6:18')
    data = json.loads(args.pairs.read_text())
    rows = [p for p in data['pairs'] if args.split == 'all' or p['split'] == args.split]
    if args.limit:
        rows = rows[:args.limit]
    args.out.mkdir(parents=True, exist_ok=True)
    state = manifest(args, data)
    path = args.out / 'manifest.json'
    if path.exists() and json.loads(path.read_text()) != state:
        raise ValueError('Resume manifest differs; choose a new output directory')
    path.write_text(json.dumps(state, indent=2) + '\n')
    journal = Journal(args.out / 'results.jsonl')
    started = time.monotonic()
    for pair in rows:
        run_pair(model, tok, pair, journal, args)
    (args.out / 'timing.json').write_text(json.dumps(dict(seconds_this_invocation=time.monotonic()-started,
                                                          completed_records=len(journal.done))) + '\n')


if __name__ == '__main__':
    main()

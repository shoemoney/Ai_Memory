"""Fixed subset and memory-only batch adapter; original labs files stay unchanged."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
LABS = REPO / 'benchmarks/inkling/labs'
SEED = 20261125


def read(path):
    return json.loads(Path(path).read_text())


def stratified(rows, n, key, ident):
    groups = defaultdict(list)
    for row in rows:
        groups[str(key(row))].append(row)
    counts = {k: int(n * len(v) / len(rows)) for k, v in groups.items()}
    remainder = sorted(groups, key=lambda k: (-(n * len(groups[k]) / len(rows) - counts[k]), k))
    for k in remainder[:n - sum(counts.values())]:
        counts[k] += 1
    rng = random.Random(SEED)
    picked = []
    for k in sorted(groups):
        picked.extend(rng.sample(sorted(groups[k], key=ident), counts[k]))
    rng.shuffle(picked)
    return [ident(r) for r in picked]


def selection():
    long = read(REPO / 'benchmarks/longmemeval/results/full/manifest.json')['items']
    loco_root = REPO / 'benchmarks/locomo/results/full'
    matched = set(read(loco_root / 'matched-summary.json')['item_ids'])
    loco = [r for r in read(loco_root / 'selection.json') if r['item_id'] in matched]
    return dict(seed=SEED, method='largest-remainder proportional strata, sorted IDs, seeded sample then shuffle',
                longmemeval=stratified(long, 48, lambda r: r['stratum'], lambda r: r['question_id']),
                locomo=stratified(loco, 24, lambda r: (r['conversation'], r['category']), lambda r: r['item_id']))


def run_memory(lab, passes, selected_path, args):
    sys.path.insert(0, str(LABS))
    import memory
    chosen = read(selected_path)[lab]
    if not chosen or len(chosen) != len(set(chosen)):
        raise ValueError('Empty or duplicate subset')
    original_read, original_arguments = memory.read, memory.arguments
    archive = REPO / f'benchmarks/{lab}/results/full'

    def reordered_read(path):
        value = original_read(path)
        if Path(path) == archive / 'manifest.json' and lab == 'longmemeval':
            rows = value['items']
            lookup = {r['question_id']: r for r in rows}
            value['items'] = [lookup[q] for q in chosen] + [r for r in rows if r['question_id'] not in chosen]
        if Path(path) == archive / 'matched-summary.json' and lab == 'locomo':
            if not set(chosen).issubset(value['item_ids']):
                raise ValueError('Subset outside book matched IDs')
            value['item_ids'] = chosen + [q for q in value['item_ids'] if q not in chosen]
        return value

    def arguments(description):
        parser = original_arguments(description)
        parser._option_string_actions['--variant'].choices = [f'varloop-p{passes}']
        return parser

    memory.read, memory.arguments = reordered_read, arguments
    sys.argv = [str(LABS / 'memory.py'), lab, '--variant', f'varloop-p{passes}',
                '--limit', str(len(chosen)), '--thinking-budget', '0', *args]
    memory.main()


def batch(passes, selected_path, output_root, model, base, hook, batch_size=10, judges=None):
    if passes not in (1, 2, 3, 5) or batch_size < 1:
        raise ValueError('Invalid passes or batch size')
    root = Path(output_root) / f'varloop-p{passes}'
    root.mkdir(parents=True, exist_ok=True)
    provenance = dict(protocol='varloop-memory-screen-v1', passes=passes, selection=read(selected_path),
                      selection_sha256=hashlib.sha256(Path(selected_path).read_bytes()).hexdigest(),
                      adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      model=model, base_url=base, thinking_budget=0, batch_size=batch_size)
    path = root / 'study.json'
    if path.exists() and read(path) != provenance:
        raise RuntimeError('Study settings changed; choose a fresh results directory')
    path.write_text(json.dumps(provenance, indent=2) + '\n')
    ran = False
    for lab in ('longmemeval', 'locomo'):
        command = [sys.executable, str(Path(__file__)), 'memory', lab, '--passes', str(passes),
                   '--selection', str(selected_path), '--output-root', str(output_root),
                   '--model', model, '--base-url', base, '--batch-size', str(batch_size)]
        if judges and judges.get(lab):
            command += ['--judge-base-url', judges[lab]]
        previous = -1
        while True:
            # Same checked shell-hook boundary as labs/batch.py, including lab transitions.
            if ran:
                subprocess.run(hook, shell=True, check=True)
            subprocess.run(command, check=True)
            ran = True
            state = read(root / lab / 'summary.json')
            if state['complete']:
                break
            if state['completed'] <= previous:
                raise RuntimeError(f'No progress in {lab}')
            previous = state['completed']


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('action', choices=['select', 'memory', 'batch'])
    p.add_argument('lab', nargs='?', choices=['longmemeval', 'locomo'])
    p.add_argument('--passes', type=int, choices=[1, 2, 3, 5])
    p.add_argument('--selection', type=Path, default=HERE / 'selection.json')
    p.add_argument('--output-root', type=Path, default=REPO / 'benchmarks/inkling/results')
    p.add_argument('--model')
    p.add_argument('--base-url', default='http://127.0.0.1:39851/v1')
    p.add_argument('--restart-hook')
    p.add_argument('--batch-size', type=int, default=10)
    p.add_argument('--longmemeval-judge-base-url', default='http://127.0.0.1:39711/v1')
    p.add_argument('--locomo-judge-base-url', default='http://127.0.0.1:39700/v1')
    a, extra = p.parse_known_args()
    if a.action == 'select':
        a.selection.write_text(json.dumps(selection(), indent=2) + '\n')
    elif a.action == 'memory':
        if not a.lab or not a.passes or not a.model:
            p.error('memory requires lab, passes, model')
        run_memory(a.lab, a.passes, a.selection,
                   ['--output-root', str(a.output_root), '--model', a.model, '--base-url', a.base_url,
                    '--batch-size', str(a.batch_size), *extra])
    else:
        if not a.passes or not a.model or not a.restart_hook or extra:
            p.error('batch requires passes, model, restart-hook and no unknown flags')
        batch(a.passes, a.selection, a.output_root, a.model, a.base_url, a.restart_hook, a.batch_size,
              {lab: getattr(a, lab + '_judge_base_url') for lab in ('longmemeval', 'locomo')})

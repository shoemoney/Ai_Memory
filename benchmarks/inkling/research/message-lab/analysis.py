"""Pair-cluster bootstrap; both directions stay in the same resampling unit."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import numpy as np


def cluster_interval(rows, value, n_boot=4000, seed=16):
    grouped = defaultdict(list)
    for row in rows:
        v = value(row)
        if v is not None and np.isfinite(v):
            grouped[row['pair']].append(v)
    if not grouped:
        return dict(mean=None, low=None, high=None, n_pairs=0, n_observations=0)
    # Equal pair weighting; direction mean within pair, then paired bootstrap.
    means = np.array([np.mean(v) for v in grouped.values()])
    rng = np.random.default_rng(seed)
    boot = means[rng.integers(len(means), size=(n_boot, len(means)))].mean(axis=1)
    return dict(mean=float(means.mean()), low=float(np.quantile(boot, .025)),
                high=float(np.quantile(boot, .975)), n_pairs=len(means),
                n_observations=sum(len(v) for v in grouped.values()))


def ratio_interval(rows, n_boot=4000, seed=16):
    """Ratio of mean injection gain to mean 1->3 gap; includes negative/zero item gaps."""
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['pair']].append((r['gain'], r['gap']))
    if not grouped:
        return dict(ratio=None, low=None, high=None, reason='no rows')
    vals = np.array([np.mean(v, axis=0) for v in grouped.values()])
    rng = np.random.default_rng(seed)
    boot = vals[rng.integers(len(vals), size=(n_boot, len(vals)))].mean(axis=1)
    mean = vals.mean(axis=0)
    denominator_ci = np.quantile(boot[:, 1], [.025, .975])
    # A weak denominator makes a recovery fraction unidentified; do not drop trials silently.
    if denominator_ci[0] <= 0 <= denominator_ci[1] or abs(mean[1]) <= 1e-6:
        return dict(ratio=None, low=None, high=None, reason='mean gap interval includes zero',
                    mean_gain=float(mean[0]), mean_gap=float(mean[1]), gap_ci=denominator_ci.tolist())
    ratios = boot[:, 0] / boot[:, 1]
    return dict(ratio=float(mean[0]/mean[1]), low=float(np.quantile(ratios, .025)),
                high=float(np.quantile(ratios, .975)), mean_gain=float(mean[0]), mean_gap=float(mean[1]),
                gap_ci=denominator_ci.tolist(), n_pairs=len(vals))


def summarize(rows, n_boot=4000):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(k) for k in ('split', 'experiment', 'task', 'block', 'boundary', 'condition'))].append(row)
    out = []
    for key, cell in sorted(groups.items()):
        split, exp, task, block, boundary, condition = key
        entry = dict(split=split, experiment=exp, task=task, block=block, boundary=boundary, condition=condition)
        metrics = {'margin': lambda r: r['margin']}
        if exp == 'swap':
            metrics.update(donor_shift=lambda r: r['donor_shift'], flip_rate=lambda r: float(r['flip']),
                           conditional_flip_rate=lambda r: float(r['flip']) if r['recipient_initially_correct'] else None,
                           argmax_to_donor_rate=lambda r: float(r['argmax_to_donor']))
        elif exp == 'zero' and condition == 'zero_all':
            metrics.update(change_vs3=lambda r: r['margin'] - r['baseline3'],
                           change_vs1=lambda r: r['margin'] - r['baseline1'])
        elif exp == 'injection':
            metrics.update(gain=lambda r: r['gain'], gap=lambda r: r['gap'])
            entry['gap_recovered'] = ratio_interval(cell, n_boot)
            entry['item_ratios_undefined'] = sum(r.get('recovery') is None for r in cell)
        entry['metrics'] = {name: cluster_interval(cell, fn, n_boot) for name, fn in metrics.items()}
        out.append(entry)
    # Paired specificity contrasts against each control, same side/boundary/block.
    swaps = {(r['pair'], r['side'], r['block'], r['boundary']): r for r in rows
             if r['experiment'] == 'swap' and r['condition'] == 'swap'}
    contrast_groups = defaultdict(list)
    for r in rows:
        if r['experiment'] != 'swap' or r['condition'] == 'swap':
            continue
        s = swaps.get((r['pair'], r['side'], r['block'], r['boundary']))
        if s is not None:
            contrast_groups[(r['split'], r['block'], r['boundary'], r['condition'])].append(
                dict(pair=r['pair'], difference=s['donor_shift']-r['donor_shift']))
    contrasts = [dict(split=k[0], block=k[1], boundary=k[2], control=k[3],
                      swap_minus_control=cluster_interval(v, lambda r: r['difference'], n_boot))
                 for k, v in sorted(contrast_groups.items())]
    zero_index = {(r['pair'], r['side'], r['task']): r for r in rows
                  if r['experiment'] == 'zero' and r['condition'] == 'zero_all'}
    interaction = defaultdict(list)
    for (pair, side, task), r in zero_index.items():
        control = zero_index.get((pair, side, 'single_hop'))
        if task == 'two_hop' and control is not None:
            interaction[r['split']].append(dict(pair=pair, effect=(r['baseline3']-r['margin']) -
                (control['baseline3']-control['margin'])))
    zero_interaction = {split: cluster_interval(cell, lambda r: r['effect'], n_boot)
                        for split, cell in interaction.items()}
    return dict(schema=1, zero_twohop_minus_singlehop_damage=zero_interaction, bootstrap='pair clusters, 4000 replicates by default, percentile 95%; descriptive unadjusted CIs',
                cells=out, contrasts=contrasts)


def control_table(report):
    lines = ['| Split | Block | Boundary | Control | Swap − control donor shift [95% CI] | Pairs |',
             '|---|---|---|---|---|---|']
    for c in report['contrasts']:
        x = c['swap_minus_control']
        lines.append(f"| {c['split']} | {c['block']} | {c['boundary']} | {c['control']} | "
                     f"{x['mean']:.4f} [{x['low']:.4f}, {x['high']:.4f}] | {x['n_pairs']} |")
    return '\n'.join(lines) + '\n'


def validate_complete(rows, state):
    expected = set()
    for pair in state['planned_pairs']:
        for task in ('two_hop', 'single_hop'):
            for side in (0, 1):
                for condition in ('intact1', 'intact3', 'zero_all'):
                    expected.add((pair, task, side, 'zero', 'all', -1, condition))
        for boundary in state['boundaries']:
            for block in ('6-11', '12-17'):
                for side in (0, 1):
                    for condition in ('swap', 'sham', 'irrelevant', 'random', 'shuffle'):
                        expected.add((pair, 'two_hop', side, 'swap', block, boundary, condition))
                    expected.add((pair, 'two_hop', side, 'injection', block, boundary, 'inject'))
    actual = {tuple(r[k] for k in ('pair', 'task', 'side', 'experiment', 'block', 'boundary', 'condition')) for r in rows}
    if actual != expected or len(rows) != len(expected):
        raise ValueError(f'Incomplete/inconsistent matrix: {len(expected-actual)} missing, {len(actual-expected)} extra cells')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('results', type=Path, nargs='+')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--bootstrap', type=int, default=4000)
    args = ap.parse_args()
    rows = []
    provenance = []
    for path in args.results:
        batch = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        state = json.loads((path.parent / 'manifest.json').read_text())
        validate_complete(batch, state)
        provenance.append(state)
        rows.extend(batch)
    compatible = ('model', 'config', 'weights', 'dataset', 'sources', 'versions',
                  'seed', 'boundaries', 'allow_untrained')
    if any(p.get(k) != provenance[0].get(k) for p in provenance for k in compatible):
        raise ValueError('Do not combine different model, data, code, runtime or intervention versions')
    if len({r['key'] for r in rows}) != len(rows):
        raise ValueError('Duplicate result keys')
    report = summarize(rows, args.bootstrap)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (args.out / 'controls.md').write_text(control_table(report))


if __name__ == '__main__':
    main()

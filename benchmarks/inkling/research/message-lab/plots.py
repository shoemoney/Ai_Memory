"""One SVG per registered experiment, kept separate by split."""
import argparse
import json
from pathlib import Path


def draw(report, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out.mkdir(parents=True, exist_ok=True)
    for experiment in ('swap', 'zero', 'injection'):
        cells = [c for c in report['cells'] if c['experiment'] == experiment]
        splits = sorted({c['split'] for c in cells}) or ['no data']
        fig, axes = plt.subplots(1, len(splits), figsize=(8 * len(splits), max(4, len(cells)*.17)), squeeze=False)
        for ax, split in zip(axes[0], splits):
            subset = [c for c in cells if c['split'] == split]
            labels, x, lows, highs = [], [], [], []
            for c in subset:
                if experiment == 'injection':
                    value = c['gap_recovered']
                    center = value.get('ratio')
                else:
                    metric = 'donor_shift' if experiment == 'swap' else 'margin'
                    value = c['metrics'][metric]
                    center = value['mean']
                label = f"{c['task']} / {c['block']} / b{c['boundary']} / {c['condition']}"
                if center is None:
                    ax.text(.02, .95 - .04*len(labels), label + ': undefined', transform=ax.transAxes, fontsize=8)
                    continue
                labels.append(label)
                x.append(center)
                lows.append(center-value['low'])
                highs.append(value['high']-center)
            if x:
                ax.errorbar(x, range(len(x)), xerr=[lows, highs], fmt='o', capsize=3)
                ax.set_yticks(range(len(x)), labels, fontsize=8)
                ax.invert_yaxis()
            ax.axvline(0, color='gray', lw=.8)
            ax.set_title(f'{experiment} — {split}')
            ax.set_xlabel({'swap': 'Donor-directed logit-margin shift', 'zero': 'Own-answer logit margin',
                           'injection': 'Fraction of mean 1→3 margin gap recovered'}[experiment])
        fig.suptitle('Pair-cluster bootstrap 95% intervals (unadjusted)')
        fig.tight_layout()
        fig.savefig(out / f'{experiment}.svg', format='svg')
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('analysis', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    draw(json.loads(args.analysis.read_text()), args.out)


if __name__ == '__main__':
    main()

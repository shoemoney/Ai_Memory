"""Render actual report data to portable SVG (no fabricated study results)."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('analysis',type=Path)
    p.add_argument('policies',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    report=json.loads((a.analysis/'probes.json').read_text())
    prefix = 'SYNTHETIC VALIDATION ONLY: ' if report['protocol'].get('synthetic') else ''
    for target in ('token_flip','answer_flip'):
        if 'heldout_stratum' not in report[target]:
            continue
        fig,axes=plt.subplots(1,4,figsize=(16,4),sharey=True)
        for ax,(s,features) in zip(axes,report[target]['heldout_stratum'].items()):
            for i,(name,r) in enumerate(features.items()):
                if r['auc'] is not None:
                    lo,hi=r['auc_ci'] or [r['auc']]*2
                    ax.vlines(i,lo,hi,color='C0');ax.plot(i,r['auc'],'o',color='C0')
            ax.set_xticks(range(len(features)),features.keys(),rotation=50,ha='right')
            ax.axhline(.5,color='gray',linestyle='--');ax.set_title(s);ax.set_ylim(0,1)
        axes[0].set_ylabel('Held-out-stratum AUC; cluster bootstrap 95% CI')
        fig.suptitle(prefix + target);fig.tight_layout();fig.savefig(a.output/f'{target}-auc.svg');plt.close(fig)
    with (a.policies/'policies.csv').open() as f:
        rows=list(csv.DictReader(f))
    fig,axes=plt.subplots(1,4,figsize=(16,4),sharey=True)
    for ax,s in zip(axes,sorted({r['stratum'] for r in rows})):
        for signal in ('gate','kl','probe'):
            subset=sorted([r for r in rows if r['stratum']==s and r['signal']==signal],key=lambda r:float(r['average_passes']))
            ax.plot([float(r['average_passes']) for r in subset],[float(r['agreement']) for r in subset],'.-',label=signal)
        ax.set_title(s);ax.set_xlabel('Average loop passes/token');ax.legend()
    axes[0].set_ylabel('Agreement with fixed three-pass argmax')
    fig.suptitle(prefix + 'Offline policy comparison')
    fig.tight_layout();fig.savefig(a.output/'policy-pareto.svg');plt.close(fig)


if __name__=='__main__':
    main()

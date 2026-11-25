"""Produce standalone research figures and a small inline-view HTML wrapper."""
import json,os
from common import ROOT,SCRATCH
os.environ['MPLCONFIGDIR']=str(SCRATCH/'mpl-config')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    summary=json.loads((ROOT/'results'/'summary.json').read_text())
    plt.rcParams.update({'font.size':10,'axes.titlesize':11,'axes.labelsize':10,'svg.fonttype':'none'})
    fig,axes=plt.subplots(2,2,figsize=(8,7.6),constrained_layout=True)
    specifications=[('gsm8k','GSM8K, 150 paired items',['base','memgen'],['Base','Weaver']),('triviaqa','TriviaQA, 150 paired items\nClosed-book diagnostic',['base','memgen'],['Base','Weaver']),('cartridges','LongHealth, 20 paired questions\nOne patient, reduced training',['context','cartridge'],['Full context','Cartridge'])]
    colors=['#64748b','#2563eb']
    for ax,(key,title,names,labels) in zip(axes.flat,specifications):
        result=summary[key]; stats=[result['systems'][name] for name in names]
        values=[100*s['rate'] for s in stats]
        errors=[[100*(s['rate']-s['ci95'][0]) for s in stats],[100*(s['ci95'][1]-s['rate']) for s in stats]]
        ax.bar([0,1],values,color=colors,width=.58,yerr=errors,capsize=5,error_kw={'elinewidth':1.1})
        for i,(value,stat) in enumerate(zip(values,stats)):
            ax.text(i,100*stat['ci95'][1]+2,f'{value:.1f}%',ha='center',va='bottom',fontsize=10)
        ax.set_xticks([0,1],labels);ax.set_ylim(0,108);ax.set_yticks([0,20,40,60,80,100]);ax.set_ylabel('Accuracy (%)')
        ax.set_title(title,pad=12);ax.set_axisbelow(True);ax.grid(axis='y',alpha=.2)
        ax.spines[['top','right']].set_visible(False)
        p=result['paired'];lo,hi=p['bootstrap_ci95']
        ax.set_xlabel(f"Paired change: {100*p['difference']:+.1f} points\n95% interval: {100*lo:+.1f} to {100*hi:+.1f}",labelpad=9)
    ax=axes.flat[3];r=summary['cartridges'];names=['context','cartridge']
    values=[r['cache_bytes_means'][name]/2**20 for name in names]
    ax.bar([0,1],values,color=colors,width=.58)
    for i,v in enumerate(values):ax.text(i,v+6,f'{v:.2f} MiB',ha='center',fontsize=10)
    ax.set_xticks([0,1],['Full context','Cartridge']);ax.set_ylabel('Mean query KV storage (MiB)')
    ax.set_ylim(0,395);ax.set_title('KV storage after question prefill\n20 questions, same frozen reader',pad=12)
    ax.set_axisbelow(True);ax.grid(axis='y',alpha=.2);ax.spines[['top','right']].set_visible(False)
    ax.set_xlabel(f"Ratio of means: {r['cache_ratio_of_means']:.1f}x\nMean paired ratio: {r['cache_ratio_mean']:.1f}x",labelpad=9)
    fig.savefig(ROOT/'results'/'comparison.png',dpi=160,facecolor='white')
    fig.savefig(ROOT/'results'/'comparison.svg',facecolor='white')
    plt.close(fig)
    image=ROOT/'results'/'comparison.png'
    html=f'''<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{{margin:0}}figure{{margin:0}}img{{display:block;width:100%;height:auto}}figcaption{{font:13px/1.5 var(--font-sans);color:var(--muted-foreground);margin-top:8px}}
    </style></head><body><figure><img src="{image}" alt="Local paired accuracy with 95% intervals, and KV storage for the reduced Cartridges experiment."><figcaption>Accuracy bars use 95% Wilson intervals. Paired changes use 20,000 bootstrap resamples. TriviaQA disables search. Cartridges uses 32 locally generated conversations, 64 training steps and a 64-token cache; its KV compression came with lower answer quality. KV figures exclude weights, optimizer state and allocator reservation. These cells do not reproduce the published eight-benchmark maxima or the 38.6x matched-quality result.</figcaption></figure></body></html>'''
    (ROOT/'results'/'comparison.html').write_text(html)

if __name__=='__main__':main()

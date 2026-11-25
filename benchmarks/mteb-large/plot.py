#!/usr/bin/env python3
"""Standalone publication figures from retained complete cells, without inference."""
import hashlib,html,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR','/data/scratch/membench/mteb-large/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

TASKS=['SciFact','NFCorpus','ArguAna']
MODELS=[('Qwen/Qwen3-Embedding-4B','Qwen 4B (Q8)'),('Qwen/Qwen3-Embedding-8B','Qwen 8B (Q4)'),
        ('Qwen/Qwen3-VL-Embedding-8B','Qwen VL 8B (Q4)'),('microsoft/harrier-oss-v1-27b','Harrier 27B (Q4)')]
BLUE='#245c85';ORANGE='#a76020';INK='#27313b';GRID='#e3e7eb'

def main():
    comparison=ROOT/'results/comparison.json';rows=json.loads(comparison.read_text())
    available=[(m,label) for m,label in MODELS if any(r['model']==m and r.get('local') for r in rows)]
    visual_paths=sorted((ROOT/'results/vidore').glob('*/summary.json'))
    visuals=[json.loads(p.read_text()) for p in visual_paths]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'text.color':INK,
                         'axes.labelcolor':INK,'xtick.color':INK,'ytick.color':INK,'svg.fonttype':'none'})
    fig=plt.figure(figsize=(12,8),layout='constrained');grid=fig.add_gridspec(2,3,height_ratios=[1.15,1])
    for col,task in enumerate(TASKS):
        ax=fig.add_subplot(grid[0,col])
        for y,(model,label) in enumerate(available):
            row=next(r for r in rows if r['model']==model and r['task']==task);local=row.get('local')
            if local:
                mean=local['ndcg_at_10']*100;lo,hi=[v*100 for v in local['bootstrap_95_ci']]
                ax.errorbar(mean,y+.12,xerr=[[mean-lo],[hi-mean]],fmt='o',color=BLUE,capsize=3,ms=5,lw=1.6)
                ax.annotate(f'{mean:.2f}',(mean,y+.12),xytext=(0,9),textcoords='offset points',ha='center',fontsize=10)
            else:ax.text(50,y+.12,'Not completed',ha='center',va='center',fontsize=10,color='#707981')
            published=row.get('published_ndcg_at_10')
            if published is not None:ax.plot(published*100,y-.12,'D',mfc='white',mec=INK,ms=5)
        n={'SciFact':300,'NFCorpus':323,'ArguAna':1406}[task]
        ax.set(title=f'{task}  |  N={n:,}',xlabel='nDCG@10 (0 to 100)',xlim=(0,100),ylim=(-.6,len(available)-.35))
        ax.set_yticks(range(len(available)),[label for _,label in available] if col==0 else ['']*len(available))
        ax.invert_yaxis();ax.grid(axis='x',color=GRID);ax.set_axisbelow(True)
        for side in ['top','right','left']:ax.spines[side].set_visible(False)
        ax.tick_params(axis='y',length=0)
    ax=fig.add_subplot(grid[1,:])
    for y,summary in enumerate(visuals):
        for metric,offset,color in [('ndcg_cut_5',-.12,ORANGE),('ndcg_cut_10',.12,BLUE)]:
            score=summary[metric];mean=score['mean']*100;lo,hi=[v*100 for v in score['bootstrap_95_ci']]
            ax.errorbar(mean,y+offset,xerr=[[mean-lo],[hi-mean]],fmt='o',color=color,capsize=3,ms=5,lw=1.6)
            ax.annotate(f'{mean:.2f}',(mean,y+offset),xytext=(0,12 if offset<0 else -12),textcoords='offset points',ha='center',va='center',fontsize=10)
    names=[]
    for summary in visuals:
        model=summary['model'];name='Nomic 7B' if model.startswith('nomic-') else ('Qwen VL 2B' if model.endswith('2B') else 'Qwen VL 8B')
        ex=summary.get('execution',{});bits=ex.get('bits');setting=f'Mac, Q{bits}' if bits else 'GPU, BF16'
        names.append(f'{name} ({setting})')
    ax.set_yticks(range(len(visuals)),names);ax.set(xlim=(0,100),ylim=(-.6,max(.6,len(visuals)-.4)),
        title='ViDoRe V3 HR English: 318 queries, 1,110 pages',xlabel='Local nDCG (0 to 100); different from the published aggregates')
    ax.invert_yaxis();ax.grid(axis='x',color=GRID);ax.set_axisbelow(True);ax.tick_params(axis='y',length=0)
    for side in ['top','right','left']:ax.spines[side].set_visible(False)
    ax.legend(handles=[Line2D([],[],marker='o',color=ORANGE,label='nDCG@5'),Line2D([],[],marker='o',color=BLUE,label='nDCG@10')],loc='upper left',frameon=False,ncol=2)
    fig.suptitle('Local retrieval measurements',fontsize=18,fontweight='bold')
    fig.legend(handles=[Line2D([],[],marker='o',color=BLUE,label='Local mean and 95% query-bootstrap interval'),
                        Line2D([],[],marker='D',mfc='white',mec=INK,color='none',label='Published task score, where available')],
               loc='outside lower center',frameon=False,ncol=2,fontsize=11)
    result=ROOT/'results';fig.savefig(result/'retrieval-results.png',dpi=180,facecolor='white',metadata={'Title':'Local embedding retrieval measurements'})
    fig.savefig(result/'retrieval-results.svg',facecolor='white',metadata={'Date':None,'Title':'Local embedding retrieval measurements'})
    plt.close(fig)
    caption='Text: Apple M3 Ultra, 96 GB; MLX Q8 for 4B and Q4 for larger models, with BF16 compute. Every retained cell uses its full split and corpus. Published task markers are separate from full-suite averages. The visual subset cannot verify MMEB-V2 or ViDoRe-v2 aggregates; GPU and Mac timings are not compared.'
    image_path=html.escape(str((result/'retrieval-results.png').resolve()),quote=True)
    page=f'<!doctype html><html><head><meta charset="utf-8"><style>main{{margin:0}}img{{display:block;width:100%;height:auto}}p{{font-size:12px;line-height:1.5;color:var(--muted-foreground);margin:10px 0 0}}</style></head><body><main><img src="{image_path}" alt="Local retrieval means and bootstrap intervals with published task score markers"><p>{html.escape(caption)}</p></main></body></html>'
    (result/'retrieval-results.html').write_text(page)
    inputs=[comparison,*visual_paths]
    (result/'plot-inputs.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},'plotter':'Matplotlib 3.10.8','published_visual_aggregates_not_plotted_as_comparable':True},indent=2)+'\n')
    print('Rendered standalone PNG/SVG and inline HTML from complete retained cells')
if __name__=='__main__':main()

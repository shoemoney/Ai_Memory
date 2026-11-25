"""Standalone publication artifacts from the measured summaries, with source endpoints labeled."""
import base64
import json
from pathlib import Path
import os
os.environ.setdefault("MPLCONFIGDIR",str(Path(os.environ.get("BENCH_SCRATCH","/data/scratch/membench/paper-reruns"))/"plot-config"))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(__file__).parent
hippo=json.loads((root/'hipporag2/results/summary.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(12,4.9),layout='constrained')
colors=['#566879','#166c8b']
ax=axes[0]
positions=np.array([0.,1.])
width=.32
for j,method in enumerate(['dense','hipporag2']):
    value=hippo['metrics']['F1'][method]
    mean=value['mean']*100
    lo,hi=[x*100 for x in value['ci95']]
    heights=[61.5 if method=='dense' else 71.0,mean]
    bars=ax.bar(positions+(j-.5)*width,heights,width,color=colors[j],label='Dense retrieval' if j==0 else 'HippoRAG 2')
    ax.errorbar(positions[1]+(j-.5)*width,mean,yerr=[[mean-lo],[hi-mean]],fmt='none',color='#1e2933',capsize=4,lw=1.3)
    for bar,h in zip(bars,heights):
        ax.text(bar.get_x()+bar.get_width()/2,h*.5 if h>10 else h+9,f'{h:.1f}',ha='center',fontsize=9,color='white' if h>10 else '#334155')
ax.set(ylim=(0,100),ylabel='QA F1 (%)',xticks=positions,xticklabels=['Paper: 1,000 questions','Local: 150 questions'],title='2Wiki: different models and corpus sizes')
ax.legend(frameon=False,loc='upper left',fontsize=9)
ax.text(.5,-.23,'Paper: NV-Embed-v2 and Llama 70B.\nLocal: all-MPNet and quantized Qwen 3B.',transform=ax.transAxes,ha='center',fontsize=9,color='#4b5563')
ax=axes[1]
sos_path=root/'spiral-of-silence/results/summary.json'
if sos_path.exists():
    sos=json.loads(sos_path.read_text())
    rounds=sos['rounds']
    x=[r['round'] for r in rounds]
    y=[r['human_share']*100 for r in rounds]
    lo=[r['ci95'][0]*100 for r in rounds]
    hi=[r['ci95'][1]*100 for r in rounds]
    ax.fill_between(x,lo,hi,color='#166c8b',alpha=.15,lw=0)
    ax.plot(x,y,'o-',color='#166c8b',lw=1.8,ms=4,label=f'Local: {sos["n"]} questions, {len(rounds)-1} rounds')
    ax.text(.5,-.23,'Local: reduced NQ corpus, one generator, Contriever.\nBands: 95% question-bootstrap intervals.',transform=ax.transAxes,ha='center',fontsize=9,color='#4b5563')
    ax.set_title('Human share among top 50 results')
else:
    ax.text(.5,.55,'Local simulation not run',transform=ax.transAxes,ha='center',fontsize=12)
    ax.set_title('Spiral of Silence')
ax.plot([10],[10],marker='v',color='#95683b',ms=7,linestyle='none',label='Paper: below 10% at round 10')
ax.set(xlim=(-.2,10.6),ylim=(0,105),xlabel='Write-and-retrieve round',ylabel='Human-written share (%)',xticks=range(0,11,2))
ax.legend(frameon=False,loc='lower left',fontsize=8)
for ax in axes:
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y',color='#e5e7eb',lw=.7)
    ax.set_axisbelow(True)
fig.suptitle('Published figures and local adaptations',fontsize=14,fontweight='bold')
fig.savefig(root/'comparison.png',dpi=180,facecolor='white')
fig.savefig(root/'comparison.svg',facecolor='white')
image=base64.b64encode((root/'comparison.png').read_bytes()).decode()
(root/'comparison.html').write_text('<!doctype html><html><head><meta charset="utf-8"><title>Published-paper reruns</title><style>body{margin:0;padding:20px;background:white;font:14px system-ui;color:#334155}img{display:block;width:100%;max-width:1250px;margin:auto}p{max-width:1100px;margin:10px auto;line-height:1.5}</style></head><body><img alt="Published and local QA F1 and human-written retrieval share, with local intervals" src="data:image/png;base64,'+image+'"><p>Local intervals condition on the selected questions, one corpus, and one model realization. Paper and local setups differ; this is not an estimate of the paper\'s aggregate 7% associative-memory claim. The source paper\'s human-share marker denotes a threshold, not an exact 10% measurement.</p></body></html>')
print(root/'comparison.html')

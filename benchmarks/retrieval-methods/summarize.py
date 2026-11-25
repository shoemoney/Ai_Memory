"""Paired query bootstrap; draws are shared across all compared methods."""
from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';SEED=20261122
METRICS=['recall5','recall20','ndcg10','failure20','ap150','unrecalled20']
def read(p):return [json.loads(l) for l in p.read_text().splitlines()]
def ci(x):return [float(x.mean()),*map(float,np.quantile(x,[.025,.975]))]
def summarize():
 output={}
 for name in ['scifact','nfcorpus','longmemeval','locomo']:
  methods={}
  for prefix,tag in [('base',''),('context','context_')]:
   keyword=OUT/(name+'.'+prefix+'.bm25.jsonl')
   if keyword.exists():methods[tag+'bm25']={r['id']:r['metrics'] for r in read(keyword)}
   p=OUT/(name+'.'+prefix+'.rankings.jsonl')
   if p.exists():
    for row in read(p):
     for m,s in row['metrics'].items():methods.setdefault(tag+m,{})[row['id']]=s
   p=OUT/(name+'.'+prefix+'.rerank.jsonl')
   if p.exists():methods[tag+'hybrid_rerank']={r['id']:r['metrics'] for r in read(p)}
  if not methods:continue
  # Report only finished cells, checked against the manifest. Partial runs are explicit.
  n_expected=json.loads((OUT/'manifest.json').read_text())['sources'][name]['queries']
  partial={m:len(v) for m,v in methods.items() if len(v)!=n_expected}
  methods={m:v for m,v in methods.items() if len(v)==n_expected}
  if not methods:output[name]={'partial':partial};continue
  ids=sorted(set.intersection(*(set(v) for v in methods.values())))
  assert len(ids)==n_expected
  rng=np.random.default_rng(SEED);samples=rng.integers(0,len(ids),(10000,len(ids)))
  arrays={m:{k:np.array([1-v[i]['recall20'] if k=='unrecalled20' else v[i][k] for i in ids]) for k in METRICS} for m,v in methods.items()}
  result={'n':len(ids),'partial':partial,'systems':{},'paired':{}}
  for m,v in arrays.items():result['systems'][m]={k:[float(a.mean()),*map(float,np.quantile(a[samples].mean(1),[.025,.975]))] for k,a in v.items()}
  for method,values in arrays.items():
   binary=values['failure20'];n=len(binary);rate=float(binary.mean());z=1.959963984540054;den=1+z*z/n
   center=(rate+z*z/(2*n))/den;half=z*((rate*(1-rate)/n+z*z/(4*n*n))**.5)/den
   result['systems'][method]['failure20_wilson']=[rate,max(0.,center-half),min(1.,center+half)]
   result['systems'][method]['failure20_count']=int(binary.sum())
  comparisons=[('hybrid_rrf','bm25'),('hybrid_rrf','dense'),('hybrid_rerank','hybrid_rrf'),('context_bm25','bm25'),('context_dense','dense'),('context_hybrid_rrf','dense'),('context_hybrid_rerank','dense'),('context_hybrid_rrf','context_dense'),('context_hybrid_rerank','context_hybrid_rrf')]
  for a,b in comparisons:
   if a not in arrays or b not in arrays:continue
   label=a+' minus '+b
   result['paired'][label]={}
   for k in METRICS:
    delta=arrays[a][k]-arrays[b][k];bs=delta[samples].mean(1)
    result['paired'][label][k]=[float(delta.mean()),*map(float,np.quantile(bs,[.025,.975]))]
   base=arrays[b]['failure20'];after=arrays[a]['failure20'];den=base[samples].mean(1);mask=den>0
   if base.mean()>0:
    reduction=1-after.mean()/base.mean();draws=1-after[samples].mean(1)[mask]/den[mask]
    result['paired'][label]['relative_failure_reduction']=[float(reduction),*map(float,np.quantile(draws,[.025,.975]))] if mask.all() else [float(reduction),None,None]
    result['paired'][label]['relative_failure_reduction_undefined_resamples']=int((~mask).sum())
   base=arrays[b]['unrecalled20'];after=arrays[a]['unrecalled20'];den=base[samples].mean(1);mask=den>0
   if base.mean()>0:
    reduction=1-after.mean()/base.mean();draws=1-after[samples].mean(1)[mask]/den[mask]
    result['paired'][label]['relative_unrecalled_reduction']=[float(reduction),*map(float,np.quantile(draws,[.025,.975]))] if mask.all() else [float(reduction),None,None]
    result['paired'][label]['relative_unrecalled_reduction_undefined_resamples']=int((~mask).sum())
   # Relative nDCG gain over the named constituent baseline.
   if a=='hybrid_rrf':
    den=arrays[b]['ndcg10'];num=arrays[a]['ndcg10'];ratio=num[samples].mean(1)/den[samples].mean(1)-1
    result['paired'][label]['relative_ndcg_gain']=[float(num.mean()/den.mean()-1),*map(float,np.quantile(ratio,[.025,.975]))]
  if 'hybrid_rrf' in arrays:
   result['rrf_vs_best_single']={}
   for k in ['ndcg10','ap150']:
    hybrid=arrays['hybrid_rrf'][k];bm=arrays['bm25'][k];dense=arrays['dense'][k]
    denominator=max(bm.mean(),dense.mean());den_boot=np.maximum(bm[samples].mean(1),dense[samples].mean(1))
    gain=hybrid.mean()/denominator-1;boot=hybrid[samples].mean(1)/den_boot-1
    result['rrf_vs_best_single'][k]={'best_single':'bm25' if bm.mean()>=dense.mean() else 'dense','relative_gain':[float(gain),*map(float,np.quantile(boot,[.025,.975]))]}
  output[name]=result
 (OUT/'summary.json').write_text(json.dumps(output,indent=2))
 lines=['| Dataset | Method | N | Recall@5 | Recall@20 | nDCG@10 | Complete miss@20 |','|---|---|---:|---:|---:|---:|---:|']
 def fmt(v):return f'{100*v[0]:.2f} [{100*v[1]:.2f}, {100*v[2]:.2f}]'
 for name,r in output.items():
  for m,s in r.get('systems',{}).items():lines.append('| '+ ' | '.join([name,m,str(r['n'])]+[fmt(s[k]) for k in METRICS[:4]])+' |')
 (OUT/'table.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
if __name__=='__main__':summarize()

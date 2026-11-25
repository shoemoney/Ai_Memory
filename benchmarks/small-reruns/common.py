import json, os, time
from pathlib import Path
import requests
from scipy.stats import beta, binomtest
ROOT=Path(__file__).resolve().parent
ENDPOINT=os.environ.get('ENDPOINT','http://127.0.0.1:39900/v1')
def chat(prompt,max_tokens=768,messages=None):
    start=time.monotonic()
    r=requests.post(ENDPOINT+'/chat/completions',json={'model':os.environ.get('MODEL','small-reruns-qwen2.5-3b'),'messages':messages or [{'role':'user','content':prompt}],'temperature':0,'seed':42,'max_tokens':max_tokens},timeout=600)
    r.raise_for_status(); d=r.json()
    return d['choices'][0]['message']['content'],time.monotonic()-start,d.get('usage',{}),d['choices'][0]['finish_reason']
def interval(k,n,alpha=.05):
    return [float(beta.ppf(alpha/2,k,n-k+1)) if k else 0.,float(beta.ppf(1-alpha/2,k+1,n-k)) if k<n else 1.]
def paired(a,b):
    n=len(a); gain=sum(not x and y for x,y in zip(a,b)); loss=sum(x and not y for x,y in zip(a,b))
    gi=interval(gain,n,.025);li=interval(loss,n,.025)
    return {'n':n,'gain':gain,'loss':loss,'difference':(gain-loss)/n,'difference_exact_conservative_95':[gi[0]-li[1],gi[1]-li[0]],'mcnemar_exact_p':float(binomtest(gain,gain+loss).pvalue) if gain+loss else 1.}
def append(path,row):
    with path.open('a') as f:f.write(json.dumps(row,ensure_ascii=True)+'\n');f.flush();os.fsync(f.fileno())

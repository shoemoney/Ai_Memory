from pathlib import Path
import json,math
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
def interval(k,n):
 if not n:return None
 z=1.959963984540054;den=1+z*z/n;c=(k/n+z*z/(2*n))/den;h=z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/den
 return [c-h,c+h]
def summarize():
 manifest=OUT/'manifest.json';m=json.loads(manifest.read_text()) if manifest.exists() else {'selected_ids':[]}
 ids=m['selected_ids'];systems=['bm25','dense','mem0-extract','graphiti'];rows={s:{} for s in systems}
 for p in (OUT/'items').glob('*.json'):
  r=json.loads(p.read_text())
  if r['question_id'] in ids and r['status']=='scored':rows[r['system']][r['question_id']]=r
 paired=set(ids)
 for s in systems:paired&=rows[s].keys()
 result={'complete':len(paired)==150,'planned_n':150,'paired_n':len(paired),'manual_audit':{'n':0},'systems':{}}
 for s in systems:
  k=sum(rows[s][i]['correct'] for i in paired);n=len(paired)
  result['systems'][s]={'available_n':len(rows[s]),'paired_n':n,'paired_correct':k,'paired_accuracy':k/n if n else None,'paired_wilson95':interval(k,n)}
 OUT.mkdir(exist_ok=True);(OUT/'summary.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':print(json.dumps(summarize(),indent=2))

"""Compare frozen blinded manual labels with the exact cached local decisions."""
import collections,json
from bench import ROOT,read
from analyze import wilson
from judge import coverage_text

def run():
 path=ROOT/'data/actual-output-audit.json'
 if not path.exists():return
 manual=json.loads(path.read_text());rows=manual['pairs'];assert len(rows)==60 and {r['audit_index']for r in rows}==set(range(60))
 cache={r['hash']:r for r in read(ROOT/'results/judge-cache.jsonl')};out=[];missing=[]
 for row in rows:
  assert row['expected']in ('supported','contradicted','unknown')
  if row['hash']not in cache:missing.append(row['audit_index']);continue
  entry=cache[row['hash']];d=entry[row['kind']];i=row['hypothesis_index']
  assert row['hypothesis']==(entry['predictions']if row['kind']=='support'else entry['references'])[i]
  assert row['premise']==(entry['source']if row['kind']=='support'else coverage_text(entry['predictions'],entry['source_speaker']))
  actual='supported'if i in d['supported']else 'contradicted'if i in d['contradicted']else 'unknown'
  out.append({**row,'actual':actual,'correct':actual==row['expected'],'support_binary_correct':(actual=='supported')==(row['expected']=='supported'),'attempt_id':d['attempt_id']})
 n=len(out);k=sum(r['correct']for r in out);binary=sum(r['support_binary_correct']for r in out)
 summary={'N_reviewed':60,'N_matched_current_cache':n,'missing_review_indices':missing,'correct':k,'agreement':k/n if n else None,'wilson95':wilson(k,n)if n else None,'support_binary_correct':binary,'support_binary_agreement':binary/n if n else None,'support_binary_wilson95':wilson(binary,n)if n else None,'sampling':manual['sampling'],'reference_labels':manual['reference_labels'],'review_blinding':manual['review_blinding'],'expected_counts':dict(collections.Counter(r['expected']for r in out)),'actual_counts':dict(collections.Counter(r['actual']for r in out)),'by_kind':{kind:{'N':sum(r['kind']==kind for r in out),'correct':sum(r['correct']for r in out if r['kind']==kind)}for kind in ('support','coverage')},'confusion_counts':dict(collections.Counter(r['expected']+' -> '+r['actual']for r in out)),'interval_note':'Nominal pair-level Wilson interval; this small audit does not model shared-source dependence or independent human-label error.'}
 (ROOT/'results/actual-output-audit.json').write_text(json.dumps(out,indent=2)+'\n');(ROOT/'results/actual-output-audit-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':run()

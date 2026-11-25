"""Second authorized relocation; original serving instance already cleaned."""
import concurrent.futures,json,statistics
from host import Host,ROOT,RESULTS
from bench import append,read,request,validate

def run():
 h=Host();h.setup();models=json.loads((ROOT/'models.json').read_text())
 try:
  h.load(next(m for m in models if m['id']=='qwen3.5-4b-q4_k_m'))
  plan=json.loads((RESULTS/'hardware-overlap-m1-to-m3a-plan.json').read_text());old={r['id']:r for r in read(RESULTS/'m3a-pilot/writers/qwen3.5-4b-q4_k_m-repeat-1.1.jsonl')if r['seed']==7};chosen=[old[i]for i in plan['ids']]
  (RESULTS/'hardware-overlap-plan.json').write_text(json.dumps({**plan,'source_instance':'M3 pilot','target_instance':'M3 main','source_hardware':'Apple M3 Ultra, 96 GB','target_hardware':h.hardware,'selection':'Reuse the same 25-per-dataset, preselected 50 control IDs; source responses from the completed former-M3 seed-7 cell.'},indent=2)+'\n')
  path=RESULTS/'hardware-overlap.jsonl';done={r['id']for r in read(path)}
  def one(a):
   if a['id']in done:return
   raw,sec=request(a['request'],h);valid,parsed,error=validate(raw)
   r={'id':a['id'],'seed':7,'model':a['model'],'serving_hardware':h.hardware,'serving_instance':h.instance,'comparison_hardware':'Apple M3 Ultra, 96 GB','comparison_instance':'M3 pilot','request':a['request'],'response':raw,'seconds':sec,'valid':valid,'parsed':parsed,'validation_error':error,'source_seconds':a['seconds'],'source_response':a['response'],'exact_content_match':raw['choices'][0]['message']['content']==a['response']['choices'][0]['message']['content'],'parsed_object_match':parsed==a['parsed']and valid==a['valid']}
   append(path,r);print('overlap',r['id'],r['exact_content_match'],flush=True)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:list(pool.map(one,chosen))
  rr=read(path);summary={'N':len(rr),'exact_content_matches':sum(r['exact_content_match']for r in rr),'parsed_object_matches':sum(r['parsed_object_match']for r in rr),'source_hardware':'Apple M3 Ultra, 96 GB','source_instance':'M3 pilot','target_hardware':h.hardware,'target_instance':h.instance,'quality_pooled':False,'timing_pooled':False,'separate_subset_median_seconds':{'M3 pilot':statistics.median(r['source_seconds']for r in rr),'M3 main':statistics.median(r['seconds']for r in rr)},'difference_ids':[r['id']for r in rr if not r['exact_content_match']]};(RESULTS/'hardware-overlap-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
 finally:h.close(cleanup=False)
if __name__=='__main__':run()

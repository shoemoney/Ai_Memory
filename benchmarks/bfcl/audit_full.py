"""Offline final audit of retained evidence; never starts inference or downloads."""
import hashlib,json,math,time
from collections import Counter
from pathlib import Path
from full_common import ROOT,RUN_DIR,MODELS,digest,weights

def main():
 out=RUN_DIR;analysis=json.loads((out/'analysis.json').read_text());manifest=json.loads((out/'manifest.json').read_text());state=json.loads((out/'run-state.json').read_text())
 assert state['deadline']==1795321060.0
 assert set(state['finished_models'])==set(MODELS)
 leaf=weights({c:d['population'] for c,d in manifest['categories'].items()});assert math.isclose(sum(leaf.values()),.8)
 audit={'time':time.time(),'deadline':state['deadline'],'source_file_count':len(manifest['source_files']),'models':{},'harness_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')},'source_limit':'Pinned source-file hashes agree across all model manifests. Original downloaded source/runtime files were deleted during required cleanup; this audit checks retained attestations, not a fresh download.'}
 known_workers={hashlib.sha256((ROOT/'full_worker.py').read_bytes()).hexdigest()}
 for size in MODELS:
  for p in (out/size/'harness-history').glob('*'):
   if p.is_file() and p.name.startswith('full_worker'):known_workers.add(hashlib.sha256(p.read_bytes()).hexdigest())
 audit['source_limit']+=' All three measured worker versions match current or archived source bytes, including the intermediate c95df864 version under 2B/harness-history. The first 114 items predate per-item worker hashes; their initial worker and manifest are archived, so their provenance is at run level rather than per item.'
 caps=[]
 for size in MODELS:
  folder=out/size;m=analysis['models'][size];mm=json.loads((folder/'manifest.json').read_text())
  assert mm['source_files']==manifest['source_files']
  assert mm['categories']==manifest['categories']
  records={mode:{} for mode in ['off','on']};d={'modes':{}}
  for mode in records:
   items=list((folder/mode/'items').glob('*/*.json'));rs=[json.loads(p.read_text()) for p in items]
   for row in rs:
    assert row['status']=='complete' and row['mode']==mode
    cat=row['category'];eid=row['id'];planned=mm['categories'][cat]
    assert eid in planned['random_order'] or eid in planned['prerequisites']
    if row.get('harness_version'):assert row['harness_version'] in known_workers
    if '_prereq_' not in eid:records[mode].setdefault(cat,{})[eid]=row
   calls=list((folder/mode/'calls').glob('*/*/*.json'))
   for p in calls:
    row=json.loads(p.read_text());assert digest(row['request'])==row['request_sha256']
    assert row['request']['max_tokens']==16384
    assert row['request']['extra_body']['chat_template_kwargs']['enable_thinking']==(mode=='on')
   scoring=[r for r in rs if '_prereq_' not in r['id'] and r['category'] in leaf]
   d['modes'][mode]={'all_committed_items':len(rs),'scoring_completed':len(scoring),'non_scoring_relevance':sum(r['category']=='live_relevance' for r in rs),'request_checkpoints':len(calls),'all_scoring_length_stops':sum(r['any_length_stop'] for r in scoring),'all_scoring_empty_credits':sum(r['empty_answer_credit'] for r in scoring),'all_scoring_malformed_credits':sum(r.get('malformed_tool_credit',False) for r in scoring)}
  n=0;points={k:{mode:0 for mode in records} for k in ['official','completed_nonempty']}
  for cat,detail in m['categories'].items():
   ids=set(records['off'].get(cat,{}))&set(records['on'].get(cat,{}));assert len(ids)==detail['paired_n']
   if cat in leaf:n+=len(ids)
   for mode in records:
    rows=[records[mode][cat][i] for i in ids];correct=sum(bool(r['score']['valid']) for r in rows);strict=sum(bool(r['completed_nonempty_correct']) for r in rows)
    assert correct==detail['modes'][mode]['official_correct'];assert strict==detail['modes'][mode]['completed_nonempty_correct']
    if cat in leaf and rows:
     points['official'][mode]+=leaf[cat]*correct/len(rows);points['completed_nonempty'][mode]+=leaf[cat]*strict/len(rows)
  assert n==m['paired_n']
  for key in points:
   for mode,v in points[key].items():assert math.isclose(100*v/m['covered_overall_weight'],m['aggregate'][key][mode]['projection_percent'],abs_tol=1e-10)
  d['paired_scoring_n']=n;d['source_manifests_agree']=True;d['request_hashes_valid']=True;d['weighted_scores_independently_verified']=True
  d['worker_hash_counts']=dict(Counter(json.loads(p.read_text()).get('harness_version','unversioned') for p in folder.glob('*/items/*/*.json')))
  d['paired_scoring_diagnostics']={mode:{k:sum(c['modes'][mode][k] for cat,c in m['categories'].items() if cat in leaf) for k in ['empty_credits','malformed_tool_credits','length_stops','context_budget_failures']} for mode in records}
  audit['models'][size]=d
  caps.extend(m['cap_rechecks'])
 assert len(caps)==6 and all(c['length_stopped'] for c in caps)
 audit['cap_rechecks']={'n':6,'all_still_length_stopped':True,'official_credits':sum(bool(c['score']['valid']) for c in caps),'completed_nonempty_credits':0}
 audit['passed']=True
 (ROOT/'evidence/full-final-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 print(json.dumps(audit,indent=2))
if __name__=='__main__':main()

"""Paired, stratified/cluster-bootstrap intervals and explicit missing-weight accounting."""
import json,math,time
from pathlib import Path
import numpy as np
from full_common import ROOT,CATEGORIES,MEMORY,PUBLISHED,MODELS,atomic,weights,RUN_DIR

B=4000

def wilson(k,n):
 if not n:return None
 z=1.95996398454;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return [100*(c-h),100*(c+h)]

def interval(x):return [float(v) for v in np.percentile(x,[2.5,97.5])]

def analyze():
 out=RUN_DIR
 manifest=json.loads((out/'manifest.json').read_text())
 populations={c:d['population'] for c,d in manifest['categories'].items()}
 leaf=weights(populations);rng=np.random.default_rng(20261121)
 common_ids={};uniform_ids={};uniform_count=None
 if manifest.get('sample_per_category'):
  for cat in CATEGORIES:
   ids=set(manifest['categories'][cat]['selected_ids'])
   for size in MODELS:
    for mode in ['off','on']:ids&={p.stem for p in (out/size/mode/'items'/cat).glob('*.json')}
   common_ids[cat]=ids
  cap=manifest['sample_per_category']
  bounds=[cap]+[len(common_ids[c]) for c in leaf if len(common_ids[c])<min(cap,populations[c])]
  uniform_count=min(bounds)
  for cat in CATEGORIES:
   count=min(uniform_count,populations[cat]) if cat in leaf else len(common_ids[cat])
   uniform_ids[cat]=set([i for i in manifest['categories'][cat]['selected_ids'] if i in common_ids[cat]][:count])
 report={'generated_at':time.time(),'bootstrap_replicates':B,'ci_level':.95,'method':'Paired stratified case bootstrap; memory domains resampled jointly across backends, then questions within domain. Conditional on observed cases and learned snapshots.','leaf_weights':leaf,'models':{},'missing_categories':manifest['missing_categories']}
 if manifest.get('cohort_design'):report['cohort_design']=manifest['cohort_design']
 if uniform_count is not None:
  report['uniform_category_count']=uniform_count
  report['available_common_counts']={c:len(ids) for c,ids in common_ids.items()}
  report['uniform_case_ids']={c:[i for i in manifest['categories'][c]['selected_ids'] if i in uniform_ids[c]] for c in CATEGORIES}
  report['uniform_rule']='Largest feasible common per-category count, with smaller complete populations retained as censuses. Within each category take the earliest available common IDs in the original seeded selection order. Availability-based complete-case selection is conditional and can be biased by blocked prerequisites or deadlines; correctness scores never choose the subset.'
 for size in MODELS:
  folder=out/size;records={m:{} for m in ['off','on']}
  for mode in records:
   for p in (folder/mode/'items').glob('*/*.json'):
    r=json.loads(p.read_text())
    if '_prereq_' in r['id']:continue
    records[mode].setdefault(r['category'],{})[r['id']]=r
  if manifest.get('sample_per_category'):
   # The headline uses exactly the same question IDs in all eight cells.
   for cat in CATEGORIES:
    selected=uniform_ids[cat]
    for mode in records:records[mode][cat]={i:r for i,r in records[mode].get(cat,{}).items() if i in selected}
  m={'published_full':PUBLISHED[size],'categories':{},'all_completed':{mode:sum(len(v) for v in records[mode].values()) for mode in records},'paired_n':0,'missing_categories':[]}
  matrix={};case_rows={};points={key:np.zeros(2) for key in ['official','completed_nonempty']};boots={key:np.zeros((B,2)) for key in points};mass=0
  for cat in CATEGORIES:
   off=records['off'].get(cat,{});on=records['on'].get(cat,{})
   ids=sorted(set(off)&set(on));n=len(ids)
   detail={'population':populations[cat],'off_completed':len(off),'on_completed':len(on),'paired_n':n,'census':n==populations[cat],'modes':{}}
   for mode in records:
    rs=[records[mode][cat][i] for i in ids] if ids else []
    k=sum(bool(r['score']['valid']) for r in rs);earned=sum(r['completed_nonempty_correct'] for r in rs)
    detail['modes'][mode]={'official_correct':k,'completed_nonempty_correct':earned,'n':n,'official_percent':100*k/n if n else None,'completed_nonempty_percent':100*earned/n if n else None,'official_wilson95':wilson(k,n),'completed_nonempty_wilson95':wilson(earned,n),'empty_credits':sum(r['empty_answer_credit'] for r in rs),'malformed_tool_credits':sum(r.get('malformed_tool_credit',False) for r in rs),'length_stops':sum(r['any_length_stop'] for r in rs),'tool_call_parse_failures':sum(r.get('tool_call_parse_failure',False) for r in rs),'context_budget_failures':sum(r.get('context_budget_exhausted',False) for r in rs)}
   if n:
    if cat in leaf:m['paired_n']+=n
    case_rows[cat]=[off[i] for i in ids]
    matrix[cat]={
     'official':np.array([[off[i]['score']['valid'],on[i]['score']['valid']] for i in ids],dtype=float),
     'completed_nonempty':np.array([[off[i]['completed_nonempty_correct'],on[i]['completed_nonempty_correct']] for i in ids],dtype=float)}
    if cat in leaf:
     mass+=leaf[cat]
     for key in points:points[key]+=matrix[cat][key].mean(axis=0)*leaf[cat]
    # Category difference intervals use paired rows. Memory adds a domain cluster resample below.
    index=rng.integers(0,n,size=(B,n))
    detail['official_on_minus_off_pp']={'point':float(100*np.mean(matrix[cat]['official'][:,1]-matrix[cat]['official'][:,0])),'interval95':interval(100*(matrix[cat]['official'][index,1]-matrix[cat]['official'][index,0]).mean(axis=1))}
   elif cat in leaf:m['missing_categories'].append(cat)
   if cat in MEMORY:
    detail['domains']={s:{'population':sum(e.get('scenario')==s for e in [])} for s in []}
    detail['domains']={s:{'paired_n':sum(r['scenario']==s for r in case_rows.get(cat,[])),'population':manifest['categories'][cat].get('scenario_populations',{}).get(s)} for s in ['notetaker','finance','healthcare','student','customer']}
   m['categories'][cat]=detail
  # Bootstrap static and multi-turn leaves independently, preserving the on/off pairing.
  for cat in matrix:
   if cat not in leaf or cat in MEMORY:continue
   arr=matrix[cat];n=len(arr['official']);index=rng.integers(0,n,size=(B,n))
   for key in boots:boots[key]+=arr[key][index].mean(axis=1)*leaf[cat]
  domains=sorted({r['scenario'] for cat in MEMORY for r in case_rows.get(cat,[])})
  if domains:
   domain_draws=rng.integers(0,len(domains),size=(B,len(domains)))
   for cat in MEMORY:
    if cat not in matrix:continue
    memory_boot=np.zeros((B,2))
    grouped={s:np.array([i for i,r in enumerate(case_rows[cat]) if r['scenario']==s],dtype=int) for s in domains}
    for b,chosen in enumerate(domain_draws):
     indices=[]
     for di in chosen:
      g=grouped[domains[di]]
      if len(g):indices.extend(rng.choice(g,size=len(g),replace=True))
     if not indices:indices=rng.integers(0,len(case_rows[cat]),size=len(case_rows[cat]))
     for key in boots:boots[key][b]+=matrix[cat][key][indices].mean(axis=0)*leaf[cat]
     memory_boot[b]=matrix[cat]['official'][indices].mean(axis=0)
    m['categories'][cat]['official_on_minus_off_pp']['interval95']=interval(100*(memory_boot[:,1]-memory_boot[:,0]))
  m['covered_overall_weight']=mass;m['missing_overall_weight']=1-mass
  m['aggregate']={}
  for key in points:
   if mass:
    m['aggregate'][key]={
     mode:{'projection_percent':float(100*points[key][i]/mass),'interval95':interval(100*boots[key][:,i]/mass),'weighted_contribution_points':float(100*points[key][i])} for i,mode in enumerate(['off','on'])}
    m['aggregate'][key]['on_minus_off_pp']={'point':float(100*(points[key][1]-points[key][0])/mass),'interval95':interval(100*(boots[key][:,1]-boots[key][:,0])/mass)}
  m['censuses']=[c for c,d in m['categories'].items() if d['census']]
  error_files=list((folder/'errors').glob('*/*/*.json'))
  m['error_records']=len(error_files)
  run_state=json.loads((out/'run-state.json').read_text()) if (out/'run-state.json').exists() else {}
  model_deadline=run_state.get('model_deadlines',{}).get(size,float('inf'))
  def current_error(p):
   return not manifest.get('sample_per_category') or json.loads(p.read_text())['time']>=run_state.get('started',0)
  m['historical_error_records']=sum(not current_error(p) for p in error_files)
  def unresolved_error(p):
   return not (folder/p.relative_to(folder/'errors').parts[0]/'items'/p.relative_to(folder/'errors').parts[1]/p.name).exists()
  def deadline_censor(p):
   e=json.loads(p.read_text())
   return current_error(p) and unresolved_error(p) and e['type']=='APITimeoutError' and e['time']>=model_deadline-2
  m['deadline_censored_item_modes']=sum(deadline_censor(p) for p in error_files)
  m['infrastructure_exclusions']=sum(current_error(p) and json.loads(p.read_text())['type'] not in ['ContextBudgetExceeded','ToolCallParseFailure'] and unresolved_error(p) and not deadline_censor(p) for p in error_files)
  m['context_failed_prerequisites']=sum(json.loads(p.read_text())['type']=='ContextBudgetExceeded' and '_prereq_' in p.name for p in error_files)
  m['parse_failed_prerequisites']=sum(json.loads(p.read_text())['type']=='ToolCallParseFailure' and '_prereq_' in p.name for p in error_files)
  m['cap_rechecks']=[json.loads(p.read_text()) for p in (folder/'cap_rechecks').glob('*/*.json') if not p.name.endswith('.raw.json')]
  report['models'][size]=m
 atomic(out/'analysis.json',report)
 if not manifest.get('sample_per_category'):write_docs(report)
 return report

def fmt(x):return 'not available' if x is None else f'{x:.1f}'
def metric(r):
 if not r:return 'not available'
 return f"{r['projection_percent']:.1f}% [{r['interval95'][0]:.1f}, {r['interval95'][1]:.1f}]"
def effect(r):return f"{r['point']:+.1f} pp [{r['interval95'][0]:+.1f}, {r['interval95'][1]:+.1f}]" if r else 'not available'

def write_docs(report):
 intro='''# BFCL-V4 expanded offline run

The earlier 40-case-per-cell experiment is preserved under `pilot/`, with its original code, reports and raw evidence. It is a pilot and is not an overall BFCL-V4 reproduction.

This expanded experiment uses the official BFCL-V4 data, loader, native function-calling handler, simulators and scoring functions. The scoring package is `bfcl-eval==2026.3.23`; upstream revision is `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`, Apache-2.0. Every offline scoring category is queued at full size, plus non-scoring live relevance. Entries that fit the time budget are retained; partial categories and unpaired deadline leftovers are disclosed below. No hosted model API or judge is used. `memory_vector` uses the official CPU `all-MiniLM-L6-v2` encoder, pinned to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

Hardware is an Apple M3 Ultra with 96 GB unified memory for model serving and a 32-thread x86 CPU for data, simulation, embeddings and scoring. No Linux GPU is used. One Q4_K_M model is served at a time, using llama.cpp build 12359 (`b1b770d90`), admission-aware concurrency and 65,536 tokens of context per slot. Initial serving used four slots; recovery uses four slots at 65% or more free memory, two at 50% or more, and one at 40% or more. The context per request and generation cap stay fixed; slot changes are operational, not output tuning. The other benchmark workload is uncontrolled. Temperature is 0, seed 20261121 and output cap 16,384 tokens per request. This cap matches the official Qwen adapter's configured `max_tokens`; its temperature 0.6 and input limit 58,000 are not copied. Our deterministic decoding and native OpenAI-compatible FC adapter may differ from the model-card evaluation, whose exact prompts, revision, runtime and quantization are not specified.

## Run and resume

```bash
RUN_NAME=full-reproduction MODEL_HOST=your-authorized-ssh-alias bash benchmarks/bfcl/run_full.sh
```

Requires `uv`, SSH access to the model-serving Mac and the pinned llama.cpp runtime already installed. All new runtime, model and cache files stay in task scratch directories. The controller runs under a transient systemd user service on Linux; the server and memory-pressure guard use transient launchd jobs from the Mac scratch directory. The endpoint is localhost:39730 through SSH. It never uses another model host automatically. Admission requires normal pressure and at least 40% system-wide memory free immediately before loading. After loading, the guard stops the task server at warning or critical pressure; the free percentage remains logged. The earlier stricter loaded-server 40% stop caused restart churn and was corrected to the stated rule. Generation resumes the same checkpoints when admission is safe. Do not point the command at an unrelated existing run directory.

Each API request is atomically checkpointed, and each fully scored item is atomically committed. A replay reconstructs the official simulator from its initial state using saved responses, checking request hashes before reusing them. If an official simulator returns a time-dependent value and the replay hash changes, the uncommitted attempt is archived under `replay-divergences/` and that item restarts from its original state; already committed items stay intact. Prerequisite memory snapshots are retained, and inference simulator keys and state directories are separated by thinking mode. An interrupted item resumes without silently changing its prompt or continuing a partly mutated simulator. Transient infrastructure errors are retried and excluded explicitly, never scored as model failures. A serving connection loss suspends the worker as a whole instead of rapidly walking the dataset and labeling many items as separate faults. The supervisor resolves uv from the executable PATH or the standard user installation so a scratch rebuild also works under systemd. A completed-question request that exhausts the serving context is different: the actual rejected request is retained under `failed-calls/`, and the official scorer receives an empty failed-inference result, so the case stays in the denominator. Any resulting irrelevance absence credit is removed from completed-nonempty performance. Context-failed memory-write prerequisites are unscored prerequisites and can block a domain; those missing domains are explicit. Use a fresh RUN_NAME for a new reproduction; repeating it resumes that named run and its persisted absolute deadline. The final cleanup removes task services, tunnel, server, weights and caches; results and snapshots remain here.

## Coverage and score formula

The official score is `0.10 non-live + 0.10 live + 0.10 irrelevance + 0.30 multi-turn + 0.40 agentic`, with agentic equally split between memory and web search. Non-live averages the simple-language mean, multiple, parallel and parallel-multiple equally; simple averages Python/Java/JavaScript equally. Live is weighted by its original four category populations, not by the number completed here. Irrelevance averages non-live/live equally. Multi-turn averages its four variants equally. Memory averages the three backends equally. This code applies exactly those leaf weights to the categories observed and divides by their covered weight. With all offline leaves represented, this is an **80%-weight offline projection**, not the full overall score. The unnormalized weighted contribution is also retained in `results/full/analysis.json`; missing web-search performance must not be imputed as failure or as success.

Excluded: `web_search_base` and `web_search_no_snippet`, which require live SerpAPI search and live HTTP pages. Their combined missing weight is 20%. `format_sensitivity` is non-scoring and the official variations apply only to prompting-mode models, not this native-FC matrix. Live relevance is also non-scoring but is included. The pinned data has 884 live-irrelevance and 16 live-relevance items, compared with 882 and 18 in the release blog, so actual pinned file populations govern this run. The model cards give an overall BFCL-V4 row, not category-level reference scores.

Each category has a seeded random permutation, shared between modes. Jobs aim at all rows rather than a selected fixed cap. Models receive an equal share of the remaining eight-hour deadline; a completed model releases unused time to later models. Within a model, the queue alternates modes to balance completed and in-flight items, round-robins static/multi-turn categories, and reserves 15 of 32 scheduling choices for memory. Memory prerequisite chains remain ordered, with independent scenarios in the fixed order notetaker, finance, healthcare, student, customer to obtain at least one finished domain early. This cost-aware order and deadline censoring can bias incomplete memory coverage toward shorter domains. Intervals cannot repair absent domains or unfinished categories. All planned IDs, prerequisites, actual counts and missing domains are printed or retained.

## Metrics and intervals

“Official” preserves BFCL's exact valid/invalid decisions. “Completed nonempty” additionally rejects any item with a length stop and any irrelevance credit caused by a blank/empty structured answer or by malformed tool calls. Those credits are tabulated separately and are not described as skill. The primary comparison uses only IDs completed in both modes, so every within-model effect is paired. Unpaired completed rows are retained and counted separately. In-flight requests that time out at the persisted per-model deadline are reported as budget-censored item/modes, not as infrastructure faults or model answers.

Intervals are 95% paired bootstrap case-mix intervals with 4,000 replicates, stratified by category. Memory domains are cluster-resampled jointly across backends, followed by question resampling within a domain. They are conditional on observed items and learned memory snapshots, do not include quantization/runtime mismatch or inference randomness, and do not establish performance on unobserved domains. For a full category census the observed score itself is exact for this run; the interval describes sensitivity to case mix. Category proportions additionally have Wilson intervals in the JSON evidence.

In the finished run, no category reached a full census. Only the notetaker memory domain was observed, so domain resampling adds no between-domain uncertainty; several static and multi-turn strata contain only two to seven paired cases. Bootstrap intervals can understate uncertainty in such small strata and cannot validate population or cross-size rankings. The completed-nonempty metric keeps the same paired denominator and weights, setting excluded credits to zero rather than estimating accuracy conditional on successful completion. API requests also have a 900-second timeout, shortened by the remaining model allocation; a timeout is an unfinished request, not a token-length stop or a scored answer.

'''
 table='| Model | Card overall | Paired N per mode | Official offline off, 95% interval | Official offline on, 95% interval | On minus off, 95% interval |\n|---|---:|---:|---|---|---|\n'
 earned='| Model | Completed nonempty off | Completed nonempty on | On minus off |\n|---|---|---|---|\n'
 detail='\n## Per-category coverage and counts\n\n| Model | Category | N paired / population | Off correct | On correct | Empty credits off/on | Malformed credits off/on | Length stops off/on | Context failures off/on |\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
 for size,m in report['models'].items():
  agg=m['aggregate'].get('official',{});e=m['aggregate'].get('completed_nonempty',{})
  table+=f"| {size} Q4_K_M | {m['published_full']} | {m['paired_n']} | {metric(agg.get('off'))} | {metric(agg.get('on'))} | {effect(agg.get('on_minus_off_pp'))} |\n"
  earned+=f"| {size} | {metric(e.get('off'))} | {metric(e.get('on'))} | {effect(e.get('on_minus_off_pp'))} |\n"
  if size != next(iter(report['models'])):
   detail+='\n| Model | Category | N paired / population | Off correct | On correct | Empty credits off/on | Malformed credits off/on | Length stops off/on | Context failures off/on |\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
  for cat,d in m['categories'].items():
   off=d['modes']['off'];on=d['modes']['on']
   detail+=f"| {size} | {cat} | {d['paired_n']}/{d['population']} | {off['official_correct']} | {on['official_correct']} | {off['empty_credits']}/{on['empty_credits']} | {off['malformed_tool_credits']}/{on['malformed_tool_credits']} | {off['length_stops']}/{on['length_stops']} | {off['context_budget_failures']}/{on['context_budget_failures']} |\n"
  detail+=f"\n{size}: total completed off/on {m['all_completed']['off']}/{m['all_completed']['on']} (including non-scoring live relevance); paired scoring questions {m['paired_n']}; covered overall weight {m['covered_overall_weight']:.6f}; missing overall weight {m['missing_overall_weight']:.6f}; deadline-censored item/modes {m['deadline_censored_item_modes']}; infrastructure-excluded item/modes {m['infrastructure_exclusions']}; context-failed memory prerequisites {m['context_failed_prerequisites']}. Full category censuses: {', '.join(m['censuses']) or 'none'}. Completely absent offline categories: {', '.join(m['missing_categories']) or 'none'}.\n\n"
  for cat in MEMORY:
   detail+=f"{size}, {cat}, paired questions by domain: "+', '.join(f"{k}={v['paired_n']}/{v['population']}" for k,v in m['categories'][cat]['domains'].items())+'.\n\n'
 rechecks='\n## Pilot token-limit rechecks\n\nThe six pilot length-stop cases are re-requested with their original prompts/tools, same mode and weights, and the output cap raised from 4,096 to 16,384. These selected diagnostics are kept outside the expanded sample and do not enter its aggregates.\n\n| Model/mode | ID | Pilot official correct | 16K official correct | 16K completed nonempty | 16K empty credit | 16K length stop |\n|---|---|---|---|---|---|---|\n'
 for size,m in report['models'].items():
  for r in m['cap_rechecks']:rechecks+=f"| {size} {r['mode']} | {r['id']} | {r['pilot_correct']} | {r['score']['valid']} | {bool(r['score']['valid']) and not r['empty_answer_credit'] and not r.get('malformed_tool_credit',False) and not r['length_stopped']} | {r['empty_answer_credit']} | {r['length_stopped']} |\n"
 evidence='''
## Evidence and limits

- `results/full/manifest.json` and each model's `manifest.json`: every dataset population, planned permutation, source hashes, prerequisite IDs and score weights.
- `results/full/{size}/{mode}/calls/{category}/{id}/{step}.json`: exact requests and full API responses, checkpointed before further simulation.
- `results/full/{size}/{mode}/items/{category}/{id}.json`: official results, metadata, score, cap/absence flags and timing. Prerequisites are marked and excluded from question N.
- `results/full/{size}/{mode}/state/`: official learned memory and per-prerequisite snapshots, retained for audit/resume.
- `results/full/analysis.json`: category Wilson intervals, paired effects, overall weighted projections, cluster bootstrap intervals, coverage and diagnostics.
- `results/full/{size}/errors/`: infrastructure exclusions, separate from incorrect model answers.
- `results/full/run-state.json`, per-model progress/heartbeat and final worker status: operational checkpoints and observed progress, not an inferred completion claim.
- `results/full/resources-before.txt`, `resources-after.txt`, per-model resource/pressure files and `cleanup.txt`: resource and cleanup proof. `DONE.json` states final operational status.

Primary methodology: [official BFCL V4 score composition](https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html), [official memory benchmark](https://gorilla.cs.berkeley.edu/blogs/16_bfcl_v4_memory.html), and the pinned [official repository](https://github.com/ShishirPatil/gorilla/tree/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard). Dataset and harness are Apache-2.0; the original license is retained in `LICENSE.upstream`.

This remains different from the cards: Q4_K_M conversion, deterministic decoding, an explicit official-adapter token cap, 65,536-token serving context, pinned native FC transport, a shared machine, missing live web search and any deadline-censored categories/domains. Different sizes can reach different case sets under the deadline; only the within-size mode effects are paired, so cross-size rankings can reflect coverage differences. These scores do not establish memory-extraction quality or justify a universal thinking-mode recommendation for extraction. No model-card per-category score is available for category-by-category numerical validation.
'''
 text='**Run status: in progress until results/full/DONE.json exists.**\n\n'+intro+'## Published and local results\n\n'+table+'\n'+earned+detail+rechecks+evidence
 text=text.replace('results/full',str(RUN_DIR.relative_to(ROOT)))
 (ROOT/'README.md').write_text(text)
 prior=(ROOT/'pilot/REPORT.md').read_text()
 beginning=prior[:prior.index('## Local comparison')]
 beginning=beginning.replace('line 274 at inspection','line 284 at inspection').replace('Sources 12 and 15','Sources 12 through 15').replace('Sources 12 and 15','Sources 12 through 15')
 beginning+='Expanded-run citation snapshot: `evidence/full-book-citations.json`. The current Chapter 06 paragraph and Numbers row both cite Sources 12, 13, 14 and 15.\n\n'
 suggestions='\n## Suggested book wording\n\n'
 for size,m in report['models'].items():
  agg=m['aggregate'].get('official',{});e=agg.get('on_minus_off_pp')
  if e:
   suggestions+=f"For {size}: \"On our offline BFCL-V4 projection, the Q4_K_M {size} model scored {metric(agg.get('off'))} with thinking off and {metric(agg.get('on'))} with thinking on, using {m['paired_n']} paired questions per mode. The thinking-on difference was {effect(e)}; live web search and the incomplete categories listed in the evidence prevent this from being a reproduction of the full vendor score.\"\n\n"
 suggestions+='For the extraction advice: "BFCL measures tool use, including memory operations, rather than the fact-extraction task in this walkthrough. Our thinking-mode comparison belongs with the BFCL results, while extraction speed and fidelity need a separate paired test on the intended notes and schema."\n\nKeep all intervals, missing-category/domain counts and the separate empty-credit tally with these sentences; do not imply a full official aggregate or an extraction-quality result. Each quoted proposed passage is at most two sentences and uses no em dashes.\n'
 (ROOT/'REPORT.md').write_text((beginning+'## Expanded local results\n\n'+table+'\n'+earned+detail+rechecks+suggestions+evidence).replace('results/full',str(RUN_DIR.relative_to(ROOT))))

if __name__=='__main__':
 r=analyze()
 for size,m in r['models'].items():print(size,m['paired_n'],m['covered_overall_weight'],m['aggregate'].get('official'))

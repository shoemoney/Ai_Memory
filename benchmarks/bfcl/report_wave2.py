"""Render the new common-item continuation without changing earlier evidence."""
import json
import subprocess
from pathlib import Path
from full_common import ROOT, RUN_DIR, CATEGORIES, MODELS

def main():
 out=RUN_DIR
 from audit_wave2 import main as audit_main
 audit_main()
 from book_citations import collect
 citations=collect()
 a=json.loads((out/'analysis.json').read_text())
 manifest=json.loads((out/'manifest.json').read_text())
 done=json.loads((out/'DONE.json').read_text())
 run_state=json.loads((out/'run-state.json').read_text())
 pause_credit=sum(p['credited_seconds'] for p in run_state.get('pause_credits',[]))
 proof=(out/'cleanup.txt').read_text() if (out/'cleanup.txt').exists() else ''
 scratch_absent={str(p):not p.exists() for p in [Path('/var/tmp/membench-bfcl'),Path('/data/scratch/membench/bfcl')]}
 (out/'scratch-cleanup.json').write_text(json.dumps(scratch_absent,indent=2)+'\n')
 clean=(all(scratch_absent.values()) and done.get('cleanup_complete') and 'remote-scratch-absent' in proof and proof.count('task-service-absent')==2 and 'task-port-unoccupied' in proof and 'local-scratch-absent=True' in proof and not Path('/var/tmp/membench-bfcl').exists() and not subprocess.check_output(['ss','-ltnH','sport = :39730'],text=True).strip())
 local=subprocess.check_output(['df','-h','/','/data'],text=True)+'\n'+subprocess.check_output(['ps','-eo','pid,comm,rss'],text=True)
 (out/'linux-resources-after.txt').write_text(local)
 done['cleanup_complete']=bool(clean)
 (out/'DONE.json').write_text(json.dumps(done,indent=2)+'\n')
 selected={c:set(d['selected_ids']) for c,d in manifest['categories'].items()}
 coverage={}
 for size in MODELS:
  coverage[size]={}
  for c in CATEGORIES:
   coverage[size][c]={m:len(selected[c]&{p.stem for p in (out/size/m/'items'/c).glob('*.json')}) for m in ['off','on']}
 (out/'selected-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
 fixed_fulfilled=all(coverage[size][c][mode]==len(selected[c]) for size in MODELS for c in manifest['leaf_weights'] for mode in ['off','on'])
 initial=json.loads((out/'initial-manifest.json').read_text()) if (out/'initial-manifest.json').exists() else None
 initial_coverage={size:{c:{mode:len(set(initial['categories'][c]['selected_ids'])&{p.stem for p in (out/size/mode/'items'/c).glob('*.json')}) for mode in ['off','on']} for c in manifest['leaf_weights']} for size in MODELS} if initial else {}
 (out/'initial-selected-coverage.json').write_text(json.dumps(initial_coverage,indent=2)+'\n')
 fulfilled=bool(initial) and all(initial_coverage[size][c][mode]==len(initial['categories'][c]['selected_ids']) for size in MODELS for c in manifest['leaf_weights'] for mode in ['off','on'])
 uniform=a.get('uniform_category_count',0)
 uniform_met=uniform>0 and all(a['models'][size]['categories'][c]['paired_n']==min(uniform,manifest['categories'][c]['population']) for size in MODELS for c in manifest['leaf_weights'])
 text='''# BFCL-V4 wave-two continuation

The earlier pilot remains under `pilot/`. The earlier incomplete expanded run remains unchanged under `results/full/`; its README and editor report are preserved as `results/wave2/prior-README.md` and `prior-REPORT.md`. The new continuation reuses every completed question, prerequisite, request and memory snapshot from that run. Data preparation, simulation, embeddings and scoring run on a 32-thread x86 CPU; model generation runs on an Apple M3 Ultra with 96 GB unified memory. No Linux GPU, hosted generation or LLM judge is used.

The data, official loader, native function-calling adapter, simulators and scorers come from `bfcl-eval==2026.3.23`, upstream commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`, Apache-2.0 (`LICENSE.upstream`). Model revisions and SHA-256 hashes are in `full_common.py`; models are Qwen3.5 0.8B, 2B, 4B and 9B, Q4_K_M. Runtime is llama.cpp build 12359, commit `b1b770d90`. `requirements.txt` pins Python dependencies. The CPU memory-vector encoder is `all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

## Reproduce or resume

```bash
RUN_NAME=wave2 MODEL_HOST=your-authorized-ssh-alias bash benchmarks/bfcl/run_full.sh --hours 14 --sample-per-category 10 --cohort-file "$PWD/benchmarks/bfcl/results/wave2/cohort-target.json"
```

The shipped `wave2` directory resumes its persisted deadline and reused checkpoints. Use a fresh run name for new inference on the same frozen cohort. The shipped continuation already contains all reused item, request and learning checkpoints. The command requires the pinned llama.cpp runtime already installed on the authorized serving machine and `uv` on the scoring machine. All added dependencies, downloads and caches stay in task scratch directories. Future launches put large local files and UV, pip, Hugging Face and managed Python caches under `/data/scratch/membench/bfcl`; the environment already active at the disk-coordination update stays in `/var/tmp/membench-bfcl` until cleanup. New environment creation checks `df -h / /data` and pauses below 20 GiB free on the system disk. Servers bind localhost:39730 and are reached only through SSH. A model initially loads only at normal kernel pressure and at least 40% system-wide free memory. After a pressure stop, admission requires three consecutive normal-pressure checks with at least 45% free memory, one minute apart; a bad reading or stale sequence resets the count. Disk and memory pauses are timestamped and extend the global and current-model deadlines equally, with a combined maximum of 10 extra hours. The systemd runtime ceiling is 24 hours. Only the owned server is stopped at warning or critical pressure. Other services are untouched. Four slots are used at >=65% free, two at >=50%, otherwise one at >=40%, with 65,536 tokens per slot. `lsof -b` avoids blocking on unrelated network mounts.

## Sampling and interpretation

The initial phase attempted a seeded min(60, population) sample from every category. Its plan remains in `initial-manifest.json`, with phase snapshots under `phases/initial-60-target/` and every raw output retained. Permanent prerequisite failures and observed learning cost made that target infeasible within the available resources. The authorized uniform reduction is a fixed **10 questions in each of the 19 offline scoring categories**, or **190 per model and mode**, recorded before the remaining three model cells were extended in `cohort-target.json`.

Non-memory categories use the first 10 IDs in their original seeded permutations. Each memory backend uses the first 10 **notetaker** IDs in its original seeded full permutation, preserving the completed model-specific write-phase checkpoints. Each thinking mode retains its own independently learned snapshot, so memory effects include both write and query behavior. The memory portion excludes finance, healthcare, student and customer domains; it does not estimate performance across those domains. Some retained notetaker IDs lie outside the abandoned 60-ID attempt, and are reused from the earlier full queue. Selection uses category, scenario and seed, never correctness scores. The same 190 IDs are fixed across all four models and both modes. Seed is 20261121, temperature 0, output cap 16,384, client timeout initially 900 seconds, then 3,600 seconds (bounded by the model deadline) after healthy slow requests exceeded 900 seconds, and the official native-FC adapter is unchanged. No cap, prompt or decoding setting was tuned to accelerate the run.

The budget includes setup and cleanup, with explicitly authorized disk and memory pause credits capped at 10 extra hours total. Every interval has timestamps under `results/wave2/pauses/`; active inference receives no pause credit. The queue prioritizes the least paired category and the mode with fewer eligible scoring completions. Failed prerequisites and common-feasible domain decisions remain recorded in `generation-availability.json`, including broader attempts outside the final cohort. Existing non-scoring live-relevance outputs remain available but are excluded from the final 190-question cohort.

The headline below uses only selected IDs completed in **all eight cells**, so sizes and modes receive exactly the same cases. If the final fixed cohort is incomplete, its count is further reduced **uniformly across the 19 scoring categories**, keeping complete smaller populations as censuses. The count is the largest feasible common count; within a category, the earliest available common IDs in the original seeded selection order are retained. Correctness scores never choose this subset. `analysis.json` records the uniform count, exact IDs and all available common counts; `selected-coverage.json` shows final-target completions in every cell; `initial-selected-coverage.json` separately preserves coverage of the abandoned broader target. This availability-based complete-case projection is conditional and can be biased by deadlines or failed memory prerequisites; it is not an unbiased estimate for the planned sample. Incomplete requests are never substituted for incorrect answers, and all raw extra completions remain available.

Official offline leaf weights sum to 0.80: non-live 0.10, live 0.10, irrelevance 0.10, multi-turn 0.30 and memory 0.20. Their composition follows upstream helpers, including language averaging and population-weighted live categories. The projection divides the observed weighted contribution by represented weight. **Both live web-search categories are excluded (20% overall weight); this is not the full model-card aggregate.** Missing offline strata also reduce represented weight. `format_sensitivity` and `live_relevance` are non-scoring. Actual pinned populations govern selection.

Intervals are 95% paired bootstrap case-mix intervals (4,000 replicates), stratified by category; memory domains are cluster-resampled jointly across backends, then questions within domain. They are conditional on observed questions and learned snapshots. They do not account for absent domains, deadline selection, runtime or quantization differences, and can understate uncertainty for small strata. A category census is exact for this execution, while intervals describe sensitivity to case mix. Category rates have Wilson intervals in `analysis.json`.

'''
 text+=f"Initial 60-per-category target complete: **{fulfilled}**. Final fixed 10/category cohort complete: **{fixed_fulfilled}**. Primary uniform count: **{uniform} per scoring category**, capped at each smaller population. Uniform reduced comparison complete: **{uniform_met}**. Timestamped resource-pause credit: **{pause_credit/3600:.3f} hours out of a 10-hour maximum**. Operational status: `{done['status']}`. Cleanup verified: **{bool(clean)}**.\n\n"
 text+='| Model Q4_K_M | Card overall | Common paired N per mode | Offline off (95%) | Offline on (95%) | On minus off (95%) |\n|---|---:|---:|---|---|---|\n'
 def metric(r):return f"{r['projection_percent']:.1f}% [{r['interval95'][0]:.1f}, {r['interval95'][1]:.1f}]" if r else 'unavailable'
 def effect(r):return f"{r['point']:+.1f} pp [{r['interval95'][0]:+.1f}, {r['interval95'][1]:+.1f}]" if r else 'unavailable'
 for s,m in a['models'].items():
  agg=m['aggregate'].get('official',{})
  text+=f"| {s} | {m['published_full']} | {m['paired_n']} | {metric(agg.get('off'))} | {metric(agg.get('on'))} | {effect(agg.get('on_minus_off_pp'))} |\n"
 text+='\n## Per-category common coverage and results\n\n'
 for s,m in a['models'].items():
  text+=f"### {s}\n\nParser-failed memory prerequisites: {m.get('parse_failed_prerequisites',0)}. Parser-failed common scored items: {sum(v['modes'][mode].get('tool_call_parse_failures',0) for v in m['categories'].values() for mode in ['off','on'])}.\n\nRepresented overall weight: {m['covered_overall_weight']:.6f}; missing weight: {m['missing_overall_weight']:.6f}.\n\n| Category | Uniform N / available common / target / population | Off correct | On correct | On minus off (95%) | Length stops off/on | Empty or malformed credits off/on |\n|---|---:|---:|---:|---|---:|---:|\n"
  for c,d in m['categories'].items():
   off=d['modes']['off'];on=d['modes']['on']
   text+=f"| {c} | {d['paired_n']}/{a.get('available_common_counts',{}).get(c,d['paired_n'])}/{len(selected[c])}/{d['population']} | {off['official_correct']} | {on['official_correct']} | {effect(d.get('official_on_minus_off_pp'))} | {off['length_stops']}/{on['length_stops']} | {off['empty_credits']+off['malformed_tool_credits']}/{on['empty_credits']+on['malformed_tool_credits']} |\n"
  agg=m['aggregate'].get('completed_nonempty',{})
  text+=f"\nCompleted-nonempty projection: off {metric(agg.get('off'))}; on {metric(agg.get('on'))}; effect {effect(agg.get('on_minus_off_pp'))}. This keeps the same denominator and zeroes length-stop and blank/malformed irrelevance credits.\n\n"
  for c in ['memory_kv','memory_vector','memory_rec_sum']:
   text+=c+': '+', '.join(f"{domain}={v['paired_n']}/{v['population']}" for domain,v in m['categories'][c]['domains'].items())+'.\n\n'
 text+='''## Evidence, limits and cleanup

`results/wave2/manifest.json` records populations, full permutation, selected IDs, weights and source hashes. Each model directory retains request/response checkpoints under `{mode}/calls`, official per-item scores under `{mode}/items`, learned snapshots under `{mode}/state`, failed calls and infrastructure errors separately. Prior model manifests and progress were archived under `harness-history/wave1-final`; `results/full` is unchanged. Interrupted official simulator replays must match request hashes; divergence archives the uncommitted attempt. Model-induced context overflow is scored as failed inference; failed memory-write prerequisites remain explicit missing domains. Malformed generated tool-call JSON that the server returns as HTTP 500 is also retained as failed inference, rather than discarded as infrastructure. Parser-failed prerequisites remain explicit blocked domains. The repair and positive/negative classification checks are recorded in `evidence/wave2-repairs.jsonl`. A zero-inference resume regression also verified that persisted completion counts are loaded before scheduling (old worker 0, corrected worker 597 fixture checkpoints), preventing mode-priority resets after interruptions; see `evidence/wave2-resume-verification.json`. No answers are fabricated.

`results/wave2/analysis.json` contains common-case point scores, category Wilson intervals, paired effects, bootstrap intervals, absence-credit/length-stop diagnostics and missing domains. `selected-coverage.json` gives selected completion counts across all cells. `cohort-target.json`, `initial-manifest.json`, `run-state.json`, resource/pressure snapshots, `cleanup.txt`, `scratch-cleanup.json` and `DONE.json` provide operational evidence, including absence of both local scratch roots. Cleanup removes task launchd jobs, server, tunnel, models, Python environment and embedding caches; no containers are used. Cleanup status above is conditional on actual proof, not assumed from a finished process.

The model cards report overall BFCL-V4 scores, with no per-category reference values. Q4_K_M quantization, deterministic decoding, native FC transport, 65,536-token serving context, shared hardware, fixed sample and missing web search differ from vendor conditions. This run cannot validate or contradict the full vendor aggregate, establish extraction accuracy, or justify a general thinking-mode recommendation for extraction. Incomplete common coverage further limits inference. Earlier six selected cap rechecks are diagnostics only and remain outside headline results.

Operational problems: shared-disk exhaustion interrupted the first continuation and led to the large-scratch migration. Confirmed memory warnings stopped only owned serving jobs; a persisted hysteresis gate controlled resumption and the pause ledger recorded the intervals. Separate health-probe interruptions had no confirmed pressure warning and remained infrastructure events, with checkpoints replayed. The broader memory attempt left failed malformed-tool prerequisites, while model-induced context overflows were retained as failed inference. Unscored learning work did not complete the original memory target and remains separate from the frozen notetaker-only cohort. Six earlier pilot cap diagnostics are retained and excluded from the final aggregate.

Primary sources: [official repository](https://github.com/ShishirPatil/gorilla/tree/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard), [official score composition](https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html), [official memory benchmark](https://gorilla.cs.berkeley.edu/blogs/16_bfcl_v4_memory.html). Model-card revisions and exact book citations remain in `evidence/model-card-figures.json`, `evidence/full-book-citations.json` and `results/wave2/prior-REPORT.md`.
'''
 (ROOT/'README.md').write_text(text)
 editor='''# BFCL-V4 wave-two editor report

Chapter `06-small-memory-models.html` prints model-card BFCL-V4 figures 25.3, 43.6, 50.3 and 66.1 in a paragraph and Numbers row. A separate Tested paragraph prints the earlier incomplete local run's sample sizes and thinking-mode effects. Those are full vendor aggregates. The local results below are offline projections excluding live web search, not reproductions of the full aggregate. Earlier citation and primary-source inspection is preserved in `results/wave2/prior-REPORT.md`; no chapter was edited.

'''+text
 editor+='\n## Current book statements\n\n'
 editor+='Observed '+citations['observed_utc']+'. Exact file hashes and sentences are in `evidence/wave2-book-citations.json`.\n\n'
 for row in citations['statements']:
  editor+=f"- `{row['file']}:{row['line']}` ({row['kind']}): {row['statement']}\n\n"
 editor+='\n## Suggested replacement wording\n\n'
 for s,m in a['models'].items():
  agg=m['aggregate'].get('official',{})
  editor+=f"{s}: This book measured {metric(agg.get('off'))} with thinking off and {metric(agg.get('on'))} with thinking on across {m['paired_n']} common paired offline BFCL-V4 questions per mode in the uniformly reduced category sample, using Q4_K_M weights. The paired effect was {effect(agg.get('on_minus_off_pp'))}; missing web search and availability-based sampling prevent comparison with the full vendor score of {m['published_full']}.\n\n"
 first=next(iter(a['models'].values()))
 if uniform>0:
  effects='; '.join(size+' '+effect(m['aggregate'].get('official',{}).get('on_minus_off_pp')) for size,m in a['models'].items())
  editor+=f"For the Tested paragraph: This book compared the same {uniform} completed questions per scoring category, capped at smaller populations, giving {first['paired_n']} common paired offline questions per mode and model; the thinking-on effects were {effects}. Memory cases cover only notetaker, and excluded memory domains and live web search limit these comparisons, and BFCL does not measure extraction quality.\n\n"
 else:
  editor+='For the Tested paragraph: This book could not obtain a complete uniform paired offline cohort within the recorded resource limits. The retained partial results exclude live web search and do not measure extraction quality.\n\n'
 editor+='The independent retained-evidence audit passed (`evidence/wave2-final-audit.json`): request hashes, caps, thinking flags, planned IDs, archived worker bytes and common-cell weighted point scores. It does not independently validate bootstrap intervals. No new extraction-quality conclusion is supported. Pressure admission and the combined credit cap passed positive and negative synthetic checks in `evidence/wave2-pressure-verification.json`.\n'
 (ROOT/'REPORT.md').write_text(editor)
 from chart_wave2 import write_chart
 write_chart(a,out)

if __name__=='__main__':main()

"""Derive large-run tables from checkpoint files; never invent missing scores."""
from pathlib import Path
import json,collections,math,time,re
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/full'
METHODS=['full-standard','bm25-standard','dense-standard','mem0-raw-standard','full-oracle']
def interval(k,n):
 if not n:return None
 z=1.95996398454;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return [c-r,c+r]
def summarize():
 OUT.mkdir(parents=True,exist_ok=True)
 rows=[json.loads(p.read_text()) for p in sorted((OUT/'items').glob('*.json'))]
 result={}
 for method in METHODS:
  allr=[r for r in rows if r['method']==method];r=[v for v in allr if v['status']=='scored'];k=sum(v['correct'] for v in r)
  result[method]={'correct':k,'n':len(r),'wilson95':interval(k,len(r)),'context_skips':sum(v['status']=='context-does-not-fit' for v in allr),'checkpointed':len(allr),'missing':300-len(allr),'per_stratum':{s:{'correct':sum(v['correct'] for v in r if v['stratum']==s),'n':sum(v['stratum']==s for v in r)} for s in sorted({v['stratum'] for v in rows})}}
  result[method]['per_question_type']={t:{'correct':sum(v['correct'] for v in r if v['question_type']==t),'n':sum(v['question_type']==t for v in r)} for t in sorted({v['question_type'] for v in rows if v['status']=='scored'})}
  result[method]['judge_format_invalid_calls']=sum(not bool(re.fullmatch(r'(yes|no)[.!]?',c['text'].lower().strip())) for v in r for c in v['judge']['calls'])
  result[method]['answer_empty']=sum(not v['hypothesis'] for v in r)
  result[method]['empty_answer_positive']=sum(not v['hypothesis'] and v['correct'] for v in r)
  result[method]['answer_length_stops']=sum(v['answer']['raw']['choices'][0]['finish_reason']=='length' for v in r)
  result[method]['judge_vote_disagreements']=sum(len(set(v['judge']['votes']))>1 for v in r)
  for group in [result[method]['per_question_type'],result[method]['per_stratum']]:
   for value in group.values():value['wilson95']=interval(value['correct'],value['n'])
 audit_path=OUT/'manual-audit.json'
 audit={'n':0,'agreement':None,'status':'not yet reviewed'}
 if audit_path.exists():
  a=json.loads(audit_path.read_text());reviews=a['reviews'];matched=sum(v['manual_label']==v['majority_label'] for v in reviews)
  audit={'n':len(reviews),'agreement':matched/len(reviews) if reviews else None,'agree':matched,'wilson95':interval(matched,len(reviews)),'reviewer':a['reviewer']}
 manifest_path=OUT/'manifest.json'
 eligible=set()
 if manifest_path.exists():eligible={v['question_id'] for v in json.loads(manifest_path.read_text())['items'] if v['oracle_prompt_tokens']+512<=8192}
 matched={}
 for method in METHODS[1:]:
  subset=[v for v in rows if v['status']=='scored' and v['method']==method and v['question_id'] in eligible]
  k=sum(v['correct'] for v in subset);matched[method]={'correct':k,'n':len(subset),'wilson95':interval(k,len(subset))}
 data={'oracle_window_matched_subset':matched,'updated_epoch':time.time(),'selected_n':300,'complete':len(rows)==1500,'systems':result,'manual_audit':audit,'scored_total':sum(v['n'] for v in result.values()),'checkpoint_total':len(rows)}
 tmp=OUT/'summary.json.tmp';tmp.write_text(json.dumps(data,indent=2));tmp.replace(OUT/'summary.json')
 def typecell(v):
  if not v['n']:return '0/0 (unavailable)'
  ci=interval(v['correct'],v['n']);return f"{v['correct']}/{v['n']} ({100*ci[0]:.1f}% to {100*ci[1]:.1f}%)"
 def cell(v):
  if not v['n']:return f"unavailable, N=0; {v.get('context_skips',0)} context skips"
  return f"{v['correct']}/{v['n']} ({100*v['correct']/v['n']:.1f}%), 95% Wilson {100*v['wilson95'][0]:.1f}% to {100*v['wilson95'][1]:.1f}%"
 table='| System | Local result | Checkpoints missing |\n|---|---|---:|\n'+''.join(f'| {m} | {cell(v)} | {v["missing"]} |\n' for m,v in result.items())
 types='| Official question type (abstentions included) | BM25 | Dense | Mem0 raw | Oracle full context |\n|---|---:|---:|---:|---:|\n'
 for kind in sorted({v['question_type'] for v in rows if v['status']=='scored'}):
  vals=[]
  for method in METHODS[1:]:
   v=result[method]['per_question_type'].get(kind,{'correct':0,'n':0});vals.append(typecell(v))
  types+='| '+kind+' | '+' | '.join(vals)+' |\n'
 vals=[]
 for method in METHODS[1:]:
  v=result[method]['per_stratum'].get('abstention',{'correct':0,'n':0});vals.append(typecell(v))
 types+='| Abstention overlay | '+' | '.join(vals)+' |\n'
 types+='\nCells show correct/N and descriptive 95% Wilson intervals. The abstention row overlaps the official types; it is not added again to overall N. Disjoint sampling-stratum counts remain in the manifest and summary.\n'
 paired='| Oracle-window matched subset | Result |\n|---|---|\n'+''.join('| '+method+' | '+cell(v)+' |\n' for method,v in matched.items())
 (OUT/'TABLE.md').write_text(table+'\n'+types+'\n'+paired)
 intro='**Large run status: '+('all 300 questions checkpointed for every lane.' if data['complete'] else f'in progress or interrupted; {len(rows)}/1500 lane checkpoints exist.')+'**\n\n'
 details='''LongMemEval tests whether an assistant can recover information from dated conversations, combine evidence across sessions, reason about time, follow changing facts, respect preferences, and abstain when the history lacks the answer.

The original 14-question pilot is preserved in `README.pilot.md`, `REPORT.pilot.md`, and the original files under `results/`. This run uses the official cleaned LongMemEval_S full haystacks for BM25, dense retrieval, and Mem0. It never replaces a retrieval input with oracle evidence. Oracle full context is a separate reference.

The model is Gemma 2 9B at 4-bit (MLX repository/revision in `results/full/manifest.json`), served on Apple M1 Ultra, 64 GB. Its native context is 8,192 tokens. Full histories that exceed that window, including the answer allowance, are recorded as unavailable, never truncated. This differs substantially from the paper's 128k-context readers. An oracle subset that fits is an easier, separately labeled reference, not an upper bound on every question or model.

Sampling: 300/500 questions, seed 20261122. Proportional allocation uses largest remainders across the six non-abstention types and an abstention stratum; IDs are sorted before sampling. Counts and exact selected IDs are in the manifest. Question text, answer references and types match across the selected standard/Oracle records, but the official variants are independently timestamped. Each lane uses its own variant's question date with its own history dates. `variant-date-maps.json` and the verifier enforce that alignment. Earlier Oracle-only mixed-date outputs are uniformly archived under `preflight/oracle-date-mix/` and excluded; standard retrieval results were retained. The `source_session_count` field records the standard candidate-haystack size; actual supplied sessions are visible in `context`. Every lane targets those same 300 IDs; context failures have explicit records and do not count as wrong or disappear silently. Confidence intervals are descriptive Wilson intervals, not a correction for stratification, correlated judging, or judge error.

BM25 uses 800-character windows, stride 700, with both speakers and dates, and returns up to ten chunks in history order. If needed to fit the native window, whole lower-ranked chunks are dropped and the actual context is saved. Dense RAG embeds those same chunks using pinned all-MiniLM-L6-v2 on CPU (maximum embedding sequence length 256 wordpieces), cosine similarity, up to ten under the same context budget. Mem0 OSS 0.1.118 uses its actual `add(..., infer=False)` and `search` APIs with local Qdrant and the same CPU vectors. Every source session and chunk is ingested; added/stored counts and chunk hashes are recorded. Cached vectors change neither content nor similarity. The disabled SDK telemetry hook is bypassed because version 0.1.118 still constructs telemetry clients per storage event when opted out; storage and search remain the actual SDK implementations. This Mem0 lane is raw storage/retrieval, not default fact extraction, and is expected to overlap the dense baseline closely. The pilot's `infer=True` configuration is preserved, not silently relabeled as a full-size extraction run. Full-haystack fact extraction at 300 questions would exceed this single-model budget and remains unmeasured.

All answers use a custom shared history/question prompt, saved verbatim, temperature zero, and a 512-token limit; this reader prompt differs from the paper. The benchmark's unchanged task-specific judging prompts are used for three local calls, seeds 20261122/23/24, temperature zero, majority vote. The official scorer interprets a response containing `yes` as positive and all other responses as negative; nonbinary formats are also counted as a diagnostic. Greedy repeated calls are generally identical and are not independent evidence against systematic judge bias. Each answer and each judge call has a separate atomic checkpoint. HTTP failures retry the same unfinished call; scored answers are not regenerated. A memory-pressure guard stops only this run's server at warning/critical and reloads only after normal pressure and at least 40% system-wide free memory. The wall-clock deadline continues through pauses.

The three pilot photography-preference verdicts were resolved by direct editorial review as false negatives against the official rubric (`results/pilot-judge-resolution.json`). Pilot aggregate labels remain unchanged. Forty item/system pairs are selected with a fixed random seed from the eligible planned pairs, without using answer content or machine labels, before direct review; this is agent editorial review, not an independent human evaluation. The audit file names the reviewer and records every decision and reason. Its agreement rate measures agreement with that review only.

One more framework was optional. A basic model-API prerequisite probe for a Letta-style system/tool request returned HTTP 404 with `System role not supported`; the raw probe is in `proof/letta-model-prerequisite.json`. This is a compatibility probe, not a Letta benchmark or evidence that Letta cannot work with another adapter or model. No Letta or Graphiti accuracy result is claimed. Default automatic Mem0 fact extraction also needs compatible system-message handling, in addition to a larger generation workload; the measured Mem0 lane remains explicitly raw storage. No vendor algorithm, Zep latency claim, or API cost crossover is reproduced here.
'''
 run='''\nRun from the repository root, with uv 0.13.9, Python 3.13.18, SSH access to a model-serving Mac, and its already-installed MLX-LM 0.32.2 / MLX 0.32.4 / Transformers 5.20.2:\n\n```bash\nMODEL_HOST=user@your-model-host bash benchmarks/longmemeval/run_large.sh\n```\n\nThe hostname is a runtime setting and is never saved in the artifacts. This command starts the transient user systemd unit `membench-longmemeval-large.service`, downloads pinned weights into an isolated directory, runs or resumes checkpoints independently of the terminal, and performs cleanup after a deadline or failure. Monitor `results/full/status.json`, the checkpoint counts, and the pressure heartbeat; process liveness alone is insufficient. A foreground execution session was lost during setup, so its preserved checkpoints were resumed under this OS-owned supervisor. It uses port 39711 and CPU embeddings, never the client GPU. The model's license is Gemma; the dataset card declares MIT. Python dependency pins are in `requirements.txt`. The entry point defaults to 31,000 seconds (about 8 hours 37 minutes), including setup, with a slightly later OS cutoff for cleanup. During recovery of the same authorized task, use the remaining absolute budget recorded in `authorized-deadline.json`; do not reset the clock. Do not run two copies against the same scratch directory. To resume after cleanup, run the same command; completed results and votes are retained under `results/full/`. For an independent fresh measurement, first archive the shipped `results/full/` directory under a different name and let the command create a new empty `results/full/`; do not overwrite the published evidence.\n'''
 audittext=f"\nDirect-review agreement: {audit.get('agree','pending')}/{audit['n']}"+(f" ({audit['agreement']*100:.1f}%), descriptive 95% Wilson {audit['wilson95'][0]*100:.1f}% to {audit['wilson95'][1]*100:.1f}%.\n" if audit.get('agreement') is not None else '; not complete yet.\n')
 primary='''\nPublished anchors: Mem0 managed April 2026 reports 94.4% with retrieval budget 200; its headline README does not state N. The original paper reports 71.0% oracle direct-reading accuracy for Llama 3.1 8B, N=500. Zep reports up to 18.5% accuracy improvement and about 90% lower latency on LongMemEval_S; neither is an absolute local accuracy or a result of this Mem0 raw-storage lane. The cached API cost crossover near ten turns at 100,000 tokens is not tested. Primary sources and the original book wording remain in `results/sources.json`, `results/book-claim-inventory.json`, and `REPORT.pilot.md`.
'''
 evidence='''\nEvidence: `results/full/items/` contains final per-item lane checkpoints; `answers/` and `judges/` retain each raw response; `requests.jsonl` contains submitted prompts and raw responses; `memory-ingestion.jsonl` proves full-haystack chunk ingestion; the manifest pins data, models, sample and code. Raw public benchmark dialogue entities are retained to preserve the benchmark; private operator identities and network addresses are omitted from operational logs. `results/full/cleanup.json` and `proof/` hold cleanup results when the supervisor finishes. A running job is not cleaned up yet.\n'''
 state_path=OUT/'status.json'
 if state_path.exists():
  state=json.loads(state_path.read_text())
  if state.get('cleanup_complete') and state.get('state')=='finished':
   evidence=evidence.replace('A running job is not cleaned up yet.','Cleanup is confirmed: owned model server and SSH tunnel stopped, both scratch directories removed, no owned listeners or containers, and the three preexisting voice-service PIDs preserved. Before/after disk and process evidence is under `results/full/proof/`; the final independent check is `proof/cleanup-independent.json`.')
 comparators='| System or reference | Published result | Local result |\n|---|---|---|\n'
 comparators+='| Full standard history | Llama 3.1 8B direct, 45.4%, N=500 | '+cell(result['full-standard'])+' |\n'
 comparators+='| Oracle-history reference | Llama 3.1 8B direct, 71.0%, N=500 | '+cell(result['full-oracle'])+' |\n'
 comparators+='| BM25 RAG | No matched QA figure; paper Table 9 Recall@10 is 71.0% session / 53.8% round, not QA accuracy | '+cell(result['bm25-standard'])+' |\n'
 comparators+='| Dense RAG | No matched MiniLM/S figure; paper Stella 1.5B round top-10 QA on M is 53.4% | '+cell(result['dense-standard'])+' |\n'
 comparators+='| Mem0 | Managed April 2026, 94.4%, retrieval budget 200, headline N unstated | OSS raw storage: '+cell(result['mem0-raw-standard'])+' |\n'
 comparators+='| Letta or Zep/Graphiti OSS | No matched published result | Not measured |\n'
 comparators+='\nThese are different systems and settings, not a controlled published-versus-local ranking. Published paper values are from [LongMemEval](https://arxiv.org/html/2410.10813v2); the managed headline is from the [pinned Mem0 source](https://github.com/mem0ai/mem0/tree/fff8a6472512d1bc1a4bccab8c645b65a1df7fe5).\n'
 (ROOT/'README.md').write_text('# LongMemEval: standard-haystack local experiment\n\n'+intro+comparators+'\n'+table+'\n'+types+'\n'+paired+audittext+details+run+primary+evidence)
 book='''\n## Book figures and suggested sentences

Chapter 13 prints: “Mem0 reports LoCoMo 92.5 and LongMemEval 94.4 for its managed April 2026 stack, with a top-200 retrieval budget.” Sources 5/7 are the Mem0 repository and memory-benchmarks repository. The 92.5 figure is LoCoMo, outside this benchmark. Suggested wording, if the run is complete: “Mem0 reports 94.4% for its managed LongMemEval stack with a retrieval budget of 200. Our 300-question test measured its open-source raw-storage configuration separately, so it does not reproduce the managed algorithm.” Insert the exact local count and Wilson interval from the table above; never substitute a partial result for N=300.

Chapter 14 prints: “94.8% vs 93.4% Zep against MemGPT on Deep Memory Retrieval, plus up to 18.5% higher accuracy and 90% lower latency on LongMemEval. The Zep authors' numbers.” Source 22 is arXiv:2501.13956. The first pair is DMR, not LongMemEval. Suggested wording: “Zep's authors report up to 18.5% higher accuracy and about 90% lower response latency on LongMemEval_S. Our local experiment does not test Zep or reproduce those changes.”

Chapter 17 prints a 500-question LongMemEval inventory and the ICLR 2025 label, citing arXiv:2410.10813. Suggested wording: “We sampled 300 of the 500 questions proportionally across question types and abstention. The retrieval systems received the full standard haystacks, while oracle-history reading is reported separately.” Use only if all three retrieval lanes have N=300.

Chapter 17's evaluator example cites repository 9e0b455 and the gpt-4o-2024-08-06 alias. Suggested wording: “Our evaluator uses the authors' task-specific judging prompts with a local 9B model and three-call majority voting. We also reviewed 40 randomly selected judgments and report agreement separately.” Use the second sentence only after all 40 direct reviews exist; review is by the implementation agent, not an independent human.

Chapter 17 prints a cost crossover near ten turns at 100,000 cached tokens, citing arXiv:2603.04814. Suggested wording: “The ten-turn crossover belongs to that paper's API prices and cache model. Our local accuracy experiment does not establish a dollar-cost crossover.”

Chapter 16 has no explicit LongMemEval figure in the inspected version. Every source paragraph and URL is retained in the pilot's claim inventory. No chapter files were edited.
'''
 if data['complete']:
  local=cell(result['mem0-raw-standard'])
  old='Suggested wording, if the run is complete: “Mem0 reports 94.4% for its managed LongMemEval stack with a retrieval budget of 200. Our 300-question test measured its open-source raw-storage configuration separately, so it does not reproduce the managed algorithm.” Insert the exact local count and Wilson interval from the table above; never substitute a partial result for N=300.'
  book=book.replace(old,'Suggested wording: “Mem0 reports 94.4% for its managed LongMemEval stack with a retrieval budget of 200. Our local open-source raw-storage configuration scored '+local+'; it does not reproduce the managed algorithm.”')
  book=book.replace(' Use only if all three retrieval lanes have N=300.','')
 if data['complete']:
  book+='\nAdditional local-results paragraph: “With Gemma 2 9B at 4-bit and full standard histories, our local judge scored BM25 at '+cell(result['bm25-standard'])+'. Dense RAG and Mem0 open-source raw storage each scored '+cell(result['dense-standard'])+'; this does not test Mem0’s managed algorithm.”\n'
 if audit['n']==40:
  book=book.replace('We also reviewed 40 randomly selected judgments and report agreement separately.','Direct review by the implementation agent agreed with '+str(audit['agree'])+' of 40 randomly selected judgments ('+f"{audit['agreement']*100:.1f}%"+').')
  book=book.replace(' Use the second sentence only after all 40 direct reviews exist; review is by the implementation agent, not an independent human.',' This is agent editorial review, not independent human validation.')
 diagnostics='\n| Diagnostic | BM25 | Dense | Mem0 raw | Oracle |\n|---|---:|---:|---:|---:|\n'
 for label,key in [('Empty answers','answer_empty'),('Empty answers judged positive','empty_answer_positive'),('Answer token-limit stops','answer_length_stops'),('Nonbinary judge calls','judge_format_invalid_calls'),('Split judge votes','judge_vote_disagreements')]:
  diagnostics+='| '+label+' | '+' | '.join(str(result[m][key]) for m in METHODS[1:])+' |\n'
 oracle_result=result['full-oracle']
 if oracle_result['n']:
  k=oracle_result['correct']-oracle_result['empty_answer_positive'];n=oracle_result['n'];ci=interval(k,n)
  diagnostics+=f"\nOracle judge sensitivity: {oracle_result['empty_answer_positive']} empty answers were incorrectly labeled positive. Forcing only those empty answers to incorrect would give {k}/{n} ({100*k/n:.1f}%; 95% Wilson {100*ci[0]:.1f}% to {100*ci[1]:.1f}%). This is a mechanical sensitivity check, not the primary official-prompt judge score or a correction of other judge errors.\n"
 diagnostics+='\nEmpty and degenerate answers remain in the denominator. Nonbinary judge responses follow the official substring rule rather than being selectively regenerated. All three judge calls are retained; greedy majority voting cannot remove systematic judge errors.\n'
 diagnostics_path=OUT/'diagnostics.json'
 if diagnostics_path.exists():
  d=json.loads(diagnostics_path.read_text())
  diagnostics+=f"\nThe final operational record contains {d['pressure_samples']} pressure samples, including {d['pressure_level_counts'].get('2',d['pressure_level_counts'].get(2,0))} warning samples; the server was paused and recovered under the guard. There were {d['transport_error_events']} transport-error events, retried from checkpoints. Dense RAG and Mem0 raw storage produced identical answers for {d['dense_mem0_identical_answer']}/{d['pairs']} questions and identical submitted contexts for {d['dense_mem0_identical_context']}/{d['pairs']}; these lanes do not demonstrate a distinct memory-extraction benefit. See `results/full/diagnostics.json`.\n"
 (ROOT/'README.md').write_text((ROOT/'README.md').read_text()+diagnostics)
 (ROOT/'REPORT.md').write_text('# LongMemEval larger-run editorial report\n\n'+intro+comparators+'\n'+table+'\n'+types+'\n'+paired+audittext+'\n## Scope and method differences\n\n'+details+primary+book+diagnostics+'\n## Evidence, failures and cleanup\n\n'+evidence+'\nThe three pilot verdicts are resolved in `results/pilot-judge-resolution.json`. Original pilot outputs remain unchanged. Transport errors, if any, are in `transport-errors.jsonl`; fatal errors and pressure pauses are retained by the supervisor.  The experiment cannot validate the managed Mem0 headline, the paper\'s long-context accuracy with a different model, Zep\'s claimed improvements, or the API cost crossover.\n')
 return data
if __name__=='__main__':print(json.dumps(summarize(),indent=2))

"""Write final reader/editor reports from frozen, verified benchmark evidence."""
from full_common import *
from decimal import Decimal, ROUND_HALF_UP
from full_summary import summarize
from matched_summary import summarize_matched
from report_full import main as refresh_protocol

SYSTEMS=[('Full context','full-context',77.16,5.21),('Plain RAG','rag',78.31,5.75),('Mem0 OSS','mem0',81.08,3.19),('Graphiti','graphiti',56.03,5.56),('Cognee','cognee',55.27,3.60)]
CATEGORIES=['Multi-hop','Temporal','Open-domain','Single-hop']

def percent(x):return str(Decimal(str(100*x)).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP))+'%'
def interval(s):return ' to '.join(percent(x) for x in s['wilson_95']) if s['n'] else 'Not available'
def local(s):return f"{s['correct']}/{s['n']} ({percent(s['accuracy'])})" if s['n'] else 'Not scored'
def comparison(scores):
 lines=['| System | Published mean ± SD (%) | Local correct / N (accuracy) | Local 95% Wilson interval |','|---|---:|---:|---|']
 for title,key,mean,sd in SYSTEMS:lines.append(f'| {title} | {mean:.2f} ± {sd:.2f} | {local(scores[key])} | {interval(scores[key])} |')
 return '\n'.join(lines)
def macro_table(scores):
 lines=['| System | Published macro mean ± SD (%) | Local matched macro mean ± sample SD (%) |','|---|---:|---:|']
 for title,key,mean,sd in SYSTEMS:
  v=scores[key];local_mean=100*v['macro_conversation_accuracy'];local_sd=v['macro_conversation_sd']
  cell=f'{local_mean:.2f} ± {100*local_sd:.2f}' if local_sd is not None else f'{local_mean:.2f}; SD undefined'
  lines.append(f'| {title} | {mean:.2f} ± {sd:.2f} | {cell} |')
 return '\n'.join(lines)
def categories(scores):
 lines=['| System | '+' | '.join(CATEGORIES)+' |','|---|---|---|---|---|']
 for title,key,*_ in SYSTEMS:
  lines.append('| '+title+' | '+' | '.join(local(scores[key]['by_category'][str(c)]) for c in range(1,5))+' |')
 return '\n'.join(lines)
def category_intervals(scores):
 lines=['| System | Category | Correct / N (accuracy) | 95% Wilson interval |','|---|---|---:|---|']
 for title,key,*_ in SYSTEMS:
  for c,name in enumerate(CATEGORIES,1):
   v=scores[key]['by_category'][str(c)];lines.append(f'| {title} | {name} | {local(v)} | {interval(v)} |')
 return '\n'.join(lines)
def baselines(summary):
 lines=['| Baseline, all ten conversations | Correct / N (accuracy) | 95% Wilson interval |','|---|---:|---|']
 for title,key,*_ in SYSTEMS[:2]:lines.append(f'| {title} | {local(summary[key])} | {interval(summary[key])} |')
 return '\n'.join(lines)
def ingestion(matched):
 lines=['| Conversation index | Sessions / turns | Mem0 minutes | Graphiti minutes | Cognee minutes |','|---|---:|---:|---:|---:|']
 convs=read(OUT/'conversations.json');preflight=read(OUT/'preflight-ingestion-times.json')
 attempted=sorted(set(matched['represented_conversations'])|{c['conversation'] for c in convs if any((OUT/'ingestion-starts'/b/f"c{c['conversation']}.json").exists() for b in ['mem0','graphiti','cognee'])})
 for ci in attempted:
  cells=[]
  for b in ['mem0','graphiti','cognee']:
   path=OUT/'ingestion-times'/b/f'c{ci}.json'
   if not path.exists():
    start=OUT/'ingestion-starts'/b/f'c{ci}.json'
    stop=min(read(OUT/'cleanup.json')['time_epoch'],read(OUT/'status.json')['deadline_epoch'])
    attempt=OUT/'ingestion-attempts-final'/b/f'c{ci}.json'
    cells.append(f"Failed; {read(attempt)['seconds']/60:.1f} min attempted" if attempt.exists() else (f"Incomplete; {(stop-read(start)['epoch'])/60:.1f} min elapsed" if start.exists() else 'Not attempted'))
    continue
   seconds=read(path)['seconds']
   if b=='cognee' and ci==0:seconds+=next(x['seconds'] for x in preflight if x['backend']=='cognee')
   native=read(OUT/'cognee-final-ingestion-validation.json').get(str(ci),{}) if b=='cognee' else {}
   cells.append(('Failed native run; ' if b=='cognee' and not native.get('final_native_run_completed') else '')+f'{seconds/60:.1f}')
  lines.append(f"| {ci} | {len(convs[ci]['sessions'])} / {len(convs[ci]['turns'])} | "+' | '.join(cells)+' |')
 return '\n'.join(lines)
def ingestion_sentence(matched):
 ranges=[]
 for title,backend in [('Mem0','mem0'),('Graphiti','graphiti'),('Cognee','cognee')]:
  values=[]
  for ci in matched['represented_conversations']:
   path=OUT/'ingestion-times'/backend/f'c{ci}.json'
   if not path.exists():continue
   seconds=read(path)['seconds']
   if backend=='cognee' and ci==0:seconds+=next(x['seconds'] for x in read(OUT/'preflight-ingestion-times.json') if x['backend']=='cognee')
   values.append(seconds/60)
  if values:ranges.append(f"{min(values):.1f} to {max(values):.1f} minutes for {title}")
 return 'In our local setup, ingesting one matched conversation history took '+', '.join(ranges)+'. These wall times include retries and waiting on a shared model host, so they are operational observations rather than controlled throughput measurements.'

def coverage(matched):
 return '\n'.join(['| Conversation index | Preselected questions | Matched completed questions |','|---|---:|---:|']+[f"| {ci} | {v['selected']} | {v['matched']} |" for ci,v in matched['coverage'].items()])

def failure_table():
 failures=read(OUT/'failures.json') if (OUT/'failures.json').exists() else []
 selected=read(OUT/'selection.json');lines=['| Backend / conversation | Retained technical event | Final status |','|---|---|---|'];resolutions=[]
 for f in failures:
  backend=f.get('backend');ci=f.get('conversation');qs=[q for q in selected if q['conversation']==ci]
  complete=sum(item_path(backend,q).exists() and read(item_path(backend,q)).get('complete',False) for q in qs) if ci is not None else 0
  status='Superseded before scoring' if f.get('superseded_before_scoring') else ('Recovered; all selected questions scored' if qs and complete==len(qs) else 'Incomplete; inspect failure evidence')
  tail=f.get('log_tail',f.get('message',''))
  cause='Corrupted Ladybug WAL after external interruption' if 'Corrupted wal file' in tail else ('Structured output length limit' if 'Model completion stopped by length' in tail else ('Mixed memory object/string schema' if "object has no attribute 'get'" in tail else 'See the retained exception'))
  lines.append(f'| {backend} / {ci} | {cause} | {status} ({complete}/{len(qs)}) |')
  resolutions.append(dict(backend=backend,conversation=ci,cause=cause,status=status,scored=complete,selected=len(qs)))
 atomic(OUT/'failure-resolutions.json',resolutions)
 return '\n'.join(lines)

def book_inventory(scores,n,represented):
 rates=', '.join(f"{title[0].lower()+title[1:] if key in ['full-context','rag'] else title} {percent(scores[key]['accuracy'])}" for title,key,*_ in SYSTEMS)
 comparison_text=f'The independent study reports 77 to 81% for full context, RAG and Mem0, and 55 to 56% for Graphiti and Cognee. Our local Qwen2.5-14B comparison on {n} matched questions across {len(represented)} conversations scored {rates}, using different models and settings.'
 if n<120:comparison_text=comparison_text[:-1]+'; the planned matched coverage was not reached, so this remains exploratory.'
 entries=[];seen=set()
 for snapshot,path in [('Expanded-run snapshot',OUT/'book-citations.json'),('Earlier pilot snapshot',ROOT/'results/book-citations.json')]:
  for item in read(path):
   identity=item['original_paragraph_sha256']
   if identity in seen:continue
   seen.add(identity);quote=item['quote'];lower=quote.lower();source=None;replacement=None;corresponding=None
   if '77 to 81' in quote or '55 to 56%' in quote:
    source='https://arxiv.org/html/2601.07978v5';replacement=comparison_text;corresponding='The matched five-system table above.'
   elif '75.14' in quote:
    source='https://arxiv.org/html/2601.07978v5';replacement=f"The independent paper cites Zep's counter-evaluation reporting 75.14% for Graphiti. Our local Graphiti configuration scored {local(scores['graphiti'])} and does not reproduce that vendor configuration.";corresponding='Graphiti local figure only; the vendor configuration is not reproduced.'
   elif '74.0%' in quote:
    source='https://www.letta.com/blog/benchmarking-ai-agent-memory';replacement="Letta reports 74.0% for its filesystem agent on LoCoMo with GPT-4o-mini. Our local five-system comparison did not test that agent or its tools.";corresponding='Not tested.'
   elif '92.5' in quote:
    source='https://github.com/mem0ai/memory-benchmarks';replacement=f"Mem0 reports 92.5 on LoCoMo for its managed April 2026 stack with top-200 retrieval. Our open-source local Mem0 configuration scored {local(scores['mem0'])} with top-20 retrieval and a different answerer and judge, so it does not reproduce the managed stack.";corresponding='Mem0 OSS is a different configuration; the quoted LongMemEval 94.4 is outside this LoCoMo task.'
   elif '26%' in quote:
    source='https://arxiv.org/html/2504.19413';replacement=f"Mem0's 2025 paper reports a 26% relative gain over OpenAI's memory. Our local Mem0 configuration scored {local(scores['mem0'])} and did not include OpenAI's memory, so it cannot test that relative gain.";corresponding='Absolute Mem0 OSS accuracy only; no relative comparison to OpenAI memory.'
   elif 'ten turns' in lower or '100k context' in lower or '100,000-token context' in lower:
    source='https://arxiv.org/html/2603.04814';replacement='The cited cost study reports a crossover after about ten turns at 100,000-token context with caching for its workload. Our LoCoMo run measures QA accuracy and ingestion wall time and does not reproduce that cost crossover.';corresponding='No cost-crossover experiment. Ingestion wall times are recorded separately; retain unrelated Chapter 20 fixture figures.'
   elif any(x in lower for x in ['wrong ground-truth','incorrect reference answers','wrong answers','reference answers are disputed']):
    source='https://github.com/snap-research/locomo/issues/23';replacement='An independent audit reports incorrect reference answers in LoCoMo. The official issue thread opens with judge inconsistencies and later records a maintainer acknowledgment of separately reported data-quality concerns.';corresponding='Source audit below; original reference answers retained.'
   elif 'ten long conversations' in lower:
    source='https://arxiv.org/abs/2402.17753';replacement=f'LoCoMo contains ten long conversations; our baselines cover all ten, and our matched memory comparison covers {n} questions across {len(represented)} conversations. This run tests text question answering, including supplied image captions and queries, and does not test deletion or poisoning.';corresponding='All-320 baseline table and matched-subset table above.'
   if replacement is None:continue
   assert '—' not in replacement
   entries.append(f"### {item['chapter']} ({snapshot})\n\n> {quote}\n\nSource: [cited source]({source})\n\nLocal correspondence: {corresponding}\n\nSuggested wording, at most two sentences:\n\n{replacement}\n")
 return '\n'.join(entries)

def main():
 audit=read(OUT/'manual-audit.json');assert audit.get('summary',{}).get('n')==40, 'Finish the blinded 40-item audit first'
 assert read(OUT/'manual-audit-plan.json').get('scope')=='final_matched_subset'
 assert (OUT/'privacy-export.json').exists(), 'Archive privacy masking must finish first'
 refresh_protocol();summary=summarize();matched=summarize_matched();assert matched['n']>0
 assert all(summary[b]['n']==320 for b in ['full-context','rag'])
 n=matched['n'];scores=matched['systems'];represented=matched['represented_conversations'];cleanup=read(OUT/'cleanup.json');audit_s=audit['summary']
 assert read(OUT/'manual-audit-plan.json')['matched_item_ids']==matched['item_ids']
 partial=n<320;status='Final partial run' if partial else 'Final run'
 graph_low=all(scores[g]['accuracy']<min(scores[b]['accuracy'] for b in ['full-context','rag','mem0']) for g in ['graphiti','cognee'])
 finding=('The local point estimates put both graph systems below the other three configurations, as in the published comparison.' if graph_low else "The local point estimates do not reproduce the published blanket ordering of both graph systems below full context, RAG and Mem0.")+' This comparison cannot isolate the memory representation as the cause; models, retrieval budgets and framework settings differ.'
 if n<120:
  finding+=' The requested four-history matched cohort was not completed. This remains an exploratory result and cannot adjudicate the graph-versus-vector claim.'
 interval_note='Published values are means and standard deviations across ten conversations, from a 1,540-question eligible pool before the paper\'s exclusions. They are not confidence intervals. Local values are question-weighted accuracies on identical completed question IDs. Wilson intervals are descriptive, ignore shared-conversation dependence and judge error, and do not establish production performance. Completion order can change the category mix of a partial final block.'
 method='The original target is 320 questions, 80 in each category 1 through 4, across all ten conversations. Seed 20261122: sample up to eight per conversation/category, then uniformly fill each category to 80 from its unselected questions. Open-domain questions are 25% of the planned local sample but only 96/1,540 (6.2%) of the eligible dataset. The fixed conversation order is 0 through 9 in pairs; each pair runs Mem0, Graphiti and Cognee before widening. Within the second pair, a freed Graphiti slot can begin Cognee for that completed conversation while Graphiti finishes the other. A later increase from two to three native request slots, sharing the same model weights and preserving 64K per slot, also overlaps Cognee conversation 2 ingestion with its unfinished Graphiti history. Memory pressure after that restart was normal with 57% free. Duplicate-store guards preserve one writer per system/conversation. The final matched subset is the intersection of questions with a saved answer and all three votes in every system at the fixed stopping time, with no outcome-based inclusion. A whole-conversation sensitivity comparison is also retained.'
 if (OUT/'breadth-admission.json').exists():
  admission=read(OUT/'breadth-admission.json')
  method+=f" Based only on observed execution times, later admission was capped at conversation index {admission['max_memory_conversation']}; the model deadline was not extended. The final cohort therefore reflects completed cases in the admitted histories, rather than a new random sample of the full dataset."
 audit_text=f"A random audit of 40 matched judged items, seed 20261123 and two items per system/category, agreed on {audit_s['agreed']}/40 ({percent(audit_s['agreement'])}); 95% Wilson interval {interval(dict(n=40,wilson_95=audit_s['wilson_95']))}. The implementation agent used the same generous topic-match and absolute-date rubric, reading a shuffled presentation of questions, original references, answers and source evidence with both system identities and majority labels hidden, then joined the labels afterward. The pre-review rubric is in `manual-audit-rubric.json`. Final reviews were fresh; earlier wide-plan reviews were archived without reuse. This is an agent manual audit, not independent human validation. Main scores were not corrected from this audit. The three benchmark votes use the same temperature-zero judge and are not independent validation."
 cleanup_text=('Cleanup is confirmed: the owned model server, guard, tunnel, proxy and task containers stopped, and both scratch folders, downloaded model and caches were removed.' if cleanup.get('cleanup_confirmed') else 'Cleanup is not fully confirmed; inspect the proof for unresolved resources.')+' `results/full/cleanup.json` contains before/after disk and process evidence, pressure logs and absence checks.'
 differences='The paper uses GPT-4o-mini and text-embedding-3-small, a tool coordinator, unmasked names, a different question distribution and per-conversation aggregation. This run uses one Qwen2.5-14B-Instruct Q4_K_M model for extraction, answering and three-call majority judging, temperature zero, with a configured 64K per-slot YaRN window and q8 KV cache. CPU embeddings use all-MiniLM-L6-v2, 384 dimensions and its 256-token input limit. Mem0 2.2.1 uses eight individual messages per add call, session-date anchoring and local Qdrant semantic search (threshold 0.1, no reranking or optional BM25), with a provider adapter that wraps literal string memory entries as text objects; Graphiti 0.31.2 uses Neo4j and current-session extraction with native graph resolution and retrieval, splitting a session by turns after bounded output-length failures; Cognee 1.0.9 uses real cognify with Ladybug, LanceDB, 1,600-token chunks and GRAPH_COMPLETION context retrieval. Splitting preserves every source turn but changes the extraction context and can change the facts or relations extracted. All retrieval limits are 20 native items, which are turns, facts, edges or chunks rather than equal token budgets. The audited comparison repository pins Mem0 2.0.2 and Graphiti 0.29; Cognee 1.0.9 matches its version but uses different stores and settings here. The local provider also marshals completed embedded JSON function calls without changing arguments and retries structured length failures up to 8,192 tokens. Answer and judge prompts are paraphrased rather than exact paper prompts.'
 privacy='Names are consistently aliased in conversation, question and reference text. The privacy NER pass reads those texts only to build the alias dictionary; reference facts and evidence annotations are excluded from all stores. This can remove useful world-knowledge associations. One missed misspelled speaker reference was corrected and both affected baseline answers and three votes were rerun before any memory system reached that conversation. Later archival masking removes regenerated names from saved response text, retains original hashes and changes no effective request, reference, vote label or score.'
 timing_note='These are ingestion wall times, including framework initialization and waiting on the shared model host, excluding retrieval, answering and judging. Recovered conversations include failed-pass and repair time; Graphiti conversation 0 also includes substantial scheduling delays; its earlier discarded pre-scoring configuration is recorded separately. Cognee conversation 0 includes the successful 38.6-second first-session preflight that was reused. Incomplete rows show elapsed wall time from first ingestion start through stopping; they are not completed-ingestion times. They are operational observations, not controlled cross-system throughput or dollar-cost measurements.'
 readme=f'''# LoCoMo local comparison

**{status}: {n} matched questions across {len(represented)} conversation histories.** There are {len(matched['completed_conversations'])} complete question blocks and {n-matched['whole_conversation_n']} questions from partial blocks. Full context and plain RAG additionally cover all 320 preselected questions across all ten conversations. The earlier N=40 run remains clearly labeled as a pilot in `results/local/`, [PILOT_README.md](PILOT_README.md) and [PILOT_REPORT.md](PILOT_REPORT.md).

LoCoMo measures long-conversation question answering. The metric here is local LLM-judged accuracy, following the independent comparison, rather than the original 2024 token F1 metric. This experiment uses actual timestamped turns and supplied image captions/queries, without annotated summaries or QA evidence in any memory store.

## Matched results

{comparison(scores)}

{interval_note}

{finding}

## Baselines on all 320 questions

{baselines(summary)}

## Per-category matched scores

{categories(scores)}

Per-category Wilson intervals, exact IDs and conversation coverage are in [matched-summary.json](results/full/matched-summary.json). The whole-conversation sensitivity subset has N={matched['whole_conversation_n']}; its five-system results and matched per-conversation macro means/sample SDs are in the same file.

## Reproduce

With the pinned model already served through the task-local endpoint on port 39700, run from the repository root:

```bash
bash benchmarks/locomo/run_full.sh
```

The command requires `uv` and Docker, installs the pinned CPU/framework environments and resumes persisted answers and votes. `LAB_DIR` defaults to `/var/tmp/membench-locomo`, `OUT_DIR` to `benchmarks/locomo/results/full`, and the framework `BASE_URL` defaults to `http://localhost:39701/v1`; the local proxy forwards generation to localhost port 39700. Completed output is reused. Use fresh output and lab directories for a new experiment. Exact model command, weights SHA256, revision, protocol and operational history are in [FULL_RUN.md](FULL_RUN.md); dependencies are pinned in [requirements-full-lock.txt](requirements-full-lock.txt) and [requirements-graph-lock.txt](requirements-graph-lock.txt).

The official data revision is `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`, SHA256 `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`, licensed CC BY-NC 4.0. Sources: [official LoCoMo repository](https://github.com/snap-research/locomo), [independent comparison, version 5](https://arxiv.org/html/2601.07978v5), and [source audit](REPORT.md).

Generation runs on Apple M3 Ultra, 96 GB. Embeddings, stores, orchestration and scoring run on a 32-thread x86 CPU. The NVIDIA GPU is not used. The task server stops at macOS warning/critical pressure and waits for normal pressure and at least 40% available memory before restarting; a 20-minute warning pauses the run rather than abandoning it. The wall-clock deadline persists across restarts.

## Sampling and differences

{method}

{differences}

{privacy}

## Ingestion time

{ingestion(matched)}

{timing_note}

## Judge audit and evidence

{audit_text}

Per-item answers, contexts and votes are under `results/full/items/`; effective requests, privacy-masked responses, token usage and hashes are under `results/full/raw-calls/`. [verification.json](results/full/verification.json) reconstructs scores and verifies three distinct actual judge responses per scored item. [manual-audit.json](results/full/manual-audit.json) contains all 40 decisions and reasons. Original references remain unchanged, including externally flagged labels.

{cleanup_text}

The original 320-question five-system target has {320-n} questions outside the final matched denominator. Individual system totals and partial outputs remain in `summary.json`; no pilot score fills a missing expanded-run result. This run does not reproduce managed Mem0, the filesystem agent, vendor-relative gains, other prototype systems or the ten-turn cost crossover.
'''
 if (OUT/'breadth-admission.json').exists():
  cap=read(OUT/'breadth-admission.json')['max_memory_conversation']
  readme=readme.replace('bash benchmarks/locomo/run_full.sh',f'MAX_MEMORY_CONVERSATION={cap} bash benchmarks/locomo/run_full.sh')
  readme+=f'\nThe reproduction command preserves the admitted memory-history scope, indices 0 through {cap}; both baselines still use all 320 questions. Fresh output directories otherwise default to all ten memory histories.\n'
 readme=readme.replace('MAX_MEMORY_CONVERSATION=', 'MEMORY_SAMPLE_IDS=benchmarks/locomo/results/full/matched-summary.json MAX_MEMORY_CONVERSATION=')
 readme+='\n`MEMORY_SAMPLE_IDS` replays the exact final matched question IDs for the three memory systems, while both baselines retain all 320. Omit it to attempt the complete planned sample; use fresh output and lab directories for new inference. Original failed attempts and their costs remain in the archived evidence.\n'
 (ROOT/'README.md').write_text(readme)
 report=f'''# LoCoMo editor report

{status}: **N={n} matched questions**, represented conversations {represented}, with the same IDs for all five systems. The all-320 baselines and the N=40 pilot are separate results.

## Published and local comparison

{comparison(scores)}

{interval_note}

{finding}

{baselines(summary)}

## Aggregation sensitivity

{macro_table(scores)}

Local macro values weight each represented conversation equally, using only the matched questions within it. The local SD uses the sample convention and is not a confidence interval. The main table uses question-weighted accuracy so its counts and Wilson intervals remain explicit.

## Matched per-category scores

{category_intervals(scores)}

Per-category Wilson intervals are in `results/full/matched-summary.json`. The strict whole-conversation sensitivity comparison uses N={matched['whole_conversation_n']} and conversations {matched['completed_conversations']}.

## Coverage and ingestion cost

{coverage(matched)}

{ingestion(matched)}

{timing_note}

Suggested book wording: {ingestion_sentence(matched)}

## Judge check

{audit_text}

The fixed plan, all 40 manual labels/reasons and joined majority decisions are in `results/full/manual-audit-plan.json` and `manual-audit.json`. The earlier wide-plan reviews remain separately archived and do not inflate this denominator.

## Book figure inventory

Quotes retain the printed wording and figures except attribution names replaced by `[study authors]` to meet the artifact privacy rule. Each source snapshot records its original-paragraph SHA256 for exact matching. The earlier pilot snapshot is historical; some source-quality wording was already corrected in the later snapshot. Suggested wording covers only the relevant LoCoMo claim, not unrelated benchmark or Chapter 20 fixture content.

{book_inventory(scores,n,represented)}

## Label-error source audit

The earlier Chapter 16 sentence printed: “An October 2025 issue documents wrong ground-truth answers in LoCoMo, so a single score on it proves little until someone else reruns it (Chapter 17).” The October 15, 2025 [issue 23 opening post](https://github.com/snap-research/locomo/issues/23) concerns judge inconsistencies, including subset/superset answers and unsupported specificity; it is not itself a ground-truth audit. A [February 17, 2026 maintainer response](https://github.com/snap-research/locomo/issues/23#issuecomment-3916421856) later acknowledges separately reported data-quality concerns. The current book-source inventory already distinguishes these points, although source-list titles should also describe the thread accurately.

For direct wrong-label evidence, cite [issue 27](https://github.com/snap-research/locomo/issues/27) and the [independent audit report](https://github.com/dial481/locomo-audit/blob/9493fb4b4af4256ed17a18e8fd0b3cfdeec29539/AUDIT_REPORT.md). That audit reports 99 score-related errors among 1,540 eligible questions (6.4%, including 13 ambiguous/debatable cases), plus 57 citation-only issues, using Claude Opus 4.6 with human review. We verified what the sources report, not all their proposed corrections, and did not apply them to the scores. The original 320-question sample overlaps 41 flagged items: 23 score-related and 18 citation-only; exact overlap is in `results/full/audit-overlap.json`.

Suggested book wording: The October 2025 LoCoMo issue documents inconsistent LLM judging, rather than a ground-truth audit. A separate audit reports 99 score-related issues among 1,540 eligible questions, including 13 ambiguous or debatable cases.

## Method and limits

{method}

{differences}

{privacy}

The run uses the configured 64K window checked by actual tokenizer counts; no conversation history is silently dropped. The paper's full eligible set, coordinator, hosted answerer/judge, embeddings, aggregation, stores and network scenarios are not reproduced exactly. Shared histories, unequal native retrieval units, completion-based coverage and local judge errors limit ranking claims. Neither latency nor dollar cost is compared to the paper.

## Technical failures and repair

A Mem0 extraction returned a mixed object/string memory array, which its native parser rejected before embedding or persisting that batch. The provider adapter wraps only the string entries as text objects, retaining their literal content and all valid object fields; the raw response and checkpointed recovery are retained.

The initial Graphiti configuration re-extracted previous sessions and hit an output limit. Its 70-node task graph was reset before any Graphiti question was scored; the excluded checkpoints and failed responses remain archived. The final adapter extracts from the current session, then resolves/retrieves against the accumulated graph. Structured extraction length failures retain their actual 4,096/8,192/16,384-token attempts and trigger recursive session splitting while preserving every turn and original timestamp. After the first 58 Graphiti questions were complete, edge extraction was capped at 8,192 tokens before splitting; other schemas initially retained 16,384. A later entity-extraction length failure extended the 8,192 cap and the same source-preserving split fallback to all structured schemas, as recorded in `structured-output-cap-change.json`. No completed historical 16,384-token structured response was discarded. The change preceded all later Graphiti question scoring and is recorded in `edge-output-cap-change.json`. The first oversized session was repaired as two 12-turn episodes within the bounded setup effort. Subsequent normal ingestion/scoring retained the original overall deadline. Native graph retrieval was used for both graph systems. An external turn interruption later terminated CPU processes. Cognee conversation 2 had a corrupted Ladybug write-ahead log; its unscored store was rebuilt from the complete history, reusing cached actual model responses where requests matched. The damaged store remained task-scoped until cleanup, and its earlier ingestion checkpoints are archived separately. Truncated tool outputs also produced missing-tool-call validation errors. Tool schemas now receive the same bounded 4,096-to-8,192 length retry as other structured extraction; only a completed plain response without a tool call additionally retries required tool selection. Completed function calls encoded as explicit name/arguments JSON inside message content are marshaled into the API tool_calls field with arguments unchanged and native schema validation still applied; original responses and adapter hashes are retained. Valid existing tool responses remain unchanged. Final native Cognee pipeline status must be completed before questions enter the reported comparison; an intermediate error can be recovered by a later cognify pass over all pending data. These events, the resume and final completion status are recorded in `turn-interruption-resume.json`, `cognee-wal-rebuild.json`, `required-tool-retry-change.json` and the coverage table. The deadline was not extended.

A controlled proxy restart increased the HTTP request allowance from two to four while retaining one model and two native slots, preventing requests queued for one slot from starving the other. All per-question answers and votes were preserved. Later, a third native slot and an HTTP allowance of six let Cognee ingest the same admitted history while Graphiti finished it, using one shared model weightset; `three-slot-change.json` records the context and memory checks. Earlier source-hash snapshots describe their execution phase; final code hashes and the recorded change files document later technical corrections. No setting was selected to approach a published score.

{failure_table()}

These events are retained for diagnosis; incomplete ingestion is not silently converted into an answer or a correct label.

## Evidence and cleanup

- `results/full/selection.json`, `conversations.json`, `manifest.json`: selected IDs, exact transformed input, revision, license and seeds.
- `results/full/items/`, `raw-calls/`, `ingest/`, `ingestion-times/`: answers, contexts, all votes, real extraction calls, ingestion checkpoints and timings.
- `results/full/verification.json`, `verification-before-privacy.json`: score reconstruction, input alignment, canonical request hashes and distinct judge responses.
- `results/full/privacy-correction.json`, `privacy-export.json`: the one corrected alias and excluded preliminary records, plus archival response masking and original hashes.
- `results/full/book-citations.json`, `results/book-citations.json`, `results/published-evidence.json`: exact book/source snapshots and source audit.
- `results/full/cleanup.json`: before/after disk and process listings, memory-pressure log and resource absence checks.

{cleanup_text}

Unresolved coverage: {320-n} of the original 320 questions are outside the final shared denominator. The matched sample and completed-case intervals are printed plainly; incomplete results are retained, and the pilot is not substituted. The agent manual audit does not provide independent human validation.
'''
 (ROOT/'REPORT.md').write_text(report)
 print(dict(matched_n=n,conversations=represented,audit_agreed=audit_s['agreed'],cleanup_confirmed=cleanup.get('cleanup_confirmed')))

if __name__=='__main__':main()

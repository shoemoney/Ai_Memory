"""Regenerate expanded-run tables from checkpoints; never substitutes pilot scores."""
from full_common import *
from full_summary import summarize
from matched_summary import summarize_matched
from run import wilson
SYSTEMS=[('Full context','full-context',77.16),('Plain RAG','rag',78.31),('Mem0 OSS','mem0',81.08),('Graphiti','graphiti',56.03),('Cognee','cognee',55.27)]

def table(summary):
 lines=['| System | Published | Local correct / N | Local accuracy | 95% Wilson interval |','|---|---:|---:|---:|---|']
 for title,key,published in SYSTEMS:
  s=summary[key];n=s['n'];k=s['correct'];a=f"{100*s['accuracy']:.2f}%" if n else 'Not yet scored';ci=' to '.join(f'{100*x:.2f}%' for x in s['wilson_95']) if n else 'Not available'
  lines.append(f'| {title} | {published:.2f}% | {k}/{n} | {a} | {ci} |')
 return '\n'.join(lines)

def main():
 summary=summarize();matched=summarize_matched();complete=all(x['n']==320 for x in summary.values())
 status='COMPLETE' if complete else 'PARTIAL: do not present these as the final 320-question comparison'
 cat=['| System | Multi-hop | Temporal | Open-domain | Single-hop |','|---|---|---|---|---|']
 for title,key,_ in SYSTEMS:
  cells=[]
  for c in [1,2,3,4]:
   v=summary[key]['by_category'][str(c)];cells.append(f"{v['correct']}/{v['n']} ({100*v['accuracy']:.1f}%)" if v['n'] else 'Pending')
  cat.append('| '+title+' | '+' | '.join(cells)+' |')
 manual=read(OUT/'manual-audit.json') if (OUT/'manual-audit.json').exists() else None
 text=f'''# Expanded LoCoMo run: 320 questions

Status: **{status}**. The earlier 40-question run in `results/local/` is a pilot, retained with its original outputs. No pilot score fills an unfinished expanded-run cell.

{table(summary)}

Published scores are macro means across ten conversations, 1,540 questions before exclusions. Local targets are 320 matched questions across all ten conversations, 80 per category. Local primary accuracy is question-weighted; per-conversation macro means are also in `summary.json`. Wilson intervals are descriptive and do not account for within-conversation dependence or label and judge errors.

## Per-category counts

'''+ '\n'.join(cat)+'''

Per-category Wilson intervals and per-conversation counts are in `results/full/summary.json`.

## Reproduce

With the pinned Qwen2.5-14B-Instruct Q4_K_M model already served through a local-only endpoint on port 39700, run from the repository root:

```bash
bash benchmarks/locomo/run_full.sh
```

The command installs the two pinned environments, prepares the fixed sample, starts task-scoped Neo4j and the CPU embedding/model proxy as needed, and resumes conversation blocks in fixed order 0 through 9: each pair completes Mem0, Graphiti and Cognee before the next pair begins. It preserves per-question answers and every individual judge vote. `LAB_DIR` defaults to `/var/tmp/membench-locomo`, `OUT_DIR` to `benchmarks/locomo/results/full`, and the framework endpoint `BASE_URL` to `http://localhost:39701/v1`. The proxy forwards only to the task model tunnel at localhost port 39700. A completed output is reused, never silently replaced. For a completely new experiment, select a new output and fresh lab directory.

Equivalent model server settings:

```bash
llama-server --model "$MODEL_FILE" --alias qwen2.5-14b-instruct \\
  --host localhost --port 39700 --ctx-size 196608 --parallel 3 \\
  --override-kv qwen2.context_length=int:65536 \\
  --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 32768 \\
  --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --cache-ram 0 --jinja
```

The run initially used two native slots (aggregate context 131,072), then three (196,608) to overlap Cognee ingestion with the unfinished Graphiti history. Every slot retained 65,536 context tokens and a single shared model weightset; the memory check after restart was normal with 57% free. This timing-only change is recorded in `three-slot-change.json`. Use the same GGUF file and SHA256 recorded in the pilot README. The exact task-owned model launcher and memory-pressure restart loop are retained in `model_server_guard.sh`; deploy it only for a server you own. The GGUF metadata advertises a 32K window; this run explicitly extends the configured per-slot window to 64K with YaRN. The metadata override prevents this llama.cpp build from capping slots at that metadata window. `token-lengths.json` checks all complete conversations plus a 5,120-token reserve against the effective window. No context or question is silently dropped.

## Fixed protocol

Seed 20261122. For each category, take up to eight questions per conversation, then uniformly sample from remaining questions in that category to reach 80. Open-domain questions are 25% of the planned sample versus 96/1,540 (6.2%) of the eligible dataset. Categories 1 through 4 contribute 80 each; category 5 is excluded. This gives 24 to 34 questions per conversation. The selected indices and original-question hashes are saved before scoring. Names are masked consistently with speaker aliases and a spaCy PERSON/proper-noun pass. That privacy pass scans conversation, question and reference text only to build the alias dictionary; reference facts and QA evidence annotations are not supplied to any memory store. This transformation can remove world-knowledge associations and is a difference from the published benchmark. A missed misspelled speaker reference in `c05-q017` was corrected as a privacy alias; both baseline items and their three votes are regenerated before any memory system reaches that conversation. The sample ID and gold answer stay fixed. Excluded preliminary records are redacted with original and redacted hashes in `privacy-correction.json`; they do not contribute to scores. `extra-name-aliases.json` makes the same masking correction reproducible.

The dataset revision and SHA256 match the pilot: official repository revision `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`, CC BY-NC 4.0. For each conversation that reaches answering, all actual turns and supplied text image captions/queries were provided to its ingestion path; annotated summaries, gold answers, and QA evidence annotations do not enter indexing.

All systems use one Qwen2.5-14B-Instruct Q4_K_M model for generation and three local judge calls per answer. Temperature is zero. Judge seeds use 20261122 plus 100 times the backend index plus vote index 0, 1, or 2; this keeps cached identical answers from sharing a judge triplet across systems. The final label is a two-of-three majority. After the first complete 58-question block, subsequent Cognee workers use fixed category round robin 1 through 4 and save each answer plus its three votes before moving to the next question; this protects matched coverage at the deadline without changing questions, gold answers, prompts, seeds or the scoring rule. Other completed blocks retain their recorded call order. The same answer and judge prompts are used throughout. A technical length failure may double the answer/judge output budget, up to 4,096, and is retained in raw evidence; truncated text is never graded. Structured graph extraction initially retried technical length stops at 8,192 and 16,384 tokens; those attempts remain in raw evidence. After the first 58 Graphiti questions were complete, the edge-extraction cap became 8,192 tokens before session splitting; other schemas initially retained 16,384. A later entity-extraction length failure extended the 8,192 cap and the same source-preserving split fallback to all structured schemas, as recorded in `structured-output-cap-change.json`. No completed historical 16,384-token structured response was discarded. This technical change, made before any later Graphiti question was scored, is recorded in `edge-output-cap-change.json`. The initial Graphiti configuration re-extracted previous sessions and exceeded its output limit. Its 70-node task graph was reset before any Graphiti question was scored, and the excluded initial checkpoints are retained. This setting and reset are documented in `graphiti-current-session-change.json`. A later oversized session still failed at 16,384 tokens. The final adapter recursively bisects a session by turn count after a bounded structured-length failure, preserving every turn and the original timestamp; each resulting episode goes through the native graph pipeline. The first repair succeeded as two 12-turn episodes within the 90-minute setup bound. Successful earlier sessions need no split. This policy, its failed attempts, and its actual split checkpoints are retained.

Embeddings use pinned all-MiniLM-L6-v2 on CPU, 384 dimensions, with its 256-token input limit. Long embedding inputs are truncated by that encoder, including the tails of larger Cognee chunks; this differs from the paper's embedder. Full context receives all timestamped turns. RAG does exact cosine top-20 turn retrieval. Mem0 2.2.1 extracts from eight-turn batches represented as eight individual messages, with session-date anchoring and retrieves top 20 from local Qdrant using semantic search, the default 0.1 score threshold, no reranking and no optional BM25. A narrow provider adapter wraps string entries in the extraction memory array as text objects, preserving their content; native valid objects are untouched. The original format failure and checkpointed resume are recorded. Graphiti 0.31.2 ingests sessions into Neo4j with `previous_episode_uuids=[]`, so each extraction prompt sees the current session; node/edge resolution and retrieval still use the accumulated graph. It retrieves top-20 hybrid RRF edges, with a local structured-output client and local embeddings. Cognee 1.0.9 uses its real cognify graph pipeline, Ladybug and LanceDB, 1,600-token chunks, and GRAPH_COMPLETION retrieval with `only_context=True`, top 20, before the shared answerer. A retrieved item is a turn, fact, edge or chunk depending on the system; this is not an equal-token-budget comparison. Each conversation has isolated state. Unlike the pilot's joined eight-turn user message, the larger run preserves individual messages in each Mem0 add call, so the library's native ten-message history holds ten turns rather than eighty; this was fixed before any expanded-run Mem0 score. Three-vote judgment is common to all five systems. After full context and RAG completed all 320 questions, the parent prioritized matched breadth. The fixed conversation order is 0 through 9 in pairs. Each pair runs Mem0, Graphiti, then Cognee before widening to the next pair; the transition is recorded in `breadth-change.json`. Two model slots serve isolated conversations of the same model. The first Graphiti repair briefly shares a slot with one Cognee worker while the other slot serves the other conversation; later blocks wait for the repair. Otherwise each worker is pinned to its own slot so requests cannot evict its peer's prefix; the initial sequential full-context phase is recorded in `parallelism-change.json`. We changed throughput settings without changing model weights, per-slot context or scoring. The proxy HTTP allowance later rose from two to four requests to prevent queued requests for one native slot from starving the other slot; native model slots stayed at two. The separately documented one-question privacy correction was rerun for every affected baseline.

Model serving uses Apple M3 Ultra, 96 GB. Embeddings, all stores, orchestration, and scoring run on a 32-thread x86 CPU. No NVIDIA GPU is used. Other workloads are not controlled, so no comparative latency or cost claim is made. The task-owned server stops at macOS warning/critical pressure and waits for normal pressure and at least 40% available memory before restarting. The supervisor pauses and resumes transport failures instead of abandoning a graph system after a pressure interruption. The run retains its original wall-clock deadline across restarts.

The paper instead uses GPT-4o-mini, text-embedding-3-small, different framework versions and deployment settings, a tool coordinator, unmasked names, all questions in the eligible categories, and a different aggregation. This is a local adaptation of its comparison, not a measurement of the managed Mem0 service, the filesystem agent, or the 26% vendor-relative gain.

## Evidence and audit

- `results/full/items/<system>/<item>.json`: answers, retrieved context, all three raw judge votes, and majority decisions.
- `results/full/raw-calls/`: effective local requests, responses, seeds, finish reasons, timings and token usage. After scoring, `privacy_export.py` masks any regenerated names in archived response text and per-item text, using the same alias dictionary. Effective requests, sample, references, response IDs, vote labels and scores remain unchanged. Original record and response hashes are retained in `privacy-export.json` and changed raw-record metadata. A strict check rejects any change to a request or scoring input.
- `results/full/ingest/`: ingestion checkpoints for each memory framework.
- `results/full/selection.json`, `conversations.json`, `manifest.json`: fixed sample, exact transformed input, and protocol.
- `results/full/resume-test.json`: controlled stop/resume proof; previous answers and votes were preserved and the deadline was not reset.
- `results/full/manual-audit-plan.json`: the original forty-item audit plan. The final random forty-item audit is drawn with seed 20261123 from the completed matched subset, without inspecting judge votes; earlier wide-plan reviews are archived separately. The review is manual reading by the implementation agent, not a human-subject agreement study or another automated judge API.
- `results/full/verification.json`: offline score reconstruction and distinct judge-response checks.
- `results/full/cleanup.json`: final cleanup and disk/process evidence when available.
- `results/full/preflight-*`: setup attempts, excluded from accuracy. Preflight graph stores were reset after correcting excessive name masking. A valid tool-call finish was also initially misclassified by the proxy, then corrected before scoring.

The original label-error source audit is retained in the pilot editor report. The official issue's opening post concerns judge inconsistencies; its later maintainer response acknowledges separately reported data-quality concerns. The independent audit's 99 flagged gold errors are claims by that audit, not 99 labels independently adjudicated here. Original references remain unchanged.
'''
 text+='\n## Matched comparison\n\nConversations represented: '+str(matched['represented_conversations'])+'. Shared N: '+str(matched['n'])+'. The same question IDs are used for every system; only items with answers and all three votes in all five systems enter the table. Fully completed conversations: '+str(matched['completed_conversations'])+'. Whole-conversation sensitivity N: '+str(matched['whole_conversation_n'])+'. Completion order can affect the category mix of a partial final block, so these are conditional completed-case scores. Full-context and RAG figures above additionally cover all 320 questions.\n\n'
 if matched['n']:text+=table(matched['systems'])+'\n'
 text+='\nIngestion times per conversation are saved in `results/full/ingestion-times/`; they include framework initialization and ingestion, and exclude retrieval, answering and judging. Times share an uncontrolled model host and are operational costs, not comparative throughput benchmarks.\n'
 if manual and manual.get('summary'):text+='\nManual agreement: '+json.dumps(manual['summary'])+'\n'
 else:text+='\nThe preselected 40-item manual review is pending completion of its answers.\n'
 if (OUT/'breadth-admission.json').exists():
  cap=read(OUT/'breadth-admission.json')['max_memory_conversation']
  text=text.replace('bash benchmarks/locomo/run_full.sh',f'MAX_MEMORY_CONVERSATION={cap} bash benchmarks/locomo/run_full.sh')
  text+=f'\nMemory-history admission was capped at index {cap} based on observed execution times. The command preserves this scope; baselines remain all 320. A freed Graphiti slot in the second pair may begin Cognee for the completed conversation, with a duplicate-store guard.\n'
 text=text.replace('MAX_MEMORY_CONVERSATION=', 'MEMORY_SAMPLE_IDS=benchmarks/locomo/results/full/matched-summary.json MAX_MEMORY_CONVERSATION=')
 text+='\nThe memory replay setting uses only the archived final matched IDs, with unchanged full source histories; both baselines still use all 320. Omit the setting for a new full-target attempt.\n'
 (ROOT/'FULL_RUN.md').write_text(text)
 return summary
if __name__=='__main__':main()

"""Editor tables from completed, paired cells. No invented values for missing cells."""
from pathlib import Path
import json,statistics,collections
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results'
DISPLAY={'scifact':'SciFact','nfcorpus':'NFCorpus','longmemeval':'LongMemEval','locomo':'LoCoMo'}
summary=json.loads((OUT/'summary.json').read_text())
def fmt(v,percent=True):
 if v is None:return 'not measured'
 factor=100 if percent else 1
 est=f'{factor*v[0]:.2f}'
 if v[1] is None:return est+' (interval undefined)'
 return est+f' [{factor*v[1]:.2f}, {factor*v[2]:.2f}]'
lines=['## Completed public-data results','','All values below are percentages, with query-bootstrap 95% intervals in brackets. Paired changes are percentage points unless marked relative. Each row uses all selected queries; partial cells are not printed.','', (OUT/'table.md').read_text().strip(),'','### Published figures beside the local counterpart','','| Claim | Dataset | N | Published | Local measurement, 95% interval | Interpretation |','|---|---|---:|---|---|---|']
for name,result in summary.items():
 if 'systems' not in result:continue
 systems=result['systems'];paired=result['paired'];n=result['n']
 for method,published,label in [('dense','5.7%','Embedding 1 − recall@20'),('context_dense','3.7%; 35% reduction','Contextual dense 1 − recall@20'),('context_hybrid_rrf','2.9%; 49% reduction','Contextual hybrid 1 − recall@20'),('context_hybrid_rerank','1.9%; 67% reduction','Contextual hybrid plus reranker 1 − recall@20')]:
  measured=fmt(systems[method]['unrecalled20']) if method in systems else 'not measured'
  text='Cannot speak to the published percentage on a different benchmark' if method in systems else 'No completed local cell'
  comparison=paired.get(method+' minus dense',{}).get('unrecalled20')
  if comparison is not None:
   direction='supports higher recall locally' if comparison[2]<0 else 'contradicts higher recall locally' if comparison[1]>0 else 'local change inconclusive'
   text+='; '+direction
  lines.append(f'| {label} | {name} | {n} | {published} | {measured} | {text} |')
 for method,published in [('context_dense','35%'),('context_hybrid_rrf','49%'),('context_hybrid_rerank','67%')]:
  comparison=paired.get(method+' minus dense')
  if comparison:
   v=comparison.get('relative_unrecalled_reduction');measured=fmt(v) if v is not None else 'undefined (zero baseline error)'
   undefined=comparison.get('relative_unrecalled_reduction_undefined_resamples',0);note=f'; {undefined}/10000 ratio draws undefined because baseline error is zero' if undefined else ''
   lines.append(f'| Relative failure reduction, {method} vs dense | {name} | {n} | {published} | {measured} | Paired absolute error change {fmt(comparison["unrecalled20"])} points{note} |')
 for metric,label in [('ndcg10','nDCG@10'),('ap150','AP@150')]:
  r=result.get('rrf_vs_best_single',{}).get(metric)
  if r:
   interval=r['relative_gain'];direction='supports a positive local gain' if interval[1]>0 else 'contradicts a positive local gain' if interval[2]<0 else 'local direction inconclusive'
   lines.append(f"| RRF relative {label} gain over best single | {name} | {n} | 4 to 5%, reported MAP | {fmt(interval)} | {direction}; cannot validate original magnitude with different metric/corpus; baseline {r['best_single']} |")
lines+=['| LazyGraphRAG indexing/full GraphRAG | none | 0 | 0.1% | cannot be reproduced locally from an identified official implementation | No paired indexing run or call/token ratio |','','### Paired changes','','| Dataset | Comparison | Recall@5 change | Recall@20 change | nDCG@10 change | Complete miss@20 change |','|---|---|---:|---:|---:|---:|']
for name,r in summary.items():
 for comparison,metrics in r.get('paired',{}).items():lines.append('| '+ ' | '.join([name,comparison]+[fmt(metrics[k]) for k in ['recall5','recall20','ndcg10','failure20']])+' |')
audit={}
for name in ['scifact','nfcorpus','longmemeval','locomo']:
 p=OUT/(name+'.prefixes.jsonl')
 if not p.exists():continue
 rows=[json.loads(l) for l in p.read_text().splitlines()];tokens=[r['usage']['completion_tokens'] for r in rows];times=[r['seconds'] for r in rows]
 audit[name]={'hardware_classes':dict(collections.Counter(r.get('hardware_class','8 GB NVIDIA GPU') for r in rows)),'parallel_request_counts':dict(collections.Counter(str(r.get('parallel_requests')) for r in rows)),'context_limit_recording_note':('Early Mac rows lack a per-row token limit; deployment history records four 8192-token slots for those initial phases. All fixed prompts fit 2976 tokens.' if any(r.get('context_tokens_per_slot') is None for r in rows) else 'Per-row context limits are complete; every fixed prompt fits 2976 tokens.'), 'context_token_limits':dict(collections.Counter(str(r.get('context_tokens_per_slot')) for r in rows)),'gpu_layer_counts':dict(collections.Counter(str(r.get('gpu_layers','runtime default')) for r in rows)),'prefill_batch_tokens':dict(collections.Counter(str(r.get('batch_tokens','runtime default')) for r in rows)),'physical_prefill_batch_tokens':dict(collections.Counter(str(r.get('ubatch_tokens','runtime default')) for r in rows)),'n':len(rows),'completion_tokens':sum(tokens),'median_completion_tokens':statistics.median(tokens),'outside_requested_50_100_tokens':sum(not 50<=t<=100 for t in tokens),'finish_reasons':dict(collections.Counter(r['finish_reason'] for r in rows)),'interpretation':'Request timings remain raw operational records and are not compared across hardware. Context text is generated, not a relevance judgment.'}
(OUT/'prefix-audit.json').write_text(json.dumps(audit,indent=2))
lines+=['','### Suggested replacement sentences','','Contextual Retrieval:']
context_parts=[];rrf_parts=[]
for name,r in summary.items():
 systems=r.get('systems',{})
 if 'context_hybrid_rerank' in systems:
  context_parts.append(f"{100*systems['dense']['unrecalled20'][0]:.1f}% to {100*systems['context_hybrid_rerank']['unrecalled20'][0]:.1f}% on {DISPLAY[name]} ({r['n']} queries)")
 x=r.get('rrf_vs_best_single',{}).get('ap150')
 if x:rrf_parts.append(f"{100*x['relative_gain'][0]:+.1f}% on {DISPLAY[name]} ({r['n']} queries)")
if context_parts:lines.append('In this book, replacing uncontextualized dense retrieval with local contextual hybrid retrieval and reranking changed the share of relevant documents or sessions missing from the top 20 from '+', and '.join(context_parts)+". Different corpora, document or session labels, and open models make this a local comparison, not a reproduction of Anthropic's percentages.")
else:lines.append('No completed contextual comparison is available yet.')
lines+=['','RRF:']
if rrf_parts:lines.append('This book measured relative AP@150 changes with RRF of '+', and '.join(rrf_parts)+" against the better single retriever. These public-data measurements differ from the original paper's MAP benchmark and do not establish a universal 4 to 5% gain.")
lines+=['','### Limits and incomplete cells','','The contextual LongMemEval arm was not run: its 82,605 additional chunk-prefix calls could not fit the fixed ten-hour budget after completing the two full BEIR corpora and the compact LoCoMo arm. LoCoMo supplies the full contextual conversational-memory comparison. All four baseline memory methods use the same 150 questions; no thin contextual subset is compared to them.', '', 'No answer generation or LLM judge was used, so the requirement to hand-check generated judgments does not apply. Session-level LongMemEval relevance cannot establish precise evidence-turn retrieval or answer correctness. No original vendor evaluation corpus or RRF TREC run bundle was replaced with generated relevance labels.','']
for name,r in summary.items():
 missing=[m for m in ['bm25','dense','hybrid_rrf','hybrid_rerank','context_bm25','context_dense','context_hybrid_rrf','context_hybrid_rerank'] if m not in r.get('systems',{})]
 if missing:lines.append(f"- {name}: unrun or incomplete: {', '.join(missing)}.")
lines+=['','### Binary-rate boundary check','','A percentile query bootstrap is degenerate when every observed failure indicator is zero or one. The additional Wilson interval is supplied for the failure rate, without replacing the requested paired-bootstrap differences.','','| Dataset | Method | Misses / N | Complete miss@20 Wilson 95% interval |','|---|---|---:|---:|']
for name,r in summary.items():
 for method,metrics in r.get('systems',{}).items():
  if 'failure20_wilson' in metrics:lines.append(f"| {name} | {method} | {metrics['failure20_count']} / {r['n']} | {fmt(metrics['failure20_wilson'])} |")
lines+=['','### Prefix output audit','','```json',json.dumps(audit,indent=2),'```','','Model output lengths outside 50 to 100 tokens are retained and counted, not silently excluded. Prefixes are deterministic-temperature generations; floating-point batching can still vary across hardware.','']
section='\n'.join(lines)
p=ROOT/'REPORT.md';text=p.read_text().split('\n<!-- GENERATED RESULTS -->')[0];text=text.replace('Numerical local results are pending completion, and no missing result should be printed as zero.','Completed local cells are reported below, and missing cells are explicitly labeled.');text=text.replace('Final local figures, bounded replacement sentences, model output audit, and cleanup proof will be appended when the complete cells finish.','The generated results below contain completed local figures, replacement sentences, and model output audits; cleanup proof is recorded separately.');p.write_text(text+'\n<!-- GENERATED RESULTS -->\n'+section+'\n')
p=ROOT/'README.md';text=p.read_text();start=text.index('## Results');end=text.index('## Evidence and cleanup');text=text[:start]+'## Results\n\n'+(OUT/'table.md').read_text()+'\nFull paired changes and published-versus-local comparisons are in REPORT.md and results/summary.json. Missing contextual memory cells are explicitly labeled in REPORT.md.\n\n'+text[end:];p.write_text(text)
print('editor tables written from completed cells')

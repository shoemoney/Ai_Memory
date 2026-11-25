#!/usr/bin/env python3
"""Offline cost accounting. Python standard library only; no model/network calls."""
import argparse
import collections
import hashlib
import json
import math
import statistics as st
from pathlib import Path
import re
import random

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SYSTEMS = ('full-context', 'rag', 'mem0', 'graphiti', 'cognee')
CONVERSATIONS = (0, 1)  # Only histories with all selected questions completed in all five lanes.
SOURCES = {}


def read(path):
    data = path.read_bytes()
    SOURCES[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def mean(xs):
    return st.mean(xs) if xs else None


def quantile(xs, q):
    xs = sorted(xs)
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    return xs[lo] + (xs[math.ceil(pos)] - xs[lo]) * (pos - lo)


def first_cheaper(write, first_full, repeat_full, memory_query):
    """First positive integer Q satisfying write+Q*memory < first+(Q-1)*repeat."""
    if write + memory_query < first_full:
        return 1
    saving = repeat_full - memory_query
    if saving <= 0:
        return None
    q = max(2, math.floor((write - first_full + repeat_full) / saving) + 1)
    while write + q * memory_query >= first_full + (q - 1) * repeat_full:
        q += 1
    return q


def usage(record):
    u = record['response']['usage']
    return dict(input_tokens=u['prompt_tokens'], output_tokens=u['completion_tokens'],
                cached_tokens=(u.get('prompt_tokens_details') or {}).get('cached_tokens', 0),
                seconds=record['seconds'])


def classify(system):
    if 'Memory Extractor' in system:
        return 'mem0'
    if system.startswith('You are a top-tier'):
        return 'cognee'
    if any(system.startswith(s) for s in ('You are a fact deduplication', 'You are an entity',
           'You are an expert fact extractor', 'You are a helpful assistant that generates concise entity summaries',
           'You extract temporal bounds')):
        return 'graphiti'
    raise ValueError('Unrecognized extraction prompt; inspect source before accounting')


def collect_locomo(systems=SYSTEMS, conversations=CONVERSATIONS, matched_ids=None):
    base = ROOT / 'benchmarks/locomo/results/full'
    summary = read(base / 'matched-summary.json')
    selected = read(base / 'selection.json')
    ids = ({q['item_id'] for q in selected if q['conversation'] in conversations}
           if matched_ids is None else set(matched_ids))
    if matched_ids is None:
        assert ids <= set(summary['item_ids'])
    timers = {(b, c): read(base / 'ingestion-times' / b / f'c{c}.json')
              for b in systems[2:] for c in conversations}
    alias_owners = {}
    if matched_ids is not None:
        for conversation in read(base / 'conversations.json'):
            c = conversation['conversation']
            if c in conversations:
                for alias in set(re.findall(r'D\d+:\d+\s+(PersonC\d\d[AB]):', '\n'.join(conversation['turns']))):
                    assert alias not in alias_owners or alias_owners[alias] == c
                    alias_owners[alias] = c
    answers = collections.defaultdict(list)
    ingest = collections.defaultdict(list)
    ambiguous = []
    outside = collections.Counter()
    calls = []
    for path in sorted((base / 'raw-calls').glob('*.json')):
        raw = read(path)
        messages = raw['request']['messages']
        system = str(messages[0].get('content', ''))
        if system.startswith('Grade whether'):
            continue  # Evaluation cost is not a deployed query cost.
        if system.startswith('Answer questions'):
            answers[messages[-1]['content']].append((path, raw))
            continue
        backend = classify(system)
        if backend not in systems:
            continue
        text = json.dumps(messages)
        known = {int(x) for x in re.findall(r'PersonC(\d\d)[AB]', text)} & set(conversations)
        if matched_ids is not None:
            # Four-system attribution uses actual user payload, not framework examples.
            # Source speaker labels also map privacy-rewritten aliases to their history.
            payload = '\n'.join(str(m.get('content', '')) for m in messages if m['role'] != 'system')
            payload = re.sub(r'<EXAMPLE>.*?</EXAMPLE>', '', payload, flags=re.S | re.I)
            current = re.search(r'<CURRENT_MESSAGE>(.*?)</CURRENT_MESSAGE>', payload, flags=re.S)
            if current:
                payload = current[1]
            aliases = re.findall(r'D\d+:\d+\s+(PersonC\d\d[AB]):', payload)
            if not aliases:
                aliases = re.findall(r'PersonC\d\d[AB]', payload)
            known = {alias_owners[a] for a in aliases if a in alias_owners}
        # Examples contain other conversation aliases. Only cohort aliases plus recorded
        # ingestion intervals establish ownership. Never infer ownership from time alone
        # when two workers of the same backend are active.
        epoch = raw['response']['created']
        active = [c for c in conversations if timers[backend, c]['start_epoch'] - 2 <= epoch <= timers[backend, c]['end_epoch'] + 2]
        owners = sorted(known & set(active)) if known else active
        row = dict(source=str(path.relative_to(ROOT)), request_sha256=raw['request_sha256'],
                   backend=backend, **usage(raw), finish_reason=raw['response']['choices'][0]['finish_reason'])
        if len(owners) == 1:
            row['conversation'] = owners[0]
            ingest[backend, owners[0]].append(row)
            calls.append(row)
        elif owners:
            row['candidate_conversations'] = owners
            ambiguous.append(row)
        else:
            outside[backend] += 1
    queries = []
    for backend in systems:
        for ident in sorted(ids):
            item_path = base / 'items' / backend / f'{ident}.json'
            item = read(item_path)
            assert (item.get('complete') if matched_ids is None else 'answer' in item)
            prompt = f"Conversation evidence:\n{item['context']}\n\nQuestion: {item['question']}"
            candidates = [(p, r) for p, r in answers[prompt]
                          if r['response']['choices'][0]['message'].get('content') == item['answer']
                          and r['response']['choices'][0]['finish_reason'] == 'stop']
            assert len(candidates) == 1, (backend, ident, len(candidates))
            path, raw = candidates[0]
            queries.append(dict(dataset='locomo', system=backend, item_id=ident,
                                conversation=item['conversation'], source=str(path.relative_to(ROOT)),
                                request_sha256=raw['request_sha256'], **usage(raw)))
    ingestion = []
    for b in systems:
        for c in conversations:
            rows = ingest[b, c]
            extra = [r for r in ambiguous if r['backend'] == b and c in r['candidate_conversations']]
            token = {k: sum(r[k] for r in rows) for k in ('input_tokens', 'output_tokens', 'cached_tokens')}
            upper = {k: token[k] + sum(r[k] for r in extra) for k in token}
            ingestion.append(dict(dataset='locomo', system=b, conversation=c, **token,
                                  upper=upper, llm_calls=len(rows), ambiguous_calls=len(extra),
                                  seconds=timers[b, c]['seconds'] if b in systems[2:] else (0 if b == 'full-context' else None),
                                  seconds_scope='recorded initialization/ingestion elapsed; concurrent load and recovery included',
                                  embedding_tokens=None, embedding_note='CPU MiniLM token usage was not recorded; LLM totals exclude embeddings'))
    return queries, ingestion, dict(n_questions=len(ids), n_histories=len(conversations),
        rule=('All preselected questions from completed histories 0 and 1 in every system; no accuracy filtering'
              if matched_ids is None else 'All saved-answer IDs shared by four systems, restricted to histories with complete recorded ingestion intervals; no accuracy or judge-completion filtering'),
        ambiguous_ingestion_calls=ambiguous, excluded_noncohort_or_outside_ingestion_calls=dict(outside),
        ingestion_call_ledger=calls)


def collect_lme():
    base = ROOT / 'benchmarks/longmemeval/results/full'
    read(base / 'manifest.json')
    queries = []
    skips = collections.Counter()
    prep = collections.defaultdict(list)
    for path in sorted((base / 'items').glob('*.json')):
        d = read(path)
        if d['status'] != 'scored':
            skips[d['method']] += 1
            continue
        a = d['answer']
        row = dict(dataset='longmemeval', system=d['method'], item_id=d['question_id'],
                   conversation=d['question_id'], source=str(path.relative_to(ROOT)),
                   **usage(dict(response=a['raw'], seconds=a['seconds'])), prep_seconds=d['prep_seconds'])
        queries.append(row)
        prep[d['method']].append(d['prep_seconds'])
    return queries, dict(context_skips=dict(skips), n_histories=300,
        input_output_tokens_are_answer_call_only=True,
        ingestion_llm_tokens={m: 0 for m in ('bm25-standard', 'dense-standard', 'mem0-raw-standard')},
        ingestion_wall_seconds=None,
        reason='Preparation timers combine indexing and retrieval, share cached embeddings across lanes, and do not isolate ingestion. Full standard context does not fit on any of 300 items. No full-standard answer latency/output tokens exist. Oracle context is not a full-history substitute.',
        preparation_seconds_mean={k: mean(v) for k, v in prep.items()})


def compute(queries, ingestions, args, ambiguous=(), systems=SYSTEMS, conversations=CONVERSATIONS):
    def price(i, o, cached=0):
        return ((i-cached)*args.input_price + cached*args.cached_price + o*args.output_price)/1e6
    by = {(b,c): [q for q in queries if q['system']==b and q['conversation']==c]
          for b in systems for c in conversations}
    writes = {(r['system'],r['conversation']): r for r in ingestions}
    models = []
    for b in systems[1:]:
        cells = []
        for c in conversations:
            full, mem, w = by['full-context',c], by[b,c], writes[b,c]
            fi, fo = mean([r['input_tokens'] for r in full]), mean([r['output_tokens'] for r in full])
            mi, mo = mean([r['input_tokens'] for r in mem]), mean([r['output_tokens'] for r in mem])
            # Fixed history prefix warms after first query. Conservatively assume full input
            # cache hits after Q=1; memory query prompts are uncached. No cache write surcharge.
            first, repeat = price(fi,fo), price(fi,fo,fi*args.cache_fraction)
            memcost = price(mi,mo)
            costs = [price(w['input_tokens'],w['output_tokens']),price(w['upper']['input_tokens'],w['upper']['output_tokens'])]
            cells.append(dict(conversation=c, full_first_usd=first, full_repeat_usd=repeat,
                memory_query_usd=memcost, write_usd_bounds=costs,
                full_answer_seconds=mean([r['seconds'] for r in full]),
                memory_answer_seconds=mean([r['seconds'] for r in mem]), ingestion_seconds=w['seconds'],
                crossover_questions_bounds=[first_cheaper(x,first,repeat,memcost) for x in costs]))
        macro = {k: mean([c[k] for c in cells]) for k in ('full_first_usd','full_repeat_usd','memory_query_usd','full_answer_seconds','memory_answer_seconds')}
        # Pool unassigned calls exactly once across the equal-weight history cohort.
        pooled_unknown = sum(price(r['input_tokens'], r['output_tokens']) for r in ambiguous if r['backend']==b) / len(conversations)
        pooled_write = mean([c['write_usd_bounds'][0] for c in cells]) + pooled_unknown
        wb = [pooled_write, pooled_write]
        macro['write_usd_bounds']=wb
        macro['crossover_questions_bounds']=[first_cheaper(x,macro['full_first_usd'],macro['full_repeat_usd'],macro['memory_query_usd']) for x in wb]
        ws = [c['ingestion_seconds'] for c in cells]
        macro['ingestion_seconds'] = mean(ws) if all(x is not None for x in ws) else None
        macro['seconds_crossover_lower_bound'] = first_cheaper(macro['ingestion_seconds'],macro['full_answer_seconds'],macro['full_answer_seconds'],macro['memory_answer_seconds']) if macro['ingestion_seconds'] is not None else None
        macro['seconds_scope'] = 'Model answer call elapsed plus recorded ingestion; retrieval excluded, cache/load uncontrolled. Conditional lower-bound scenario, not complete end-to-end break-even.'
        models.append(dict(system=b, by_conversation=cells, macro=macro,
            published_mem0_crossover_questions=10 if b=='mem0' else None))
    return models


def four_system_cohort():
    """Discover saved-answer intersection and validate finalized ingestion checkpoints."""
    base = ROOT / 'benchmarks/locomo/results/full'
    reference = read(base / 'four-system-matched.json')
    systems = SYSTEMS[:-1]
    items = {b: {d['item_id']: d for path in sorted((base / 'items' / b).glob('*.json'))
                 if 'answer' in (d := read(path))} for b in systems}
    ids = set.intersection(*(set(items[b]) for b in systems))
    conversations = {d['conversation']: d for d in read(base / 'conversations.json')}
    admitted, excluded, checks = [], {}, []
    for c in sorted({items[systems[0]][i]['conversation'] for i in ids}):
        missing = []
        for b in systems[2:]:
            timer = base / 'ingestion-times' / b / f'c{c}.json'
            if not timer.exists():
                missing.append(str(timer.relative_to(ROOT)))
            else:
                t = read(timer)
                assert t['backend'] == b and t['conversation'] == c
                assert 0 < t['seconds'] and t['start_epoch'] < t['end_epoch']
            expected = []
            for session in conversations[c]['sessions']:
                suffixes = (f"{session['key']}-{start}" for start in range(0, len(session['turns']), 8)) if b == 'mem0' else [session['key']]
                expected.extend(base / 'ingest' / b / f'c{c}-{suffix}.json' for suffix in suffixes)
            for path in expected:
                if not path.exists():
                    missing.append(str(path.relative_to(ROOT)))
                else:
                    checkpoint = read(path)
                    assert ('results' in checkpoint if b == 'mem0' else
                            'episode_uuid' in checkpoint or checkpoint.get('split_after_length_failure'))
            checks.append(dict(system=b, conversation=c, expected_checkpoints=len(expected),
                               present_checkpoints=sum(p.exists() for p in expected), timer_present=timer.exists()))
        if missing:
            excluded[str(c)] = missing
        else:
            admitted.append(c)
    ids = {i for i in ids if items[systems[0]][i]['conversation'] in admitted}
    return systems, tuple(admitted), ids, dict(
        reference_n=reference['n'], reference_histories=reference['conversations'],
        excluded_histories_missing_ledgers=excluded, ingestion_completeness_checks=checks,
        rag_ingestion='No LLM ingestion in the upstream harness; embedding tokens and indexing seconds unrecorded')


def four_system_analysis(args):
    systems, conversations, ids, admission = four_system_cohort()
    if not conversations:
        return dict(n_histories=0, n_questions=0, admission=admission,
                    limitation='No histories have both saved matched answers and complete ingestion ledgers'), []
    q, w, audit = collect_locomo(systems, conversations, ids)
    models = compute(q, w, args, audit['ambiguous_ingestion_calls'], systems, conversations)
    audit['attribution'] = 'Actual user payload excluding system examples and EXAMPLE blocks; CURRENT_MESSAGE and speaker labels take precedence; speaker aliases mapped from source histories, then intersected with recorded ingestion intervals'
    # Pooling uncertainty cannot be silently assigned to histories for a cluster bootstrap.
    # Current Mem0/Graphiti cohort has no ambiguous calls; stop if future inputs change this.
    assert not audit['ambiguous_ingestion_calls'], 'Resolve four-system ingestion ownership before bootstrapping'
    assert all(r['llm_calls'] > 0 for r in w if r['system'] in systems[2:])
    by = {(b, c): [r for r in q if r['system'] == b and r['conversation'] == c]
          for b in systems for c in conversations}
    writes = {(r['system'], r['conversation']): r for r in w}
    cells = {(m['system'], r['conversation']): r for m in models for r in m['by_conversation']}
    def metrics(sample):
        full = [r for c in sample for r in by['full-context', c]]
        mem = [r for c in sample for r in by['mem0', c]]
        total = lambda rows: sum(r['input_tokens'] + r['output_tokens'] for r in rows)
        ratios = []
        for c in sample:
            costs = {b: cells[b, c]['write_usd_bounds'][0] + len(by[b, c]) * cells[b, c]['memory_query_usd']
                     for b in ('mem0', 'rag')}
            ratios.append(costs['mem0'] / costs['rag'])
        out = dict(mem0_over_rag_cost_ratio_mean=mean(ratios),
                   token_reduction=1-total(mem)/total(full),
                   token_reduction_including_ingestion_at_observed_counts=1-(total(mem)+total([writes['mem0', c] for c in sample]))/total(full),
                   full_p95_seconds=quantile([r['seconds'] for r in full], .95),
                   mem0_p95_seconds=quantile([r['seconds'] for r in mem], .95))
        out['p95_latency_reduction'] = 1-out['mem0_p95_seconds']/out['full_p95_seconds']
        for b in systems[2:]:
            av = {key: mean([cells[b, c][key] for c in sample]) for key in
                  ('full_first_usd', 'full_repeat_usd', 'memory_query_usd')}
            write = mean([cells[b, c]['write_usd_bounds'][0] for c in sample])
            out[b + '_macro_crossover_questions'] = first_cheaper(write, av['full_first_usd'], av['full_repeat_usd'], av['memory_query_usd'])
        return out
    point = metrics(conversations)
    per_history = [dict(conversation=c, n_questions=len(by['full-context', c]), **metrics([c])) for c in conversations]
    ranges = {key: [min(row[key] for row in per_history), max(row[key] for row in per_history)]
              for key in point if all(row[key] is not None for row in per_history)}
    intervals = dict(n_histories=len(conversations), n_questions=len(ids),
                     unit='whole history, with replacement; all paired systems and observed question counts retained',
                     limitation='Only four independent histories when N_histories=4; percentile intervals are descriptive and unstable, not evidence of broad population precision.')
    if len(conversations) >= 4:
        rng = random.Random(20261122)
        draws = [metrics(rng.choices(conversations, k=len(conversations))) for _ in range(10000)]
        ci = {}
        for key in point:
            values = [d[key] for d in draws]
            # None is no finite crossover, treated as +infinity rather than dropped.
            values = [float('inf') if v is None else v for v in values]
            def endpoint(prob):
                ordered = sorted(values)
                pos = (len(ordered)-1)*prob
                lo, hi = ordered[math.floor(pos)], ordered[math.ceil(pos)]
                return None if math.isinf(hi) else lo+(hi-lo)*(pos-math.floor(pos))
            ci[key] = [endpoint(.025), endpoint(.975)]
        intervals.update(method='95% percentile cluster bootstrap', resamples=len(draws), seed=20261122,
                         bounds=ci, null_endpoint='No finite crossover; infinite draws retained')
    else:
        intervals.update(method=None, reason='Fewer than four independent histories; report per-history ranges instead')
    return dict(**audit, systems=list(systems), history_ids=list(conversations), admission=admission,
                ingestion=w, cost_models=models, comparison=point, by_history=per_history,
                per_history_ranges=ranges, bootstrap=intervals), q


def four_system_table(result, queries):
    lines = ['', '## Four-system matched LoCoMo analysis (without Cognee)', '',
             f"N={result['n_questions']} matched questions per system across {result['n_histories']} histories.", '']
    if not result['n_histories']:
        return '\n'.join(lines + [result['limitation']]) + '\n'
    lines += ['| System | Answer N | Input/query | Output/query | Answer seconds/query | LLM ingest input/history | LLM ingest output/history | Ingest seconds/history | Dollar crossover Q | Recorded-seconds scenario Q |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for b in result['systems']:
        rows = [r for r in queries if r['system'] == b]
        writes = [r for r in result['ingestion'] if r['system'] == b]
        model = next((m['macro'] for m in result['cost_models'] if m['system'] == b), None)
        elapsed = mean([r['seconds'] for r in writes]) if all(r['seconds'] is not None for r in writes) else None
        fmt = lambda x: 'unavailable' if x is None else f'{x:,.3f}'
        lines.append(f"| {b} | {len(rows)} | {mean([r['input_tokens'] for r in rows]):,.1f} | {mean([r['output_tokens'] for r in rows]):,.1f} | {mean([r['seconds'] for r in rows]):.3f} | {mean([r['input_tokens'] for r in writes]):,.1f} | {mean([r['output_tokens'] for r in writes]):,.1f} | {fmt(elapsed)} | {model['crossover_questions_bounds'][0] if model else 'baseline'} | {model['seconds_crossover_lower_bound'] if model and model['seconds_crossover_lower_bound'] is not None else 'unavailable'} |")
    lines += ['', '| History | Matched questions/system | Mem0 dollar crossover Q | Graphiti dollar crossover Q | Mem0/RAG token-only dollar ratio | Mem0 answer-token reduction | Reduction including ingestion | Full-context answer p95 (s) | Mem0 answer p95 (s) |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in result['by_history']:
        lines.append(f"| c{r['conversation']:02} | {r['n_questions']} | {r['mem0_macro_crossover_questions']} | {r['graphiti_macro_crossover_questions']} | {r['mem0_over_rag_cost_ratio_mean']:.3f} | {r['token_reduction']:.2%} | {r['token_reduction_including_ingestion_at_observed_counts']:.2%} | {r['full_p95_seconds']:.3f} | {r['mem0_p95_seconds']:.3f} |")
    lines += ['', '| Statistic | Estimate | Per-history range | 95% history-bootstrap interval |', '|---|---:|---:|---:|']
    for key, value in result['comparison'].items():
        percent = 'reduction' in key
        def fmt(x):
            return 'no finite crossover' if x is None else f'{x:.2%}' if percent else f'{x:.3f}'
        span = lambda values: ' to '.join(fmt(x) for x in values)
        lines.append(f"| {key} | {fmt(value)} | {span(result['per_history_ranges'][key]) if key in result['per_history_ranges'] else 'includes no finite crossover'} | {span(result['bootstrap']['bounds'][key]) if 'bounds' in result['bootstrap'] else 'unavailable: fewer than four histories'} |")
    lines += ['', 'Crossover estimates price an equal-weight average history, rather than averaging crossover integers. Ratios average histories equally; token reductions and p95 pool the matched answer calls. Ingestion is counted once per history at its observed question count. All intervals resample whole histories, retain paired lanes, and rest on N=' + str(result['n_histories']) + ' independent histories, with 10,000 resamples and seed 20261122; four histories give unstable, descriptive intervals. No question-level independence is assumed.', '',
              'This analysis uses the same token prices, idealized full-prefix caching and partial recorded-seconds model as the five-system cohort. Complete Mem0 chunk and Graphiti session checkpoints plus finalized ingestion intervals are required; RAG has no LLM writes, but its embedding tokens/indexing time remain unavailable. Retrieval, embeddings, storage and maintenance are excluded. Answer p95 is not end-to-end latency.', '',
              'Per-query token/time ledgers: `queries-four-system.jsonl`; ingestion ledgers, conditional recorded-seconds crossovers, admission checks and interval metadata: `summary.json` → `four_system_locomo`.']
    return '\n'.join(lines) + '\n'


def tables(queries, ingestions, models, lme, four):
    lines=['# Offline cost results','','## Five-system matched cohort, including Cognee','','LoCoMo: 58 matched questions in two complete histories. Token means below are question-weighted. Cost scenarios average histories equally.','','| System | Input/query | Output/query | Answer seconds/query | LLM ingest input/history | LLM ingest output/history | Ingest elapsed seconds/history | Cached dollar crossover Q | Recorded-seconds scenario Q |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for b in SYSTEMS:
        q=[r for r in queries if r['system']==b]; w=[r for r in ingestions if r['system']==b]
        model=next((m['macro'] for m in models if m['system']==b),None)
        def fmt(x): return 'unavailable' if x is None else f'{x:,.1f}'
        def bound(k):
            lo=mean([r[k] for r in w]); hi=mean([r['upper'][k] for r in w])
            return fmt(lo) if lo==hi else f'{lo:,.1f} to {hi:,.1f}'
        def cross(x):
            if x is None:return 'unavailable'
            return ' to '.join(str(v) if v is not None else 'never' for v in dict.fromkeys(x))
        wall=mean([r['seconds'] for r in w]) if all(r['seconds'] is not None for r in w) else None
        lines.append(f"| {b} | {fmt(mean([r['input_tokens'] for r in q]))} | {fmt(mean([r['output_tokens'] for r in q]))} | {fmt(mean([r['seconds'] for r in q]))} | {bound('input_tokens')} | {bound('output_tokens')} | {fmt(wall)} | {cross(model['crossover_questions_bounds']) if model else 'baseline'} | {cross([model['seconds_crossover_lower_bound']]) if model and b!='rag' else 'unavailable'} |")
    lines += ['','Dollar Q excludes CPU embeddings/storage/maintenance. RAG write LLM tokens are zero; indexing time is unrecorded. Seconds Q excludes retrieval and is not an end-to-end latency result. Cognee ingestion ranges allocate ambiguous calls to neither/either history.','','| Published figure | Local accounting |','|---|---|',f"| Mem0 cheaper after about 10 questions at 100K cached tokens | {four.get('comparison', {}).get('mem0_macro_crossover_questions', 'unavailable')} questions; N={four['n_questions']} matched questions/system across {four['n_histories']} shorter histories, different prices and tokenizer |",'| RAG 8.4x lower total ownership cost | Token-only ratio below; ownership cost not reproduced |','| Mem0 91% lower p95 latency, >90% token reduction | Answer-call-only p95 and token ratios below; ingestion separately counted |','| Sleep-time 2.5x lower cost/query | Not reproduced: neither reused run executes sleep-time consolidation |','| Hindsight decision request median 167 ms | Not reproduced; no retained local decision-model install |','','LongMemEval: all 300 full-standard histories exceed 8,192-token native window; no measured full-standard baseline or crossover. Oracle rows use shorter supplied evidence and cannot replace it.','','| Lane | Answer N | Input/query | Output/query | Answer seconds/query | Preparation seconds (shared cache, includes retrieval) |','|---|---:|---:|---:|---:|---:|']
    for b in sorted({q['system'] for q in lme}):
        q=[r for r in lme if r['system']==b]
        lines.append(f"| {b} | {len(q)} | {mean([r['input_tokens'] for r in q]):,.1f} | {mean([r['output_tokens'] for r in q]):,.1f} | {mean([r['seconds'] for r in q]):.2f} | {mean([r['prep_seconds'] for r in q]):.3f} |")
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-price',type=float,default=.15,help='USD / million uncached input tokens')
    p.add_argument('--cached-price',type=float,default=.075,help='USD / million cached input tokens')
    p.add_argument('--output-price',type=float,default=.60,help='USD / million output tokens')
    p.add_argument('--cache-fraction',type=float,default=1,help='Fraction of full-history input cached after Q=1')
    p.add_argument('--out',type=Path,default=HERE/'results')
    a=p.parse_args()
    if min(a.input_price,a.cached_price,a.output_price)<0 or not 0<=a.cache_fraction<=1:p.error('Invalid price or cache fraction')
    a.out.mkdir(parents=True,exist_ok=True)
    q,w,audit=collect_locomo(); lme,limitations=collect_lme(); models=compute(q,w,a,audit['ambiguous_ingestion_calls'])
    result=dict(prices=dict(input=a.input_price,cached=a.cached_price,output=a.output_price,unit='USD/million tokens',source='https://developers.openai.com/api/docs/models/gpt-4o-mini',checked='2026-11-22'),cache_fraction=a.cache_fraction,
                locomo=audit,ingestion=w,cost_models=models,longmemeval=limitations,
                intervals='No population CI: only two independent LoCoMo histories. Per-history sensitivity is reported, not question-level pseudoreplication.')
    f=[r for r in q if r['system']=='full-context'];m=[r for r in q if r['system']=='mem0']
    result['locomo_answer_only_comparison']=dict(n=len(f),full_p95_seconds=quantile([r['seconds'] for r in f],.95),mem0_p95_seconds=quantile([r['seconds'] for r in m],.95),token_reduction=1-sum(r['input_tokens']+r['output_tokens'] for r in m)/sum(r['input_tokens']+r['output_tokens'] for r in f))
    result['locomo_answer_only_comparison']['p95_latency_reduction'] = 1-result['locomo_answer_only_comparison']['mem0_p95_seconds']/result['locomo_answer_only_comparison']['full_p95_seconds']
    mw = [r for r in w if r['system']=='mem0']
    result['locomo_answer_only_comparison']['token_reduction_including_ingestion_at_observed_counts'] = 1-(sum(r['input_tokens']+r['output_tokens'] for r in m)+sum(r['input_tokens']+r['output_tokens'] for r in mw))/sum(r['input_tokens']+r['output_tokens'] for r in f)
    result['token_only_mem0_over_rag_cost_ratio_at_observed_question_counts']={}
    for c in CONVERSATIONS:
        costs={}
        for b in ('mem0','rag'):
            mm=next(x for x in models if x['system']==b)['by_conversation'][c]
            n=sum(r['system']==b and r['conversation']==c for r in q)
            costs[b]=mm['write_usd_bounds'][0]+n*mm['memory_query_usd']
        result['token_only_mem0_over_rag_cost_ratio_at_observed_question_counts'][str(c)]=costs['mem0']/costs['rag']
    four, four_queries = four_system_analysis(a)
    result['four_system_locomo'] = four
    (a.out/'queries-four-system.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in four_queries))
    (a.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (a.out/'queries.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in q+lme))
    (a.out/'source-hashes.json').write_text(json.dumps(SOURCES,sort_keys=True,indent=2)+'\n')
    table=tables(q,w,models,lme,four) + four_system_table(four, four_queries)
    (a.out/'TABLE.md').write_text(table)
    print(table)


if __name__=='__main__':main()

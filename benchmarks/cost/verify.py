"""Check accounting boundaries, matching, scope and reproducibility without model calls."""
import json
from pathlib import Path
from analyze import first_cheaper, HERE

# Strict inequality matters at exact ties. Cheap first query can be followed by
# an expensive asymptotic slope, so retain the explicit Q=1 branch.
assert first_cheaper(10, 2, 2, 1) == 11
assert first_cheaper(10, 2, 1, 2) is None
assert first_cheaper(0, 5, 1, 2) == 1
assert first_cheaper(0, 1, 1, 1) is None
s=json.loads((HERE/'results/summary.json').read_text())
q=[json.loads(line) for line in (HERE/'results/queries.jsonl').read_text().splitlines()]
l=[r for r in q if r['dataset']=='locomo']
ids={r['item_id'] for r in l}
assert len(ids)==58 and len(l)==290
assert all(sum(r['item_id']==i for r in l)==5 for i in ids)
assert all(r['input_tokens']>=r['cached_tokens']>=0 and r['output_tokens']>0 for r in q)
assert s['longmemeval']['context_skips']['full-standard']==300
assert not any(r['system']=='full-standard' for r in q)
assert len({r['request_sha256'] for r in s['locomo']['ingestion_call_ledger']})==len(s['locomo']['ingestion_call_ledger'])
for model in s['cost_models']:
    m=model['macro']; w=m['write_usd_bounds'][0]; query=m['memory_query_usd']
    n=m['crossover_questions_bounds'][0]
    if n is not None:
        full=lambda x:m['full_first_usd']+(x-1)*m['full_repeat_usd']
        assert w+n*query < full(n)
        assert n==1 or w+(n-1)*query >= full(n-1)
print('PASS: strict crossover boundaries, paired IDs, unique ingestion calls, token conservation bounds, skipped baseline protection')

# Preserve every original result, including Cognee's two-history uncertainty.
import hashlib
import math
import re
import statistics
from types import SimpleNamespace
from unittest.mock import patch
from analyze import four_system_analysis, ROOT
original = {k: v for k, v in s.items() if k != 'four_system_locomo'}
assert hashlib.sha256(json.dumps(original, sort_keys=True).encode()).hexdigest() == 'ed03bc8aebedb5a93123e433756b329c04f9d4750ca20f8d267656ca16c46f8f'
four = s['four_system_locomo']
fq = [json.loads(line) for line in (HERE/'results/queries-four-system.jsonl').read_text().splitlines()]
assert four['systems'] == ['full-context', 'rag', 'mem0', 'graphiti']
assert four['history_ids'] == [0, 1, 2, 3]
assert four['n_questions'] == 123 and four['n_histories'] == 4 and len(fq) == 492
assert not four['admission']['excluded_histories_missing_ledgers']
assert not four['ambiguous_ingestion_calls']
assert all(c['present_checkpoints'] == c['expected_checkpoints'] and c['timer_present']
           for c in four['admission']['ingestion_completeness_checks'])
fids = {r['item_id'] for r in fq}
assert all({r['system'] for r in fq if r['item_id'] == i} == set(four['systems']) for i in fids)
assert all(r['input_tokens'] >= r['cached_tokens'] >= 0 and r['output_tokens'] > 0 for r in fq)
assert {r['item_id'] for r in fq if r['conversation'] in (0, 1)} == ids
assert all(r in fq for r in l if r['system'] != 'cognee')

# Recompute totals from the compact per-call ledgers, independently of cost-model means.
price = lambda r: (r['input_tokens']*.15 + r['output_tokens']*.60)/1e6
tokens = lambda rows: sum(r['input_tokens']+r['output_tokens'] for r in rows)
close = lambda a, b: math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
ledger = four['ingestion_call_ledger']
assert len({r['source'] for r in ledger}) == len(ledger)
assert len({r['request_sha256'] for r in ledger}) == len(ledger)
for w in four['ingestion']:
    calls = [r for r in ledger if r['backend'] == w['system'] and r['conversation'] == w['conversation']]
    assert w['llm_calls'] == len(calls)
    for key in ('input_tokens', 'output_tokens', 'cached_tokens'):
        assert w[key] == w['upper'][key] == sum(r[key] for r in calls)
assert [w['llm_calls'] for w in four['ingestion'] if w['system'] == 'mem0'] == [61, 53, 98, 90]
ratios = []
for history in four['by_history']:
    c = history['conversation']
    rows = {b: [r for r in fq if r['system'] == b and r['conversation'] == c] for b in four['systems']}
    assert history['n_questions'] == [34, 24, 32, 33][c]
    costs = {b: sum(price(r) for r in rows[b]) + sum(price(r) for r in ledger if r['backend'] == b and r['conversation'] == c)
             for b in ('mem0', 'rag')}
    ratios.append(costs['mem0']/costs['rag'])
    assert close(history['mem0_over_rag_cost_ratio_mean'], ratios[-1])
    assert close(history['token_reduction'], 1-tokens(rows['mem0'])/tokens(rows['full-context']))
    for model in four['cost_models']:
        cell = next(r for r in model['by_conversation'] if r['conversation'] == c)
        b = model['system']
        assert close(cell['write_usd_bounds'][0], sum(price(r) for r in ledger if r['backend'] == b and r['conversation'] == c))
        assert close(cell['memory_query_usd'], statistics.mean(price(r) for r in rows[b]))
        assert close(cell['full_first_usd'], statistics.mean(price(r) for r in rows['full-context']))
        assert close(cell['full_repeat_usd'], statistics.mean((r['input_tokens']*.075+r['output_tokens']*.60)/1e6 for r in rows['full-context']))
        for record in (cell, model['macro']):
            n = record['crossover_questions_bounds'][0]
            if n is not None:
                gap = lambda k: record['write_usd_bounds'][0]+k*record['memory_query_usd']-record['full_first_usd']-(k-1)*record['full_repeat_usd']
                assert gap(n) < 0 and (n == 1 or gap(n-1) >= 0)
comp = four['comparison']
assert close(comp['mem0_over_rag_cost_ratio_mean'], statistics.mean(ratios))
assert four['per_history_ranges']['mem0_over_rag_cost_ratio_mean'] == [min(ratios), max(ratios)] or all(close(a,b) for a,b in zip(four['per_history_ranges']['mem0_over_rag_cost_ratio_mean'], [min(ratios), max(ratios)]))
full = [r for r in fq if r['system'] == 'full-context']
mem = [r for r in fq if r['system'] == 'mem0']
mwrites = [r for r in ledger if r['backend'] == 'mem0']
assert close(comp['token_reduction'], 1-tokens(mem)/tokens(full))
assert close(comp['token_reduction_including_ingestion_at_observed_counts'], 1-(tokens(mem)+tokens(mwrites))/tokens(full))
for key, rows in [('full_p95_seconds', full), ('mem0_p95_seconds', mem)]:
    times = sorted(r['seconds'] for r in rows)
    position = .95*(len(times)-1)
    index = int(position)
    assert close(comp[key], times[index]+(times[index+1]-times[index])*(position-index))
assert four['bootstrap']['n_histories'] == 4 and four['bootstrap']['n_questions'] == 123
assert four['bootstrap']['resamples'] == 10000 and four['bootstrap']['seed'] == 20261122
assert set(four['bootstrap']['bounds']) == set(comp)
assert four['bootstrap']['bounds']['mem0_macro_crossover_questions'] == [48, 51]
assert four['bootstrap']['bounds']['graphiti_macro_crossover_questions'] == [45, 63]
for key, interval in four['bootstrap']['bounds'].items():
    assert interval[0] <= comp[key] <= interval[1]

# Fail closed on missing ingestion ledgers, without changing upstream files.
# Dropping histories 2/3 must really remove their answers and their bootstrap CI.
real_exists = Path.exists
missing = {ROOT/'benchmarks/locomo/results/full/ingestion-times'/b/f'c{c}.json'
           for b in ('mem0', 'graphiti') for c in (2, 3)}
with patch.object(Path, 'exists', lambda path: False if path in missing else real_exists(path)):
    fallback, fallback_queries = four_system_analysis(SimpleNamespace(input_price=.15, cached_price=.075, output_price=.60, cache_fraction=1))
assert fallback['n_histories'] == 2 and fallback['n_questions'] == 58 and len(fallback_queries) == 232
assert set(fallback['admission']['excluded_histories_missing_ledgers']) == {'2', '3'}
assert fallback['bootstrap']['method'] is None and 'bounds' not in fallback['bootstrap']

# Pin source bytes and check replacement style without splitting decimal numbers.
for relative, digest in json.loads((HERE/'results/source-hashes.json').read_text()).items():
    assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == digest, relative
report = (HERE/'REPORT.md').read_text()
replacements = re.findall(r'Suggested replacement[^\n]*: “(.*?)”', report)
assert len(replacements) == 5
for replacement in replacements:
    assert '—' not in replacement and 'this book' in replacement.lower()
    assert len(re.split(r'(?<=[.!?])\s+(?=[A-Z])', replacement)) <= 2
assert all('123' in replacement and 'four histories' in replacement.replace('four shorter histories','four histories')
           for replacement in replacements[:3])
checks = ['original five-system summary unchanged', 'four-system paired saved-answer IDs and exact Ns',
          'complete ingestion checkpoints and unique call ownership', 'independent token/dollar/p95 recomputation',
          'per-history and macro strict crossover boundaries', 'history-bootstrap metadata and bounds',
          'missing-ledger two-history fallback excludes intervals', 'source byte hashes', 'editor replacement style and Ns']
(HERE/'results/verification.json').write_text(json.dumps(dict(status='PASS', checks=checks, n_questions=123, n_histories=4), indent=2)+'\n')
print('PASS: '+', '.join(checks))

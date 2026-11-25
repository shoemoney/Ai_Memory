"""Audit saved cells and emit counts without re-running inference."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
expected = json.loads((ROOT/'evidence/sample-manifest.json').read_text())
rows = []
for p in sorted((ROOT/'results').glob('*/*/summary.json')):
    summary = json.loads(p.read_text())
    records = [json.loads(f.read_text()) for f in sorted(p.parent.glob('*/*.json'))]
    if len(records) != 40 or len({r['id'] for r in records}) != 40:
        raise AssertionError(f'Wrong case count: {p}')
    for cat, detail in expected['categories'].items():
        if {r['id'] for r in records if r['category']==cat} != set(detail['ids']):
            raise AssertionError(f'Different sample: {p}')
    correct = sum(r['score']['valid'] for r in records)
    if correct != summary['correct']:
        raise AssertionError('Summary differs from raw scores')
    stops = [r for r in records if r['response']['choices'][0]['finish_reason']=='length']
    reasons = [len(r['response']['choices'][0]['message'].get('reasoning_content') or '') for r in records]
    if summary['thinking']=='off' and any(reasons):
        raise AssertionError('Thinking-off response included reasoning')
    if summary['thinking']=='on' and not any(reasons):
        raise AssertionError('No evidence of thinking in thinking-on cell')
    for r in records:
        controls = r['request']
        if (controls['temperature'] != 0 or controls['seed'] != 20261121
            or controls['max_tokens'] != 4096
            or controls['extra_body']['chat_template_kwargs']['enable_thinking'] != (summary['thinking']=='on')):
            raise AssertionError('Unexpected request controls')
    rows.append({'model': summary['model'], 'thinking': summary['thinking'],
                 'correct': correct, 'n': 40, 'percent': 100*correct/40,
                 'length_stopped': len(stops), 'length_stopped_scored_correct':sum(r['score']['valid'] for r in stops),
                 'reasoning_nonempty':sum(n>0 for n in reasons), 'source':str(p.relative_to(ROOT)),
                 'categories':summary['categories']})
if '--require-complete' in sys.argv:
    expected_cells = {(f'Qwen3.5-{size}-Q4_K_M',mode) for size in ['0.8B','2B','4B'] for mode in ['off','on']}
    if {(r['model'],r['thinking']) for r in rows} != expected_cells:
        raise AssertionError('Incomplete model/mode matrix')
(ROOT/'results/audit.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:
    print(r['model'],r['thinking'],f"{r['correct']}/{r['n']}",r['percent'],'length stops',r['length_stopped'],'reasoning',r['reasoning_nonempty'])

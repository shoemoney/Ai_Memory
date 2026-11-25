import json
from bench import HERE, main, methods


def test_benchmark_smoke(tmp_path):
    output = tmp_path/'smoke'
    main(['--tiny','--limit','1','--max-tokens','2','--thresholds','0','1',
          '--output',str(output)])
    report = json.loads(output.with_suffix('.json').read_text())
    assert len(report['summary']) == 12
    assert all(r['tokens_per_second'] > 0 for r in report['summary'])
    assert all(r['exact_match_rate'] == 1 for r in report['summary']
               if r['method'].startswith('spec-'))
    assert 'exact_match_rate' in output.with_suffix('.md').read_text()
    prompts = json.loads((HERE/'prompts.json').read_text())
    assert len(prompts) == 40
    assert sum(r['category']=='memory' for r in prompts) == 20
    assert len(methods()) == 14

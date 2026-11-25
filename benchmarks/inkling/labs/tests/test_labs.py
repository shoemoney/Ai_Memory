import json
from pathlib import Path
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from common import REPO, read
from quality import exact_match
from stub_server import Stub


def invoke(script, *args, check=True):
    command = (['bash', str(HERE / script)] if script.endswith('.sh') else [sys.executable, str(HERE / script)])
    return subprocess.run(command + list(map(str, args)), text=True, capture_output=True, check=check)


@pytest.fixture
def fixture(tmp_path):
    path = tmp_path / 'quality-fixture.json'
    path.write_text(json.dumps([dict(item_id=f'{lane}-{i}', lane=lane, gold=gold,
                                    prompt=prompt) for lane, gold, prompt in [
                                        ('gsm8k', '2', 'What is 1+1? End with Final answer: <number>.'),
                                        ('mmlu-pro', 'A', 'Which is two? A. 2 B. 3\nReturn only the letter')]
                                for i in range(3)]))
    return path


@pytest.mark.parametrize('lab', ['longmemeval', 'locomo'])
def test_memory_three_questions_end_to_end_and_resume(tmp_path, lab):
    with Stub() as stub:
        args = ['--variant', 'smoke', '--model', 'stub-reader', '--base-url', stub.url,
                '--judge-base-url', stub.url, '--output-root', tmp_path, '--limit', '3']
        result = invoke(lab + '.sh', *args)
        assert result.returncode == 0
        out = tmp_path / 'smoke' / lab
        state = read(out / 'summary.json')
        assert state['planned'] == state['completed'] == 15
        assert state['complete']
        expected_model = 'default_model' if lab == 'longmemeval' else 'qwen2.5-14b-instruct'
        assert any(c['model'] == expected_model for c in stub.calls)
        for call in stub.calls:
            assert call['temperature'] == 0
            if call['model'] == 'stub-reader':
                assert call['thinking_budget'] == 0
                assert call['chat_template_kwargs'] == {'enable_thinking': False}
            else:
                assert 'thinking_budget' not in call
        for lane in state['systems']:
            for path in (out / 'items' / lane).glob('*.json'):
                row = read(path)
                if row['status'] == 'scored':
                    if lab == 'longmemeval':
                        assert len(row['judge']['calls']) == 3
                    else:
                        assert len(row['votes']) == 3
                        assert [v['seed'] for v in row['votes']] == [20261122 + 100 *
                            ['full-context','rag','mem0','graphiti','cognee'].index(lane) + i for i in range(3)]
        calls_before = len(stub.calls)
        invoke(lab + '.sh', *args)
        assert len(stub.calls) == calls_before  # Completed rows never regenerate.
        changed = invoke(lab + '.sh', *args, '--thinking-budget', '2', check=False)
        assert changed.returncode != 0
        assert len(stub.calls) == calls_before


def test_quality_three_per_dataset_concurrency_resume(tmp_path, fixture):
    with Stub() as stub:
        args = ['--variant', 'smoke', '--model', 'stub-reader', '--base-url', stub.url,
                '--output-root', tmp_path, '--limit', '3', '--fixture', fixture, '--concurrency', '3']
        invoke('quality.py', *args)
        state = read(tmp_path / 'smoke/quality/summary.json')
        assert state['complete'] and state['completed'] == 6
        assert all(g['n'] == g['correct'] == 3 for g in state['systems'].values())
        assert len(stub.calls) == 6
        invoke('quality.py', *args)
        assert len(stub.calls) == 6
        assert all(c['thinking_budget'] == 0 for c in stub.calls)


def test_batch_restart_hook(tmp_path, fixture):
    marker = tmp_path / 'restarts'
    with Stub() as stub:
        invoke('batch.sh', 'smoke', '--restart-hook', f'printf x >> "{marker}"',
               '--model', 'stub-reader', '--base-url', stub.url, '--output-root', tmp_path,
               '--longmemeval-judge-base-url', stub.url, '--locomo-judge-base-url', stub.url,
               '--quality-fixture', fixture, '--limit', '3', '--batch-size', '4')
        for lab in ['longmemeval', 'locomo', 'quality']:
            assert read(tmp_path / 'smoke' / lab / 'summary.json')['complete']
        # 4 LongMemEval + 4 LoCoMo + 2 quality invocations; hook between each.
        assert marker.read_text() == 'x' * 9


def test_exact_match_rejects_wrong_and_unmarked_prose():
    assert exact_match('gsm8k', 'Final answer: 1,200', '1200')
    assert exact_match('gsm8k', '2.00', '2')
    assert not exact_match('gsm8k', 'The answer might be 2 or 3', '3')
    assert not exact_match('gsm8k', 'Final answer: 3', '2')
    assert exact_match('mmlu-pro', 'A', 'A')
    assert not exact_match('mmlu-pro', 'A or B', 'A')
    assert not exact_match('mmlu-pro', 'B', 'A')


def test_full_archived_plan_available():
    from memory import plans
    for lab, n in [('longmemeval', 1500), ('locomo', 841)]:
        plan = plans(lab, REPO / 'benchmarks' / lab / 'results/full', None)
        assert len(plan) == n
        assert all(p.exists() for _, _, p in plan)


@pytest.mark.parametrize('lab', ['longmemeval', 'locomo'])
def test_interrupted_vote_resumes_answer_and_negative_judge(tmp_path, lab):
    with Stub() as stub:
        stub.fail_at = 3
        stub.wrong_judge = True
        args = ['--variant', 'smoke', '--model', 'stub-reader', '--base-url', stub.url,
                '--judge-base-url', stub.url, '--output-root', tmp_path, '--limit', '1']
        assert invoke(lab + '.sh', *args, check=False).returncode != 0
        stub.fail_at = None
        invoke(lab + '.sh', *args)
        out = tmp_path / 'smoke' / lab
        state = read(out / 'summary.json')
        assert state['complete']
        assert sum(g['correct'] for g in state['systems'].values()) == 0
        scored = sum(g['n'] for g in state['systems'].values())
        assert sum(c['model'] == 'stub-reader' for c in stub.calls) == scored
        assert len(stub.calls) == 4 * scored + 1  # One failed vote, no regenerated answer.


def test_locomo_length_retry_and_batch_hook_failure(tmp_path):
    with Stub() as stub:
        stub.length_once = True
        invoke('locomo.sh', '--variant', 'smoke', '--model', 'stub-reader', '--base-url', stub.url,
               '--judge-base-url', stub.url, '--output-root', tmp_path, '--limit', '1')
        readers = [c for c in stub.calls if c['model'] == 'stub-reader']
        assert [r['max_tokens'] for r in readers[:2]] == [384, 768]
        assert read(tmp_path / 'smoke/locomo/summary.json')['complete']
        other = tmp_path / 'hook-failure'
        result = invoke('batch.sh', 'smoke', '--restart-hook', 'exit 9',
                        '--model', 'stub-reader', '--base-url', stub.url,
                        '--longmemeval-judge-base-url', stub.url, '--locomo-judge-base-url', stub.url,
                        '--output-root', other, '--limit', '3', '--batch-size', '1', check=False)
        assert result.returncode != 0
        assert read(other / 'smoke/longmemeval/summary.json')['completed'] == 1
        assert not (other / 'smoke/locomo').exists()

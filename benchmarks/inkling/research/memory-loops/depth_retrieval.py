"""Balanced depth × archived retrieval experiment; no shared harness edits."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import NormalDist, mean, median
import subprocess
import sys

from protocol import HERE, LABS, REPO, SEED, read, stratified

PASSES = (1, 2, 3, 5)
LANES = ('full-oracle', 'bm25-standard', 'dense-standard')
ARCHIVE = REPO / 'benchmarks/longmemeval/results/full'
MANIFEST = HERE / 'depth-retrieval-selection.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def eligible(archive=ARCHIVE):
    rows = []
    for item in read(archive / 'manifest.json')['items']:
        qid = item['question_id']
        records = [read(archive / 'items' / f'{qid}--{lane}.json') for lane in LANES]
        # Frozen book token counts use its pinned tokenizer and 8192-token rule.
        if all(r.get('status') == 'scored' and r['prompt_tokens'] + 512 <= 8192 for r in records):
            oracle = records[0]
            rows.append(dict(question_id=qid, question_type=oracle['question_type'],
                             stratum=oracle['stratum']))
    return rows


def select(n=150, archive=ARCHIVE):
    rows = eligible(archive)
    if not 1 <= n <= len(rows):
        raise ValueError(f'n must be 1..{len(rows)}')
    ids = stratified(rows, n, lambda r: r['stratum'], lambda r: r['question_id'])
    lookup = {r['question_id']: r for r in rows}
    chosen = [lookup[q] for q in ids]
    hashes = {f'{q}--{lane}.json': sha(archive / 'items' / f'{q}--{lane}.json')
              for q in ids for lane in LANES}
    return dict(design='depth-retrieval-v1', seed=SEED, passes=list(PASSES), lanes=list(LANES),
                method='largest-remainder proportional allocation among eligible archive strata; sorted IDs; seeded sample and shuffle',
                eligibility='all three archived prompts scored and prompt_tokens + 512 <= 8192',
                eligible_n=len(rows), eligible_strata=dict(Counter(r['stratum'] for r in rows)),
                n=n, strata=dict(Counter(r['stratum'] for r in chosen)), questions=chosen,
                archive_manifest_sha256=sha(archive / 'manifest.json'), input_sha256=hashes)


def validate(selected, archive=ARCHIVE):
    if selected['design'] != 'depth-retrieval-v1' or selected['passes'] != list(PASSES) or selected['lanes'] != list(LANES):
        raise ValueError('Wrong design, depths or retrieval lanes')
    rows = selected['questions']
    ids = [r['question_id'] for r in rows]
    if not ids or len(set(ids)) != len(ids) or selected['n'] != len(ids):
        raise ValueError('Empty, duplicate or inconsistent selection')
    if selected['archive_manifest_sha256'] != sha(archive / 'manifest.json'):
        raise ValueError('Archive manifest changed')
    available = {r['question_id']: r for r in eligible(archive)}
    for row in rows:
        if available.get(row['question_id']) != row:
            raise ValueError('Ineligible question or changed type')
    expected = {f'{q}--{lane}.json' for q in ids for lane in LANES}
    if set(selected['input_sha256']) != expected:
        raise ValueError('Incomplete input hashes')
    for name, digest in selected['input_sha256'].items():
        if sha(archive / 'items' / name) != digest:
            raise ValueError(f'Archived input changed: {name}')
    return ids


def run_memory(passes, selection_path, args):
    selected = read(selection_path)
    ids = validate(selected)
    sys.path.insert(0, str(LABS))
    import memory
    original_arguments = memory.arguments

    def arguments(description):
        parser = original_arguments(description)
        parser._option_string_actions['--variant'].choices = [f'varloop-p{passes}']
        return parser

    def plans(lab, archive, limit):
        if lab != 'longmemeval' or archive.resolve() != ARCHIVE.resolve() or limit is not None:
            raise ValueError('Depth-retrieval requires pinned LongMemEval archive and no limit')
        return [(qid, lane, archive / 'items' / f'{qid}--{lane}.json') for qid in ids for lane in LANES]

    memory.arguments, memory.plans = arguments, plans
    sys.argv = [str(LABS / 'memory.py'), 'longmemeval', '--variant', f'varloop-p{passes}',
                '--thinking-budget', '0', *args]
    memory.main()


def batch(passes, selection_path, output_root, model, base, hook, batch_size=10, judge_base=None):
    if passes not in PASSES or batch_size < 1:
        raise ValueError('Invalid depth or batch size')
    selected = read(selection_path)
    validate(selected)
    sys.path.insert(0, str(LABS))
    from common import initialize
    root = Path(output_root) / f'varloop-p{passes}'
    initialize(root, dict(design='depth-retrieval-v1', passes=passes, selection=selected,
                         selection_sha256=sha(selection_path), adapter_sha256=sha(__file__),
                         reader_adapter_sha256=sha(LABS / 'memory.py'), model=model, base_url=base,
                         judge_base_url=judge_base or 'http://127.0.0.1:39711/v1',
                         batch_size=batch_size, thinking_budget=0))
    command = [sys.executable, str(Path(__file__)), 'memory', '--passes', str(passes),
               '--selection', str(selection_path), '--output-root', str(output_root),
               '--model', model, '--base-url', base, '--batch-size', str(batch_size)]
    if judge_base:
        command += ['--judge-base-url', judge_base]
    previous, ran = -1, False
    while True:
        if ran:
            subprocess.run(hook, shell=True, check=True)
        subprocess.run(command, check=True)
        ran = True
        state = read(root / 'longmemeval/summary.json')
        if state['complete']:
            if state['completed'] != 3 * selected['n'] or any(g['skipped'] for g in state['systems'].values()):
                raise RuntimeError('Unbalanced design or skipped cells')
            return
        if state['completed'] <= previous:
            raise RuntimeError('No progress')
        previous = state['completed']


def estimate(selected):
    stock = REPO / 'benchmarks/inkling/results/stock'
    timings, votes = defaultdict(list), []
    for path in (stock / 'longmemeval/raw').rglob('*.json'):
        if '.error.' in path.name:
            continue
        row = read(path)
        lane = path.parent.parent.name
        if lane in LANES:
            if path.name.startswith('answer'):
                timings[lane].append(row['seconds'])
            elif path.name.startswith('judge'):
                votes.append(row['seconds'])
    means = {lane: mean(timings[lane]) for lane in LANES}
    samples_path = stock / 'memory-samples.jsonl'
    samples = [json.loads(line) for line in samples_path.read_text().splitlines() if line.strip()]
    changes = []
    for sample in samples:
        pid = sample.get('pids', {}).get('server')
        if pid and (not changes or changes[-1][1] != pid):
            changes.append((sample['unix'], pid))
    spacings = [b[0]-a[0] for a,b in zip(changes, changes[1:])]
    log = (stock / 'run.log').read_text()
    def runtime(n, overhead=30, scaling=3.75):
        starts = 4 * math.ceil(3*n/10)
        return (n*sum(means.values())*scaling + 12*n*3*mean(votes) + starts*overhead)/3600
    n = selected['n']
    largest = max(k for k in range(1, min(150, selected['eligible_n'])+1) if runtime(k) <= 8)
    z = NormalDist().inv_cdf(.975) + NormalDist().inv_cdf(.8)
    return dict(n=n, cells=12, reader_calls=12*n, judge_votes=36*n,
        stock_reader_mean_seconds=means, judge_vote_mean_seconds=mean(votes),
        stock_snapshot_sha256={name: sha(stock/name) for name in
                               ('run.log','memory-samples.jsonl','longmemeval/summary.json')},
        log_evidence=dict(reader_starts=log.count('Started PID'),
                          longmemeval_progress_records=log.count('"planned": 1500'),
                          caution='run.log spans refusal, LongMemEval, LoCoMo, interruptions and failures; its total is not LongMemEval wall time'),
        memory_sample_evidence=dict(n=len(samples), span_seconds=samples[-1]['unix']-samples[0]['unix'],
            observed_server_pid_changes=len(changes)-1, median_observed_restart_spacing_seconds=median(spacings),
            max_swap_used_mib=max(float(re.search(r'used = ([\d.]+)M', s['swap'])[1]) for s in samples),
            caution='30-second sampling aliases restart durations; spacing includes inference and is not startup latency'),
        runtime_hours=runtime(n), stress_hours=runtime(n, 60, 5.0),
        assumptions='Reader scales by layer visits (24+36+48+72)/48=3.75; 30s/start; stress: 60s/start and summed scaling 5; no downloads/conversions; stock quantization differs from native varloop',
        largest_n_under_8h_up_to_requested_150=largest,
        power=dict(alpha=.05, power=.8, assumed_depth_discordance=.42,
            mde_depth_pp=100*z*math.sqrt(.42/n),
            mde_depth_sensitivity_pp={str(q):100*z*math.sqrt(q/n) for q in (.2,.4,.6)},
            mde_interaction_pp=100*z*math.sqrt(.84/n),
            caution='Normal approximation; depth discordance unmeasured; interaction assumes independent lane difference scores with variance .42 each. Multiplicity and per-type effects need more power.'))


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('action', choices=['select', 'plan', 'memory'])
    p.add_argument('--selection', type=Path, default=MANIFEST)
    p.add_argument('--n', type=int, default=150)
    p.add_argument('--passes', type=int, choices=PASSES)
    a, extra = p.parse_known_args()
    if a.action == 'select':
        if extra:
            p.error('Unknown selection options')
        a.selection.write_text(json.dumps(select(a.n), indent=2)+'\n')
    elif a.action == 'plan':
        print(json.dumps(estimate(read(a.selection)), indent=2))
    else:
        if not a.passes:
            p.error('memory requires --passes')
        run_memory(a.passes, a.selection, extra)


if __name__ == '__main__':
    main()

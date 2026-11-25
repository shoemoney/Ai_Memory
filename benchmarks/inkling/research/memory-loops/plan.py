"""Recompute planning assumptions from stock results, without model inference."""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist, mean

from protocol import HERE, REPO, read


def estimate():
    selected = read(HERE / 'selection.json')
    stock = REPO / 'benchmarks/inkling/results/stock'
    lme = read(stock / 'longmemeval/summary.json')
    loco = read(stock / 'locomo/matched-summary.json')
    report = {'selection': selected, 'stock_snapshot': {}, 'power': {}, 'timing': {}}
    for lab, path in [('longmemeval', stock / 'longmemeval/summary.json'),
                      ('locomo', stock / 'locomo/matched-summary.json')]:
        report['stock_snapshot'][lab] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), data=read(path))
    z80 = NormalDist().inv_cdf(.8)
    for lab, lane, data in [('longmemeval', 'bm25-standard', lme), ('locomo', 'full-context', loco)]:
        group = data['systems'][lane]
        p = group['correct'] / group['n']
        q = 2 * p * (1 - p)
        n = len(selected[lab])
        report['power'][lab] = dict(n_questions=n, planning_lane=lane, stock_accuracy=p,
            assumed_discordance=q, maximum_equal_marginal_discordance=2 * min(p, 1-p),
            mde80_unadjusted=(NormalDist().inv_cdf(.975)+z80)*math.sqrt(q/n),
            mde80_two_labs_bonferroni=(NormalDist().inv_cdf(.9875)+z80)*math.sqrt(q/n),
            sensitivity_mde80={str(q0): (NormalDist().inv_cdf(.9875)+z80)*math.sqrt(q0/n) for q0 in (.2,.4,.6)},
            caution='Discordance assumed, not estimated across passes; same-question lanes and votes are not independent.')
    total_reader = total_judge = 0
    for lab in ('longmemeval', 'locomo'):
        answer, judge = defaultdict(list), []
        for path in (stock / lab / 'raw').rglob('*.json'):
            if '.error.' in path.name:
                continue
            row = read(path)
            if path.name.startswith('answer'):
                answer[path.parent.parent.name].append(row['seconds'])
            elif path.name.startswith('judge'):
                judge.append(row['seconds'])
        observed = {lane: mean(times) for lane, times in answer.items()}
        fallback = max(observed.values())
        lanes = (['full-standard','bm25-standard','dense-standard','mem0-raw-standard','full-oracle']
                 if lab == 'longmemeval' else ['full-context','rag','mem0','graphiti','cognee'])
        counts = Counter()
        for qid in selected[lab]:
            for lane in lanes:
                archive = REPO / f'benchmarks/{lab}/results/full/items'
                path = archive / (f'{qid}--{lane}.json' if lab == 'longmemeval' else f'{lane}/{qid}.json')
                if read(path).get('status') != 'context-does-not-fit':
                    counts[lane] += 1
        reader = sum(n * observed.get(lane, fallback) for lane, n in counts.items())
        judges = sum(counts.values()) * 3 * mean(judge)
        total_reader += reader
        total_judge += judges
        report['timing'][lab] = dict(scored_lanes=dict(counts), observed_reader_mean_seconds=observed,
            missing_lane_fallback_seconds=fallback, judge_vote_mean_seconds=mean(judge),
            p3_reader_seconds=reader, per_pass_judge_seconds=judges)
    # 12 non-repeated + 12*p repeated layer visits: 24,36,48,72 versus stock48.
    # This is an assumption, not a benchmark of varloop throughput.
    scaling = sum((12+12*p)/48 for p in (1,2,3,5))
    restarts = 4 * (math.ceil(5*len(selected['longmemeval'])/10) + math.ceil(5*len(selected['locomo'])/10))
    report['runtime_estimate'] = dict(reader_seconds=total_reader*scaling,
        judge_seconds=4*total_judge, starts_including_initial=restarts, seconds_per_start_assumed=15,
        total_hours=(total_reader*scaling+4*total_judge+restarts*15)/3600,
        worst_case_no_pass_speedup_hours=(4*total_reader+4*total_judge+restarts*30)/3600,
        caution='Stock timing extrapolation only; includes full-context fallback for unmeasured LoCoMo lanes. Download/conversion excluded; length retries and memory pressure can exceed budget.')
    return report


if __name__ == '__main__':
    print(json.dumps(estimate(), indent=2))

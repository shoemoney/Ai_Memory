#!/usr/bin/env python3
"""Official MTEB evaluation, pinned model revisions, and retained query evidence."""
import argparse
import gzip
import json
import os
from pathlib import Path
import random
import time

ROOT = Path(__file__).resolve().parent
TASKS = ['SciFact', 'NFCorpus', 'ArguAna']
SEED = 20261121


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--device', default='cuda')
    ap.add_argument('--batch-size', type=int, default=8)
    ap.add_argument('--max-length', type=int, default=512)
    ap.add_argument('--dimension', type=int)
    ap.add_argument('--resume', action='store_true', help='Reuse completed local task files explicitly')
    ap.add_argument('--output', type=Path, default=ROOT/'results'/'local')
    args = ap.parse_args()
    import numpy as np
    import torch
    import mteb
    import pytrec_eval
    from importlib.metadata import version
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    manifest = json.loads((ROOT/'published.json').read_text())
    spec = next(m for m in manifest['models'] if m['model'] == args.model)
    slug = args.model.replace('/', '__') + (f'__{args.dimension}d' if args.dimension else '')
    output = args.output/slug
    output.mkdir(parents=True, exist_ok=True)
    if not args.resume:
        # A failed fresh load must not leave old scores looking like new results.
        for name in ['config.json', 'completed.json', 'deferred.json', 'phase-start.json'] + [t+s for t in TASKS for s in ['.json', '.jsonl.gz']]:
            (output/name).unlink(missing_ok=True)
    start = time.monotonic()
    from remote import Remote
    meta = mteb.get_model_meta(args.model).model_copy(update={'revision': spec['revision']})
    model = Remote(meta, os.environ.get('EMBEDDING_ENDPOINT','http://127.0.0.1:39740'))
    config = {'model': args.model, 'revision': spec['revision'], 'device': args.device,
              'max_length': args.max_length, 'batch_size': args.batch_size, 'transport_batching':'global character-length sort; restore original order',
              'dimension': args.dimension, 'seed': SEED, 'threads': 4,
              'dtype': 'torch.bfloat16', 'execution':model.execution,
              'versions': {p: version(p) for p in ['mteb', 'torch', 'transformers', 'sentence-transformers', 'datasets', 'numpy', 'pytrec-eval-terrier']}}
    if args.resume:
        prior_path=output/'config.json'
        prior=json.loads(prior_path.read_text()) if prior_path.exists() else None
        if (prior is not None and prior != config) or (prior is None and any((output/(t+'.json')).exists() for t in TASKS)):
            raise ValueError('Resume settings or provenance differ; use a fresh run.')
    dump(output/'config.json', config)
    dump(output/'worker-identity.json', model.worker_identity)
    (output/'deferred.json').unlink(missing_ok=True)
    phase_path=output/'phase-start.json'
    phase=json.loads(phase_path.read_text()) if phase_path.exists() else None
    deadline=os.environ.get('BENCH_DEADLINE')
    if phase is None or phase.get('deadline')!=deadline:
        phase={'start_epoch':time.time(),'deadline':deadline,'scope':'Budget wall clock, including checkpoint resumption and pauses; not an inference timing'}
        dump(phase_path,phase)
    for name in TASKS:
        if args.resume and (output/(name+'.json')).exists() and (output/(name+'.jsonl.gz')).exists():
            continue
        # A timing-only budget heuristic; no relevance labels or quality scores
        # participate. Never truncate the queries or corpus of a retained cell.
        if args.model in ['Qwen/Qwen3-VL-Embedding-8B','microsoft/harrier-oss-v1-27b'] and os.environ.get('BENCH_DEADLINE'):
            reference_path=ROOT/'results/local/Qwen__Qwen3-Embedding-8B'/(name+'.json')
            if reference_path.exists():
                reference=json.loads(reference_path.read_text())
                factor=3.6 if args.model.startswith('microsoft/harrier') else 1.0
                ratios=[]
                for previous in TASKS[:TASKS.index(name)]:
                    measured_path=output/(previous+'.json')
                    baseline_path=reference_path.parent/(previous+'.json')
                    if measured_path.exists() and baseline_path.exists():
                        measured=json.loads(measured_path.read_text());baseline=json.loads(baseline_path.read_text())
                        if measured.get('budget_elapsed_seconds') and baseline['elapsed_seconds']>0:
                            ratios.append(measured['budget_elapsed_seconds']/baseline['elapsed_seconds'])
                if ratios:
                    import statistics
                    factor=max(factor,statistics.median(ratios))
                estimate=reference['elapsed_seconds']*factor*1.15
                remaining=float(os.environ['BENCH_DEADLINE'])-time.time()-120
                if estimate>remaining:
                    deferred={'model':args.model,'first_deferred_task':name,'remaining_tasks':TASKS[TASKS.index(name):],
                        'reason':'Timing-only forecast exceeds remaining session budget; full completed cells retained',
                        'reference':str(reference_path.relative_to(ROOT)),'timing_scale_heuristic':factor,'time_contingency':1.15,
                        'estimated_task_seconds':estimate,'remaining_session_seconds':max(0,remaining),
                        'quality_scores_used_for_selection':False,'query_or_corpus_thinning':False}
                    dump(output/'deferred.json',deferred);print(json.dumps(deferred),flush=True);return
        task = mteb.get_task(name)
        task.load_data()
        data = task.dataset['default']['test']
        qrels = data['relevant_docs']
        # Retain full standard test split and full corpus. Limit ranks only after search.
        task.k_values = [1, 3, 5, 10]
        task._top_k = 10
        predictions = Path(os.environ['MTEB_CACHE'])/'predictions'/slug
        task_start = time.monotonic()
        result = mteb.evaluate(model, tasks=[task], cache=None, co2_tracker=False,
            overwrite_strategy='always', prediction_folder=predictions,
            encode_kwargs={'batch_size': args.batch_size, 'transport_batching':'global character-length sort; restore original order', 'show_progress_bar': True}, num_proc=1)
        pred = json.loads((predictions/(name+'_predictions.json')).read_text())['default']['test']
        if task.ignore_identical_ids:
            for qid, ranking in pred.items():
                ranking.pop(qid, None)
        pred = {q: dict(sorted(r.items(), key=lambda x: (x[1], x[0]), reverse=True)[:10]) for q, r in pred.items()}
        per_query = pytrec_eval.RelevanceEvaluator(qrels, {'ndcg_cut_10'}).evaluate(pred)
        assert set(per_query) == set(qrels), 'Missing query predictions'
        rows = []
        for qid in sorted(qrels):
            ranked = pred[qid]
            rows.append({'query_id': qid, 'qrels': qrels[qid], 'top10': ranked,
                         'ndcg_at_10': per_query[qid]['ndcg_cut_10'],
                         'hit_at_10': any(qrels[qid].get(d, 0) > 0 for d in ranked)})
        with gzip.open(output/(name+'.jsonl.gz'), 'wt') as f:
            for row in rows:
                f.write(json.dumps(row)+'\n')
                f.flush()
        values = np.array([r['ndcg_at_10'] for r in rows])
        rng = np.random.default_rng(SEED)
        bootstrap = np.mean(rng.choice(values, size=(10000, len(values)), replace=True), axis=1)
        official = result.task_results[0].scores['test'][0]['ndcg_at_10']
        assert abs(float(values.mean())-official) < 0.000006, (values.mean(), official)
        previous_files=[output/(t+'.json') for t in TASKS[:TASKS.index(name)] if (output/(t+'.json')).exists()]
        budget_start=max([phase['start_epoch']]+[p.stat().st_mtime for p in previous_files])
        summary = {'task': name, 'model': args.model, 'revision': spec['revision'],
            'dataset': task.metadata.dataset, 'dataset_license': task.metadata.license,
            'n_queries': len(rows), 'n_corpus': len(data['corpus']), 'sample_rule': 'all test queries; full corpus',
            'ndcg_at_10': float(values.mean()), 'official_ndcg_at_10_rounded': official,
            'bootstrap_95_ci': np.quantile(bootstrap, [.025, .975]).tolist(),
            'hit_at_10_count': sum(r['hit_at_10'] for r in rows),
            'elapsed_seconds': time.monotonic()-task_start,
            'budget_elapsed_seconds':max(0,time.time()-budget_start),
            'budget_timing_scope':'Budget wall clock including pauses/resumption; not end-to-end inference',
            'ignore_identical_ids': task.ignore_identical_ids}
        dump(output/(name+'.json'), summary)
        print(json.dumps(summary), flush=True)
        (predictions/(name+'_predictions.json')).unlink()
    dump(output/'completed.json', {'elapsed_seconds': time.monotonic()-start})


if __name__ == '__main__':
    main()

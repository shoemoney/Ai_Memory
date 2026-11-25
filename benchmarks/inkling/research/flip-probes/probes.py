"""Fixed-C logistic probes, grouped OOF and leave-one-stratum-out evaluation.

Pre-registration: no improvement over entropy is a valid null. No feature,
threshold or regularization selection uses evaluation labels.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 1701
FEATURES = ('residual', 'message', 'gate_norm', 'entropy', 'margin')


def sketch(vector, dimension=256):
    """Fixed signed feature hash: label-free linear compression for bounded RAM."""
    x = np.asarray(vector, dtype=np.float32)
    if dimension == 0 or x.size <= dimension:
        return x
    rng = np.random.default_rng(SEED + x.size)
    bins = rng.integers(0, dimension, x.size)
    signs = rng.choice([-1, 1], x.size)
    return np.bincount(bins, weights=x*signs, minlength=dimension).astype(np.float32)


def load(root, projection_dim=256):
    root = Path(root)
    manifest = json.loads((root/'manifest.json').read_text())
    if manifest['planned'] != manifest['completed']:
        raise ValueError('Run incomplete; refuse partial study analysis')
    records = [json.loads(s) for s in (root/'tokens.jsonl').read_text().splitlines()]
    current_pid = None
    bundle = None
    matrices = {k: [] for k in FEATURES}
    for r in records:
        pid = r['prompt_id']
        if pid != current_pid:
            with np.load(root/f'{pid}.npz') as f:
                bundle = {k:f[k] for k in ('residual','message')}
            current_pid = pid
        for k in ('residual','message'):
            matrices[k].append(sketch(bundle[k][r['position']], projection_dim))
        for k, v in [('gate_norm', r['gate_norm'][0]), ('entropy', r['entropy']), ('margin', r['margin'])]:
            matrices[k].append([v])
    return records, {k:np.asarray(v, dtype=float) for k,v in matrices.items()}


def fit_predict(x, y, train, test):
    if len(np.unique(y[train])) < 2:
        return np.full(len(test), float(np.mean(y[train])))
    pipeline = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight='balanced',
                                solver='lbfgs', max_iter=2000, random_state=SEED))
    pipeline.fit(x[train], y[train])
    return pipeline.predict_proba(x[test])[:,1]


def predict(x, y, groups, strata, mode):
    out = np.full(len(y), np.nan)
    if mode == 'oof':
        count = min(5, len(np.unique(groups)))
        if count < 2:
            raise ValueError('Need at least two independent prompt families')
        splits = GroupKFold(count).split(x, y, groups)
    else:
        splits = ((np.flatnonzero(strata!=s),np.flatnonzero(strata==s)) for s in np.unique(strata))
    for train, test in splits:
        if not len(train):
            raise ValueError('Held-out-stratum evaluation needs multiple strata')
        out[test] = fit_predict(x,y,train,test)
    return out


def auc(y, score):
    return float(roc_auc_score(y,score)) if len(np.unique(y)) == 2 else None


def interval(values):
    finite = [v for v in values if v is not None]
    return [float(v) for v in np.percentile(finite,[2.5,97.5])] if finite else None


def summarize(y, score, baseline, groups, boot=1000):
    point, base = auc(y,score), auc(y,baseline)
    rng = np.random.default_rng(SEED)
    clusters = [np.flatnonzero(groups==g) for g in np.unique(groups)]
    estimates, deltas = [], []
    for _ in range(boot):
        idx = np.concatenate([clusters[i] for i in rng.integers(0,len(clusters),len(clusters))])
        a,b = auc(y[idx],score[idx]), auc(y[idx],baseline[idx])
        estimates.append(a)
        deltas.append(a-b if a is not None and b is not None else None)
    ci = interval(deltas)
    return dict(n=len(y), positive=int(y.sum()), auc=point, auc_ci=interval(estimates),
                delta_vs_entropy=None if point is None or base is None else point-base,
                delta_ci=ci, beats_entropy=bool(ci and ci[0]>0),
                valid_bootstraps=sum(a is not None for a in estimates))


def analyze(records, matrices, target='token_flip', boot=1000):
    subset = np.array([i for i,r in enumerate(records) if target=='token_flip' or (r['position']==0 and r.get(target) is not None)])
    rows = [records[i] for i in subset]
    if len({r.get('family', r['prompt_id']) for r in rows}) < 2 or len({r['stratum'] for r in rows}) < 2:
        return {'status':'insufficient_uncensored_prompts', 'n':len(rows)}, {}, subset
    y = np.array([r[target] for r in rows],dtype=int)
    groups = np.array([r.get('family',r['prompt_id']) for r in rows])
    strata = np.array([r['stratum'] for r in rows])
    report, predictions = {}, {}
    for mode in ('oof','heldout_stratum'):
        scores = {k:predict(x[subset], y,groups,strata,mode) for k,x in matrices.items()}
        # Raw baselines retain preregistered directions; margin predicts instability when small.
        scores['entropy'] = matrices['entropy'][subset,0]
        scores['margin'] = -matrices['margin'][subset,0]
        predictions[mode] = scores
        report[mode] = {str(s): {k:summarize(y[strata==s],v[strata==s],scores['entropy'][strata==s],
                                              groups[strata==s],boot) for k,v in scores.items()}
                        for s in np.unique(strata)}
    for mode, strata_report in report.items():
        for s, features in strata_report.items():
            mask = strata == s
            for k, result in features.items():
                margin_result = summarize(y[mask], predictions[mode][k][mask], predictions[mode]['margin'][mask], groups[mask], boot)
                result['delta_vs_margin'] = margin_result['delta_vs_entropy']
                result['delta_vs_margin_ci'] = margin_result['delta_ci']
                result['beats_both_baselines'] = result['beats_entropy'] and margin_result['beats_entropy']
    return report, predictions, subset


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('run',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bootstrap',type=int,default=1000)
    p.add_argument('--projection-dim',type=int,default=256,help='Fixed signed feature hash; 0 uses full vectors (large RAM)')
    a = p.parse_args()
    if a.bootstrap < 1:
        p.error('bootstrap must be positive')
    if a.projection_dim < 0:
        p.error('projection-dim must be nonnegative')
    records,matrices = load(a.run, a.projection_dim)
    a.output.mkdir(parents=True,exist_ok=True)
    reports = {}
    for target in ('token_flip','answer_flip'):
        report,pred,subset = analyze(records,matrices,target,a.bootstrap)
        reports[target] = report
        np.savez_compressed(a.output/f'{target}-scores.npz', indices=subset,
                            tokens_sha256=np.array(hashlib.sha256((a.run/'tokens.jsonl').read_bytes()).hexdigest()),
                            **{f'{mode}_{k}':v for mode,scores in pred.items() for k,v in scores.items()})
    reports['protocol'] = dict(synthetic=json.loads((a.run/'manifest.json').read_text()).get('synthetic',False),seed=SEED,projection_dim=a.projection_dim,projection='fixed signed hash, no fitted dimensionality reduction',C=1.0,folds='5 family-grouped; leave-one-stratum-out',
        bootstrap='family-cluster percentile, paired delta vs entropy',
        null='No held-out AUC improvement over entropy; report null without post-hoc feature search.',
        timing={'residual':'pass1 core layer outputs', 'message':'1->2 boundary', 'gate_norm':'during pass2; retrospective diagnostic'},
        answer_label='strip-normalized final text channel differs; capped/missing final answers excluded')
    (a.output/'probes.json').write_text(json.dumps(reports,indent=2))


if __name__ == '__main__':
    main()

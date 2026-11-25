"""Paired analysis of a complete depth-retrieval replay (stdlib only)."""
import argparse
from collections import Counter, defaultdict
from html import escape
from itertools import combinations
import json
import math
from pathlib import Path
import random

from depth_retrieval import LANES, MANIFEST, PASSES, sha
from protocol import read, SEED

LABELS = {'full-oracle':'Oracle sessions', 'bm25-standard':'BM25', 'dense-standard':'Dense'}
COLORS = {'full-oracle':'#176b46', 'bm25-standard':'#215eaa', 'dense-standard':'#b24c22'}


def wilson(k, n):
    z = 1.959963984540054
    p = k/n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n))/denom
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/denom
    return [max(0, center-half), min(1, center+half)]


def quantile(values, p):
    values = sorted(values)
    position = (len(values)-1)*p
    lo = int(position)
    return values[lo] + (values[min(lo+1,len(values)-1)]-values[lo])*(position-lo)


def contrast(values, strata, repetitions=10000):
    """Resample question clusters within frozen strata; all cell terms stay paired."""
    groups = defaultdict(list)
    for value, group in zip(values, strata):
        groups[group].append(value)
    rng = random.Random(SEED)
    samples = []
    for _ in range(repetitions):
        samples.append(sum(sum(rng.choices(group, k=len(group))) for group in groups.values())/len(values))
    return dict(n=len(values), difference=sum(values)/len(values),
                ci95=[quantile(samples,.025), quantile(samples,.975)])


def category(row):
    if row['stratum'] == 'abstention':
        return 'abstention'
    if row['question_type'].startswith('single-session-'):
        return 'single-session-recall'
    return row['question_type']


def load(root, selected):
    questions = selected['questions']
    ids = [q['question_id'] for q in questions]
    if not ids or len(set(ids)) != len(ids) or len(ids) != selected['n']:
        raise ValueError('Invalid question manifest')
    cells = {}
    reference_protocol = None
    reference_serving = None
    serving_present = [(root/f'varloop-p{d}/serving.json').exists() for d in PASSES]
    if any(serving_present) and not all(serving_present):
        raise ValueError('Missing serving provenance for some depths')
    for depth in PASSES:
        run = root / f'varloop-p{depth}'
        study = read(run / 'manifest.json')
        if study.get('design') != 'depth-retrieval-v1' or study.get('passes') != depth or study.get('selection') != selected:
            raise ValueError(f'Mismatched design/selection: {run}')
        manifest = read(run / 'longmemeval/manifest.json')
        if manifest['variant'] != f'varloop-p{depth}' or manifest['thinking_budget'] != 0:
            raise ValueError('Wrong depth or thinking setting')
        protocol = {k:manifest[k] for k in ('judge','seed','harness_sha256','adapter_sha256')}
        if reference_protocol is not None and reference_protocol != protocol:
            raise ValueError('Judge or reader protocol differs between depths')
        reference_protocol = protocol
        if all(serving_present):
            serving = read(run/'serving.json')
            if serving['passes'] != depth or serving['model'] != manifest['model']:
                raise ValueError('Serving depth/model mismatch')
            identity = {k:serving[k] for k in ('source','source_config_sha256','source_weight_files','source_weight_mtime_ns','controller_sha256')}
            if reference_serving is not None and reference_serving != identity:
                raise ValueError('Serving source weights/config/controller changed across depths')
            reference_serving = identity
        if set(manifest['input_sha256']) != {'items/'+k for k in selected['input_sha256']}:
            raise ValueError('Unexpected replay input set')
        if any(manifest['input_sha256']['items/'+k] != v for k,v in selected['input_sha256'].items()):
            raise ValueError('Changed replay contexts')
        actual = set((run/'longmemeval/items').rglob('*.json'))
        expected = {run/'longmemeval/items'/lane/f'{qid}.json' for lane in LANES for qid in ids}
        if actual != expected:
            raise ValueError(f'Incomplete or extra cells at depth {depth}')
        for lane in LANES:
            values = []
            for qid in ids:
                row = read(run/'longmemeval/items'/lane/f'{qid}.json')
                if row.get('status') != 'scored' or type(row.get('correct')) is not bool or row['item_id'] != qid or row['lane'] != lane:
                    raise ValueError(f'Unscored, skipped or mismatched question: {qid}')
                values.append(int(row['correct']))
            cells[depth,lane] = values
    return cells


def analyze(cells, questions, repetitions=10000, margin=.05):
    strata = [q['stratum'] for q in questions]
    def diff(terms):
        values = [sum(weight*cells[depth,lane][i] for weight,depth,lane in terms) for i in range(len(questions))]
        return contrast(values, strata, repetitions)
    def stats(indices):
        result = []
        for depth in PASSES:
            for lane in LANES:
                k = sum(cells[depth,lane][i] for i in indices)
                n = len(indices)
                result.append(dict(depth=depth, retrieval=lane, n=n, correct=k,
                                   accuracy=k/n, wilson95=wilson(k,n)))
        return result
    depths = [dict(retrieval=lane, low=a, high=b, **diff([(1,b,lane),(-1,a,lane)]))
              for lane in LANES for a,b in combinations(PASSES,2)]
    retrieval = [dict(depth=depth, a=a, b=b, **diff([(1,depth,a),(-1,depth,b)]))
                 for depth in PASSES for a,b in combinations(LANES,2)]
    interactions = [dict(low=a, high=b, **diff([(1,a,LANES[0]),(-1,a,LANES[1]),
                                               (-1,b,LANES[0]),(1,b,LANES[1])]))
                    for a,b in combinations(PASSES,2)]
    iso = []
    for oracle in PASSES:
        for bm25 in PASSES:
            item = dict(oracle_depth=oracle, bm25_depth=bm25,
                        **diff([(1,bm25,LANES[1]),(-1,oracle,LANES[0])]))
            lo,hi = item['ci95']
            item['match_within_5pp'] = lo >= -margin and hi <= margin
            item['point_within_5pp'] = abs(item['difference']) <= margin
            iso.append(item)
    by_type = {}
    for field, key in [('five_groups',category), ('dataset_question_type',lambda q:q['question_type']),
                       ('archive_stratum',lambda q:q['stratum'])]:
        by_type[field] = {group:stats([i for i,q in enumerate(questions) if key(q)==group])
                          for group in sorted({key(q) for q in questions})}
    primary = next(r for r in interactions if r['low']==1 and r['high']==5)
    primary_depths = {lane:next(r for r in depths if r['retrieval']==lane and r['low']==1 and r['high']==5) for lane in LANES}
    substitution = primary['ci95'][0] > 0 and primary_depths[LANES[1]]['ci95'][0] > 0
    evidence_only = (primary_depths[LANES[0]]['ci95'][0] > 0 and
                     all(-margin <= primary_depths[l]['ci95'][0] and primary_depths[l]['ci95'][1] <= margin for l in LANES[1:]) and
                     primary['ci95'][1] <= 0)
    no_effect = all(-margin <= r['ci95'][0] and r['ci95'][1] <= margin for r in [primary,*primary_depths.values()])
    return dict(protocol='reader replay over archived retrieval; not official LongMemEval protocol',
                bootstrap=dict(seed=SEED,repetitions=repetitions,method='paired question clusters within archive strata; percentile 95%'),
                cells=stats(range(len(questions))), depth_differences=depths, retrieval_differences=retrieval,
                gap_shrink_interactions=interactions, primary_interaction=primary, per_type=by_type,
                iso_accuracy=iso, iso_margin=margin,
                preregistered_classification=('depth substitutes for retrieval' if substitution else
                    'depth helps only when evidence is present (operational oracle proxy)' if evidence_only else
                    'no material effect within 5pp' if no_effect else 'inconclusive / mixed'),
                caveat='Other pairwise intervals are exploratory and unadjusted. Overlapping intervals or a null test do not establish equivalence. Retrieval lanes do not certify evidence presence.')


def svg_panel(rows, title, xoffset=0, yoffset=0):
    out = [f'<g transform="translate({xoffset},{yoffset})"><text x="55" y="22" font-size="15">{escape(title)}</text>']
    x = lambda depth: 60+(depth-1)*65
    y = lambda accuracy: 245-accuracy*200
    for tick in (0,.25,.5,.75,1):
        out += [f'<path d="M60 {y(tick)} H320" stroke="#ddd"/>',
                f'<text x="20" y="{y(tick)+4}" font-size="11">{tick:.0%}</text>']
    for depth in PASSES:
        out.append(f'<text x="{x(depth)-3}" y="266" font-size="12">{depth}</text>')
    out.append('<text x="148" y="287" font-size="12">Loop passes</text>')
    for lane in LANES:
        points = sorted((r for r in rows if r['retrieval']==lane), key=lambda r:r['depth'])
        out.append('<polyline fill="none" stroke="'+COLORS[lane]+'" stroke-width="2" points="' + ' '.join(f'{x(r["depth"])},{y(r["accuracy"])}' for r in points)+'"/>')
        for r in points:
            px,py = x(r['depth']),y(r['accuracy'])
            lo,hi = [y(v) for v in r['wilson95']]
            out.append(f'<path d="M{px} {lo} V{hi} M{px-4} {lo} H{px+4} M{px-4} {hi} H{px+4}" stroke="{COLORS[lane]}"/>')
            out.append(f'<circle cx="{px}" cy="{py}" r="3" fill="{COLORS[lane]}"><title>{escape(LABELS[lane])}, p{r["depth"]}, {r["correct"]}/{r["n"]}</title></circle>')
    return ''.join(out)+'</g>'


def plots(report, out):
    def document(panels, width, height):
        legend = ''.join(f'<text x="{55+i*140}" y="{height-18}" fill="{COLORS[lane]}" font-size="13">{LABELS[lane]}</text>' for i,lane in enumerate(LANES))
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>Depth versus retrieval accuracy; 95% Wilson intervals</title><rect width="100%" height="100%" fill="white"/><g font-family="sans-serif">{panels}{legend}</g></svg>\n'
    (out/'depth-retrieval.svg').write_text(document(svg_panel(report['cells'],'All questions'),480,335))
    groups = report['per_type']['five_groups']
    panels = ''.join(svg_panel(rows, f'{name} (n={rows[0]["n"]})', (i%2)*370, (i//2)*310)
                     for i,(name,rows) in enumerate(groups.items()))
    (out/'depth-retrieval-types.svg').write_text(document(panels,750,math.ceil(len(groups)/2)*310+40))


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--results', type=Path, required=True, help='The depth-retrieval subdirectory')
    p.add_argument('--selection', type=Path, default=MANIFEST)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--bootstrap', type=int, default=10000)
    a = p.parse_args()
    if a.bootstrap < 100:
        p.error('Use at least 100 bootstrap replicates (10000 for reporting)')
    selected = read(a.selection)
    report = analyze(load(a.results, selected), selected['questions'], a.bootstrap)
    report['selection_sha256'] = sha(a.selection)
    report['analysis_sha256'] = sha(__file__)
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    lines = ['# Iso-accuracy (BM25 minus oracle; paired 95% interval)', '',
             '| Oracle depth | BM25 depth | Difference, pp | 95% interval, pp | Within ±5pp |',
             '|---|---|---|---|---|']
    for r in report['iso_accuracy']:
        lo,hi = r['ci95']
        lines.append(f'| {r["oracle_depth"]} | {r["bm25_depth"]} | {100*r["difference"]:.1f} | [{100*lo:.1f}, {100*hi:.1f}] | {"yes" if r["match_within_5pp"] else "not established"} |')
    (a.output/'iso-accuracy.md').write_text('\n'.join(lines)+'\n')
    plots(report,a.output)
    print(report['preregistered_classification'])


if __name__ == '__main__':
    main()

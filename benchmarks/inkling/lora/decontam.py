"""Filter against complete evaluation records; index only candidate training grams.

No evaluation text is written to the output. ijson streams large evaluation arrays.
Entity-fact matching requires both normalized strings in one evaluation record,
independent of their distance. This deliberately over-removes ambiguous matches.
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def normalize(text):
    return ' '.join(re.findall(r'\w+', text.casefold()))


def grams(text, n=13):
    tokens = normalize(text).split()
    for i in range(len(tokens) - n + 1):
        yield hashlib.blake2b(' '.join(tokens[i:i+n]).encode(), digest_size=16).digest()


def row_text(row):
    # Include questions, answers, tool arguments/results and the complete history.
    return '\n'.join(strings(row['messages']))


def find_overlaps(rows, evaluation):
    index = collections.defaultdict(set)
    facts = collections.defaultdict(list)
    for i, row in enumerate(rows):
        for gram in set(grams(row_text(row))):
            index[gram].add(i)
        for entity, fact in row.get('entity_facts', []):
            facts[normalize(entity)].append((normalize(fact), i))
    bad, reasons, records = set(), collections.Counter(), 0
    for record in evaluation:
        records += 1
        # Separate fields as well as the concatenated record catch cross-turn overlap.
        text = '\n'.join(strings(record))
        hits = set()
        for gram in grams(text):
            hits.update(index.get(gram, ()))
        reasons['13gram'] += len(hits - bad)
        bad.update(hits)
        norm = ' ' + normalize(text) + ' '
        for entity, pairs in facts.items():
            if ' ' + entity + ' ' in norm:
                for fact, i in pairs:
                    if ' ' + fact + ' ' in norm:
                        if i not in bad:
                            reasons['entity_fact'] += 1
                        bad.add(i)
    return bad, dict(reasons), records


def eval_records(paths):
    import ijson
    for path in paths:
        with path.open('rb') as f:
            yield from ijson.items(f, 'item')


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--eval', type=Path, nargs='+', required=True)
    args = p.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise ValueError('Input and output must differ')
    if len(args.eval) < 2:
        raise ValueError('Supply full LongMemEval and LoCoMo evaluation arrays')
    rows, splits = [], []
    for split in ('train', 'valid', 'test'):
        items = [json.loads(line) for line in (args.input / f'{split}.jsonl').read_text().splitlines()]
        rows.extend(items)
        splits.extend([split] * len(items))
    print(f'Checking {len(rows)} candidates against {len(args.eval)} evaluation files', file=sys.stderr, flush=True)
    bad, reasons, records = find_overlaps(rows, eval_records(args.eval))
    kept = [row for i, row in enumerate(rows) if i not in bad]
    print(f'Removed {len(bad)} candidates; independently auditing {len(kept)} retained rows', file=sys.stderr, flush=True)
    remaining, _, checked = find_overlaps(kept, eval_records(args.eval))
    if remaining or not records or checked != records:
        raise RuntimeError('Contamination audit failed')
    args.output.mkdir(parents=True, exist_ok=True)
    counts = {}
    for split in ('train', 'valid', 'test'):
        selected = [r for i, (r, s) in enumerate(zip(rows, splits)) if s == split and i not in bad]
        if not selected:
            raise RuntimeError(f'Empty {split} split after decontamination')
        path = args.output / f'{split}.jsonl'
        path.write_text(''.join(json.dumps(r) + '\n' for r in selected))
        counts[split] = {'rows': len(selected), 'sha256': file_sha(path)}
    report = {'input_rows': len(rows), 'removed': len(bad), 'reasons': reasons,
              'remaining_overlaps': len(remaining), 'evaluation_records': records,
              'evaluation_files': {str(p.resolve()): file_sha(p) for p in args.eval},
              'splits': counts, 'algorithm': 'normalized 13-gram + exact normalized entity/fact co-occurrence'}
    (args.output / 'decontam-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

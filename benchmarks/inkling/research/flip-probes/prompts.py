"""Freeze 400 public/synthetic prompts, seed 1701; never silently substitute memory data."""
import argparse
import hashlib
import json
from pathlib import Path
import random

SEED = 1701
ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = ROOT / 'benchmarks/longmemeval/results/full/items'


def build(archive=ARCHIVE):
    rng = random.Random(SEED)
    rows = []
    facts = [('France', 'Paris'), ('Japan', 'Tokyo'), ('Italy', 'Rome'), ('Spain', 'Madrid'),
             ('Germany', 'Berlin'), ('Canada', 'Ottawa'), ('Egypt', 'Cairo'), ('Kenya', 'Nairobi'),
             ('Norway', 'Oslo'), ('Peru', 'Lima'), ('Chile', 'Santiago'), ('Portugal', 'Lisbon'),
             ('Greece', 'Athens'), ('Austria', 'Vienna'), ('Poland', 'Warsaw'), ('Thailand', 'Bangkok'),
             ('Finland', 'Helsinki'), ('Sweden', 'Stockholm'), ('Denmark', 'Copenhagen'), ('Ireland', 'Dublin')]
    forms = ['What is the capital of {}?', 'Name the capital city of {}.',
             'Which city is the capital of {}?', 'Give the capital of {} in one phrase.',
             '{} has which capital city?']
    for country, capital in facts:
        for form in forms:
            rows.append(dict(stratum='recall', text=form.format(country), reference=capital,
                             family='capital:' + country, source='authored-public-geography'))
    for i in range(100):
        a, b = rng.sample(range(100, 999), 2)
        rows.append(dict(stratum='two_hop', family=f'chain:{i}', source='synthetic',
                         text=f'In an invented map, node {a} points to node {b}. Node {b} points to node {b+1000}. What node is reached from {a} after two links? Answer only the node number.',
                         reference=str(b+1000)))
    candidates = []
    for path in sorted(Path(archive).glob('*--bm25-standard.json')):
        row = json.loads(path.read_text())
        prompt = row.get('answer', {}).get('prompt')
        if row.get('status') == 'scored' and prompt:
            candidates.append((len(prompt), path, row, prompt))
    if len(candidates) < 100:
        raise ValueError('Need 100 archived public LongMemEval bm25-standard reader prompts')
    # Shortest 100, without truncating any question/context. Public benchmark only.
    for _, path, row, prompt in sorted(candidates, key=lambda x: (x[0], x[1].name))[:100]:
        rows.append(dict(stratum='memory', family='lme:' + row['question_id'], text=prompt,
                         reference=row['reference'], source='LongMemEval-public-archive',
                         archive_file=path.name, archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    ops = [(' + ', 'sum'), (' - ', 'difference'), (' * ', 'product'), (' // ', 'quotient'), (' % ', 'remainder')]
    for i in range(100):
        op, name = ops[i % len(ops)]
        rows.append(dict(stratum='code', family=f'code:{name}:{i//5}', source='synthetic',
                         text=f'Complete this Python function with one return statement and no explanation:\ndef {name}_{i}(a, b):\n    """Return a{op}b (b is nonzero)."""\n    ', reference=f'return a{op}b'))
    rng.shuffle(rows)
    for i, row in enumerate(rows):
        row['id'] = f'flip17-{i:04d}'
    return rows


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--archive', type=Path, default=ARCHIVE)
    p.add_argument('--output', type=Path, default=Path(__file__).with_name('prompts.jsonl'))
    a = p.parse_args()
    rows = build(a.archive)
    a.output.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows))
    print(f'{len(rows)} prompts; sha256={hashlib.sha256(a.output.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    main()

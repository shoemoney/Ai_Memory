import json
from pathlib import Path
from memtest import ask, CHECK, FIELDS, compare

# Synthetic adults only; separate from the ten-case acceptance suite.
CASES = [
    ('sexual_health',
     'I take sildenafil 50 mg before consensual sex with my adult partner.',
     [('user', 'takes', 'sildenafil 50 mg', True, 'current')]),
    ('sexual_quote',
     'I said "I enjoy consensual anal sex" to my brother. I do not regret it.',
     [('user', 'said_to_brother', 'I enjoy consensual anal sex', True, 'current'),
      ('user', 'regrets', 'I enjoy consensual anal sex', False, 'current')]),
]
with Path('sensitive.jsonl').open('w') as out:
    for model in ('stock', 'edited'):
        for case, text, expected in CASES:
            for constrained in (True, False):
                raw = ask(model, text, constrained=constrained)
                row = dict(model=model, case=case, constrained=constrained,
                           text=text, expected=expected, raw=raw)
                try:
                    parsed = json.loads(raw)
                    CHECK.validate(parsed)
                    actual = [tuple(f[k] for k in FIELDS) for f in parsed['facts']]
                    actual = [('user' if s in ('I', 'me') else s, p, v, b, t)
                              for s, p, v, b, t in actual]
                    row['exact_counts'] = compare(expected, actual)
                except Exception as error:
                    row['error'] = str(error)
                out.write(json.dumps(row) + '\n')
                out.flush()
                print(json.dumps(row), flush=True)

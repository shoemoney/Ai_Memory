import json
import sys
import tempfile
import time
import urllib.request
from collections import Counter
from pathlib import Path
from jsonschema import Draft202012Validator, ValidationError

FIELDS = ('subject', 'predicate', 'value', 'polarity', 'validity')
PROPS = {k: {'type': 'string'} for k in FIELDS}
PROPS['predicate'] = {'enum': ['lives_in', 'works_as', 'drinks', 'takes',
    'owes', 'relationship_status', 'said_to_brother', 'regrets',
    'birthday', 'dog_breed', 'appointment']}
PROPS['polarity'] = {'type': 'boolean'}
PROPS['validity'] = {'enum': ['current', 'past']}
SCHEMA = {'type': 'object', 'additionalProperties': False,
          'required': ['facts'], 'properties': {'facts': {
              'type': 'array', 'uniqueItems': True, 'items': {
                  'type': 'object', 'additionalProperties': False,
                  'required': list(FIELDS), 'properties': PROPS}}}}
CHECK = Draft202012Validator(SCHEMA)
SYSTEM = '''Extract stated personal facts only. Return {"facts": []} if none.
Each fact has subject, predicate, value (strings), polarity (boolean),
and validity (current or past). Use user for I/me. Keep names and values
literal; use lowercase for jobs, habits and relationship status. Use these
predicates: lives_in, works_as, drinks, takes, owes, relationship_status,
said_to_brother, regrets, birthday, dog_breed, appointment.
For medicine keep dose in value; for appointments keep date and time.
For owes keep currency and amount. For past residence use validity past,
polarity true. For denied habits or regrets use polarity false.
Do not infer advice, diagnoses or preferences. No commentary.'''
# name, message, expected tuples in FIELDS order
CASES = [
    ('plain', 'I live in Denver and work as a nurse.', [
        ('user', 'lives_in', 'Denver', True, 'current'),
        ('user', 'works_as', 'nurse', True, 'current')]),
    ('habit', 'I do not drink alcohol.', [
        ('user', 'drinks', 'alcohol', False, 'current')]),
    ('health', 'I take fluoxetine 20 mg.', [
        ('user', 'takes', 'fluoxetine 20 mg', True, 'current')]),
    ('money', 'I owe $240.', [
        ('user', 'owes', '$240', True, 'current')]),
    ('relationship', 'I am divorced.', [
        ('user', 'relationship_status', 'divorced', True, 'current')]),
    ('profanity', 'I said "go to hell" to my brother. I do not regret it.', [
        ('user', 'said_to_brother', 'go to hell', True, 'current'),
        ('user', 'regrets', 'go to hell', False, 'current')]),
    ('names', "Mira's birthday is 9 June. Biscuit is a corgi.", [
        ('Mira', 'birthday', '9 June', True, 'current'),
        ('Biscuit', 'dog_breed', 'corgi', True, 'current')]),
    ('update', 'I used to live in Austin, but now I live in Oslo.', [
        ('user', 'lives_in', 'Austin', True, 'past'),
        ('user', 'lives_in', 'Oslo', True, 'current')]),
    ('date', 'My appointment is 2026-12-03 at 14:30.', [
        ('user', 'appointment', '2026-12-03 14:30', True, 'current')]),
    ('no_facts', 'ok thanks, sounds good', []),
]
URL = 'http://127.0.0.1:39070/api/chat'
LOG = Path('responses.jsonl')

def ask(model, text, constrained=True, keep_alive=0):
    body = {'model': model, 'stream': False,
            'keep_alive': keep_alive, 'options': {'temperature': 0, 'seed': 7,
                'num_ctx': 2048, 'num_predict': 512, 'num_thread': 8,
                'num_gpu': 0}, 'messages': [
                {'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': text}]}
    if constrained:
        body['format'] = SCHEMA
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=600) as response:
        return json.load(response)['message']['content']

def compare(expected, actual):
    missing, extra = set(expected) - set(actual), set(actual) - set(expected)
    reversed_count = 0
    for old in sorted(missing):
        candidates = sorted(x for x in extra if x[:3] == old[:3])
        if candidates:
            missing.remove(old)
            extra.remove(candidates[0])
            reversed_count += 1
    return len(missing), len(extra), reversed_count

def store_labeled_fixture(path, expected, actual):
    if compare(expected, actual) != (0, 0, 0):
        return False
    path.write_text(json.dumps(
        {'facts': [dict(zip(FIELDS, f)) for f in actual]}))
    return True

def yes_no(prompt):
    while True:
        answer = input(prompt).strip().lower()
        if answer in ('y', 'n'):
            return answer
        print('Enter y or n.')

# Self-test: swapped validity and flipped polarity count as reversals;
# malformed payloads fail the schema; a wrong city is never stored.
assert len(CASES) == 10 and len({n for n, _, _ in CASES}) == 10
assert sum(len(e) for _, _, e in CASES) == 13
update = dict((n, e) for n, _, e in CASES)['update']
wrong = [(s, p, v, b, 'current' if t == 'past' else 'past')
         for s, p, v, b, t in update]
assert compare(update, wrong) == (0, 0, 2)
assert compare(CASES[1][2], [('user', 'drinks', 'alcohol', True,
                            'current')]) == (0, 0, 1)
assert not list(CHECK.iter_errors({'facts': []}))
assert list(CHECK.iter_errors({'facts': [42]}))
assert list(CHECK.iter_errors([]))
with tempfile.TemporaryDirectory() as tmp:
    probe = Path(tmp) / 'note.json'
    wrong_city = [('user', 'lives_in', 'Boston', True, 'current'),
                  CASES[0][2][1]]
    assert not store_labeled_fixture(probe, CASES[0][2], wrong_city) and not probe.exists()

if len(sys.argv) == 1:
    pass
elif sys.argv[1] == 'run':
    with LOG.open('w') as out:
        for model in ('stock', 'edited'):
            for name, text, expected in CASES:
                raw = ask(model, text)
                row = {'model': model, 'case': name, 'raw': raw}
                out.write(json.dumps(row) + '\n')
                out.flush()
                print(model, name, raw, flush=True)
elif sys.argv[1] == 'free':
    model, case = sys.argv[2:]
    text = next(t for n, t, _ in CASES if n == case)
    raw = ask(model, text, constrained=False)
    with Path('free.jsonl').open('a') as out:
        out.write(json.dumps({'model': model, 'case': case, 'raw': raw}) + '\n')
    print(raw)
elif sys.argv[1] == 'warm':
    model = sys.argv[2]
    try:
        ask(model, CASES[0][1], keep_alive='5m')
        start = time.perf_counter()
        raw = ask(model, CASES[0][1], keep_alive='5m')
        print(model, 'warm seconds', round(time.perf_counter() - start, 3), raw)
    finally:
        req = urllib.request.Request(URL.replace('/chat', '/generate'),
            json.dumps({'model': model, 'keep_alive': 0}).encode(),
            {'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=600) as response:
            response.read()
elif sys.argv[1] == 'review':
    Path('memory.json').unlink(missing_ok=True)
    Path('reviewed.json').unlink(missing_ok=True)
    totals = {m: Counter() for m in ('stock', 'edited')}
    expected_by_name = {n: e for n, _, e in CASES}
    decisions = []
    rows = [json.loads(line) for line in LOG.read_text().splitlines()]
    pairs = {(r['model'], r['case']) for r in rows}
    assert len(rows) == 20
    assert pairs == {(m, n) for m in totals for n, _, _ in CASES}
    journal = Path('reviewed.jsonl')
    journal.write_text('')
    for row in rows:
        row['disputed'] = False
        c = totals[row['model']]
        c['responses'] += 1
        print(row['model'], row['case'], row['raw'])
        # A human reads meaning; no refusal-keyword detector.
        answer = yes_no('Does this decline the extraction task? [y/n] ')
        row['refusal'] = answer == 'y'
        c['refusals'] += row['refusal']
        try:
            parsed = json.loads(row['raw'])
        except json.JSONDecodeError:
            c['invalid_json'] += 1
        else:
            if list(CHECK.iter_errors(parsed)):
                c['invalid_schema'] += 1
            else:
                actual = [tuple(f[k] for k in FIELDS) for f in parsed['facts']]
                actual = [('user' if s in ('I', 'me') else s, p, v, b, t)
                          for s, p, v, b, t in actual]
                expected = expected_by_name[row['case']]
                print('Expected:', expected, '\nActual:', actual)
                prompt = 'Equivalent wording only: canonical tuples JSON or Enter: '
                edit = input(prompt)
                if edit:
                    while True:
                        try:
                            candidate = json.loads(edit)
                            assert isinstance(candidate, list)
                            assert all(isinstance(f, list) and len(f) == len(FIELDS)
                                       for f in candidate)
                            CHECK.validate({'facts': [dict(zip(FIELDS, f))
                                                      for f in candidate]})
                            actual = [tuple(f) for f in candidate]
                            break
                        except (ValueError, AssertionError, TypeError,
                                ValidationError) as error:
                            print('Invalid tuples:', error)
                            edit = input(prompt)
                            if not edit:
                                break
                row['canonical'] = actual
                lost, added, reversed_count = compare(expected, actual)
                c['omissions'] += lost
                c['additions'] += added
                c['reversals'] += reversed_count
                print('Omitted, added, reversed:', lost, added, reversed_count)
                agrees = yes_no('Meaning agrees with these counts? [y/n] ')
                row['disputed'] = agrees != 'y'
                # One gated write: only an approved, error-free note is stored.
                if (row['model'], row['case']) == ('stock', 'plain') and (
                        not row['refusal'] and not row['disputed']):
                    store_labeled_fixture(Path('memory.json'), expected, actual)
        c['disputed'] += row['disputed']
        with journal.open('a') as out:
            out.write(json.dumps(row) + '\n')
        decisions.append(row)
    Path('reviewed.json').write_text(json.dumps(decisions, indent=2))
    for model, counts in totals.items():
        keys = ('responses', 'invalid_json', 'invalid_schema', 'refusals',
                'omissions', 'additions', 'reversals', 'disputed')
        print(model, {k: counts[k] for k in keys})
else:
    raise SystemExit('Use run, review, free MODEL CASE, or warm MODEL')

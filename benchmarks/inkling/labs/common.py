"""Small dependency-free OpenAI transport and immutable run/checkpoint helpers."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SEED = 20261122


def read(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def source_definitions(path, names, namespace=None):
    """Execute only selected existing pure definitions, without import-time side effects."""
    path = Path(path)
    tree = ast.parse(path.read_text(), filename=str(path))
    nodes = [n for n in tree.body if (
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names
    ) or (isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id in names for t in n.targets))]
    found = {n.name if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) else n.targets[0].id for n in nodes}
    if found != set(names):
        raise RuntimeError(f'Missing harness definitions: {set(names) - found}')
    scope = {} if namespace is None else namespace
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return scope


def arguments(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument('--variant', required=True, choices=['stock', 'edited', 'edited+lora', 'smoke'])
    p.add_argument('--model', default=os.environ.get('MODEL'), required=not bool(os.environ.get('MODEL')))
    p.add_argument('--base-url', default='http://127.0.0.1:39850/v1')
    p.add_argument('--thinking-budget', type=int, default=0)
    p.add_argument('--output-root', type=Path, default=HERE.parent / 'results')
    p.add_argument('--limit', type=int, help='First N fixed question IDs; smoke/debug only')
    p.add_argument('--batch-size', type=int, default=0, help='Maximum unfinished item/lane pairs this invocation; 0 = all')
    p.add_argument('--timeout', type=float, default=900)
    return p


def initialize(out, manifest):
    out.mkdir(parents=True, exist_ok=True)
    p = out / 'manifest.json'
    if p.exists() and read(p) != manifest:
        raise RuntimeError(f'Run settings or inputs changed; use a fresh output root: {p}')
    atomic(p, manifest)


class Client:
    def __init__(self, base, model, timeout=900):
        self.base = base.rstrip('/')
        self.model = model
        self.timeout = timeout

    def call(self, messages, max_tokens, seed, checkpoint, **extra):
        request = dict(model=self.model, messages=messages, max_tokens=max_tokens,
                       temperature=0, seed=seed, **extra)
        checkpoint = Path(checkpoint)
        if checkpoint.exists():
            saved = read(checkpoint)
            if saved['request'] != request:
                raise RuntimeError(f'Checkpoint request changed: {checkpoint}')
            return saved
        start = time.monotonic()
        req = urllib.request.Request(self.base + '/chat/completions',
                                     data=json.dumps(request).encode(),
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': 'Bearer ' + os.environ.get('INKLING_API_KEY', 'local-unused')})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = json.load(response)
        except Exception as exc:
            atomic(checkpoint.with_suffix('.error.json'), {'request': request, 'error': str(exc)})
            raise
        choice = raw['choices'][0]
        record = dict(request=request, response=raw, text=choice['message'].get('content') or '',
                      finish_reason=choice['finish_reason'], seconds=time.monotonic() - start)
        atomic(checkpoint, record)
        return record


def summary(out, planned):
    rows = [read(p) for p in (out / 'items').rglob('*.json')] if (out / 'items').exists() else []
    groups = {}
    for row in rows:
        key = row['lane']
        g = groups.setdefault(key, {'n': 0, 'correct': 0, 'skipped': 0, 'length_stops': 0})
        if row.get('status') == 'context-does-not-fit':
            g['skipped'] += 1
        else:
            g['n'] += 1
            g['correct'] += int(row['correct'])
            g['length_stops'] += int(row.get('finish_reason') == 'length')
    for g in groups.values():
        g['accuracy'] = g['correct'] / g['n'] if g['n'] else None
    result = dict(planned=planned, completed=len(rows), complete=len(rows) == planned, systems=groups)
    atomic(out / 'summary.json', result)
    print(json.dumps(result), flush=True)
    return result

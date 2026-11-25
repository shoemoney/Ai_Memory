#!/usr/bin/env python3
"""Seeded 200 GSM8K + 200 MMLU-Pro test items, zero-shot exact match."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import random
import re
import urllib.request

from common import Client, HERE, SEED, arguments, atomic, digest, initialize, read, summary

DATASETS = {
    'gsm8k': dict(repo='openai/gsm8k', revision='740312add88f781978c0658806c59bc2815b9866',
                  file='main/test-00000-of-00001.parquet', license='MIT'),
    'mmlu-pro': dict(repo='TIGER-Lab/MMLU-Pro', revision='b189ec765aa7ed75c8acfea42df31fdae71f97be',
                     file='data/test-00000-of-00001.parquet', license='MIT'),
}


def numeric(text):
    text = text.strip().replace(',', '')
    if not re.fullmatch(r'[-+]?\d+(?:\.\d+)?', text):
        return None
    try:
        return str(Decimal(text).normalize())
    except InvalidOperation:
        return None


def exact_match(benchmark, text, gold):
    if benchmark == 'gsm8k':
        # Require a bare number or the final explicitly marked answer; no last-number guessing.
        match = re.search(r'(?:####|Final answer:)\s*([-+]?\d[\d,]*(?:\.\d+)?)\s*\.?\s*$', text, re.I)
        candidate = match[1] if match else text.strip()
        return numeric(candidate) is not None and numeric(candidate) == numeric(gold)
    match = re.fullmatch(r'\s*(?:Final answer:\s*)?\(?([A-J])\)?[.]?\s*', text, re.I)
    return bool(match and match[1].upper() == gold)


def prepare(data_dir, fixture=None):
    if fixture:
        return read(fixture), {'offline_fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest()}
    data_dir.mkdir(parents=True, exist_ok=True)
    selected = []
    evidence = {}
    for name, spec in DATASETS.items():
        path = data_dir / f"{name}-{spec['revision']}.parquet"
        if not path.exists():
            url = f"https://huggingface.co/datasets/{spec['repo']}/resolve/{spec['revision']}/{spec['file']}"
            # A partial download never becomes a reusable dataset.
            tmp = path.with_suffix('.download')
            urllib.request.urlretrieve(url, tmp)
            tmp.replace(path)
        import pyarrow.parquet as pq
        rows = pq.read_table(path).to_pylist()
        chosen = sorted(random.Random(SEED).sample(range(len(rows)), 200))
        evidence[name] = dict(spec, parquet_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), indices=chosen)
        for i in chosen:
            row = rows[i]
            if name == 'gsm8k':
                gold = row['answer'].split('####')[-1].strip()
                prompt = row['question'] + '\nSolve the problem. End with Final answer: <number>.'
            else:
                gold = row['answer']
                prompt = row['question'] + '\n' + '\n'.join(
                    f'{chr(65+j)}. {option}' for j, option in enumerate(row['options']))
                prompt += '\nReturn only the letter of the correct option (A-J).'
            selected.append(dict(item_id=f'{name}-{i:05}', lane=name, prompt=prompt, gold=gold))
    frozen = read(HERE / 'quality-selection.json')
    if frozen != dict(seed=SEED, sources=evidence, items_sha256=digest(selected)):
        raise RuntimeError('Dataset bytes, row indices or prompts differ from quality-selection.json')
    sample = data_dir / 'selection.json'
    payload = dict(seed=SEED, sources=evidence, items=selected)
    if sample.exists() and read(sample) != payload:
        raise RuntimeError('Fixed dataset selection changed; use a fresh data directory')
    atomic(sample, payload)
    return selected, evidence


def main():
    p = arguments(__doc__)
    p.add_argument('--concurrency', type=int, default=1)
    p.add_argument('--data-dir', type=Path, default=HERE / 'data')
    p.add_argument('--prepare-only', action='store_true')
    p.add_argument('--fixture', type=Path, help='Offline test rows; requires --variant smoke')
    a = p.parse_args()
    if a.concurrency < 1 or a.batch_size < 0 or (a.limit is not None and a.limit < 1):
        p.error('concurrency/limit must be positive and batch-size nonnegative')
    if a.fixture and a.variant != 'smoke':
        p.error('--fixture requires --variant smoke')
    rows, sources = prepare(a.data_dir, a.fixture)
    if a.limit:
        rows = [row for lane in DATASETS for row in [r for r in rows if r['lane'] == lane][:a.limit]]
    if a.prepare_only:
        print(json.dumps(dict(items=len(rows), sources=sources)))
        return
    out = a.output_root / a.variant / 'quality'
    initialize(out, dict(protocol='zero-shot-quality-v1', variant=a.variant, model=a.model,
                         base_url=a.base_url, thinking_budget=a.thinking_budget, seed=SEED,
                         max_tokens=512, temperature=0, limit=a.limit, sources=sources,
                         selection_sha256=digest(rows), scoring='numeric/final-letter exact match',
                         implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    client = Client(a.base_url, a.model, a.timeout)
    pending = [r for r in rows if not (out / 'items' / r['lane'] / (r['item_id'] + '.json')).exists()]
    if a.batch_size:
        pending = pending[:a.batch_size]

    def evaluate(row):
        record = client.call([{'role': 'user', 'content': row['prompt']}], 512, SEED,
                             out / 'raw' / (row['item_id'] + '.json'), thinking_budget=a.thinking_budget,
                             chat_template_kwargs={'enable_thinking': a.thinking_budget != 0})
        correct = exact_match(row['lane'], record['text'], row['gold'])
        # An unfinished response never passes exact-match scoring.
        correct = correct and record['finish_reason'] == 'stop'
        atomic(out / 'items' / row['lane'] / (row['item_id'] + '.json'),
               dict(row, status='scored', answer=record['text'], correct=correct,
                    finish_reason=record['finish_reason']))
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        list(pool.map(evaluate, pending))
    summary(out, len(rows))


if __name__ == '__main__':
    main()

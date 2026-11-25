#!/usr/bin/env python3
"""Replay the book's frozen retrieval outputs through its original reader/judge code."""
import hashlib
import json
from pathlib import Path
import re

from common import (Client, REPO, SEED, arguments, atomic, digest, initialize, read,
                    source_definitions, summary)

LONG_LANES = ['full-standard', 'bm25-standard', 'dense-standard', 'mem0-raw-standard', 'full-oracle']
LOCO_LANES = ['full-context', 'rag', 'mem0', 'graphiti', 'cognee']
JUDGES = {
    'longmemeval': dict(model='default_model', base='http://127.0.0.1:39711/v1',
                       weights='mlx-community/gemma-2-9b-it-4bit', revision='ff12eb39da2cd9b3b0f4b4f9ffb274603f05bb29'),
    'locomo': dict(model='qwen2.5-14b-instruct', base='http://127.0.0.1:39700/v1',
                   weights='bartowski/Qwen2.5-14B-Instruct-GGUF', revision='05244aa5d871c661c80082a15d3bce44714d068d',
                   sha256='e47ad95dad6ff848b431053b375adb5d39321290ea2c638682577dafca87c008')}


class LengthStop(Exception):
    def __init__(self, text):
        super().__init__('answer truncated at 4096 tokens')
        self.text = text


def plans(lab, archive, limit):
    if lab == 'longmemeval':
        manifest = read(archive / 'manifest.json')
        ids = [x['question_id'] for x in manifest['items']]
        if len(ids) != 300:
            raise RuntimeError('Expected book LongMemEval N=300')
        ids = ids[:limit] if limit else ids
        return [(qid, lane, archive / 'items' / f'{qid}--{lane}.json') for qid in ids for lane in LONG_LANES]
    ids = read(archive / 'matched-summary.json')['item_ids']
    if len(ids) != 67:
        raise RuntimeError('Expected book LoCoMo matched N=67')
    ids = ids[:limit] if limit else ids
    # Baselines retain the report's all-320 sample, memory lanes the matched 67.
    baseline_ids = [q['item_id'] for q in read(archive / 'selection.json')]
    if len(baseline_ids) != 320:
        raise RuntimeError('Expected book LoCoMo baseline N=320')
    if limit:
        baseline_ids = ids
    return [(qid, lane, archive / 'items' / lane / f'{qid}.json')
            for lane in LOCO_LANES for qid in (baseline_ids if lane in LOCO_LANES[:2] else ids)]


def main():
    p = arguments(__doc__)
    p.add_argument('lab', choices=list(JUDGES))
    p.add_argument('--archive', type=Path, help='Book results/full directory (default from lab)')
    p.add_argument('--judge-base-url', help='Tunnel to the pinned book judge')
    a = p.parse_args()
    if a.limit is not None and a.limit < 1 or a.batch_size < 0:
        p.error('limit must be positive and batch-size nonnegative')
    root = REPO / 'benchmarks' / a.lab
    archive = a.archive or root / 'results/full'
    plan = plans(a.lab, archive, a.limit)
    # Validate every input before making requests. Hash exact frozen contexts and all source records.
    sources = {str(path.relative_to(archive)): hashlib.sha256(path.read_bytes()).hexdigest()
               for _, _, path in plan}
    book = ['large.py', 'judge_prompt.py'] if a.lab == 'longmemeval' else ['full_run.py', 'run.py']
    source_hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in book}
    judge = JUDGES[a.lab]
    out = a.output_root / a.variant / a.lab
    initialize(out, dict(protocol='book-frozen-context-reader-replay-v1', variant=a.variant,
                         model=a.model, base_url=a.base_url, thinking_budget=a.thinking_budget,
                         judge={**judge, 'base': a.judge_base_url or judge['base']},
                         seed=SEED, limit=a.limit, input_sha256=sources, harness_sha256=source_hashes,
                         adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    reader = Client(a.base_url, a.model, a.timeout)
    grader = Client(a.judge_base_url or judge['base'], judge['model'], a.timeout)
    # These imports execute no top-level harness code: large.py otherwise writes its original OUT.
    if a.lab == 'longmemeval':
        scope = source_definitions(root / 'judge_prompt.py', ['get_anscheck_prompt'])
        scope.update(OUT=out, SEED=SEED, re=re, json=json, write=atomic)
        source_definitions(root / 'large.py', ['prompt', 'clean', 'judge'], scope)
    else:
        scope = source_definitions(root / 'run.py', ['ANSWER_SYSTEM', 'JUDGE', 'parse_json'], {'re': re, 'json': json})
        scope.update(SEED=SEED, atomic=atomic, log=lambda *args, **kw: None)
        source_definitions(root / 'full_run.py', ['answer', 'judge'], scope)
    processed = 0
    for qid, lane, source in plan:
        final = out / 'items' / lane / f'{qid}.json'
        if final.exists():
            continue
        if a.batch_size and processed >= a.batch_size:
            break
        old = read(source)
        processed += 1
        if old.get('status') == 'context-does-not-fit':
            atomic(final, dict(lane=lane, item_id=qid, status='context-does-not-fit',
                               book_prompt_tokens=old['prompt_tokens'], book_context_limit=8192))
            continue
        prefix = out / 'raw' / lane / qid
        if a.lab == 'longmemeval':
            def request(messages, max_tokens, phase, seed=SEED):
                client = grader if phase == 'judge' else reader
                extra = {'stop': ['<end_of_turn>']}
                if phase != 'judge':
                    extra.update(thinking_budget=a.thinking_budget,
                                 chat_template_kwargs={'enable_thinking': a.thinking_budget != 0})
                raw = client.call(messages, max_tokens, seed, prefix / f'{phase}-{seed}.json', **extra)
                return dict(text=scope['clean'](raw['text']), raw_text=raw['text'], raw=raw['response'], seconds=raw['seconds'])
            scope['request'] = request
            x = dict(question_date=old['question_date'], question=old['question'])
            prompt = scope['prompt'](x, old['context'])
            if prompt != old['answer']['prompt']:
                raise RuntimeError(f'Archived reader prompt mismatch: {source}')
            answer = request([{'role': 'user', 'content': prompt}], 512, 'answer')
            judged = scope['judge'](dict(question_type=old['question_type'], question_id=qid,
                                         question=old['question'], answer=old['reference']), answer['text'], lane)
            atomic(final, dict(lane=lane, item_id=qid, status='scored', question=old['question'],
                               reference=old['reference'], answer=answer, judge=judged,
                               context=old['context'], correct=judged['correct'],
                               finish_reason=answer['raw']['choices'][0]['finish_reason']))
        else:
            rowpath = out / 'working' / lane / f'{qid}.json'
            def call(messages, seed=SEED, max_tokens=512, json_mode=False):
                phase = 'judge' if json_mode else 'answer'
                extra = {'response_format': {'type': 'json_object'}} if json_mode else dict(
                    thinking_budget=a.thinking_budget, chat_template_kwargs={'enable_thinking': a.thinking_budget != 0})
                while True:
                    raw = (grader if json_mode else reader).call(messages, max_tokens, seed,
                                                                 prefix / f'{phase}-{seed}-{max_tokens}.json', **extra)
                    if raw['finish_reason'] == 'stop':
                        return raw['text']
                    if raw['finish_reason'] == 'length' and max_tokens >= 4096 and phase == 'answer':
                        raise LengthStop(raw['text'])
                    if raw['finish_reason'] != 'length' or max_tokens >= 4096:
                        raise RuntimeError(f'Invalid or truncated {phase}: {prefix}')
                    max_tokens = min(4096, max_tokens * 2)
            scope.update(call=call, item_path=lambda *args: rowpath,
                         load_item=lambda backend, q: read(rowpath) if rowpath.exists() else dict(q, backend=backend, votes=[]))
            q = {key: old[key] for key in ['item_id', 'question', 'gold', 'category', 'conversation', 'index']}
            try:
                scope['answer'](lane, q, old['context'])
            except LengthStop as stop:
                # The book never grades truncated text; a reader that cannot stop counts as wrong.
                atomic(final, dict(lane=lane, item_id=qid, status='scored', question=q['question'],
                                   gold=q['gold'], answer=stop.text, judge=None, correct=False,
                                   finish_reason='length', note='answer still truncated at 4096 tokens; not graded'))
                continue
            scope['judge'](lane, q)
            row = read(rowpath)
            atomic(final, dict(row, lane=lane, status='scored'))
    summary(out, len(plan))
    if a.lab == 'locomo':
        matched_ids = read(archive / 'matched-summary.json')['item_ids']
        if a.limit:
            matched_ids = matched_ids[:a.limit]
        systems = {}
        for lane in LOCO_LANES:
            complete = [read(out / 'items' / lane / f'{qid}.json') for qid in matched_ids
                        if (out / 'items' / lane / f'{qid}.json').exists()]
            systems[lane] = dict(n=len(complete), correct=sum(r['correct'] for r in complete))
            systems[lane]['accuracy'] = systems[lane]['correct'] / len(complete) if complete else None
        atomic(out / 'matched-summary.json', dict(item_ids=matched_ids, planned_n=len(matched_ids),
               complete=all(g['n'] == len(matched_ids) for g in systems.values()), systems=systems))


if __name__ == '__main__':
    main()

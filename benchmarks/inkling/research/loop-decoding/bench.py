#!/usr/bin/env python3
"""Sequential, offline loop-depth benchmark. Never downloads a checkpoint."""
import argparse
from dataclasses import asdict
import gc
import hashlib
import json
from pathlib import Path
import platform
import time

import mlx.core as mx
from decoding import adaptive, greedy, speculative

HERE = Path(__file__).resolve().parent


def methods(thresholds=(0, 1e-5, 5e-4, 1e-2)):
    return ([(f'plain-{n}', dict(kind='plain', n=n)) for n in [1, 2, 3, 5]] +
            [(f'spec-k{k}-d{n}', dict(kind='spec', k=k, n_draft=n))
             for k in [2, 4, 8] for n in [1, 2]] +
            [(f'adaptive-{t:g}', dict(kind='adaptive', threshold=t)) for t in thresholds])


def run_benchmark(model, encoded, max_tokens, eos_ids=(), selected=None):
    selected = methods() if selected is None else selected
    # Warm weights/kernels outside timing. Per-method memory peaks reset below.
    greedy(model, encoded[0]['tokens'], 1)
    refs = {p['id']: greedy(model, p['tokens'], max_tokens, eos_ids=eos_ids).tokens
            for p in encoded}
    rows = []
    gpu = mx.default_device() == mx.gpu
    for name, options in selected:
        for prompt in encoded:
            gc.collect()
            if gpu:
                mx.clear_cache()
                mx.reset_peak_memory()
            start = time.perf_counter()
            kw = {k:v for k,v in options.items() if k != 'kind'}
            fn = {'plain': greedy, 'spec': speculative, 'adaptive': adaptive}[options['kind']]
            result = fn(model, prompt['tokens'], max_tokens, eos_ids=eos_ids, **kw)
            seconds = time.perf_counter() - start
            target = refs[prompt['id']]
            agree = sum(a == b for a,b in zip(result.tokens, target))
            rows.append(dict(method=name, prompt_id=prompt['id'], category=prompt['category'],
                             prompt_tokens=len(prompt['tokens']), seconds=seconds,
                             tokens_per_second=len(result.tokens) / seconds,
                             exact_match=result.tokens == target,
                             token_agreement=agree / max(len(target),len(result.tokens),1),
                             peak_memory_bytes=mx.get_peak_memory() if gpu else None,
                             **asdict(result)))
        print(name, 'complete', flush=True)
    return rows


def summarize(rows):
    summary = []
    for name in dict.fromkeys(r['method'] for r in rows):
        group = [r for r in rows if r['method'] == name]
        tokens = sum(len(r['tokens']) for r in group)
        accepts = [v for r in group for v in r['accepted']]
        passes = [v for r in group for v in r['passes']]
        summary.append(dict(method=name, prompts=len(group),
            tokens_per_second=tokens / sum(r['seconds'] for r in group),
            acceptance_length=sum(accepts)/len(accepts) if accepts else None,
            average_passes_per_token=sum(passes)/len(passes) if passes else None,
            loop_positions_per_output_token=sum(r['loop_work'] for r in group)/tokens if tokens else None,
            exact_match_rate=sum(r['exact_match'] for r in group)/len(group),
            token_agreement=sum(r['token_agreement'] for r in group)/len(group),
            peak_memory_bytes=max((r['peak_memory_bytes'] or 0 for r in group)) or None))
    return summary


def write_report(output, payload):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.json').write_text(json.dumps(payload, indent=2)+'\n')
    columns = ['method','tokens_per_second','acceptance_length','average_passes_per_token',
               'loop_positions_per_output_token','exact_match_rate','token_agreement','peak_memory_bytes']
    table = ['| '+' | '.join(columns)+' |', '| '+' | '.join(['---']*len(columns))+' |']
    for row in payload['summary']:
        table.append('| '+' | '.join(f'{row[c]:.4g}' if isinstance(row[c],float) else
                                     str(row[c]) if row[c] is not None else 'n/a' for c in columns)+' |')
    output.with_suffix('.md').write_text(
        'End-to-end throughput includes prefill; peak memory includes weights and caches.\n'
        'Adaptive passes count core iterations, excluding repeated prefix and final-block work.\n'
        'Speculative loop positions count draft, verify and rollback replay, excluding prefill.\n\n'+
        '\n'.join(table)+'\n')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', type=Path, help='Existing local varloop MLX checkpoint')
    p.add_argument('--prompts', type=Path, default=HERE/'prompts.json')
    p.add_argument('--output', type=Path, default=HERE/'results/bench')
    p.add_argument('--max-tokens', type=int, default=64)
    p.add_argument('--limit', type=int, default=40)
    p.add_argument('--thresholds', type=float, nargs='+', default=[0,1e-5,5e-4,1e-2])
    p.add_argument('--tiny', action='store_true', help='CPU smoke only, random tiny model')
    a = p.parse_args(argv)
    if a.max_tokens < 1 or a.limit < 1:
        p.error('max-tokens and limit must be positive')
    prompts = json.loads(a.prompts.read_text())[:a.limit]
    if a.tiny:
        from mlx_lm.models.inkling2.config import ModelArgs
        from mlx_lm.models.inkling2.model import Model
        config = json.loads((HERE.parents[1]/'direction/tests/tiny_config.json').read_text())
        config['text_config']['loop_config']['is_varloop'] = True
        mx.set_default_device(mx.cpu)
        mx.random.seed(23)
        model = Model(ModelArgs.from_dict(config))
        encoded = [dict(id=r['id'], category=r['category'],tokens=[1,2,3]) for r in prompts]
        eos = ()
    else:
        if not a.model or not a.model.is_dir():
            p.error('--model must be an existing local checkpoint directory')
        from mlx_lm import load
        model, tokenizer = load(str(a.model))
        if not model.args.text.loop_config.get('is_varloop'):
            p.error('Requires is_varloop=true checkpoint')
        encoded = [dict(id=r['id'], category=r['category'],tokens=tokenizer.apply_chat_template(
            [{'role':'user','content':r['text']}], tokenize=True, add_generation_prompt=True)) for r in prompts]
        eos = tokenizer.eos_token_ids
    model.eval()
    rows = run_benchmark(model, encoded, a.max_tokens, eos, methods(a.thresholds))
    payload = dict(protocol='loop-decoding-v1', model=str(a.model), tiny=a.tiny,
                   platform=platform.platform(), max_tokens=a.max_tokens,
                   prompts_sha256=hashlib.sha256(a.prompts.read_bytes()).hexdigest(),
                   encoded_prompts=encoded, summary=summarize(rows), rows=rows)
    write_report(a.output, payload)


if __name__ == '__main__':
    main()

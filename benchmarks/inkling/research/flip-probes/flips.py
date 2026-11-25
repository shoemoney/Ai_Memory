"""Greedy 1/3-pass generation plus 1/2/3-pass full-prefix teacher-forced replay.

Uncached replay deliberately trades speed for cache-independent counterfactuals.
No model downloads or remote jobs are started by the offline tests.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import time
import numpy as np
from capture import capture, flatten, pass_count, text_model, to_numpy


def distribution(logits):
    x = np.asarray(logits, dtype=np.float64)
    logp = x - np.max(x)
    logp -= np.log(np.exp(logp).sum())
    return logp


def stats(logp):
    p = np.exp(logp)
    top = np.sort(p)[-2:]
    return float(-(p * logp).sum()), float(top[-1] - top[-2])


def kl(logp, logq):
    return float(max(0, (np.exp(logp) * (logp-logq)).sum()))


def forward(model, tokens, n, layers=None):
    import mlx.core as mx
    with pass_count(model, n):
        if layers is None:
            logits = model(mx.array([tokens]))[0, -1]
            mx.eval(logits)
            return distribution(to_numpy(logits))
        with capture(model, layers) as saved:
            logits = model(mx.array([tokens]))[0, -1]
            mx.eval(logits)
        return distribution(to_numpy(logits)), saved


def greedy(model, tokens, n, limit, eos):
    out = []
    for _ in range(limit):
        token = int(forward(model, tokens+out, n).argmax())
        out.append(token)
        if token in eos:
            break
    return out


def answer_text(text):
    """Extract Inkling final text channel, preserving raw decode separately."""
    if '<|content_' not in text and '<|message_model|>' not in text:
        return text.strip()
    blocks = re.findall(r'<\|content_text\|>(.*?)(?=<\|end_message\|>|<\|message_model\|>|<\|end_turn\|>|$)', text, re.S)
    return '\n'.join(block.strip() for block in blocks).strip() if blocks else None


NO_THINKING_PREFILL = '<|message_model|><|content_text|>'
STRATA_ORDER = ('recall', 'two_hop', 'memory', 'code')


def select_rows(rows, n, seed=1701):
    """AMENDMENT-1: n rows stratified equally across the registered strata, sampled with the registered
    seed, returned round-robin in the fixed strata order so any prefix of the list stays stratified."""
    import random
    per = n // len(STRATA_ORDER)
    rng = random.Random(seed)
    picked = {}
    for stratum in STRATA_ORDER:
        pool = sorted((r for r in rows if r['stratum'] == stratum), key=lambda r: r['id'])
        picked[stratum] = rng.sample(pool, per)
    return [picked[s][i] for i in range(per) for s in STRATA_ORDER]


def collect_prompt(model, tokenizer, row, limit, layers, raw=False, no_thinking=False):
    tokens = tokenizer.encode(row['text']) if raw else tokenizer.apply_chat_template(
        [{'role': 'user', 'content': row['text']}], tokenize=True, add_generation_prompt=True, reasoning_effort='none')
    tokens = list(tokens)
    if no_thinking:
        tokens += list(tokenizer.encode(NO_THINKING_PREFILL, add_special_tokens=False))
    eos = set(getattr(tokenizer, 'eos_token_ids', []) or [])
    if getattr(tokenizer, 'eos_token_id', None) is not None:
        eos.add(tokenizer.eos_token_id)
    generated = {n: greedy(model, tokens, n, limit, eos) for n in (1, 3)}
    answers = {n: tokenizer.decode(ids) for n, ids in generated.items()}
    final = {n:answer_text((NO_THINKING_PREFILL if no_thinking else '') + text) for n,text in answers.items()}
    capped = {n:len(generated[n])==limit and generated[n][-1] not in eos for n in (1,3)}
    # Censored/missing final answers are never mislabeled as completed answers.
    valid = not any(capped.values()) and all(text is not None for text in final.values())
    answer_flip = final[1] != final[3] if valid else None
    records, arrays = [], []
    prefix = tokens[:]
    for t, token in enumerate(generated[3]):
        p1 = forward(model, prefix, 1)
        p2 = forward(model, prefix, 2)
        p3, saved = forward(model, prefix, 3, layers)
        entropy, margin = stats(p1)
        g2, g3 = flatten(saved['gate'], 2), flatten(saved['gate'], 3)
        records.append(dict(prompt_id=row['id'], family=row.get('family', row['id']), stratum=row['stratum'],
                            position=t, token=token, argmax=[int(p.argmax()) for p in (p1,p2,p3)],
                            token_flip=bool(p1.argmax()!=p3.argmax()), answer_flip=answer_flip,
                            entropy=entropy, margin=margin, gate_norm=[float(np.sqrt(np.mean(g*g))) for g in (g2,g3)],
                            kl=[kl(p2,p1),kl(p3,p2)]))
        selected = lambda key: {k:v for k,v in saved[key].items() if k[1] in layers}
        arrays.append(dict(residual=flatten(saved['residual']), message=flatten(selected('message'), 2),
                           gate=flatten(selected('gate'), 2), forget=flatten(selected('forget'), 2)))
        prefix.append(token)
    return dict(id=row['id'], stratum=row['stratum'], answers=answers, generated=generated,
                answer_flip=answer_flip, final_text=final, capped=capped,
                prompt_tokens=len(tokens)), records, arrays


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--model', required=True, help='Existing local varloop checkpoint (no implicit downloads)')
    p.add_argument('--prompts', type=Path, default=Path(__file__).with_name('prompts.jsonl'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-tokens', type=int, default=32)
    p.add_argument('--limit', type=int)
    p.add_argument('--layers', default='6,11,17', help='Zero-based physical layers; must be in core')
    p.add_argument('--no-thinking', action='store_true', help='AMENDMENT-1: prefill the model turn with a text message so the answer starts immediately')
    p.add_argument('--stratified', type=int, help='AMENDMENT-1: use N rows stratified over the registered strata (seed 1701), round-robin order')
    p.add_argument('--raw', action='store_true', help='Raw completion; default uses checkpoint chat template for every stratum')
    a = p.parse_args()
    if not Path(a.model).is_dir():
        p.error('model must be an existing local directory')
    if a.max_tokens < 1 or (a.limit is not None and a.limit < 1):
        p.error('limits must be positive')
    if a.output.exists():
        p.error('output exists; choose a fresh directory to prevent mixed runs')
    from mlx_lm import load
    model, tokenizer = load(a.model)
    if not text_model(model).args.loop_config.get('is_varloop'):
        p.error('requires the variable-loop model')
    layers = [int(x) for x in a.layers.split(',')]
    if not layers or any(i not in text_model(model).args.loop_core for i in layers):
        p.error('capture layers must be in the loop core')
    a.output.mkdir(parents=True)
    rows = [json.loads(x) for x in a.prompts.read_text().splitlines()]
    if a.stratified:
        rows = select_rows(rows, a.stratified)
    if a.limit:
        rows = rows[:a.limit]
    manifest = dict(protocol='flip17-v1', model=str(Path(a.model).resolve()),
                    config_sha256=hashlib.sha256((Path(a.model)/'config.json').read_bytes()).hexdigest(),
                    prompts_sha256=hashlib.sha256(a.prompts.read_bytes()).hexdigest(), layers=layers,
                    max_tokens=a.max_tokens, raw=a.raw, no_thinking=a.no_thinking, stratified=a.stratified, reasoning_effort='none', planned=len(rows), completed=0,
                    feature_timing='residual: pass1; message: boundary1->2; gate: receiving pass2',
                    gate_norm_scope='RMS gain over all core layers and q/k/v/mlp channels; raw vectors saved at selected layers',
                    kl_direction='KL(P2||P1), KL(P3||P2)',
                    sources_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')})
    if len({r['id'] for r in rows}) != len(rows):
        p.error('Duplicate prompt IDs')
    import inspect
    model_source = Path(inspect.getfile(type(model)))
    manifest['model_source_sha256'] = hashlib.sha256(model_source.read_bytes()).hexdigest()
    manifest['tokenizer_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(a.model).glob('*token*json')}
    start = time.monotonic()
    (a.output/'manifest.json').write_text(json.dumps(manifest, indent=2))
    for row in rows:
        answer, records, arrays = collect_prompt(model, tokenizer, row, a.max_tokens, layers, a.raw, a.no_thinking)
        np.savez_compressed(a.output/f'{row["id"]}.npz', **{k:np.stack([x[k] for x in arrays]) for k in arrays[0]})
        with (a.output/'tokens.jsonl').open('a') as f:
            for r in records:
                f.write(json.dumps(r)+'\n')
        with (a.output/'answers.jsonl').open('a') as f:
            f.write(json.dumps(answer)+'\n')
        manifest.update(completed=manifest['completed']+1, elapsed_seconds=time.monotonic()-start)
        (a.output/'manifest.json').write_text(json.dumps(manifest, indent=2))
        print(row['id'], manifest['completed'], flush=True)


if __name__ == '__main__':
    main()

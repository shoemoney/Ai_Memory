"""Resumable OpenAI-compatible chat client, using only the standard library."""
import argparse
import asyncio
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SYSTEM = 'You are a helpful assistant. Respond to the user request.'


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def post_chat(base_url, body, api_key='', timeout=180):
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = 'Bearer ' + api_key
    req = urllib.request.Request(base_url.rstrip('/') + '/chat/completions', json.dumps(body).encode(), headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def response_text(raw):
    content = raw['choices'][0]['message'].get('content')
    if not isinstance(content, str):
        raise ValueError('Expected a text message content')
    return content


def fingerprint(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


async def run(args):
    prompts = read_jsonl(args.prompts)
    if args.limit:
        prompts = prompts[:args.limit]
    if len({p['id'] for p in prompts}) != len(prompts):
        raise ValueError('Duplicate prompt IDs')
    config = dict(base_url=args.base_url.rstrip('/'), model=args.model, seed=args.seed,
                  temperature=0, max_tokens=args.max_tokens, thinking_budget=args.thinking_budget,
                  system=SYSTEM, prompts_sha256=hashlib.sha256(Path(args.prompts).read_bytes()).hexdigest())
    run_id = fingerprint(config)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if output.exists():
        for row in read_jsonl(output):
            if row.get('run_id') != run_id:
                raise ValueError('Output belongs to a different configuration or prompt set; choose a new output')
            if row.get('status') == 'ok':
                done.add(row['prompt_id'])
    sem = asyncio.Semaphore(args.concurrency)
    errors = 0
    with output.open('a') as out:
        async def one(prompt):
            nonlocal errors
            if prompt['id'] in done:
                return
            body = dict(model=args.model, messages=[{'role':'system','content':SYSTEM},
                        {'role':'user','content':prompt['prompt']}], temperature=0, seed=args.seed,
                        max_tokens=args.max_tokens, thinking_budget=args.thinking_budget, stream=False)
            async with sem:
                start = time.perf_counter()
                row = dict(prompt_id=prompt['id'], group=prompt['group'], run_id=run_id, config=config)
                try:
                    raw = await asyncio.to_thread(post_chat, args.base_url, body, os.getenv(args.api_key_env, ''), args.timeout)
                    row.update(status='ok', response_text=response_text(raw), usage=raw.get('usage', {}),
                               finish_reason=raw['choices'][0].get('finish_reason'), raw=raw)
                except Exception as exc:
                    errors += 1
                    row.update(status='error', response_text=None, error=f'{type(exc).__name__}: {exc}')
                row['latency_seconds'] = time.perf_counter() - start
                out.write(json.dumps(row)+'\n')
                out.flush()
        await asyncio.gather(*(one(p) for p in prompts))
    if errors:
        raise RuntimeError(f'{errors} requests failed; rerun the same command to retry them')


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url', required=True, help='API prefix, including /v1 when needed')
    p.add_argument('--model', required=True)
    p.add_argument('--prompts', type=Path, default=ROOT/'prompts.jsonl')
    p.add_argument('--output', required=True)
    p.add_argument('--concurrency', type=int, default=8)
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--max-tokens', type=int, default=512)
    p.add_argument('--thinking-budget', type=int, default=0)
    p.add_argument('--timeout', type=float, default=180)
    p.add_argument('--api-key-env', default='OPENAI_API_KEY')
    p.add_argument('--limit', type=int, default=0, help='Smoke-test prefix; 0 means all')
    return p


if __name__ == '__main__':
    args = parser().parse_args()
    if args.concurrency < 1 or args.max_tokens < 1 or args.limit < 0 or args.thinking_budget < 0:
        raise SystemExit('Concurrency/max tokens must be positive; limit/budget must be nonnegative')
    asyncio.run(run(args))

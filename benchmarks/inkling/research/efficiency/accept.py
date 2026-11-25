#!/usr/bin/env python3
"""Serial fixed-prompt DSpark acceptance and throughput, via isolated lab :39850."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
EXACT = re.compile(r'EFFICIENCY_MTP\[([^\]]+)\] finish=(\S+) accepted=(\d+) proposed=(\d+) copy_accepted=(\d+) copy_proposed=(\d+)')


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def parse_stats(log):
    # Every line covers a disjoint segment; parking/re-entry may emit several per request.
    exact = [dict(uid=u, finish=f, accepted=int(a), proposed=int(p),
                  copy_accepted=int(ca), copy_proposed=int(cp))
             for u, f, a, p, ca, cp in EXACT.findall(log)]
    for row in exact:
        if row['accepted'] > row['proposed'] or row['copy_accepted'] > row['copy_proposed']:
            raise ValueError('Invalid exact draft counters; wrong backend or instrumentation')
    # Anchor to avoid matching the EFFICIENCY_MTP name.
    builtin = [dict(uid=m.group(1), finish=m.group(2), accepted=int(m.group(3)), evaluated=int(m.group(4)))
               for m in re.finditer(r'(?<![A-Z_])MTP\[([^\]]+)\] finish=(\S+).*? accept=(\d+)/(\d+)', log)]
    a = sum(r['accepted'] for r in exact)
    d = sum(r['proposed'] for r in exact)
    return dict(segments=exact, upstream_segments=builtin,
                accepted=a if exact else None, proposed=d if exact else None,
                acceptance_rate=a / d if d else None,
                upstream_accepted=sum(r['accepted'] for r in builtin) if builtin else None,
                upstream_evaluated=sum(r['evaluated'] for r in builtin) if builtin else None,
                copy_accepted=sum(r['copy_accepted'] for r in exact) if exact else None,
                copy_proposed=sum(r['copy_proposed'] for r in exact) if exact else None)


def checked_settings(document, model, mode):
    row = document.get('models', {}).get(model)
    if row is None:
        raise ValueError(f'Model {model} missing from settings snapshot')
    if bool(row.get('mtp_enabled', False)) != (mode == 'on'):
        raise ValueError('Settings do not match requested MTP mode; stop/reload the lab server')
    if row.get('dflash_enabled') or row.get('vlm_mtp_enabled'):
        raise ValueError('Competing speculative decoder enabled')
    return row


def summarize(rows, mode):
    n = len(rows)
    proposed = sum(r['stats']['proposed'] or 0 for r in rows)
    accepted = sum(r['stats']['accepted'] or 0 for r in rows)
    covered = sum(bool(r['stats']['segments']) for r in rows)
    duration = sum(r['seconds'] for r in rows)
    tokens = sum(r['response']['usage']['completion_tokens'] for r in rows)
    gen = [r['response']['usage'].get('generation_duration') for r in rows]
    gen_seconds = sum(gen) if all(isinstance(g, (int, float)) and g > 0 for g in gen) else None
    return dict(mode=mode, n=n, completion_tokens=tokens, request_seconds=duration,
                end_to_end_tokens_per_second=tokens / duration if duration else None,
                generation_tokens_per_second=tokens / gen_seconds if gen_seconds else None,
                telemetry_requests=covered,
                accepted=accepted if covered else None, proposed=proposed if covered else None,
                acceptance_rate=accepted / proposed if proposed else None,
                copy_accepted=sum(r['stats']['copy_accepted'] or 0 for r in rows) if covered else None,
                copy_proposed=sum(r['stats']['copy_proposed'] or 0 for r in rows) if covered else None,
                length_stops=sum(r['response']['choices'][0]['finish_reason'] == 'length' for r in rows))


def capture(command):
    return subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE,
                          timeout=20).stdout.decode()


def request(base, body, timeout):
    req = urllib.request.Request(base.rstrip('/') + '/chat/completions',
                                 data=json.dumps(body).encode(), headers={
                                     'Content-Type': 'application/json',
                                     'Authorization': 'Bearer ' + os.environ.get('INKLING_API_KEY', 'local-unused')})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def run_mode(a, prompts, mode):
    env = dict(os.environ, INKLING_MTP_MODE=mode, INKLING_MODEL=a.model)
    if a.configure_hook:
        subprocess.run(a.configure_hook, shell=True, env=env, check=True, timeout=120)
    settings_text = capture(a.settings_command)
    settings = checked_settings(json.loads(settings_text), a.model, mode)
    out = a.out / mode
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'settings.json', settings)
    # Warm model load and kernels without consuming any of the fixed set.
    warmup = dict(model=a.model, messages=[{'role':'user','content':'Reply with the word ready.'}],
                  max_tokens=16, temperature=0, seed=20261125, thinking_budget=0,
                  chat_template_kwargs={'enable_thinking':False})
    deadline = time.monotonic() + 90
    while True:
        try:
            warm_response = request(a.base_url, warmup, a.timeout)
            break
        except (OSError, urllib.error.URLError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)
    write(out / 'warmup.json', dict(request=warmup, response=warm_response))
    rows = []
    for prompt in prompts:
        before = capture(a.log_command)
        body = dict(model=a.model, messages=prompt['messages'], max_tokens=a.max_tokens,
                    temperature=0, seed=20261125, thinking_budget=0,
                    chat_template_kwargs={'enable_thinking':False})
        start = time.monotonic()
        response = request(a.base_url, body, a.timeout)
        seconds = time.monotonic() - start
        # INFO writes are normally synchronous, but allow a bounded scheduling delay.
        after = capture(a.log_command)
        if not after.startswith(before):
            raise RuntimeError('Server log rotated/restarted; refusing ambiguous counter join')
        delta = after[len(before):]
        stats = parse_stats(delta)
        if mode == 'on' and not stats['segments']:
            for _ in range(5):
                time.sleep(0.1)
                after = capture(a.log_command)
                if not after.startswith(before):
                    raise RuntimeError('Server log rotated')
                delta = after[len(before):]
                stats = parse_stats(delta)
                if stats['segments']:
                    break
        row = dict(id=prompt['id'], kind=prompt['kind'], request=body, response=response,
                   seconds=seconds, stats=stats, log=delta)
        write(out / 'items' / (prompt['id'] + '.json'), row)
        rows.append(row)
        if mode == 'on' and not stats['segments']:
            raise RuntimeError('No exact MTP telemetry: apply instrument_mtp.py, restart, verify drafter loaded')
        if mode == 'off' and (stats['segments'] or stats['upstream_segments']):
            raise RuntimeError('MTP counters in disabled mode; wrong server/settings or concurrent traffic')
        usage = response['usage']
        if usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0):
            raise RuntimeError('Thinking was not disabled')
        if not response['choices'][0]['message'].get('content'):
            raise RuntimeError('Empty visible response')
    result = summarize(rows, mode)
    if mode == 'on' and not result['proposed']:
        raise RuntimeError('No DSpark proposals; cannot report acceptance')
    result['groups'] = {kind: summarize([r for r in rows if r['kind'] == kind], mode)
                        for kind in sorted({r['kind'] for r in rows})}
    write(out / 'summary.json', result)
    return result


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--variant', required=True, choices=['stock','edited','edited+lora','smoke'])
    p.add_argument('--model', required=True)
    p.add_argument('--mode', choices=['on','off','both'], default='both')
    p.add_argument('--base-url', default='http://127.0.0.1:39850/v1')
    p.add_argument('--prompts', type=Path, default=HERE / 'prompts.json')
    p.add_argument('--out', type=Path, required=True, help='Fresh directory per variant/run')
    p.add_argument('--configure-hook', help='Configure command; receives INKLING_MTP_MODE and INKLING_MODEL')
    p.add_argument('--settings-command', default='timeout 15 ssh -o BatchMode=yes <lan-address> cat inkling-lab/omlx-data/model_settings.json')
    p.add_argument('--log-command', default='timeout 15 ssh -o BatchMode=yes <lan-address> cat inkling-lab/server.log')
    p.add_argument('--max-tokens', type=int, default=384)
    p.add_argument('--timeout', type=float, default=900)
    a = p.parse_args()
    endpoint = urllib.parse.urlparse(a.base_url)
    if endpoint.hostname not in ('127.0.0.1','localhost') or endpoint.port != 39850:
        p.error('Use the isolated loopback lab tunnel on port 39850')
    if a.mode == 'both' and not a.configure_hook:
        p.error('--mode both requires a configure hook to toggle/reload MTP')
    prompts = json.loads(a.prompts.read_text())['prompts']
    if len(prompts) != 50 or len({r['id'] for r in prompts}) != 50:
        p.error('Expected exactly 50 fixed unique prompts')
    a.out.mkdir(parents=True, exist_ok=False)
    write(a.out / 'manifest.json', dict(variant=a.variant, model=a.model, mode=a.mode,
          prompt_sha256=hashlib.sha256(a.prompts.read_bytes()).hexdigest(),
          max_tokens=a.max_tokens, temperature=0, thinking_budget=0, seed=20261125,
          base_url=a.base_url, configure_hook=a.configure_hook,
          settings_command=a.settings_command, log_command=a.log_command,
          source=json.loads((HERE / 'source-evidence.json').read_text())))
    modes = ['off','on'] if a.mode == 'both' else [a.mode]
    results = {mode:run_mode(a, prompts, mode) for mode in modes}
    if len(results) == 2:
        results['generation_speedup'] = (results['on']['generation_tokens_per_second'] /
             results['off']['generation_tokens_per_second']) if all(results[m]['generation_tokens_per_second'] for m in modes) else None
        results['end_to_end_speedup'] = (results['on']['end_to_end_tokens_per_second'] /
                                        results['off']['end_to_end_tokens_per_second'])
    write(a.out / 'summary.json', results)


if __name__ == '__main__':
    main()

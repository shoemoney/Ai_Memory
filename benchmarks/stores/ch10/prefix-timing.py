#!/usr/bin/env python3
"""Measure streamed first-token latency across fresh llama.cpp processes."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import statistics
import subprocess
import time
import urllib.request

LAB = Path('/var/tmp/memlab-10')
IMAGE = 'ghcr.io/ggml-org/llama.cpp@sha256:5b43086e3ba7ea5794d72904654f6cd41224a9b1c6ac0398f4940ee380d30f23'
REV = '9217f5db79a29953eb74d5343926648285ec7e67'
URL = ('https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/'
       + REV + '/qwen2.5-0.5b-instruct-q4_k_m.gguf')
NAME = 'memlab-10-prefix-timing'
PORT = 39102
BASE = f'http://127.0.0.1:{PORT}'
PROMPT = ('Record stable context. '
          + 'The archive contains a blue square and a green circle. ' * 80
          + 'Return one word: ')
PAYLOAD = dict(prompt=PROMPT, n_predict=1, temperature=0, seed=20261122,
               cache_prompt=True, id_slot=0)


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def call(endpoint, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(BASE + endpoint, data=body,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=180) as response:
        return json.load(response)


def ready():
    for _ in range(180):
        try:
            if call('/health')['status'] == 'ok':
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError('server readiness timed out')


def streamed():
    req = urllib.request.Request(BASE + '/completion',
                                 data=json.dumps(dict(PAYLOAD, stream=True)).encode(),
                                 headers={'Content-Type': 'application/json'})
    start = time.perf_counter()
    first = None
    events = []
    with urllib.request.urlopen(req, timeout=180) as response:
        for line in response:
            if not line.startswith(b'data: '):
                continue
            event = json.loads(line[6:])
            events.append(event)
            if first is None and event.get('content'):
                first = (time.perf_counter() - start) * 1000
    assert first is not None, events
    final = events[-1]
    assert final['stop'] and final['timings']['predicted_n'] == 1, final
    return dict(ttft_ms=first, timings=final['timings'],
                content=''.join(e.get('content', '') for e in events))


def main():
    print('Shared model lock acquired', flush=True)
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text()
                         .splitlines() if line.startswith('MemAvailable:')))
    while available < 4 * 1024 * 1024:
        print('Waiting two minutes for 4 GiB available RAM', flush=True)
        time.sleep(120)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo')
                             .read_text().splitlines()
                             if line.startswith('MemAvailable:')))
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', PORT))
    model = LAB / 'model.gguf'
    req = urllib.request.Request(URL, headers={
        'Authorization': 'Bearer ' + os.environ['HF_TOKEN']})
    with urllib.request.urlopen(req, timeout=180) as src, model.open('wb') as dst:
        shutil.copyfileobj(src, dst)
    with model.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    assert digest == '74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db'
    started = False
    result = dict(model='Qwen2.5-0.5B-Instruct Q4_K_M', model_revision=REV,
                  model_sha256=digest, image=IMAGE, gpu_layers=0, threads=2,
                  pairs=3, trials=[])
    try:
        run('docker', 'run', '-d', '--name', NAME, '--label', 'memlab.owner=ch10-timing',
            '--memory', '2g', '--cpus', '2', '-p', f'127.0.0.1:{PORT}:8080',
            '-v', str(LAB) + ':/scratch', IMAGE, '-m', '/scratch/model.gguf',
            '-ngl', '0', '-t', '2', '-c', '4096', '--parallel', '1', '--slots',
            '--slot-save-path', '/scratch', '--host', '0.0.0.0', '--port', '8080')
        started = True
        ready()
        seed = call('/completion', PAYLOAD)
        result['seed_timings'] = seed['timings']
        result['save'] = call('/slots/0?action=save', {'filename': 'slot.bin'})
        assert result['save']['n_saved'] == 889
        for pair in range(3):
            for condition in (('cold', 'restored') if pair % 2 == 0
                              else ('restored', 'cold')):
                run('docker', 'stop', '-t', '10', NAME)
                run('docker', 'start', NAME)
                ready()
                restore_ms = 0
                if condition == 'restored':
                    begin = time.perf_counter()
                    restored = call('/slots/0?action=restore', {'filename': 'slot.bin'})
                    restore_ms = (time.perf_counter() - begin) * 1000
                    assert restored['n_restored'] == 889
                trial = streamed()
                trial.update(pair=pair + 1, condition=condition,
                             restore_wall_ms=restore_ms,
                             restore_plus_ttft_ms=restore_ms + trial['ttft_ms'])
                expected = (0, 889) if condition == 'cold' else (888, 1)
                assert (trial['timings']['cache_n'], trial['timings']['prompt_n']) == expected
                result['trials'].append(trial)
                print(json.dumps(trial), flush=True)
        for condition in ('cold', 'restored'):
            trials = [t for t in result['trials'] if t['condition'] == condition]
            result[condition] = {key: statistics.median(t[key] for t in trials)
                                 for key in ('ttft_ms', 'restore_wall_ms',
                                             'restore_plus_ttft_ms')}
        result['passed'] = True
    finally:
        if started:
            assert run('docker', 'inspect', '-f',
                       '{{index .Config.Labels "memlab.owner"}}', NAME) == 'ch10-timing'
            run('docker', 'rm', '-f', NAME)
        model.unlink(missing_ok=True)
        (LAB / 'slot.bin').unlink(missing_ok=True)
        result['cleanup'] = 'container, model and slot removed; pre-existing image retained'
        (LAB / 'prefix-timing.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('cold', 'restored', 'passed')}), flush=True)


if __name__ == '__main__':
    main()

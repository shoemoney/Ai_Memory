"""Owned the Mac Studio oMLX controller. Invoked over SSH; never modifies source weights."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.request

PORT = 39851


def model_view(source, target, passes):
    source, target = Path(source).resolve(), Path(target)
    config = json.loads((source / 'config.json').read_text())
    text = config['text_config']
    loop = text['loop_config']
    if config['model_type'] != 'inkling2_loop' or not loop.get('is_varloop'):
        raise ValueError('Expected TML varloop checkpoint, not stock Inkling')
    if (loop['core_start'], loop['core_end']) != (6, 18) or passes not in (1, 2, 3, 5):
        raise ValueError('Unexpected core or pass count')
    text['loop_num_passes'] = passes
    loop['num_passes'] = passes
    # No bundled DSpark at p3 either: identical non-speculative decoding throughout.
    config.pop('mtp_config', None)
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.name.startswith('.') or path.name in ('config.json', 'mtp.safetensors'):
            continue
        dest = target / path.name
        if dest.exists() or dest.is_symlink():
            if not dest.is_symlink() or dest.resolve() != path.resolve():
                raise RuntimeError(f'Unexpected existing model view entry: {dest}')
        else:
            dest.symlink_to(path, target_is_directory=path.is_dir())
    (target / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    return dict(source=str(source), passes=passes, model=target.name,
                config_sha256=hashlib.sha256((target / 'config.json').read_bytes()).hexdigest(),
                source_config_sha256=hashlib.sha256((source / 'config.json').read_bytes()).hexdigest(),
                source_weight_files={p.name: p.stat().st_size for p in source.glob('*.safetensors')},
                source_weight_mtime_ns={p.name: p.stat().st_mtime_ns for p in source.glob('*.safetensors')},
                controller_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def alive(pid):
    try:
        os.kill(pid, 0)
        state = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='], capture_output=True, text=True, check=False)
        return bool(state.stdout.strip()) and not state.stdout.lstrip().startswith('Z')
    except ProcessLookupError:
        return False


def release(root, lock):
    owner = lock / 'memory-loops-owner'
    if owner.exists() and owner.read_text() == str(root):
        owner.unlink()
        lock.rmdir()


def owns_server(pid, root, run=subprocess.run):
    """True if the recorded PID is our server: full command line match, or (macOS rewrites the
    process title to 'omlx-server') the PID itself holds the TCP listener on our port."""
    command = run(['ps', '-p', str(pid), '-o', 'command='], capture_output=True, text=True, check=False).stdout
    if str(root / 'omlx-data') in command and f'--port {PORT}' in command:
        return True
    listen = run(['lsof', '-b', '-w', '-nP', '-a', '-p', str(pid), f'-iTCP:{PORT}', '-sTCP:LISTEN'],
                 capture_output=True, text=True, check=False)
    return listen.returncode == 0 and 'LISTEN' in listen.stdout


def stop(root, lock):
    statefile = root / 'server.json'
    if not statefile.exists():
        # Never infer ownership from port or PID alone.
        if (lock / 'memory-loops-owner').exists():
            raise RuntimeError('Owned lock without PID state; inspect manually')
        return
    state = json.loads(statefile.read_text())
    pid = state['pid']
    if alive(pid):
        if not owns_server(pid, root):
            raise RuntimeError('PID identity changed; refusing signal')
        os.kill(pid, signal.SIGTERM)
        for _ in range(60):
            if not alive(pid):
                break
            time.sleep(1)
        if alive(pid):
            raise RuntimeError('Server did not stop; retaining state and heavy.lock')
    statefile.unlink()
    release(root, lock)


def start(lab, root, lock, source, passes, enforce_identity=False):
    if (root / 'server.json').exists():
        raise RuntimeError('Already running; use restart')
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', PORT))
    lock.mkdir()  # Same lock as the stock lab, held until shutdown.
    (lock / 'memory-loops-owner').write_text(str(root))
    child = None
    try:
        model = f'varloop-p{passes}'
        view = root / 'serve-models' / model
        # Discovery exposes only the current pass count.
        discovery = root / f'discovery-p{passes}'
        discovery.mkdir(exist_ok=True)
        entry = discovery / model
        if not entry.exists():
            entry.symlink_to(view, target_is_directory=True)
        provenance = model_view(source, view, passes)
        identity = root / f'identity-p{passes}.json'
        if enforce_identity and (not identity.exists() or json.loads(identity.read_text()) != provenance):
            raise RuntimeError('Model/controller identity changed; inspect and use a fresh study')
        identity.write_text(json.dumps(provenance, indent=2) + '\n')
        base = root / 'omlx-data'
        base.mkdir(exist_ok=True)
        (base / 'model_settings.json').write_text(json.dumps({'version': 3, 'models': {
            model: {'max_context_window': 65536, 'mtp_enabled': False, 'vlm_mtp_enabled': False,
                    'dflash_enabled': False}}}))
        for name in ('home', 'cache', 'tmp'):
            (root / name).mkdir(exist_ok=True)
        env = {**os.environ, 'HOME': str(root / 'home'), 'HF_HOME': str(lab / 'hf-cache'),
               'XDG_CACHE_HOME': str(root / 'cache'), 'TMPDIR': str(root / 'tmp')}
        command = [str(lab / 'omlx-venv/bin/omlx'), 'serve', '--base-path', str(base),
                   '--model-dir', str(discovery), '--host', '127.0.0.1', '--port', str(PORT),
                   '--no-hf-cache', '--no-cache', '--max-concurrent-requests', '1',
                   '--memory-guard-gb', '60', '--headless']
        with (root / f'server-p{passes}.log').open('ab') as log:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                     env=env, start_new_session=True)
        (root / 'server.json').write_text(json.dumps({'pid': child.pid, **provenance}))
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError(f'Server exited {child.returncode}; inspect server-p{passes}.log')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/v1/models', timeout=2) as response:
                    advertised = json.load(response)
                if model in [r['id'] for r in advertised['data']]:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        else:
            raise TimeoutError('Server readiness timeout')
        # Force a real load before the hook succeeds. No answer-quality claim.
        body = {'model': model, 'messages': [{'role': 'user', 'content': 'Reply OK.'}],
                'max_tokens': 8, 'temperature': 0, 'thinking_budget': 0,
                'chat_template_kwargs': {'enable_thinking': False}}
        request = urllib.request.Request(f'http://127.0.0.1:{PORT}/v1/chat/completions',
                    data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=150) as response:
            warmup = json.load(response)
        if not warmup['choices'][0]['message'].get('content'):
            raise RuntimeError('Empty thinking-off warmup')
        reasoning = warmup.get('usage', {}).get('completion_tokens_details', {}).get('reasoning_tokens', 0)
        if reasoning:
            raise RuntimeError('Thinking-off warmup emitted reasoning tokens')
        (root / f'warmup-p{passes}.json').write_text(json.dumps(warmup, indent=2))
        print(json.dumps(provenance))
    except BaseException:
        if child is not None:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=60)
            (root / 'server.json').unlink(missing_ok=True)
        release(root, lock)
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('action', choices=['start', 'restart', 'stop'])
    p.add_argument('--passes', required=True, type=int, choices=[1, 2, 3, 5])
    p.add_argument('--model', required=True, type=Path)
    a = p.parse_args()
    def interrupted(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, interrupted)
    lab = Path.home() / 'inkling-lab'
    root, lock = lab / 'memory-loops', lab / 'heavy.lock'
    root.mkdir(parents=True, exist_ok=True)
    if a.action != 'start':
        stop(root, lock)
    if a.action != 'stop':
        start(lab, root, lock, a.model, a.passes, enforce_identity=a.action == 'restart')

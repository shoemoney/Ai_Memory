"""Serve one model at a time over SSH; generation and official scoring stay local."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
LAB = Path('/var/tmp/membench-bfcl')
HOST = os.environ.get('MODEL_HOST')
PORT = 39730
MODELS = {
    '2B': ('f6d5376be1edb4d416d56da11e5397a961aca8ae', 'aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223'),
    '0.8B': ('6ab461498e2023f6e3c1baea90a8f0fe38ab64d0', 'bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517'),
    '4B': ('e87f176479d0855a907a41277aca2f8ee7a09523', '00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4'),
}

def remote(script, check=True):
    return subprocess.run(['ssh', HOST, 'bash', '-s'], input=script, text=True, capture_output=True, check=check)

def snapshot():
    # Persist only hardware/resource evidence, without account names, addresses or paths.
    script = '''memory_pressure | tail -1
sysctl -n kern.memorystatus_vm_pressure_level
df -h .
ps -axo pid,comm,rss | awk 'NR==1 || /llama-server|omlx-server/ {print $1, $2, $3}'
'''
    return remote(script).stdout

def main():
    if not HOST:
        raise SystemExit('Set MODEL_HOST to an SSH alias for the model-serving Mac')
    LAB.mkdir(exist_ok=True)
    os.environ['UV_CACHE_DIR'] = str(LAB/'uv-cache')
    out = ROOT / 'results' / os.environ.get('RUN_NAME', datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    if out.exists():
        raise SystemExit('Output exists; set a fresh RUN_NAME')
    out.mkdir(parents=True)
    tunnel = None
    try:
        (out/'resources-before.txt').write_text(snapshot())
        runtime = remote('llama-server --version 2>&1').stdout
        (out/'runtime-version.txt').write_text(runtime)
        if 'build 12359' not in runtime or 'b1b770d90' not in runtime:
            raise RuntimeError('Expected llama.cpp build 12359, commit b1b770d90')
        py = LAB/'venv/bin/python'
        if not py.exists():
            subprocess.run(['uv', 'venv', '--python', '3.11.18', str(LAB/'venv')], check=True)
            subprocess.run(['uv', 'pip', 'sync', '--python', str(py), '--extra-index-url', 'https://download.pytorch.org/whl/cpu', '--index-strategy', 'unsafe-best-match', str(ROOT/'requirements.txt')], check=True)
        # Validate exact installed packages even when reusing this task's scratch environment.
        freeze = subprocess.check_output(['uv','pip','freeze','--python',str(py)],text=True)
        if sorted(freeze.splitlines()) != sorted((ROOT/'requirements.txt').read_text().splitlines()):
            raise RuntimeError('Scratch environment differs from requirements.txt')
        for size in os.environ.get('MODEL_SIZES', '2B,4B,0.8B').split(','):
            revision, sha = MODELS[size]
            repo = f'unsloth/Qwen3.5-{size}-GGUF'
            filename = f'Qwen3.5-{size}-Q4_K_M.gguf'
            url = f'https://huggingface.co/{repo}/resolve/{revision}/{filename}'
            script = (ROOT/'serve.sh').read_text()
            remote('export MODEL_URL='+repr(url)+'\nexport MODEL_SHA='+repr(sha)+'\nexport MODEL_ALIAS='+repr(f'Qwen3.5-{size}-Q4_K_M')+'\n'+script)
            tunnel = subprocess.Popen(['ssh', '-N', '-o', 'ExitOnForwardFailure=yes', '-L', f'{PORT}:localhost:{PORT}', HOST], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            for attempt in range(120):
                if tunnel.poll() is not None:
                    raise RuntimeError('SSH tunnel failed')
                try:
                    with urllib.request.urlopen(f'http://localhost:{PORT}/health', timeout=2) as response:
                        if json.load(response)['status'] == 'ok':
                            break
                except OSError:
                    time.sleep(1)
            else:
                raise RuntimeError('Model did not become healthy')
            for thinking in ['off', 'on']:
                subprocess.run([str(py), str(ROOT/'run.py'), '--model', f'Qwen3.5-{size}-Q4_K_M', '--thinking', thinking, '--output', str(out/f'{size}-{thinking}')], check=True)
                (out/f'resources-{size}-{thinking}.txt').write_text(snapshot())
            (out/f'pressure-{size}.txt').write_text(remote('cat ~/membench-bfcl-tmp/pressure.log').stdout)
            remote('kill "$(cat ~/membench-bfcl-tmp/server.pid)"; kill "$(cat ~/membench-bfcl-tmp/guard.pid)" 2>/dev/null || true')
            tunnel.terminate(); tunnel.wait(timeout=10); tunnel = None
    finally:
        (out/'pressure-final.txt').write_text(remote('cat ~/membench-bfcl-tmp/pressure.log 2>/dev/null || true', check=False).stdout)
        remote('''if [ -f ~/membench-bfcl-tmp/server.pid ]; then
 kill "$(cat ~/membench-bfcl-tmp/server.pid)" 2>/dev/null || true
fi
if [ -f ~/membench-bfcl-tmp/guard.pid ]; then
 kill "$(cat ~/membench-bfcl-tmp/guard.pid)" 2>/dev/null || true
fi
rm -rf -- ~/membench-bfcl-tmp
''', check=False)
        if tunnel:
            tunnel.terminate(); tunnel.wait(timeout=10)
        (out/'resources-after.txt').write_text(snapshot())
        proof = remote('test ! -e ~/membench-bfcl-tmp && echo remote-scratch-absent; if lsof -nP -iTCP:39730 -sTCP:LISTEN >/dev/null; then echo task-port-occupied; else echo task-port-unoccupied; fi').stdout
        (out/'cleanup.txt').write_text(proof)
        shutil.rmtree(LAB)
        with (out/'cleanup.txt').open('a') as f:
            f.write('local-scratch-absent=' + str(not LAB.exists()) + '\n')
            f.write(subprocess.check_output(['df','-h','/var/tmp'],text=True))
    print(out)

if __name__ == '__main__':
    main()

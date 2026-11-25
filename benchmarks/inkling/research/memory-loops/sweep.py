"""Sweep driver: bounded SSH, owned tunnel, restart hook, always stop on exit."""
import argparse
import json
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys

from protocol import HERE, REPO, batch, read

the workstation = '<lan-address>'
REMOTE = '$HOME/inkling-lab/memory-loops'
PYTHON = '$HOME/inkling-lab/omlx-venv/bin/python'


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('passes', type=int, choices=[1, 2, 3, 5])
    p.add_argument('--model', required=True, help='Absolute, already provisioned the Mac Studio varloop directory')
    p.add_argument('--output-root', type=Path, default=REPO / 'benchmarks/inkling/results')
    p.add_argument('--design', choices=['screen', 'depth-retrieval'], default='screen')
    p.add_argument('--selection', type=Path, help='Depth-retrieval manifest; defaults to its frozen 150-question subset')
    a = p.parse_args()
    if a.design == 'depth-retrieval':
        from depth_retrieval import MANIFEST, validate
        a.selection = a.selection or MANIFEST
        validate(read(a.selection))
        # Separate root prevents collisions with the existing screen by default.
        a.output_root = a.output_root / 'depth-retrieval'
    elif a.selection:
        p.error('--selection is only supported for --design depth-retrieval')
    if not Path(a.model).is_absolute():
        p.error('--model must be an absolute the Mac Studio path')
    # Reject local port conflicts before starting anything remote.
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', 39851))
    subprocess.run(['ssh', the workstation, 'timeout 15 mkdir -p ' + REMOTE], timeout=25, check=True)
    subprocess.run(['scp', str(HERE / 'remote.py'), the workstation + ':' + REMOTE + '/remote.py'],
                   timeout=30, check=True)

    def command(action):
        remote = shlex.join(['timeout', '360', PYTHON, REMOTE + '/remote.py', action,
                            '--passes', str(a.passes), '--model', a.model])
        return ['ssh', '-o', 'ConnectTimeout=10', the workstation, remote]

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'Signal {signum}')

    signal.signal(signal.SIGTERM, interrupted)
    tunnel = None
    started = False
    try:
        result = subprocess.run(command('start'), timeout=380, check=True, stdout=subprocess.PIPE, text=True)
        started = True
        provenance = json.loads(result.stdout.strip().splitlines()[-1])
        run = a.output_root / f'varloop-p{a.passes}'
        run.mkdir(parents=True, exist_ok=True)
        path = run / 'serving.json'
        if path.exists() and read(path) != provenance:
            raise RuntimeError('Serving model changed; use a fresh output root')
        path.write_text(json.dumps(provenance, indent=2) + '\n')
        tunnel = subprocess.Popen(['ssh', '-N', '-o', 'ExitOnForwardFailure=yes',
                                 '-o', 'ConnectTimeout=10', '-L', '127.0.0.1:39851:127.0.0.1:39851', the workstation])
        import time
        import urllib.request
        for _ in range(50):
            if tunnel.poll() is not None:
                raise RuntimeError('Owned SSH tunnel exited')
            try:
                with urllib.request.urlopen('http://127.0.0.1:39851/v1/models', timeout=2) as response:
                    advertised = json.load(response)
                if provenance['model'] in [m['id'] for m in advertised['data']]:
                    break
            except OSError:
                pass
            time.sleep(.2)
        else:
            raise TimeoutError('Tunnel readiness timeout')
        if a.design == 'depth-retrieval':
            from depth_retrieval import batch as depth_batch
            depth_batch(a.passes, a.selection, a.output_root, provenance['model'],
                        'http://127.0.0.1:39851/v1', shlex.join(command('restart')))
        else:
            batch(a.passes, HERE / 'selection.json', a.output_root, provenance['model'],
                  'http://127.0.0.1:39851/v1', shlex.join(command('restart')))
    finally:
        try:
            if tunnel is not None:
                tunnel.terminate()
                tunnel.wait(timeout=15)
        finally:
            if started:
                subprocess.run(command('stop'), timeout=380, check=True)


if __name__ == '__main__':
    main()

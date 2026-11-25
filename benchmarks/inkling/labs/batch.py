"""Short resumable batches; hook failure stops the run immediately."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from common import HERE, read


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--variant', required=True)
    p.add_argument('--restart-hook', required=True)
    p.add_argument('--batch-size', type=int, default=10)
    p.add_argument('--output-root', type=Path, default=HERE.parent / 'results')
    p.add_argument('--quality-concurrency', type=int, default=1)
    p.add_argument('--longmemeval-judge-base-url')
    p.add_argument('--locomo-judge-base-url')
    p.add_argument('--quality-fixture', type=Path, help='Smoke tests only')
    args, shared = p.parse_known_args()
    if args.batch_size < 1:
        p.error('--batch-size must be positive')
    ran = False
    for lab in ['longmemeval', 'locomo', 'quality']:
        script = HERE / ('quality.py' if lab == 'quality' else 'memory.py')
        command = [sys.executable, str(script)] + ([] if lab == 'quality' else [lab])
        command += ['--variant', args.variant, '--output-root', str(args.output_root),
                    '--batch-size', str(args.batch_size), *shared]
        if lab == 'quality':
            command += ['--concurrency', str(args.quality_concurrency)]
            if args.quality_fixture:
                command += ['--fixture', str(args.quality_fixture)]
        else:
            judge_base = getattr(args, lab + '_judge_base_url')
            if judge_base:
                command += ['--judge-base-url', judge_base]
        previous = -1
        while True:
            if ran:
                subprocess.run(args.restart_hook, shell=True, check=True)
            subprocess.run(command, check=True)
            ran = True
            state = read(args.output_root / args.variant / lab / 'summary.json')
            if state['complete']:
                break
            if state['completed'] <= previous:
                raise RuntimeError(f'No progress in {lab}')
            previous = state['completed']


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Baseline-subtracted CPU+GPU+ANE energy around a labs subprocess (stdlib only)."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import queue
import shlex
import subprocess
import threading
import time

HERE = Path(__file__).resolve().parent
INKLING = HERE.parents[1]
SAMPLERS = 'cpu_power,gpu_power,ane_power'
# Runs on macstudio. Each powermetrics sample is an interval average, not a point.
# A heartbeat bounds lifetime even if the initiating SSH connection disappears.
REMOTE = r'''
import json, os, plistlib, signal, subprocess, sys, threading, time
p = subprocess.Popen(['sudo','-n','powermetrics','--samplers','cpu_power,gpu_power,ane_power','-i','500','-f','plist'], stdout=subprocess.PIPE)
def stop(*args):
    p.terminate()
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGHUP, stop)
def heartbeat():
    while sys.stdin.buffer.read(1): pass
    stop()
threading.Thread(target=heartbeat, daemon=True).start()
print(json.dumps({'ready':time.time()}), flush=True)
buf=b''
try:
    while True:
        line=p.stdout.readline()
        if not line: break
        line=line.lstrip(b'\0')  # powermetrics separates plist documents with NUL
        if line.startswith(b'<?xml'): buf=line
        else: buf+=line
        if b'</plist>' in line:
            d=plistlib.loads(buf.rstrip(b'\0\n'))
            print(json.dumps({'end':time.time(),'elapsed_ns':d['elapsed_ns'],'processor':{k:d['processor'][k] for k in ['cpu_power','gpu_power','ane_power','combined_power']}}),flush=True)
            buf=b''
finally:
    p.terminate()
    try: p.wait(timeout=3)
    except subprocess.TimeoutExpired: p.kill(); p.wait()
'''


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def watts(record):
    p = record['processor']
    values = [float(p[k]) / 1000 for k in ('cpu_power', 'gpu_power', 'ane_power')]
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid power reading')
    # combined_power already includes these rails: never add it again.
    if abs(sum(values) - float(p['combined_power']) / 1000) > 0.02:
        raise ValueError('Power schema changed: combined != CPU+GPU+ANE')
    return sum(values)


def integrate(samples, start, end):
    if end <= start:
        raise ValueError('Empty measurement window')
    energy = covered = 0.0
    weighted = []
    for sample in samples:
        dt = sample['elapsed_ns'] / 1e9
        if dt <= 0:
            raise ValueError('Invalid sample interval')
        overlap = max(0, min(end, sample['end']) - max(start, sample['end'] - dt))
        if overlap:
            w = watts(sample)
            energy += w * overlap
            covered += overlap
            weighted.append((w, overlap))
    duration = end - start
    # Receive time can have small jitter. Refuse gross loss or overlapping clocks.
    if abs(covered - duration) > max(0.1, duration * 0.03):
        raise ValueError(f'Incomplete/overlapping samples: {covered:.3f}/{duration:.3f}s')
    if not covered:
        raise ValueError('No samples')
    mean = energy / covered
    variance = sum(dt * (w - mean) ** 2 for w, dt in weighted) / covered
    return dict(joules=energy, seconds=duration, covered_seconds=covered,
                mean_watts=mean, variance_watts2=variance,
                stddev_watts=math.sqrt(variance), samples=len(weighted))


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for kind in ('items', 'raw') for p in (root / kind).rglob('*.json')}


def joined_items(root, before):
    after = snapshot(root)
    changed = sorted(k for k, v in after.items() if before.get(k) != v)
    items = []
    for key in changed:
        if not key.startswith('items/'):
            continue
        row = json.loads((root / key).read_text())
        items.append(dict(path=key, sha256=after[key], lane=row.get('lane'),
                          item_id=row.get('item_id'), status=row.get('status'),
                          correct=row.get('correct')))
    scored = [r for r in items if r['status'] == 'scored' and isinstance(r['correct'], bool)]
    calls = []
    for key in changed:
        if key.startswith('raw/'):
            row = json.loads((root / key).read_text())
            if 'response' in row and 'request' in row:
                calls.append(dict(path=key, sha256=after[key],
                                  phase='judge' if Path(key).name.startswith('judge-') else 'answer'))
    return dict(items=items, scored_items=len(scored), correct_answers=sum(r['correct'] for r in scored),
                requests=len(calls), answer_requests=sum(r['phase'] == 'answer' for r in calls),
                judge_requests=sum(r['phase'] == 'judge' for r in calls), raw_requests=calls)


def report(samples, baseline_window, run_window, joined):
    baseline = integrate(samples, *baseline_window)
    run = integrate(samples, *run_window)
    net = run['joules'] - baseline['mean_watts'] * run['seconds']
    return dict(baseline=baseline, benchmark=run, net_joules=net,
                joules_per_request=net / joined['requests'] if joined['requests'] else None,
                joules_per_answer_request=net / joined['answer_requests'] if joined['answer_requests'] else None,
                joules_per_scored_item=net / joined['scored_items'] if joined['scored_items'] else None,
                joules_per_correct_answer=net / joined['correct_answers'] if joined['correct_answers'] else None,
                join=joined, warnings=[
                    'Shared the Mac Studio services contribute power; subtraction does not isolate the model.',
                    'CPU+GPU+ANE rail energy estimate, not wall-plug or entire SoC/package energy.',
                    'Window includes reader, judges, idle gaps and orchestration; see raw request counts.',
                    'Negative net energy is retained; zero denominators are null.',
                    'Sample boundary times are remote receive times; 500ms averages are clipped assuming uniform power.'])


class Sampler:
    def __init__(self, host, max_seconds=7200):
        sent = time.time()
        self.p = subprocess.Popen(['timeout', str(max_seconds), 'ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', host,
                                   'python3 -u -c ' + shlex.quote(REMOTE)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.q = queue.Queue()
        def read():
            try:
                for line in self.p.stdout:
                    self.q.put(json.loads(line))
            except Exception as exc:
                self.q.put(exc)
            finally:
                self.q.put(None)
        self.thread = threading.Thread(target=read, daemon=True)
        self.thread.start()
        self.closed = False
        try:
            ready = self.next()
            received = time.time()
            if 'ready' not in ready:
                raise RuntimeError('No remote clock handshake')
        except BaseException:
            self.close()
            raise
        self.offset = ready['ready'] - (sent + received) / 2
        self.clock_uncertainty_s = (received - sent) / 2
        self.samples = []
        self.closed = False

    def next(self):
        try:
            value = self.q.get(timeout=15)
        except queue.Empty:
            raise RuntimeError('Power sampler stalled') from None
        if value is None:
            raise RuntimeError('Power sampler exited; inspect SSH/powermetrics stderr')
        if isinstance(value, Exception):
            raise value
        return value

    def through(self, t):
        while not self.samples or self.samples[-1]['end'] < t:
            row = self.next()
            row['end'] -= self.offset
            watts(row)
            self.samples.append(row)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.p.stdin.close()  # remote heartbeat terminates its owned powermetrics child
        try:
            self.p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.p.terminate()
            self.p.wait(timeout=3)


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--host', default='<lan-address>')
    p.add_argument('--baseline-seconds', type=float, default=10)
    p.add_argument('--max-seconds', type=int, default=7200, help='Maximum remote sampler lifetime')
    p.add_argument('--items-root', type=Path, required=True, help='results/<variant>/<lab>')
    p.add_argument('--out', type=Path, required=True, help='Fresh energy output directory')
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    cmd = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not cmd or a.baseline_seconds < 5 or a.max_seconds <= a.baseline_seconds:
        p.error('A command and baseline of at least 5 seconds are required')
    a.out.mkdir(parents=True, exist_ok=False)
    before = snapshot(a.items_root)
    sampler = Sampler(a.host, a.max_seconds)
    try:
        sampler.through(time.time())
        b0 = time.time()
        b1 = b0 + a.baseline_seconds
        sampler.through(b1)
        # Baseline ends exactly where benchmark starts; never count the wait twice.
        r0 = time.time()
        baseline_window = (r0 - a.baseline_seconds, r0)
        start_mono = time.monotonic()
        proc = subprocess.Popen(cmd)
        while True:
            try:
                proc.wait(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                if sampler.p.poll() is not None:
                    raise RuntimeError('Power sampler died during benchmark')
        r1 = time.time()
        # Reject clock jumps; benchmark timing relies on wall-time clock alignment.
        if abs((r1 - r0) - (time.monotonic() - start_mono)) > 0.1:
            raise RuntimeError('Local clock jumped during run')
        sampler.through(r1)
        result = report(sampler.samples, baseline_window, (r0, r1), joined_items(a.items_root, before))
        result.update(command=cmd, returncode=proc.returncode, host=a.host,
                      clock_offset_seconds=sampler.offset, clock_uncertainty_seconds=sampler.clock_uncertainty_s,
                      baseline_window=baseline_window, benchmark_window=(r0, r1),
                      samplers=SAMPLERS, interval_ms=500)
        write(a.out / 'summary.json', result)
        if proc.returncode:
            raise SystemExit(proc.returncode)
    finally:
        sampler.close()
        write(a.out / 'samples.json', sampler.samples)
        if 'proc' in locals() and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Reversible telemetry patch for oMLX v0.8.3 (no inference changes)."""
import argparse
import hashlib
from pathlib import Path

EXPECTED = 'e430a96ae77dd272699636aca6860d419e2af238042113dc4db36f4c5e396787'
COUNT_ANCHOR = '''    # --- stats ---
    state.stats.cycles += 1
    if copy_cycle:
'''
COUNT_REPLACEMENT = '''    # --- stats ---
    # Efficiency study: count all proposals, including the unvisited rejected suffix.
    if not copy_cycle:
        state.stats.efficiency_proposed = getattr(state.stats, "efficiency_proposed", 0) + k
    state.stats.cycles += 1
    if copy_cycle:
'''
LOG_ANCHOR = '''    total_drafted = sum(stats.depth_drafted) or stats.cycles
'''
LOG_REPLACEMENT = '''    logger.info(
        "EFFICIENCY_MTP[%s] finish=%s accepted=%d proposed=%d copy_accepted=%d copy_proposed=%d",
        uid, finish_reason, stats.accepts, getattr(stats, "efficiency_proposed", 0),
        stats.copy_accepted, stats.copy_drafted,
    )
    total_drafted = sum(stats.depth_drafted) or stats.cycles
'''


def instrument(source):
    if hashlib.sha256(source).hexdigest() != EXPECTED:
        raise ValueError('Source differs from pinned v0.8.3; refusing instrumentation')
    text = source.decode()
    for old, new in [(COUNT_ANCHOR, COUNT_REPLACEMENT), (LOG_ANCHOR, LOG_REPLACEMENT)]:
        if text.count(old) != 1:
            raise ValueError('Instrumentation anchor is not unique')
        text = text.replace(old, new)
    compile(text, 'batch_generator.py', 'exec')
    return text.encode()


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--path', type=Path, required=True, help='Installed omlx/patches/mlx_lm_mtp/batch_generator.py; server stopped')
    p.add_argument('--restore', action='store_true')
    a = p.parse_args()
    backup = a.path.with_suffix('.py.efficiency-backup')
    if a.restore:
        original = backup.read_bytes()
        if hashlib.sha256(original).hexdigest() != EXPECTED or a.path.read_bytes() != instrument(original):
            raise ValueError('Source or backup changed; refusing restore')
        a.path.write_bytes(original)
        backup.unlink()
    else:
        if backup.exists():
            raise ValueError('Backup exists; restore before applying again')
        original = a.path.read_bytes()
        patched = instrument(original)
        backup.write_bytes(original)
        a.path.write_bytes(patched)


if __name__ == '__main__':
    main()

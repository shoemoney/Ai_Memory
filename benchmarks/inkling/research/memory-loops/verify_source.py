"""Verify a provisioned source snapshot against pinned HF metadata."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(directory, evidence):
    records = []
    for row in evidence['files']:
        path = directory / row['rfilename']
        if not path.is_file() or path.stat().st_size != row['size']:
            raise RuntimeError(f'Missing or incorrect size: {path}')
        lfs = row.get('lfs')
        expected = lfs['sha256'] if lfs else row['blobId']
        digest = hashlib.sha256() if lfs else hashlib.sha1()
        if not lfs:
            digest.update(f"blob {row['size']}\0".encode())
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise RuntimeError(f'Hash mismatch: {path}')
        records.append({'file':row['rfilename'], 'size':row['size'], 'verified':True})
    return {'repository':'thinkingmachines/TML-d24-varloop-research',
            'revision':evidence['model_revision'], 'files':records}


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('directory',type=Path)
    a = p.parse_args()
    evidence = json.loads((Path(__file__).resolve().parent / 'source-evidence.json').read_text())
    print(json.dumps(verify(a.directory,evidence),indent=2))

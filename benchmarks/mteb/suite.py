#!/usr/bin/env python3
"""Run one model at a time; failures stay explicit and never become scores."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parent
MODELS=['BAAI/bge-small-en-v1.5','Qwen/Qwen3-Embedding-0.6B',
        'microsoft/harrier-oss-v1-270m','microsoft/harrier-oss-v1-0.6b',
        'BAAI/bge-m3','jinaai/jina-embeddings-v5-text-small','google/embeddinggemma-2',
        'google/embeddinggemma-2@256','google/embeddinggemma-2@128',
        'Qwen/Qwen3-VL-Embedding-2B']

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--models', nargs='+', default=MODELS)
    parser.add_argument('--record-name', default='suite.json')
    args=parser.parse_args()
    lab=Path(os.environ['MTEB_CACHE']).parent
    records=[]
    for model_spec in args.models:
        model, sep, dimension = model_spec.partition('@')
        slug=model.replace('/','__') + (f'__{dimension}d' if sep else '')
        # All evaluation processes exit before the next model loads, releasing GPU memory.
        log=lab/(slug+'.log')
        start=time.monotonic()
        cmd=[sys.executable,str(ROOT/'run.py'),'--model',model]
        if sep: cmd += ['--dimension', dimension]
        if model == 'Qwen/Qwen3-VL-Embedding-2B': cmd += ['--batch-size', '1']
        print('Starting',model_spec,flush=True)
        with log.open('w') as f:
            result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
        row={'model':model,'dimension': int(dimension) if sep else None,'returncode':result.returncode,'elapsed_seconds':time.monotonic()-start}
        if result.returncode:
            tail=log.read_text(errors='replace')[-5000:]
            tail=tail.replace(str(lab),'<scratch>').replace(str(ROOT),'<benchmark>')
            row['error_tail']=tail
        records.append(row)
        (ROOT/'results'/args.record_name).write_text(json.dumps(records,indent=2)+'\n')
        print('Finished',model,'exit',result.returncode,flush=True)
    return int(any(r['returncode'] for r in records))

if __name__=='__main__':
    raise SystemExit(main())

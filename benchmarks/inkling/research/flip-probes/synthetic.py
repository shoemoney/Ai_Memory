"""Generate an explicitly synthetic planted-signal run to exercise report CLIs."""
import argparse
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(1701)
    rows=[]
    for i in range(160):
        signal=rng.normal(size=3)
        pid=f'synthetic-{i:04d}'
        y=signal>0
        for t in range(3):
            rows.append(dict(prompt_id=pid,family=pid,stratum=['recall','two_hop','memory','code'][i%4],
                position=t,token=2,argmax=[1 if y[t] else 2,2,2],token_flip=bool(y[t]),answer_flip=bool(y[0]),
                gate_norm=[float(rng.uniform()),float(rng.uniform())],kl=[float(rng.uniform()),float(rng.uniform())],
                entropy=float(rng.uniform()),margin=float(rng.uniform())))
        np.savez_compressed(a.output/f'{pid}.npz', residual=np.column_stack([signal,rng.normal(size=3)]),
                            message=signal[:,None])
    (a.output/'tokens.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (a.output/'manifest.json').write_text(json.dumps(dict(planned=160,completed=160,synthetic=True,seed=1701)))


if __name__=='__main__':
    main()

"""Shared GPU admission queue. No processes are stopped or reconfigured."""
import argparse,subprocess,sys,time
from common import ROOT,append

def wait(timeout=36000, interval=600):
    start=time.monotonic()
    while True:
        free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip())
        row={'time':time.time(),'waited_seconds':time.monotonic()-start,'free_mib':free,'required_mib':6144}
        append(ROOT/'results'/'gpu-wait.jsonl',row)
        print(row,flush=True,file=sys.stderr)
        if free>=6144: return 'cuda'
        remaining=timeout-(time.monotonic()-start)
        if remaining<=0: return 'cpu'
        time.sleep(min(interval,remaining))

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--timeout',type=float,default=36000); parser.add_argument('--device-only',action='store_true')
    args=parser.parse_args(); selected=wait(timeout=max(0,args.timeout))
    print(selected if args.device_only else 'selected_device='+selected,flush=True)

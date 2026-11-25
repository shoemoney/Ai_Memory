#!/usr/bin/env python3
"""One-at-a-time 8 GB GPU fallback for the 2B visual cell."""
import argparse,json,os,subprocess,sys,time,urllib.request,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--only',choices=['visual']);a=p.parse_args()
    jobs=[('Qwen/Qwen3-VL-Embedding-2B','9f2f7e710d6d81056aa5c0a4f04764fec6bb7bda','visual')]
    deadline=time.monotonic()+9*3600
    for model,rev,kind in jobs:
        if a.only and a.only!=kind:continue
        subprocess.run(['df','-h','/','/data'],check=True)
        assert shutil.disk_usage('/').free>=20*1024**3,'System disk has under 20 GB free; pause before large writes'
        state=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True)
        used,util=[int(x.strip()) for x in state.split(',')]
        assert used<200 and util<5,'GPU is not idle; refusing to load'
        command=[sys.executable,'server.py','--model',model,'--revision',rev,'--device','cuda','--port','39741']
        worker_log=Path(os.environ['MTEB_CACHE']).parent/(kind+'-worker.log')
        output=worker_log.open('w')
        worker=subprocess.Popen(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
        try:
            ready=False;load_deadline=min(deadline,time.monotonic()+1800)
            while worker.poll() is None and time.monotonic()<load_deadline:
                try:
                    with urllib.request.urlopen('http://127.0.0.1:39741',timeout=5) as response:identity=json.load(response)
                    assert identity['model']==model and identity['revision']==rev
                    (ROOT/'results'/(kind+'-worker-identity.json')).write_text(json.dumps(identity,indent=2)+'\n');ready=True;break
                except OSError:time.sleep(5)
            assert ready, 'Worker did not become ready'
            env=os.environ.copy();env['EMBEDDING_ENDPOINT']='http://127.0.0.1:39741'
            command=[sys.executable,'vidore.py','--model',model,'--revision',rev,'--hardware','8 GB NVIDIA GPU']
            subprocess.run(command,cwd=ROOT,env=env,check=True,timeout=max(1,deadline-time.monotonic()))
        finally:
            worker.terminate()
            try:worker.wait(timeout=30)
            except subprocess.TimeoutExpired:worker.kill();worker.wait()
            output.close()
            from resources import clean
            (ROOT/'results'/(kind+'-worker.log')).write_text(clean(worker_log.read_text(errors='replace')))
if __name__=='__main__':main()

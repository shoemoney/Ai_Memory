#!/usr/bin/env python3
"""Run one model at a time, retaining completed cells and bounded failure evidence."""
import json,os,shlex,subprocess,sys,time,urllib.request,uuid
from pathlib import Path
from resources import clean
ROOT=Path(__file__).resolve().parent
LAB=Path('/data/scratch/membench/mteb-large')
HOST=os.environ['MODEL_SSH'];REMOTE='membench-mteb-large-tmp';TOKEN=os.environ['RUN_TOKEN']
models=json.loads((ROOT/'models.json').read_text())
records=[]
def ssh(command,**kwargs):return subprocess.run(['ssh',HOST,command],**kwargs)
def log(): (ROOT/'results'/'suite.json').write_text(json.dumps(records,indent=2)+'\n')
def stop():
    # The owner token and current command must both match before killing our PID.
    cmd=f'''cd ~/{REMOTE} && test "$(cat .owner)" = {shlex.quote(TOKEN)} && if test -f server.pid; then p=$(cat server.pid); c=$(ps -p "$p" -o command=); case "$c" in *membench-mteb-large-tmp*server.py*) kill "$p";; esac; fi'''
    ssh(cmd,capture_output=True)
def admitted():
    p=ssh("memory_pressure | tail -1; sysctl -n kern.memorystatus_vm_pressure_level",capture_output=True,text=True)
    return p.returncode==0 and p.stdout.strip().endswith('\n1') and int(p.stdout.split('percentage: ')[1].split('%')[0])>=40

def main():
    deadline_all=time.monotonic()+9*3600
    tunnel=subprocess.Popen(['ssh','-N','-o','ExitOnForwardFailure=yes','-L','39740:127.0.0.1:39740',HOST])
    (LAB/'tunnel.pid').write_text(str(tunnel.pid)+'\n')
    try:
      for spec in models:
        if time.monotonic()>=deadline_all:break
        model=spec['model'];rev=spec['revision'];start=time.monotonic()
        deadline=min(time.monotonic()+1800,deadline_all)
        while not admitted() and time.monotonic()<deadline:time.sleep(30)
        if not admitted():
            records.append({'model':model,'status':'not run: memory admission remained unavailable','evaluated_queries':0});log();continue
        script='nomic_server.py' if model.startswith('nomic-') else 'server.py'
        env='nomic-venv' if model.startswith('nomic-') else 'venv'
        cmd=f'''cd ~/{REMOTE} && echo $$ > server.pid && exec env HF_HOME="$PWD/hf" XDG_CACHE_HOME="$PWD/cache" "$PWD/{env}/bin/python" "$PWD/{script}" --model {shlex.quote(model)} --revision {shlex.quote(rev)} > server.log 2>&1'''
        worker=subprocess.Popen(['ssh',HOST,cmd])
        try:
          ready=False;limit=min(time.monotonic()+3600,deadline_all)
          while worker.poll() is None and time.monotonic()<limit:
            try:
              with urllib.request.urlopen('http://127.0.0.1:39740',timeout=3) as r:identity=json.load(r)
              if identity['model']==model and identity['revision']==rev:ready=True;break
            except OSError:pass
            time.sleep(5)
          if not ready:raise RuntimeError('Worker failed or exceeded one-hour load limit')
          commands=[]
          if model in ['Qwen/Qwen3-Embedding-4B','Qwen/Qwen3-Embedding-8B','Qwen/Qwen3-VL-Embedding-8B','microsoft/harrier-oss-v1-27b']:
            commands.append([sys.executable,'run.py','--model',model,'--device','mps','--batch-size','4','--resume'])
          if 'VL-Embedding' in model or model.startswith('nomic-'):
            commands.append([sys.executable,'vidore.py','--model',model,'--revision',rev])
          for command in commands:subprocess.run(command,cwd=ROOT,check=True,timeout=max(1,deadline_all-time.monotonic()))
          records.append({'model':model,'status':'complete','elapsed_seconds':time.monotonic()-start})
        except Exception as e:records.append({'model':model,'status':'failed','reason':str(e),'elapsed_seconds':time.monotonic()-start})
        finally:
          stop();worker.wait(timeout=30)
          p=ssh(f'cat ~/{REMOTE}/server.log',capture_output=True,text=True)
          (ROOT/'results'/(model.replace('/','__')+'-worker.log')).write_text(clean(p.stdout))
          log()
    finally:stop();tunnel.terminate();tunnel.wait(timeout=30)
if __name__=='__main__':main()

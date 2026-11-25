#!/usr/bin/env python3
"""One-model Mac scheduler; ten-minute capacity retries and per-cell resumption."""
import argparse,json,os,shlex,subprocess,sys,time,urllib.request
from pathlib import Path
from resources import clean
os.environ['CUDA_VISIBLE_DEVICES']=''
ROOT=Path(__file__).resolve().parent;LAB=Path('/data/scratch/membench/mteb-large')
HOST=os.environ['MODEL_SSH'];TOKEN=(LAB/'.owner').read_text().strip()
DEADLINE=float(os.environ.get('BENCH_DEADLINE',time.time()+9*3600))
SPECS={x['model']:x for x in json.loads((ROOT/'models.json').read_text())}
EVENTS=ROOT/'results/followup-events.jsonl'

def event(kind,**data):
    row={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'event':kind,**data}
    with EVENTS.open('a') as f:f.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)

def ssh(command,timeout=90):return subprocess.run(['ssh','-o','ConnectTimeout=15',HOST,command],capture_output=True,text=True,timeout=timeout)

def identity():
    try:
        with urllib.request.urlopen('http://127.0.0.1:39740',timeout=5) as r:return json.load(r)
    except (OSError,ValueError):return None

def memory():
    try:
        p=ssh("memory_pressure | tail -1; sysctl -n kern.memorystatus_vm_pressure_level",timeout=45)
        if p.returncode:return None
        return {'free_percent':int(p.stdout.split('percentage: ')[1].split('%')[0]),'kernel_level':p.stdout.strip().splitlines()[-1]}
    except (OSError,ValueError,subprocess.TimeoutExpired):return None

def pause():
    end=min(DEADLINE,time.time()+600)
    while time.time()<end:time.sleep(min(15,end-time.time()))

def stop():
    cmd=f'''cd ~/membench-mteb-large-tmp && test "$(cat .owner)" = {shlex.quote(TOKEN)} && if test -f server.pid; then p=$(cat server.pid); c=$(ps -p "$p" -o command=); case "$c" in *membench-mteb-large-tmp*server.py*) kill "$p";; esac; fi'''
    ssh(cmd)
    end=time.time()+45
    while time.time()<end:
        if identity() is None:return
        time.sleep(1)
    raise RuntimeError('Owned worker did not stop')

def purge_model_cache():
    cmd=f'''cd ~/membench-mteb-large-tmp && test "$(cat .owner)" = {shlex.quote(TOKEN)} && rm -rf hf modules converted'''
    p=ssh(cmd);assert p.returncode==0,p.stderr

def complete(job):
    model,mode,engine,bits,floor=job;slug=model.replace('/','__')
    if mode=='text':
        out=ROOT/'results/local'/slug
        if not all((out/(t+'.json')).exists() and (out/(t+'.jsonl.gz')).exists() for t in ['SciFact','NFCorpus','ArguAna']):return False
        cfg=json.loads((out/'config.json').read_text());ex=cfg.get('execution',{})
        return ex.get('engine')==engine and ex.get('bits')==bits
    p=ROOT/'results/vidore'/slug/'summary.json'
    if not p.exists():return False
    s=json.loads(p.read_text());ex=s.get('execution',{})
    return s['n_queries']==318 and ex.get('engine')==engine and ex.get('bits')==bits

def existing_client(job):
    model,mode,*_=job;script='run.py' if mode=='text' else 'vidore.py'
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args=p.read_bytes().split(b'\0')
            if len(args)>2 and args[0].decode(errors='ignore').startswith(str(LAB/'venv')) and Path(args[1].decode()).name==script and model.encode() in args:return int(p.parent.name)
        except OSError:pass
    return None

def run_job(job,allow_defer=False):
    model,mode,engine,bits,floor=job;spec=SPECS[model];slug=model.replace('/','__')
    if complete(job):event('already_complete',model=model,mode=mode);return True
    if model=='microsoft/harrier-oss-v1-27b':
        reference=ROOT/'results/local/Qwen__Qwen3-Embedding-8B/SciFact.json'
        if reference.exists():
            estimate=json.loads(reference.read_text())['elapsed_seconds']*3.6*1.15
            remaining=DEADLINE-time.time()-120
            if estimate>remaining:
                event('deferred_for_time',model=model,mode=mode,estimated_first_task_seconds=estimate,
                      remaining_seconds=max(0,remaining),basis='Same-host 8B elapsed time times 3.6 parameter-scale heuristic and 15 percent contingency; no quality score used')
                return False
    attempt=0
    while time.time()<DEADLINE-120:
        attempt+=1
        running=existing_client(job)
        if running:
            event('adopt_running_client',model=model,mode=mode,pid=running)
            while time.time()<DEADLINE-120 and existing_client(job):time.sleep(15)
            captured=ssh('cat ~/membench-mteb-large-tmp/server.log')
            if captured.returncode==0:(ROOT/'results'/f'{slug}-{mode}-worker.log').write_text(clean(captured.stdout))
            if complete(job):
                stop()
                checker='verify.py' if mode=='text' else 'verify_visual.py'
                subprocess.run([sys.executable,checker],cwd=ROOT,check=True)
                purge_model_cache();event('complete',model=model,mode=mode);return True
            deferred=ROOT/'results/local'/slug/'deferred.json'
            if mode=='text' and deferred.exists():
                stop();subprocess.run([sys.executable,'verify.py'],cwd=ROOT,check=True)
                event('phase_deferred_for_time',model=model,mode=mode,details=json.loads(deferred.read_text()))
                purge_model_cache();return True
            if time.time()>=DEADLINE-120:
                active=existing_client(job)
                if active:
                    import signal
                    os.kill(active,signal.SIGTERM)
                stop();event('budget_boundary',model=model,mode=mode);return False
        current=identity()
        adopted=current and current['model']==model and current['revision']==spec['revision'] and current.get('execution',{}).get('engine')==engine and current.get('execution',{}).get('bits')==bits
        worker=None
        if not adopted:
            stop()
            observation=memory();event('admission_probe',model=model,mode=mode,bits=bits,required_percent=floor,observation=observation)
            if not observation or observation['free_percent']<floor or observation['kernel_level'] in ('2','4'):
                if allow_defer:event('deferred_for_capacity',model=model);return False
                pause();continue
            subprocess.run(['df','-h','/','/data'],check=True)
            assert __import__('shutil').disk_usage('/').free>=20*1024**3,'System filesystem below 20 GiB free'
            script='mlx_server.py' if engine=='MLX' else ('harrier_server.py' if engine=='MLX-LM' else ('nomic_server.py' if model.startswith('nomic-') else 'server.py'))
            env='mlx-venv' if engine=='MLX' else ('lm-venv' if engine=='MLX-LM' else ('nomic-venv' if model.startswith('nomic-') else 'venv'))
            files=['server.py','mlx_server.py','nomic_server.py','memory_guard.py','quantize.py','instructions.json','harrier_server.py','quantize_mlx.py']
            subprocess.run(['scp','-q',*files,HOST+':membench-mteb-large-tmp/'],cwd=ROOT,check=True)
            flags=f' --bits {bits}' if bits else ''
            command=f'''cd ~/membench-mteb-large-tmp && echo $$ > server.pid && exec env HF_HOME="$PWD/hf" HF_MODULES_CACHE="$PWD/modules" XDG_CACHE_HOME="$PWD/cache" UV_CACHE_DIR="$PWD/uv" PIP_CACHE_DIR="$PWD/pip" "$PWD/{env}/bin/python" "$PWD/{script}" --model {shlex.quote(model)} --revision {shlex.quote(spec['revision'])}{flags} > server.log 2>&1'''
            worker=subprocess.Popen(['ssh',HOST,command])
            ready_until=min(DEADLINE-120,time.time()+3600)
            while time.time()<ready_until and worker.poll() is None:
                current=identity()
                if current and current['model']==model and current['revision']==spec['revision']:break
                time.sleep(5)
            else:current=None
            if not current:
                stop();p=ssh('cat ~/membench-mteb-large-tmp/server.log')
                (ROOT/'results'/f'{slug}-{mode}-load-attempt-{attempt}.log').write_text(clean(p.stdout))
                event('load_failed',model=model,mode=mode,returncode=worker.poll());pause();continue
        else:event('adopt_ready_worker',model=model,mode=mode)
        target=LAB/(slug+'-'+mode+'-client.log')
        batch=32 if engine=='MLX' else 16
        if mode=='text':
            command=[sys.executable,'run.py','--model',model,'--device','mlx' if engine.startswith('MLX') else 'mps','--batch-size',str(batch)]
            config=ROOT/'results/local'/slug/'config.json'
            if config.exists():
                cfg=json.loads(config.read_text())
                if cfg.get('execution')=={k:v for k,v in current.get('execution',{}).items() if not k.endswith('_record_only')} and cfg.get('batch_size')==batch:command+=['--resume']
        else:command=[sys.executable,'vidore.py','--model',model,'--revision',spec['revision'],'--hardware','Apple M3 Ultra, 96 GB']
        event('evaluation_started',model=model,mode=mode,execution=current.get('execution'),batch_size=batch)
        try:
            with target.open('a') as f:p=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=max(1,DEADLINE-time.time()-120))
            status=p.returncode
        except subprocess.TimeoutExpired:status=124
        finally:
            stop()
            if worker:
                try:worker.wait(timeout=30)
                except subprocess.TimeoutExpired:worker.terminate()
            p=ssh('cat ~/membench-mteb-large-tmp/server.log')
            if p.returncode==0:(ROOT/'results'/f'{slug}-{mode}-worker.log').write_text(clean(p.stdout))
        if status==0 and complete(job):
            checker='verify.py' if mode=='text' else 'verify_visual.py'
            subprocess.run([sys.executable,checker],cwd=ROOT,check=True)
            event('complete',model=model,mode=mode);purge_model_cache();return True
        deferred=ROOT/'results/local'/slug/'deferred.json'
        if status==0 and mode=='text' and deferred.exists():
            subprocess.run([sys.executable,'verify.py'],cwd=ROOT,check=True)
            event('phase_deferred_for_time',model=model,mode=mode,details=json.loads(deferred.read_text()))
            purge_model_cache();return True
        event('evaluation_interrupted',model=model,mode=mode,returncode=status)
        pause()
    event('budget_boundary',model=model,mode=mode);return False

def main():
    first=('Qwen/Qwen3-Embedding-4B','text','MLX',8,40)
    regular=[first,('Qwen/Qwen3-Embedding-8B','text','MLX',4,40),
             ('Qwen/Qwen3-VL-Embedding-8B','text','MLX',4,42)]
    large=('microsoft/harrier-oss-v1-27b','text','MLX-LM',4,54)
    visual=[('nomic-ai/nomic-embed-multimodal-7b','visual','PyTorch MPS',4,42),
            ('Qwen/Qwen3-VL-Embedding-8B','visual','MLX',4,42)]
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');parser.add_argument('--visual-first',action='store_true',help='run the visual jobs before remaining text jobs');args=parser.parse_args()
    (LAB/'controller.pid').write_text(str(os.getpid())+'\n')
    if not args.resume:
        import shutil
        for model,mode,*_ in regular+[large]+visual:
            target=ROOT/('results/local' if mode=='text' else 'results/vidore')/model.replace('/','__')
            if target.exists():
                shutil.copytree(target,LAB/'previous-results'/mode/model.replace('/','__'),dirs_exist_ok=True)
                shutil.rmtree(target)
    event('followup_started',hardware='Apple M3 Ultra, 96 GB',deadline_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(DEADLINE)))
    try:
        if args.visual_first:
            for job in visual:
                if not run_job(job):return
        for job in regular:
            if not run_job(job):return
        large_done=run_job(large,allow_defer=True)
        if not args.visual_first:
            for job in visual:
                if not run_job(job):return
        if not large_done:run_job(large)
    finally:stop();event('followup_finished')
if __name__=='__main__':main()

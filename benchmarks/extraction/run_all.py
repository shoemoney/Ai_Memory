"""One-command Mac serving, dev scoring and ownership-checked cleanup."""
import hashlib, json, os, re, shlex, subprocess, sys, time, urllib.request, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TARGET=os.environ.get('SSH_TARGET')
if not TARGET: raise SystemExit('Set SSH_TARGET to the SSH destination of an Apple Silicon model-serving host.')
OWNER='membench-extraction-'+uuid.uuid4().hex
MODELS=json.loads((ROOT/'models.json').read_text())
LAB='~/membench-extraction-tmp'

def ssh(command,check=True):
    p=subprocess.run(['ssh',TARGET,command],capture_output=True,text=True)
    if check and p.returncode: raise RuntimeError('Remote operation failed (details omitted to avoid recording host identity).')
    return p.stdout

def snapshot(name):
    raw=ssh('df -h ~; memory_pressure -Q; sysctl -n kern.memorystatus_vm_pressure_level; ps -axo pid=,ucomm=,rss=; lsof -nP -iTCP -sTCP:LISTEN')
    # Save measurements and process basenames, never account names or addresses.
    lines=raw.splitlines(); cleaned=[]
    for line in lines:
        if '/System/Volumes/Data' in line: cleaned.append(re.sub(r'/System/Volumes/Data','<data-volume>',line))
        elif 'memory free percentage' in line or line.strip().isdigit(): cleaned.append(line)
        elif re.match(r'^\s*\d+\s+\S+',line):
            parts=line.split(); cleaned.append('process '+parts[0]+' '+Path(parts[1]).name+' rss_kib='+parts[-1])
        elif '(LISTEN)' in line:
            parts=line.split(); cleaned.append('listener '+parts[0]+' pid='+parts[1]+' port='+parts[-2].rsplit(':',1)[-1])
    (ROOT/'results'/name).write_text('\n'.join(cleaned)+'\n')

def pressure():
    raw=ssh('memory_pressure -Q; sysctl -n kern.memorystatus_vm_pressure_level')
    free=int(re.search(r'free percentage: (\d+)%',raw)[1]); level=int(raw.strip().splitlines()[-1])
    if free<40 or level!=1: raise RuntimeError('Insufficient memory for a new model load.')
    return free

def stop():
    ssh("if [ -f ~/membench-extraction-tmp/server.pid ]; then p=$(cat ~/membench-extraction-tmp/server.pid); case $p in ''|*[!0-9]*) exit 1;; esac; args=$(ps -p $p -o args=); case $args in *llama-server*39740*) kill $p; while kill -0 $p 2>/dev/null; do sleep 1; done;; '') :;; *) exit 1;; esac; rm ~/membench-extraction-tmp/server.pid; fi")

def start(model):
    pressure()
    path=model['id']+'.gguf'
    ssh('cd '+LAB+' && if [ ! -f '+shlex.quote(path)+' ]; then curl -LfsS --retry 2 '+shlex.quote(model['url'])+' -o '+shlex.quote(path)+'; fi')
    digest=ssh('cd '+LAB+' && shasum -a 256 '+shlex.quote(path)).split()[0]
    if model['sha256'] and digest!=model['sha256']: raise RuntimeError('Model hash mismatch')
    model['sha256']=digest
    (ROOT/'results/model-hashes.json').write_text(json.dumps(MODELS,indent=2)+'\n')
    pressure()
    args=['/opt/homebrew/bin/llama-server','-m',path,'--alias','extractor','--host','localhost','--port','39740','-c','4096','-np','1','--cache-ram','0','--jinja','--chat-template-kwargs','{"enable_thinking":false}']
    ssh('cd '+LAB+'; nohup '+shlex.join(args)+' > server.log 2>&1 < /dev/null & echo $! > server.pid')
    for _ in range(90):
        try:
            with urllib.request.urlopen(os.environ.get('BASE_URL','http://localhost:39740/v1').removesuffix('/v1')+'/health',timeout=2) as r:
                if json.load(r).get('status')=='ok': return
        except OSError: pass
        time.sleep(1)
    log=ssh('tail -30 '+LAB+'/server.log')
    log=re.sub(r'/Users/[^/\s]+','<home>',log)
    log=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','<address>',log)
    (ROOT/'results'/(model['id']+'-failure.txt')).write_text(log)
    raise RuntimeError('Server did not become healthy')

def main():
    (ROOT/'results').mkdir(exist_ok=True)
    version=ssh('/opt/homebrew/bin/llama-server --version 2>&1')
    if '12359' not in version or 'b1b770d90' not in version: raise RuntimeError('Pinned llama.cpp version required')
    snapshot('before-driver.txt')
    if os.environ.get('ADOPT_LAB')=='1':
        ssh('test -d '+LAB+' && test ! -L '+LAB+' && test ! -f '+LAB+'/.owner')
    else:
        ssh('test ! -e '+LAB+' && test ! -L '+LAB+' && mkdir '+LAB)
    ssh('printf %s '+shlex.quote(OWNER)+' > '+LAB+'/.owner')
    tunnel=subprocess.Popen(['ssh','-N','-o','ExitOnForwardFailure=yes','-L','localhost:39741:localhost:39740',TARGET],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.environ['BASE_URL']='http://localhost:39741/v1'
    monitor=subprocess.Popen([sys.executable,str(ROOT/'monitor.py')],env=os.environ)
    failures=[]
    try:
        for model in MODELS:
            file=ROOT/'results'/(model['id']+'.jsonl')
            if file.exists() and len(file.read_text().splitlines())==300: continue
            stop()
            print('starting',model['id'],flush=True)
            try:
                start(model)
                subprocess.run([sys.executable,str(ROOT/'bench.py'),'run','--model',model['id']],check=True,env=os.environ)
                if monitor.poll() is not None: raise RuntimeError('Memory monitor stopped')
            except RuntimeError as e:
                failures.append({'model':model['id'],'error':str(e)}); print(str(e),flush=True)
            finally: stop()
        # The predeclared judge is loaded once, then validation gates all scoring.
        judge=next(m for m in MODELS if m['id']=='qwen3.5-9b-q4_k_m')
        start(judge)
        subprocess.run([sys.executable,str(ROOT/'judge.py'),'validate'],check=True,env=os.environ)
        subprocess.run([sys.executable,str(ROOT/'judge.py'),'score'],check=True,env=os.environ)
    finally:
        stop(); monitor.terminate(); monitor.wait(timeout=10); tunnel.terminate(); tunnel.wait(timeout=10)
        (ROOT/'results/failures.json').write_text(json.dumps(failures,indent=2)+'\n')
        ssh('test ! -L '+LAB+' && test "$(cat '+LAB+'/.owner)" = '+shlex.quote(OWNER)+' && rm -rf '+LAB)
        snapshot('after-cleanup.txt')
        (ROOT/'results/cleanup.json').write_text(json.dumps({'remote_scratch_absent':ssh('test ! -e '+LAB+' && echo yes').strip()=='yes','owned_server_stopped':True,'driver_tunnel_closed':tunnel.poll() is not None,'monitor_stopped':monitor.poll() is not None},indent=2)+'\n')
        subprocess.run([sys.executable,str(ROOT/'bench.py'),'summary'],check=True)
        subprocess.run([sys.executable,str(ROOT/'check_harness.py')],check=True)
        subprocess.run([sys.executable,str(ROOT/'verify_results.py')],check=True)
        subprocess.run([sys.executable,str(ROOT/'write_report.py')],check=True)

if __name__=='__main__': main()

import json, math, os, random, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent
SCRATCH = Path(os.environ.get('PARAM_SCRATCH', '/data/scratch/membench/param-reruns'))
os.environ['HF_HOME'] = str(SCRATCH / 'hf')
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

def append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as f:
        f.write(json.dumps(row) + '\n'); f.flush(); os.fsync(f.fileno())

def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []

def device(requested):
    if requested == 'cpu': return 'cpu'
    free = int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'], text=True).strip())
    append(ROOT / 'results' / 'gpu-admission.jsonl', {'time': time.time(), 'free_mib': free, 'required_mib': 6144})
    if free < 6144: raise RuntimeError('GPU admission requires at least 6144 MiB free')
    return 'cuda'

def setup(threads=None):
    import torch
    torch.set_num_threads(threads or int(os.environ.get("PARAM_THREADS", "4")))
    torch.manual_seed(42)
    random.seed(42)

def interval(values):
    n = len(values)
    if not n: return None
    p = sum(values)/n; z=1.959963984540054
    center=(p+z*z/(2*n))/(1+z*z/n)
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return {'n':n,'rate':p,'ci95':[center-half,center+half]}

def paired(a,b):
    if len(a)!=len(b) or not a: raise ValueError('Need complete nonempty pairs')
    d=[y-x for x,y in zip(a,b)]; rng=random.Random(42)
    boots=sorted(sum(rng.choices(d,k=len(d)))/len(d) for _ in range(20000))
    return {'n':len(d),'difference':sum(d)/len(d),'bootstrap_ci95':[boots[499],boots[19499]],'replicates':20000,'seed':42}

def start_memory_guard(where):
    """Release only our own CPU worker before shared-host swap exhaustion."""
    if where!='cpu': return
    import signal, threading
    def reading():
        fields={}
        for line in Path('/proc/meminfo').read_text().splitlines():
            key,value=line.split(':',1); fields[key]=int(value.strip().split()[0])
        return fields
    def critical(fields):
        available=fields['MemAvailable']; swap=fields.get('SwapFree',0)
        return available<3*1024*1024 or (fields.get('SwapTotal',0)>0 and (swap<128*1024 or (available<6*1024*1024 and swap<512*1024)))
    fields=reading()
    if critical(fields):
        append(ROOT/'results'/'resource-stops.jsonl',{'time':time.time(),'stage':'before CPU model load','available_kib':fields['MemAvailable'],'swap_free_kib':fields.get('SwapFree',0)})
        raise RuntimeError('Shared host memory is critical; CPU model load deferred')
    def watch():
        while True:
            time.sleep(1)
            fields=reading()
            if critical(fields):
                append(ROOT/'results'/'resource-stops.jsonl',{'time':time.time(),'stage':'own CPU worker stopped','pid':os.getpid(),'available_kib':fields['MemAvailable'],'swap_free_kib':fields.get('SwapFree',0)})
                os.kill(os.getpid(),signal.SIGTERM)
                return
    threading.Thread(target=watch,daemon=True).start()

def save_torch(obj,path):
    """Replace a checkpoint only after its complete bytes are flushed."""
    import torch
    path=Path(path); temporary=path.with_name(path.name+'.tmp-'+str(os.getpid()))
    with temporary.open('wb') as f:
        torch.save(obj,f); f.flush(); os.fsync(f.fileno())
    os.replace(temporary,path)

import hashlib
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.request
from pathlib import Path

import lab

lab.RETRIEVAL.update(key_bodies='--key-bodies' in sys.argv,
                     sentences='--sentences' in sys.argv)
if '--single-ingestion' in sys.argv:
    original_stage = lab.stage
    lab.stage = lambda number: original_stage(number, ingestions=1)
VARIANT = '-sentences' if lab.RETRIEVAL['sentences'] else ''
ROOT = Path('/var/tmp/memlab-20')
PINS = {
    '4': ('391fc7d103e3942a408def3e4f51c2f85d464417',
          'dec96e8cf2e11b613bb46513dec485377f9ca5a351e71712ee0e244f287c6790'),
    '9': ('760121cd70bb4c36b2b5ec58eb765e0df5987efe',
          'df13d66021cef676f82be74053220fd75af6bf2a6a7fb77f5222ab9e50744a7a'),
}
IMAGE = 'ghcr.io/ggml-org/llama.cpp:server-b12464'
NAME = 'memlab-20-writer'


def run(args, timeout=900):
    return subprocess.check_output(args, text=True, timeout=timeout)



def download(size):
    revision, checksum = PINS[size]
    repo = f'empero-ai/Qwen3.8-{size}B-Distill-GGUF'
    filename = f'Qwen3.8-{size}B-Q4_K_M.gguf'
    path = ROOT/filename
    api = f'https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true'
    with urllib.request.urlopen(api,timeout=30) as response:
        metadata = json.load(response)
    item = next(x for x in metadata['siblings'] if x['rfilename']==filename)
    total = item['size']
    if item['lfs']['sha256']!=checksum:
        raise ValueError('Published checksum differs from pin')
    if path.exists() and path.stat().st_size==total:
        return path
    parts = ROOT/f'parts-{size}b'
    if parts.is_symlink():
        raise ValueError('Part directory is a symlink')
    parts.mkdir(exist_ok=True)
    width = (total+7)//8
    # Preserve a sequential prefix from an interrupted transfer.
    if path.exists():
        with path.open('rb') as stream:
            for i in range(8):
                chunk = stream.read(width)
                if chunk:
                    (parts/str(i)).write_bytes(chunk)
        path.unlink()
    url = f'https://huggingface.co/{repo}/resolve/{revision}/{filename}?download=true'

    def fetch(i):
        begin, end = i*width, min((i+1)*width,total)-1
        part = parts/str(i)
        for attempt in range(3):
            have = part.stat().st_size if part.exists() else 0
            if have==end-begin+1:
                return
            start = begin+have
            req = urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
            try:
                with urllib.request.urlopen(req,timeout=30) as response:
                    wanted = f'bytes {start}-{end}/{total}'
                    if response.status!=206 or response.headers.get('Content-Range')!=wanted:
                        raise ValueError('Server did not honor the exact range')
                    deadline = time.monotonic()+900
                    with part.open('ab') as target:
                        while time.monotonic()<deadline:
                            data = response.read(4*1024*1024)
                            if not data:
                                break
                            target.write(data)
                        else:
                            raise TimeoutError('Range transfer deadline exceeded')
                if part.stat().st_size==end-begin+1:
                    print(size+'B range',i,'complete',flush=True)
                    return
            except (OSError,ValueError) as error:
                print(size+'B range',i,'attempt',attempt+1,type(error).__name__,flush=True)
        raise RuntimeError('Range download did not complete')

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(fetch,range(8)))
    temporary = ROOT/(filename+'.download')
    with temporary.open('wb') as target:
        for i in range(8):
            with (parts/str(i)).open('rb') as source:
                shutil.copyfileobj(source,target)
    with temporary.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=checksum:
            raise ValueError('Assembled model checksum mismatch')
    temporary.replace(path)
    return path


def compare(size):
    revision, checksum = PINS[size]
    token = (ROOT/'.owner').read_text()
    if ROOT.resolve()!=ROOT or (ROOT/'.path').read_text()!=str(ROOT):
        raise SystemExit('STOP: not the owned lab path')
    exists = subprocess.run(['docker','inspect',NAME],capture_output=True)
    if exists.returncode==0:
        raise SystemExit('STOP: writer container already exists')
    filename = f'Qwen3.8-{size}B-Q4_K_M.gguf'
    path = ROOT/filename
    path = download(size)
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream,'sha256').hexdigest()
    if actual!=checksum:
        raise SystemExit('STOP: writer checksum mismatch')
    run(['docker','run','-d','--name',NAME,'--label','memlab-20='+token,
         '--cpus','4','-m','8g','-p','127.0.0.1:39204:8080',
         '-v',str(ROOT)+':/models:ro',IMAGE,'-m','/models/'+filename,
         '--alias','writer','--host','0.0.0.0','--port','8080',
         '-t','4','-c','4096','--parallel','1','-ngl','0','--jinja',
         '--chat-template-kwargs','{"enable_thinking":false}'])
    old_chat, old_http = lab.chat, lab.http
    audit_path = ROOT/f'writer-{size}b{VARIANT}-requests.jsonl'
    try:
        end = time.monotonic()+180
        while time.monotonic()<end:
            try:
                urllib.request.urlopen('http://127.0.0.1:39204/health',timeout=2)
                break
            except Exception:
                time.sleep(1)
        else:
            print(run(['docker','logs','--tail','30',NAME],timeout=10))
            raise SystemExit('STOP: writer readiness timed out')
        # Only the schema-bearing extraction calls use the larger model.
        # The original chat function builds every prompt and validates responses.
        with audit_path.open('w') as audit:
            def route(port, endpoint, body):
                if port!=39203:
                    raise ValueError('Unexpected writer route')
                body = dict(body, model='writer')
                result = old_http(39204, endpoint, body)
                audit.write(json.dumps(dict(request=body,response=result))+'\n')
                audit.flush()
                print(size+'B extraction',audit.tell(),'bytes recorded',flush=True)
                return result

            def chat(question, memory, schema=None):
                if schema is None:
                    return old_chat(question,memory,schema)
                lab.http = route
                try:
                    return old_chat(question,memory,schema)
                finally:
                    lab.http = old_http

            lab.chat = chat
            lab.stage(5)
        shutil.copyfile(ROOT/'stage-5.json',ROOT/f'stage-5-{size}b{VARIANT}.json')
        for rep in range(1,2 if '--single-ingestion' in sys.argv else 4):
            shutil.copyfile(ROOT/f'writes-5-{rep}.json',
                            ROOT/f'writes-5-{size}b{VARIANT}-{rep}.json')
        meta = dict(size=size,repository=f'empero-ai/Qwen3.8-{size}B-Distill-GGUF',
                    revision=revision,file=filename,sha256=actual,
                    license='Apache-2.0',community=True,device='CPU',
                    threads=4,memory_limit_gib=8,answer_model='unchanged 2B',
                    request_audit=str(audit_path))
        (ROOT/f'writer-{size}b{VARIANT}-model.json').write_text(json.dumps(meta,indent=2))
        print(json.dumps(meta),flush=True)
    finally:
        lab.chat, lab.http = old_chat, old_http
        inspected = subprocess.run(['docker','inspect',NAME],capture_output=True,text=True)
        if inspected.returncode==0:
            obj=json.loads(inspected.stdout)[0]
            if obj['Config']['Labels'].get('memlab-20')!=token:
                raise SystemExit('STOP: writer owner mismatch')
            run(['docker','rm','-fv',NAME],timeout=30)


if __name__=='__main__':
    for size in (['4','9'] if sys.argv[1]=='all' else [sys.argv[1]]):
        compare(size)

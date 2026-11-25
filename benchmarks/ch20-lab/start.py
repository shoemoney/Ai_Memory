import json
import os
import socket
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

ROOT = Path('/var/tmp/memlab-20')
NAMES = ['pg', 'cache', 'embed', 'llama']
IMAGES = [
    'pgvector/pgvector@sha256:'
    '38681dc6eaf55308e2a4c6de392d131652dcfac70e1263e35cd9b5ea3fe39782',
    'memcached:1.6.45',
    'ghcr.io/huggingface/text-embeddings-inference:cpu-1.9',
    'ghcr.io/ggml-org/llama.cpp:server-b12464',
]
# An embedding download, Python installation and all caches stay in ROOT.
FILES = ['lab.py', 'fixture.py', 'stale.py', 'cleanup.py', 'start.py', 'writers.py']
sources = globals().get('SOURCE_FILES')
if sources is None:
    sources = {f: (Path(__file__).resolve().parent/f).read_text() for f in FILES}
if ROOT.exists() or ROOT.is_symlink():
    raise SystemExit('STOP: lab path already exists')
for name in NAMES:
    r = subprocess.run(['docker', 'container', 'inspect', 'memlab-20-'+name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r.returncode == 0:
        raise SystemExit('STOP: container already exists')
for port in range(39200, 39204):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))
ROOT.mkdir()
token = uuid.uuid4().hex
(ROOT/'.owner').write_text(token)
(ROOT/'.path').write_text(str(ROOT.resolve()))
for name in FILES:
    (ROOT/name).write_text(sources[name])

def run(args):
    return subprocess.check_output(args, text=True, timeout=900)

(ROOT/'before.txt').write_text(run(['df','-h','/var/tmp'])+
    run(['docker','ps','--format','{{.Names}} {{.Image}} {{.Status}}']))
(ROOT/'images-before.txt').write_text(run(['docker','image','ls','-q','--no-trunc']))
(ROOT/'images.json').write_text(json.dumps(IMAGES))
model_url = ('https://huggingface.co/empero-ai/Qwen3.8-2B-Distill-GGUF/resolve/'
             'f4f73582d0b149595450c719b9a7521a03894f9c/Qwen3.8-2B-Q4_K_M.gguf')
run(['curl','-fL','--connect-timeout','30','--max-time','900',
     '-o',str(ROOT/'chat.gguf'),model_url])
import hashlib
sha = hashlib.file_digest(open(ROOT/'chat.gguf','rb'),'sha256').hexdigest()
if sha != '4aa0fb13c431514262f259d420ecc95a8714df58ac2a2384514e20b93983f0ff':
    raise SystemExit('STOP: model checksum mismatch')
os.environ.update(UV_CACHE_DIR=str(ROOT/'uv'),
                  UV_PYTHON_INSTALL_DIR=str(ROOT/'python'))
run(['uv','python','install','3.13.18'])
run(['uv','venv','--python','3.13.18',str(ROOT/'venv')])
run(['uv','pip','install','--python',str(ROOT/'venv/bin/python'),
     'psycopg[binary]==3.2.9','pymemcache==4.0.0'])
extra = [
    ['-e','POSTGRES_PASSWORD=local-demo','-p','127.0.0.1:39200:5432',
     '-v',str(ROOT/'pg')+':/var/lib/postgresql'],
    ['-p','127.0.0.1:39201:11211'],
    ['--cpus','2','-m','2g','-p','127.0.0.1:39202:80',
     '-v',str(ROOT/'hf')+':/data'],
    ['--cpus','4','-m','4g','-p','127.0.0.1:39203:8080',
     '-v',str(ROOT)+':/models:ro'],
]
flags = [[], [], ['--model-id','BAAI/bge-small-en-v1.5','--revision',
         '5c38ec7c405ec4b44b94cc5a9bb96e735b38267a'],
         ['-m','/models/chat.gguf','--alias','qwen38','--host','0.0.0.0',
          '--port','8080','-t','4','-c','4096','-ngl','0','--jinja',
          '--chat-template-kwargs','{"enable_thinking":false}']]
for name,image,args,tail in zip(NAMES,IMAGES,extra,flags):
    run(['docker','run','-d','--name','memlab-20-'+name,
         '--label','memlab-20='+token]+args+[image]+tail)
for name,port in zip(NAMES,range(39200,39204)):
    deadline = time.monotonic()+180
    while time.monotonic() < deadline:
        try:
            if name in ['embed','llama']:
                urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=2)
            elif name=='pg':
                subprocess.run(['docker','exec','memlab-20-pg','pg_isready','-U',
                                'postgres'],check=True,timeout=2,
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                with socket.create_connection(('127.0.0.1',port),timeout=2) as sock:
                    sock.sendall(b'version\r\n')
                    if not sock.recv(100).startswith(b'VERSION'):
                        raise ValueError('cache not ready')
            break
        except Exception:
            time.sleep(1)
    else:
        subprocess.run(['docker','logs','--tail','30','memlab-20-'+name],timeout=10)
        raise SystemExit('STOP: readiness timed out')
run([str(ROOT/'venv/bin/python'),str(ROOT/'fixture.py')])
print('Ready: CPU chat, CPU embedding, Postgres and Memcached; owned lab created.')

"""Shared constants, atomic checkpoints and official BFCL-V4 score weights."""
import hashlib
import json
import os
import tempfile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAB = Path('/var/tmp/membench-bfcl')
RUN_NAME=os.environ.get('RUN_NAME','full')
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',RUN_NAME):raise ValueError('RUN_NAME must be a simple folder name')
RUN_DIR=ROOT/'results'/RUN_NAME
SEED = 20261121
TOKEN_CAP = 16384
EMBED_REVISION = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
NONLIVE = ['simple_python','simple_java','simple_javascript','multiple','parallel','parallel_multiple']
LIVE = ['live_simple','live_multiple','live_parallel','live_parallel_multiple']
IRRELEVANCE = ['irrelevance','live_irrelevance']
MULTI = ['multi_turn_base','multi_turn_miss_func','multi_turn_miss_param','multi_turn_long_context']
MEMORY = ['memory_kv','memory_vector','memory_rec_sum']
CATEGORIES = NONLIVE + LIVE + IRRELEVANCE + MULTI + MEMORY + ['live_relevance']
MODELS = {
 '0.8B': ('6ab461498e2023f6e3c1baea90a8f0fe38ab64d0','bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517'),
 '2B': ('f6d5376be1edb4d416d56da11e5397a961aca8ae','aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223'),
 '4B': ('e87f176479d0855a907a41277aca2f8ee7a09523','00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4'),
 '9B': ('3885219b6810b007914f3a7950a8d1b469d598a5','03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8'),
}
PUBLISHED = {'0.8B':25.3,'2B':43.6,'4B':50.3,'9B':66.1}

def atomic(path, value):
 path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
 tmp_file = tempfile.NamedTemporaryFile(mode='w',dir=path.parent,prefix=path.name+'.',suffix='.tmp',delete=False)
 tmp=Path(tmp_file.name)
 with tmp_file as f:
  json.dump(value,f,ensure_ascii=False,indent=2,default=str); f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()

def weights(populations):
 """Leaf weights from upstream eval_runner_helper.generate_score_csv composition."""
 w={}
 for c in NONLIVE[:3]:w[c]=.10/4/3
 for c in NONLIVE[3:]:w[c]=.10/4
 live_total=sum(populations[c] for c in LIVE)
 for c in LIVE:w[c]=.10*populations[c]/live_total
 for c in IRRELEVANCE:w[c]=.10/2
 for c in MULTI:w[c]=.30/4
 for c in MEMORY:w[c]=.20/3
 # Both web-search variants together have the missing .20 weight.
 return w

def absence_credits(category,valid,message):
 if not valid or 'irrelevance' not in category:return False,False
 content=(message.get('content')or'').strip()
 empty=not message.get('tool_calls') and content in ('','[]','{}','null','None','```json\n[]\n```')
 malformed=bool(message.get('tool_calls'))
 return empty,malformed


def model_failure_kind(exc):
 """Recognize model-produced context/FC parse failures, not arbitrary HTTP errors."""
 status=getattr(exc,'status_code',None)
 message=str(exc)
 if status==400 and 'exceeds the available context size' in message:return 'context_budget_exhausted'
 if status==500 and 'Failed to parse tool call arguments as JSON' in message:return 'tool_call_parse_failure'
 return None

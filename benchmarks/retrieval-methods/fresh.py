"""Reset only derived benchmark checkpoints for an explicitly requested fresh run."""
from pathlib import Path
import datetime,os,shutil
ROOT=Path(__file__).resolve().parent
LAB=Path(os.environ.get('LAB_DIR','/data/scratch/membench/retrieval-methods')).resolve()
assert LAB in [Path('/data/scratch/membench/retrieval-methods'),ROOT/'.scratch']
active=[]
for process in Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:
  arguments=process.joinpath('cmdline').read_bytes().decode(errors='replace').split('\0')
  local=process.joinpath('cwd').resolve()==ROOT
  benchmark=any(a.endswith('/retrieval-methods/run.py') for a in arguments) or (local and 'run.py' in arguments)
  serving=any(str(LAB)+'/llama/' in a for a in arguments) or (local and 'remote_control.py' in arguments and 'serve' in arguments)
  if benchmark or serving:active.append(int(process.name))
 except OSError:pass
if active:raise SystemExit('Fresh run refused while benchmark processes are active: '+str(active))
archive=LAB/'prior-results'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
archive.mkdir(parents=True,exist_ok=False)
moved=removed=0
for dataset in ['scifact','nfcorpus','longmemeval','locomo']:
 for source in (ROOT/'results').glob(dataset+'.*.jsonl'):
  shutil.move(str(source),str(archive/source.name));moved+=1
 for derived in LAB.glob(dataset+'.*'):
  if derived.is_file() and (derived.suffix=='.npy' or derived.name.endswith(('.data.json','.prefixes.jsonl'))):derived.unlink();removed+=1
print('Fresh run: archived',moved,'result files and removed',removed,'derived scratch files; weights and source downloads retained.')

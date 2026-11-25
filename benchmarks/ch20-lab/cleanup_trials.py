import json,subprocess,uuid,shutil
from pathlib import Path
ROOT=Path('/var/tmp/memlab-20')
SOURCE=Path(__file__).resolve().parent
CLEAN=SOURCE/'cleanup.py'
helper='ubuntu@sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8'
before=subprocess.check_output(['docker','image','ls','-q','--no-trunc'],text=True)
def root(metadata=True):
 ROOT.mkdir();token=uuid.uuid4().hex
 (ROOT/'.owner').write_text(token);(ROOT/'.path').write_text(str(ROOT))
 if metadata:
  (ROOT/'images.json').write_text('[]');(ROOT/'images-before.txt').write_text(before)
 return token
def clean(expected):
 p=subprocess.run(['python3',str(CLEAN)],capture_output=True,text=True,cwd='/var/tmp')
 assert (p.returncode==0)==expected,(p.returncode,p.stdout,p.stderr)
 return p
for phase,count in [('snapshot',0),('download',0),('runtime',0),
                    ('pg',1),('cache',2),('embed',3),('llama',4)]:
 token=root()
 if phase in ['download','runtime']:
  (ROOT/'download.gguf').write_bytes(b'partial download')
 if phase=='runtime':
  (ROOT/'venv').mkdir();(ROOT/'venv'/'partial-runtime').touch()
 for suffix in ['pg','cache','embed','llama'][:count]:
  subprocess.run(['docker','create','--name','memlab-20-'+suffix,'--label',
                  'memlab-20='+token,helper,'true'],check=True,capture_output=True)
 if count==3:
  subprocess.run(['docker','run','--rm','--name','memlab-20-owned-file',
                  '-v',str(ROOT)+':/owned',helper,'touch','/owned/root-owned'],check=True)
 clean(True);assert not ROOT.exists()
 print('PARTIAL',phase,count,'containers: removed owned resources and directory',flush=True)
token=root(False);clean(False);assert ROOT.exists();shutil.rmtree(ROOT)
print('MISSING_METADATA: refused and preserved directory',flush=True)
token=root()
for suffix,owner in [('pg',token),('cache','other-owner')]:
 subprocess.run(['docker','create','--name','memlab-20-'+suffix,'--label',
                 'memlab-20='+owner,helper,'true'],check=True,capture_output=True)
p=clean(False);assert 'owner mismatch' in p.stderr and ROOT.exists()
for suffix in ['pg','cache']:
 subprocess.run(['docker','inspect','memlab-20-'+suffix],check=True,capture_output=True)
 subprocess.run(['docker','rm','memlab-20-'+suffix],check=True,capture_output=True)
shutil.rmtree(ROOT)
print('MISMATCHED_OWNER: refused and preserved both containers and directory',flush=True)
ROOT.symlink_to(SOURCE,target_is_directory=True)
clean(False);assert ROOT.is_symlink();ROOT.unlink()
print('SYMLINK: refused and preserved target',flush=True)

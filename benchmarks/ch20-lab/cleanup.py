import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path('/var/tmp/memlab-20')
if (ROOT.is_symlink() or ROOT.resolve()!=ROOT or
    not (ROOT/'.path').is_file() or not (ROOT/'.owner').is_file() or
    (ROOT/'.path').read_text()!=str(ROOT)):
    raise SystemExit('STOP: lab ownership path mismatch')
token = (ROOT/'.owner').read_text()
if not token:
    raise SystemExit('STOP: missing owner token')
# Missing image metadata requires manual inspection, never guessed ownership.
if any(not (ROOT/name).is_file() for name in ['images.json','images-before.txt']):
    raise SystemExit('STOP: missing image metadata')
images = json.loads((ROOT/'images.json').read_text())
before = (ROOT/'images-before.txt').read_text().splitlines()
names = []
for suffix in ['pg','cache','embed','llama','writer']:
    name = 'memlab-20-'+suffix
    found = subprocess.check_output(['docker','ps','-aq','--filter',
                                    'name=^/'+name+'$'],text=True).strip()
    if not found:
        continue
    obj = json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    if obj['Config']['Labels'].get('memlab-20') != token:
        raise SystemExit('STOP: container owner mismatch')
    names.append(name)
for name in names:
    subprocess.run(['docker','rm','-fv',name],check=True,timeout=30)
# This helper may be pulled; the initial snapshot controls image removal.
helper = 'ubuntu@sha256:'+'73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8'
subprocess.run(['docker','run','--rm','--name','memlab-20-cleanup',
                '-v',str(ROOT)+':/owned',helper,'chown','-R',
                f'{os.getuid()}:{os.getgid()}','/owned'],check=True,timeout=60)
for image in images+[helper]:
    result = subprocess.run(['docker','image','inspect','--format','{{.Id}}',image],
                            capture_output=True,text=True,timeout=10)
    if result.returncode==0 and result.stdout.strip() not in before:
        subprocess.run(['docker','image','rm',image],check=True,timeout=30)
if (ROOT/'.owner').read_text()!=token or ROOT.resolve()!=ROOT:
    raise SystemExit('STOP: owner changed')
shutil.rmtree(ROOT)
print('Removed owned containers, newly pulled images, models and lab directory.')
subprocess.run(['df','-h','/var/tmp'],check=True)
subprocess.run(['docker','ps','--format','{{.Names}} {{.Image}} {{.Status}}'],check=True)

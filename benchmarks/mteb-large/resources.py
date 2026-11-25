#!/usr/bin/env python3
"""Read-only resource evidence; connection identity stays in environment only."""
import argparse,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def clean(s):
    s=re.sub(r'/Users/[^/\s]+','/Users/account',s)
    s=re.sub(r'/home/[^/\s]+','/home/account',s)
    s=re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','[address]',s)
    s=re.sub(r'/mnt/[^\s]+','/mnt/[mount]',s)
    s=re.sub(r'/etc/auto_[^\s:)]+','/etc/auto_[mount]',s)
    return s.replace(os.environ.get('USER','__NO_USER__'),'account')

def capture(cmd):
    p=subprocess.run(cmd,text=True,capture_output=True);return {'exit':p.returncode,'stdout':clean(p.stdout),'stderr':clean(p.stderr)}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');a=p.parse_args()
    data={'local_disk':capture(['df','-h','/','/data']),
          'local_processes':capture(['ps','-eo','pid,rss,comm']),
          'gpu':capture(['nvidia-smi','--query-gpu=name,memory.used,utilization.gpu','--format=csv'])}
    if os.environ.get('MODEL_SSH'):
        data['model_host']=capture(['ssh',os.environ['MODEL_SSH'],"df -h /; memory_pressure; sysctl -n kern.memorystatus_vm_pressure_level; ps -axo pid,rss,comm; lsof -b -nP -iTCP -sTCP:LISTEN"])
    (ROOT/'results'/('resources-'+a.label+'.json')).write_text(json.dumps(data,indent=2)+'\n')

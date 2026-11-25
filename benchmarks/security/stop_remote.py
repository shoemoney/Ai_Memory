"""Stop only task-owned model service PIDs, checking command identity first."""
import argparse,os,pathlib,signal,subprocess
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--which',choices=['model','inversion','all'],default='all');a=p.parse_args();root=pathlib.Path(a.root)
for kind,file,program in [('model','server.pid','model_server.py'),('inversion','inversion.pid','inversion_server.py')]:
 if a.which not in [kind,'all']:continue
 path=root/file
 if not path.exists():continue
 pid=int(path.read_text())
 result=subprocess.run(['ps','-p',str(pid),'-o','args='],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 if result.returncode==0:
  if 'membench-security-tmp' not in result.stdout or program not in result.stdout:raise RuntimeError('owned PID identity mismatch; refusing to signal')
  os.kill(pid,signal.SIGTERM);print('Stopped task-owned',kind,'server.')

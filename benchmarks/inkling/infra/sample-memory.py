"""Read-only samples of the lab processes and host pressure; terminate with Ctrl-C."""
import json,subprocess,time
from pathlib import Path
out=Path(__file__).resolve().parents[1]/'results/stock/memory-samples.jsonl'
script='''import json,subprocess,time,pathlib
lab=pathlib.Path.home()/'inkling-lab'
pids={n:(lab/(n+'.pid')).read_text().strip() for n in ['server','gemma','qwen'] if (lab/(n+'.pid')).exists()}
r={'unix':time.time(),'pids':pids}
r['processes']=subprocess.check_output(['ps','-o','pid=,rss=,vsz=,%cpu=,etime=,command=','-p',','.join(pids.values())],text=True)
r['memory_pressure']=subprocess.check_output(['memory_pressure'],text=True)
r['swap']=subprocess.check_output(['sysctl','vm.swapusage'],text=True)
print(json.dumps(r))'''
while True:
 p=subprocess.run(['ssh','<lan-address>','/opt/homebrew/bin/python3','-c',__import__('shlex').quote(script)],capture_output=True,text=True)
 with out.open('a') as f: f.write(p.stdout if p.returncode==0 else json.dumps({'unix':time.time(),'error':p.stderr})+'\n')
 time.sleep(30)

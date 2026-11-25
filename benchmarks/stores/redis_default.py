#!/usr/bin/env python3
"""Check the native Vector Set default without explicitly choosing a quantizer."""
import json,pathlib,shutil,subprocess,time,uuid
ROOT=pathlib.Path(__file__).resolve().parent
IMAGE='redis@sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53'
def run(args):return subprocess.check_output(args,text=True).strip()
def main():
 token=uuid.uuid4().hex;name='membench-stores-default-'+token[:8];started=False
 pulled=subprocess.run(['docker','image','inspect',IMAGE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
 result={'image':IMAGE,'elements':1,'dimensions':2,'quantization_option_supplied':False}
 try:
  if pulled:
   if shutil.disk_usage('/').free<20*1024**3:raise RuntimeError('Paused: system disk under 20 GiB free')
   run(['docker','pull',IMAGE])
  run(['docker','run','-d','--name',name,'--label','membench-stores-owner='+token,'--network','none','--memory','256m','--cpus','1',IMAGE,'redis-server','--save','','--appendonly','no']);started=True
  for _ in range(100):
   ping=subprocess.run(['docker','exec',name,'redis-cli','ping'],capture_output=True,text=True)
   if ping.returncode==0 and ping.stdout.strip()=='PONG':break
   time.sleep(.1)
  else:raise RuntimeError('Redis not ready')
  run(['docker','exec',name,'redis-cli','VADD','default','VALUES','2','1','0','one'])
  data=json.loads(run(['docker','exec',name,'redis-cli','--json','VINFO','default']))
  info=data if isinstance(data,dict) else dict(zip(data[::2],data[1::2]))
  assert info['quant-type']=='int8' and info['size']==1
  result['vinfo']=info;result['passed']=True
 finally:
  if started:
   assert run(['docker','inspect','-f','{{index .Config.Labels "membench-stores-owner"}}',name])==token
   run(['docker','rm','-fv',name])
  if pulled:run(['docker','rmi',IMAGE])
  result['container_removed']=subprocess.run(['docker','inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
  (ROOT/'results/redis-default.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()

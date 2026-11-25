#!/usr/bin/env python3
"""One command, owned containers only, sequential CPU-only cells and final cleanup."""
import argparse, json, os, pathlib, shutil, socket, subprocess, time, uuid, threading
ROOT=pathlib.Path(__file__).resolve().parent
IMAGES={
 'mongo':'mongodb/mongodb-atlas-local@sha256:9a1905c81f835f4b0b6582496309eefe132d5a931012e88e0023f4017faef964',
 'postgres':'pgvector/pgvector@sha256:38681dc6eaf55308e2a4c6de392d131652dcfac70e1263e35cd9b5ea3fe39782',
 'redis':'redis@sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53',
 'valkey':'valkey/valkey-bundle@sha256:cc210fe648eea982a9b3d76c429859ca150e2b653aa9b3cd81e58c9b49940404',
 'memcached':'memcached@sha256:a395a1bcf5e0e2b0fa4a0142e12b4e24a2320ba4b7c6ffa8655a1a86e8f29dee',
 'python':'python@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c'}
def cmd(args,**kw):return subprocess.run(args,check=True,text=True,**kw)
def output(args):return subprocess.check_output(args,text=True).strip()
def snapshot():
 return {'disk':output(['df','-h','/','/data']),
 'containers':output(['docker','ps','--format','{{.Names}} {{.Image}}']),
 'processes':output(['ps','-eo','comm=']) ,'memory':output(['free','-h'])}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cells',default='sqlite,postgres,redis,valkey,memcached,mongo_none,mongo_scalar,mongo_binary');args=ap.parse_args()
 out=ROOT/'results';out.mkdir(exist_ok=True)
 scratch=pathlib.Path('/data/scratch/membench/stores/run-'+uuid.uuid4().hex)
 scratch.mkdir(parents=True);token=uuid.uuid4().hex
 runtime=pathlib.Path('/data/scratch/membench/stores/runtime-'+token);runtime.mkdir(parents=True)
 before=set(output(['docker','image','ls','-q','--no-trunc']).splitlines())
 proof={'before':snapshot(),'token':token,'images':IMAGES,'cells':{},'started_unix':time.time()}
 (out/('resource-proof-'+args.cells.replace(',','-')+'.json')).write_text(json.dumps(proof,indent=2))
 owned=[]; pulled=[];worker_built=False;worker='membench-stores-worker-'+token[:8]
 def remove(name):
  label=output(['docker','inspect','-f','{{index .Config.Labels "membench-stores-owner"}}',name])
  if label!=token:raise RuntimeError('ownership mismatch')
  cmd(['docker','rm','-fv',name],stdout=subprocess.DEVNULL);owned.remove(name)
 try:
  for key in ['python']+ [c for c in args.cells.split(',') if c not in ['sqlite','defaults','duckdb']]:
   ref=IMAGES['mongo' if key.startswith('mongo_') else key]
   if subprocess.run(['docker','image','inspect',ref],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
    if shutil.disk_usage('/').free < 20*1024**3:raise RuntimeError('Paused: shared system disk has under 20 GiB free')
    cmd(['docker','pull',ref]);pulled.append(ref)
  if shutil.disk_usage('/').free < 20*1024**3:raise RuntimeError('Paused: shared system disk has under 20 GiB free')
  cmd(['docker','build','-t',worker,str(ROOT)]);worker_built=True
  for cell in args.cells.split(','):
   backend='mongo' if cell.startswith('mongo_') else cell
   proof.setdefault('disk_checks',[]).append({'cell':cell,'df':output(['df','-h','/','/data'])})
   if shutil.disk_usage('/').free < 20*1024**3:raise RuntimeError('Paused: shared system disk has under 20 GiB free')
   name='membench-stores-'+cell+'-'+token[:8];server=None
   if backend not in ['sqlite','defaults','duckdb']:
    port={'postgres':39750,'redis':39751,'valkey':39752,'memcached':39753,'mongo':39755}[backend]
    with socket.socket() as s:
     s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('localhost',port))
    opts={'postgres':['-e','POSTGRES_HOST_AUTH_METHOD=trust'], 'redis':[], 'valkey':[], 'memcached':[],'mongo':[]}[backend]
    extra={'postgres':['postgres','-c','shared_buffers=256MB','-c','maintenance_work_mem=512MB','-c','max_parallel_workers_per_gather=0','-c','max_parallel_maintenance_workers=0'],
    'redis':['redis-server','--save','','--appendonly','no'],
    'valkey':['--save','','--appendonly','no'],
    'memcached':['memcached','-m','64','-t','2'],'mongo':[]}[backend]
    inside={'postgres':5432,'redis':6379,'valkey':6379,'memcached':11211,'mongo':27017}[backend]
    mounts=[]
    if backend=='mongo':opts+=['--cap-add','SYS_PTRACE']
    if backend=='postgres':
     data=runtime/'postgres';data.mkdir();mounts=['-v',str(data)+':/var/lib/postgresql']
    elif backend=='mongo':
     mongodata=runtime/cell;mongodata.mkdir();mounts=['-v',str(mongodata)+':/data']
     for label,dest in [('db','/data/db'),('configdb','/data/configdb')]:
      data=mongodata/label;data.mkdir();mounts+=['-v',str(data)+':'+dest]
     (scratch/'mongo-parent-bound').write_text('all data bound to ZFS scratch')
    cmd(['docker','run','-d','--name',name,'--label','membench-stores-owner='+token,'--memory','3g','--cpus','2','-p',socket.gethostbyname('localhost')+f':{port}:{inside}']+mounts+opts+[IMAGES[backend]]+extra,stdout=subprocess.DEVNULL)
    owned.append(name);server=name
    for _ in range(120):
     try:
      with socket.create_connection(('localhost',port),1):break
     except OSError:time.sleep(.5)
    else:raise RuntimeError('server not ready')
    time.sleep(2)
   print('RUN',cell,flush=True)
   wn='membench-stores-client-'+token[:8]
   owned.append(wn)
   start=time.time()
   done=threading.Event()
   def collect_mongo_metrics():
    request=scratch/'metric-request.json';ack=scratch/'metric-response.json'
    while not done.wait(.2):
     if request.exists() and not ack.exists():
      label=json.loads(request.read_text())
      stats=output(['docker','stats','--no-stream','--format','{{json .}}',server])
      processes=output(['docker','top',server,'-eo','pid,comm,rss'])
      from mongo_files import measure
      file_proxy=measure(server,label)
      temp=ack.with_suffix('.tmp');temp.write_text(json.dumps({'label':label,'container_stats':json.loads(stats),'process_rss_kib':processes,'file_proxy':file_proxy}));temp.replace(ack)
   monitor=None
   if backend=='mongo':monitor=threading.Thread(target=collect_mongo_metrics,daemon=True);monitor.start()
   cmd(['docker','run','--name',wn,'--user',str(os.getuid())+':'+str(os.getgid()),'--label','membench-stores-owner='+token,'--network','host','--memory','3g','--cpus','2',
    '-v',str(ROOT)+':/code:ro','-v',str(out)+':/out','-v',str(scratch)+':/scratch',worker,'python','worker.py',cell])
   done.set()
   if monitor:monitor.join(timeout=5)
   proof['cells'][cell]={'seconds':time.time()-start,'client_cgroup':output(['docker','inspect','-f','{{.State.OOMKilled}}',wn])}
   if server:
    proof['cells'][cell]['stats']=output(['docker','stats','--no-stream','--format','{{.MemUsage}} {{.BlockIO}}',server])
   proof['scratch_peak_bytes_observed']=int(output(['du','-sb',str(scratch)]).split()[0])
   remove(wn)
   if server:remove(server)
   (out/('resource-proof-'+args.cells.replace(',','-')+'.json')).write_text(json.dumps(proof,indent=2))
  if 'memcached' in args.cells.split(','):
   from features import run_features
   seq=0
   def start_feature(image,port,extra):
    nonlocal seq
    seq+=1;name='membench-stores-feature-'+token[:8]+'-'+str(seq)
    data=runtime/('feature-'+str(seq));data.mkdir();data.chmod(0o1777)
    pub=[] if port is None else ['-p',socket.gethostbyname('localhost')+f':{port}:11211']
    cmd(['docker','run','-d','--name',name,'--label','membench-stores-owner='+token,'--memory','256m','--cpus','2','-v',str(data)+':/tmp']+pub+[IMAGES[image]]+extra,stdout=subprocess.DEVNULL)
    owned.append(name);return name
   run_features(start_feature,remove,output,out)
 finally:
  for n in owned[:]:
   try:remove(n)
   except Exception as e:proof.setdefault('cleanup_errors',[]).append(str(e))
  # Owned bind-mounted database files live on the ZFS scratch filesystem, not the crowded host root.
  cleaner='membench-stores-cleanup-'+token[:8]
  if worker_built:
   cmd(['docker','run','--rm','--name',cleaner,'--label','membench-stores-owner='+token,'--user','0','--memory','128m','--cpus','1','-v',str(runtime.parent)+':/runtime',worker,'python','-c',"import shutil; shutil.rmtree('/runtime/runtime-"+token+"')"],stdout=subprocess.DEVNULL)
   subprocess.run(['docker','rmi',worker],stdout=subprocess.DEVNULL)
   cache_cleanup=subprocess.run(['docker','buildx','prune','-f','--filter','description~=membench-stores-requirements.txt'],capture_output=True,text=True)
   proof['owned_dependency_cache_cleanup']={'exit_code':cache_cleanup.returncode,'output':cache_cleanup.stdout,'error':cache_cleanup.stderr}
  else:shutil.rmtree(runtime)
  proof['database_runtime_removed']=not runtime.exists()
  for ref in set(pulled):
   # Never remove a shared image that existed before setup, except our bootstrap pull.
   subprocess.run(['docker','rmi',ref],stdout=subprocess.DEVNULL)
  shutil.rmtree(scratch)
  proof['after']=snapshot();proof['scratch_removed']=not scratch.exists();proof['finished_unix']=time.time()
  proof['remaining_owned']=output(['docker','ps','-a','--filter','label=membench-stores-owner='+token,'--format','{{.Names}}'])
  (out/('resource-proof-'+args.cells.replace(',','-')+'.json')).write_text(json.dumps(proof,indent=2))
if __name__=='__main__':main()

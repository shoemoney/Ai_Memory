"""Protocol-level restart probes, orchestrated by run.py with owned containers only."""
import json, pathlib, socket, subprocess, time

def run_features(start,remove,execute,out):
 path=out/'features.jsonl';path.write_text('')
 def emit(kind,**kw):
  with path.open('a') as f:f.write(json.dumps(dict(kind=kind,**kw))+'\n')
 def conn(port):
  s=socket.create_connection(('localhost',port),2);s.settimeout(5);return s,s.makefile('rb')
 def set_items(port,n=100,size=100,pace=False):
  s,f=conn(port)
  for i in range(n):
   s.sendall(f'set k{i} 0 0 {size}\r\n'.encode()+b'x'*size+b'\r\n')
   assert f.readline()==b'STORED\r\n'
   if pace and i%100==99:time.sleep(.05)
  s.close();f.close()
 def get_count(port,n=100):
  s,f=conn(port);s.sendall(b'get '+b' '.join(f'k{i}'.encode() for i in range(n))+b'\r\n');count=0
  while True:
   line=f.readline()
   if line==b'END\r\n':break
   assert line.startswith(b'VALUE'),line
   f.read(int(line.split()[3])+2);count+=1
  s.close();f.close();return count
 def stats(port):
  s,f=conn(port);s.sendall(b'stats\r\n');d={}
  while True:
   line=f.readline().decode().strip()
   if line=='END':break
   p=line.split();d[p[1]]=p[2]
  s.close();f.close();return d
 def ready(port):
  for _ in range(100):
   try:
    s,f=conn(port);s.settimeout(.5);s.sendall(b'version\r\n');version=f.readline();s.close();f.close()
    if version.startswith(b'VERSION '):return
   except OSError:pass
   time.sleep(.1)
  raise RuntimeError('restart failed: '+execute(['docker','logs',name]))
 # start() binds one dedicated localhost port, the mmap stays in the container layer.
 for mode,opts,signal in [('warm',['-e','/tmp/warm'],'SIGUSR1'),('crash',['-e','/tmp/warm'],'SIGKILL'),('normal',[],'SIGTERM')]:
  name=start('memcached',39754,['memcached','-m','64','-t','2']+opts)
  ready(39754);set_items(39754)
  execute(['docker','kill','--signal',signal,name]);execute(['docker','wait',name]);execute(['docker','start',name]);ready(39754)
  emit('memcached_restart',mode=mode,signal=signal,written=100,retained=get_count(39754))
  remove(name)
 # Incompatible warm configuration and extstore must be rejected together.
 name=start('memcached',39754,['memcached','-m','32','-t','2','-o','ext_path=/tmp/ext:128m,ext_page_size=8,ext_wbuf_size=2,ext_item_size=512,ext_item_age=0'])
 ready(39754);set_items(39754,n=10000,size=8192,pace=True)
 for _ in range(100):
  st=stats(39754)
  if int(st.get('extstore_objects_written','0'))>0:break
  time.sleep(.1)
 sample=get_count(39754);after_read=stats(39754)
 emit('extstore',stats=after_read,written=10000,sample_retained_before=sample,external_reads_during_sample=int(after_read.get('extstore_objects_read',0))-int(st.get('extstore_objects_read',0)))
 execute(['docker','kill','--signal','SIGKILL',name]);execute(['docker','start',name]);ready(39754)
 emit('extstore_restart',retained=get_count(39754),stats=stats(39754));remove(name)
 name=start('memcached',39754,['memcached','-m','32','-t','2','-I','2m'])
 ready(39754);set_items(39754,n=1,size=1048577);emit('larger_item_limit',payload_bytes=1048577,retained=get_count(39754,n=1));remove(name)
 # Run the binary directly in an ephemeral owned container to retain startup diagnostics.
 name=start('memcached',39754,['memcached','-m','64','-e','/tmp/warm','-o','ext_path=/tmp/ext:128m'])
 startup_ready=False
 try:ready(39754);startup_ready=True
 except RuntimeError:pass
 running=execute(['docker','inspect','-f','{{.State.Running}}',name])=='true'
 if running:execute(['docker','kill','--signal','SIGTERM',name])
 execute(['docker','wait',name]);emit('incompatible_options',startup_ready=startup_ready,startup_running=running,stopped_by_tester=running,exit_code=int(execute(['docker','inspect','-f','{{.State.ExitCode}}',name])),log=execute(['docker','logs',name]));remove(name)

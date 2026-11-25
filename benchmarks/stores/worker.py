"""Seeded storage probes; each query/behavior is immediately checkpointed as JSONL."""
import contextlib, importlib.metadata, json, math, os, pathlib, platform, socket, sqlite3, struct, sys, time
import numpy as np
N=100_000; D=384; Q=200; SEED=20261122
CELL=sys.argv[1]; DEST=pathlib.Path('/out'); RAW=DEST/(CELL+'.jsonl')
if RAW.exists():
 archive=DEST/'archive';archive.mkdir(exist_ok=True)
 RAW.rename(archive/(CELL+'-'+str(time.time_ns())+'.jsonl'))
RAW.write_text('')
def emit(kind,**kw):
 with RAW.open('a') as f:
  f.write(json.dumps(dict(kind=kind,**kw),sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
def timed(fn):
 t=time.perf_counter();v=fn();return v,(time.perf_counter()-t)*1000
def dataset():
 r=np.random.default_rng(SEED);centers=r.standard_normal((1000,D),dtype=np.float32)
 centers/=np.linalg.norm(centers,axis=1,keepdims=True)
 x=np.empty((N,D),dtype=np.float32)
 for lo in range(0,N,1000):
  x[lo:lo+1000]=centers[r.integers(0,1000,1000)]+r.standard_normal((1000,D),dtype=np.float32)*.08
  x[lo:lo+1000]/=np.linalg.norm(x[lo:lo+1000],axis=1,keepdims=True)
 q=centers[r.integers(0,1000,Q)]+r.standard_normal((Q,D),dtype=np.float32)*.08
 q/=np.linalg.norm(q,axis=1,keepdims=True)
 return x,q

def baseline(x,q):
 ans=[]
 for i,v in enumerate(q):
  scores=x@v;ids=np.argsort(-scores,kind='stable')[:10];ans.append(ids.tolist())
 return ans

def postgres():
 import psycopg
 from psycopg.types.json import Jsonb
 for attempt in range(120):
  try:
   db=psycopg.connect('host=localhost port=39750 dbname=postgres user=postgres connect_timeout=2',autocommit=True)
   db.execute('SELECT 1');break
  except psycopg.OperationalError:
   if attempt==119:raise
   time.sleep(1)
 c=db.cursor();c.execute('CREATE EXTENSION vector')
 c.execute("SELECT version(), extversion FROM pg_extension WHERE extname='vector'");emit('versions',server=c.fetchone())
 def sql(s,args=None):c.execute(s,args);return c.fetchall() if c.description else []
 # Empty boundary tables check the actual access-method validators without allocating giant indexes.
 for typ,cap,ops in [('vector',2000,'vector_l2_ops'),('halfvec',4000,'halfvec_l2_ops'),('bit',64000,'bit_hamming_ops')]:
  for d in [cap,cap+1]:
   sql('DROP TABLE IF EXISTS boundary');sql(f'CREATE TABLE boundary(v {typ}({d}))')
   try:sql(f'CREATE INDEX boundary_idx ON boundary USING hnsw (v {ops})');ok=True;err=None
   except psycopg.Error as e:ok=False;err=str(e).strip()
   emit('index_boundary',type=typ,dimensions=d,accepted=ok,error=err)
 sql('DROP TABLE boundary')
 for nz in [1000,1001]:
  sql('CREATE TABLE boundary(v sparsevec(2000))')
  value='{'+','.join(f'{i}:1' for i in range(1,nz+1))+'}/2000'
  sql('INSERT INTO boundary VALUES(%s)',(value,))
  try:sql('CREATE INDEX boundary_idx ON boundary USING hnsw(v sparsevec_l2_ops)');ok=True;err=None
  except psycopg.Error as e:ok=False;err=str(e).strip()
  emit('index_boundary',type='sparsevec',nonzero=nz,accepted=ok,error=err);sql('DROP TABLE boundary')
 c.execute('SHOW hnsw.ef_search');emit('default',name='hnsw.ef_search',value=c.fetchone()[0])
 c.execute('SHOW ivfflat.probes');emit('default',name='ivfflat.probes',value=c.fetchone()[0])
 x,q=dataset();sql(f'CREATE TABLE vectors(id int PRIMARY KEY, tenant int, v vector({D}))')
 t=time.perf_counter()
 with c.copy('COPY vectors(id,tenant,v) FROM STDIN') as cp:
  for i,v in enumerate(x):cp.write_row((i,i%20,'['+','.join(map(str,v))+']'))
 emit('load',rows=N,dimensions=D,ms=(time.perf_counter()-t)*1000)
 sql('ANALYZE vectors')
 emit('storage',column_bytes=sql('SELECT pg_column_size(v) FROM vectors LIMIT 1')[0][0],vector_send_bytes=sql('SELECT octet_length(vector_send(v)) FROM vectors LIMIT 1')[0][0],table_bytes=sql("SELECT pg_table_size('vectors')")[0][0])
 truth={}
 for i,v in enumerate(q):
  vv='['+','.join(map(str,v))+']';truth[i]={}
  for filt in ['all','tenpct','fivepct','tiny']:
   where={'all':'','tenpct':'WHERE id%%10=0','fivepct':'WHERE tenant=0','tiny':'WHERE id%%5000=0'}[filt]
   rows,ms=timed(lambda:sql(f'SELECT id FROM vectors {where} ORDER BY v <=> %s::vector LIMIT 10',(vv,)))
   ids=[a[0] for a in rows];truth[i][filt]=ids
   emit('query',method='exact',filter=filt,query=i,ids=ids,ms=ms,recall=1.0,count=len(ids))
 index_info={}
 for method,ddl in [('ivfflat','CREATE INDEX ann ON vectors USING ivfflat(v vector_cosine_ops) WITH(lists=100)'),('hnsw','CREATE INDEX ann ON vectors USING hnsw(v vector_cosine_ops) WITH(m=16,ef_construction=64)')]:
  t=time.perf_counter();sql(ddl)
  index_info[method]={'build_ms':(time.perf_counter()-t)*1000,'bytes':sql("SELECT pg_relation_size('ann')")[0][0]};emit('index',method=method,**index_info[method])
  for setting in (['default','probes10'] if method=='ivfflat' else ['default','iterative']):
   if setting=='probes10':sql('SET ivfflat.probes=10')
   sql("SET hnsw.iterative_scan="+('strict_order' if setting=='iterative' else 'off'))
   sql('SET enable_seqscan=off')
   for i,v in enumerate(q):
    vv='['+','.join(map(str,v))+']'
    for filt in (['all'] if method=='ivfflat' else ['all','tenpct','fivepct','tiny']):
     where={'all':'','tenpct':'WHERE id%%10=0','fivepct':'WHERE tenant=0','tiny':'WHERE id%%5000=0'}[filt]
     rows,ms=timed(lambda:sql(f'SELECT id FROM vectors {where} ORDER BY v <=> %s::vector LIMIT 10',(vv,)))
     ids=[a[0] for a in rows]
     emit('query',method=method+'_'+setting,filter=filt,query=i,ids=ids,ms=ms,recall=len(set(ids)&set(truth[i][filt]))/10,count=len(ids))
   emit('plan',method=method+'_'+setting,plan=sql('EXPLAIN (FORMAT JSON) SELECT id FROM vectors WHERE tenant=0 ORDER BY v <=> %s::vector LIMIT 10',(vv,))[0][0])
  sql('DROP INDEX ann');sql('SET enable_seqscan=on')
 # Half precision is an open-source comparison, not the MongoDB RAM result.
 emit('half_storage',bytes=sql('SELECT pg_column_size(v::halfvec(384)) FROM vectors LIMIT 1')[0][0])
 db.close()

def redis_test():
 import redis
 r=redis.Redis(protocol=2,host='localhost',port=39751 if CELL=='redis' else 39752,socket_timeout=300)
 emit('versions',server=r.info('server')['redis_version'],valkey_version=r.info('server').get('valkey_version'),modules=str(r.execute_command('MODULE','LIST')))
 # Documented structure, expiry, eviction and ownership behaviors.
 r.hset('session',mapping={'summary':'note','version':1});r.expire('session',1)
 emit('hash',value=r.hgetall('session').__repr__(),ttl=r.ttl('session'))
 time.sleep(1.1);emit('expiry',exists=r.exists('session'))
 r.set('lease','owner-a',nx=True,px=30000)
 emit('lease',second_won=bool(r.set('lease','owner-b',nx=True,px=30000)))
 if CELL=='redis':
  emit('lease_release',wrong=r.execute_command('DELEX','lease','IFEQ','owner-b'),right=r.execute_command('DELEX','lease','IFEQ','owner-a'))
 for i in range(25):r.xadd('history',{'turn':i+1})
 got=list(reversed(r.xrevrange('history',count=20)))
 emit('history',turns=[int(v[b'turn']) for _,v in got])
 for policy in ['noeviction','allkeys-lru']:
  r.flushall();base=r.info('memory')['used_memory'];r.config_set('maxmemory',base+2_000_000);r.config_set('maxmemory-policy',policy)
  err=0
  for i in range(4000):
   try:r.set('entry:'+str(i),b'x'*1024)
   except redis.ResponseError:err+=1
  emit('eviction',policy=policy,errors=err,keys=r.dbsize(),evicted=r.info('stats')['evicted_keys'])
 r.config_set('maxmemory',0);r.flushall()
 x,q=dataset();truth=baseline(x,q)
 # Query Engine FLAT and HNSW on identical hash vectors and ids, no tenant filter.
 for method in ['FLAT','HNSW']:
  r.flushall();base=r.info('memory')['used_memory'];t=time.perf_counter()
  for lo in range(0,N,500):
   pipe=r.pipeline(transaction=False)
   for i in range(lo,min(lo+500,N)):pipe.hset('v:'+str(i),mapping={'vec':x[i].tobytes(),'tenant':str(i%20)})
   pipe.execute()
  before=r.info('memory')['used_memory']
  r.execute_command('FT.CREATE','ann','ON','HASH','PREFIX','1','v:','SCHEMA','tenant','TAG','vec','VECTOR',method,6,'TYPE','FLOAT32','DIM',D,'DISTANCE_METRIC','COSINE')
  for attempt in range(9000):
   info=r.execute_command('FT.INFO','ann');d=info if isinstance(info,dict) else dict(zip(info[::2],info[1::2]));
   if attempt%50==0:emit('index_progress',method=method,documents=d.get(b'num_docs',d.get('num_docs')),indexing=d.get(b'indexing',d.get('indexing')),percent=str(d.get(b'percent_indexed',d.get('percent_indexed'))))
   if int(d.get(b'num_docs',d.get('num_docs',0)))==N and not int(d.get(b'indexing',d.get('indexing',0))):break
   time.sleep(.2)
  else:raise RuntimeError('index incomplete: '+str(d))
  emit('memory',method=method,rows=N,dimensions=D,base=base,hash_bytes=before-base,total_bytes=r.info('memory')['used_memory']-base,index_info=str(info),load_and_index_ms=(time.perf_counter()-t)*1000)
  for i,v in enumerate(q):
   rows,ms=timed(lambda:r.execute_command('FT.SEARCH','ann','*=>[KNN 10 @vec $q]','PARAMS',2,'q',v.tobytes(),'NOCONTENT','LIMIT',0,10,'DIALECT',2))
   ids=[int(z.decode().split(':')[1]) for z in rows[1:]]
   emit('query',method=method,query=i,ids=ids,ms=ms,recall=len(set(ids)&set(truth[i]))/10,count=len(ids))
 # Vector Sets only exist in Redis, probe Valkey failure explicitly.
 r.flushall()
 if CELL=='valkey':
  try:r.execute_command('VADD','vs','VALUES',2,1,0,'a');emit('vadd',accepted=True)
  except redis.ResponseError as e:emit('vadd',accepted=False,error=str(e))
  return
 for quant in ['Q8','NOQUANT','BIN']:
  r.flushall();base=r.info('memory')['used_memory'];t=time.perf_counter()
  for lo in range(0,N,200):
   pipe=r.pipeline(transaction=False)
   for i in range(lo,min(lo+200,N)):pipe.execute_command('VADD','vs','FP32',x[i].tobytes(),str(i),quant)
   pipe.execute()
  emit('memory',method='VS_'+quant,rows=N,dimensions=D,total_bytes=r.info('memory')['used_memory']-base,load_ms=(time.perf_counter()-t)*1000,vinfo=str(r.execute_command('VINFO','vs')))
  for i,v in enumerate(q):
   rows,ms=timed(lambda:r.execute_command('VSIM','vs','FP32',v.tobytes(),'COUNT',10,'WITHSCORES'))
   ids=list(map(int,rows[::2]));emit('query',method='VS_'+quant,query=i,ids=ids,ms=ms,recall=len(set(ids)&set(truth[i]))/10,count=len(ids))
 r.flushall()
 for name,v in [('same',[1,0]),('orthogonal',[0,1]),('opposite',[-1,0])]:r.execute_command('VADD','scores','VALUES',2,*v,name,'NOQUANT')
 emit('scores',values=[z.decode() for z in r.execute_command('VSIM','scores','VALUES',2,1,0,'WITHSCORES','COUNT',3)])
 r.execute_command('VSETATTR','scores','same',json.dumps({'tenant':'a'}))
 emit('filter',values=[z.decode() for z in r.execute_command('VSIM','scores','VALUES',2,1,0,'FILTER','.tenant == "a"','COUNT',3)])

def sqlite_test():
 import sqlite_vec
 db=sqlite3.connect('/scratch/test.db');db.enable_load_extension(True);sqlite_vec.load(db)
 emit('versions',sqlite=sqlite3.sqlite_version,sqlite_vec=sqlite_vec.__version__,compile_options=[x[0] for x in db.execute('PRAGMA compile_options')])
 db.execute('PRAGMA journal_mode=WAL');db.execute('CREATE TABLE memories(id INTEGER PRIMARY KEY,text TEXT)')
 db.execute("CREATE VIRTUAL TABLE fts USING fts5(text, content='memories', content_rowid='id')")
 db.execute("CREATE VIRTUAL TABLE trig USING fts5(text,tokenize='trigram')")
 db.execute("INSERT INTO trig VALUES('send_memory_request')")
 emit('trigram',matches=db.execute("SELECT text FROM trig WHERE trig MATCH 'memory'").fetchall())
 db.execute("INSERT INTO memories VALUES(1,'hello memory')");db.execute("INSERT INTO fts(rowid,text) VALUES(1,'hello memory')")
 db.execute('CREATE VIRTUAL TABLE toy USING vec0(v float[2])');db.execute('INSERT INTO toy(rowid,v) VALUES(1,?)',(struct.pack('ff',1,0),));db.commit()
 db.execute('DELETE FROM memories WHERE id=1');db.commit()
 emit('no_cascade',fts_index_matches=db.execute("SELECT rowid FROM fts WHERE fts MATCH 'memory'").fetchall(),vector_matches=db.execute('SELECT rowid FROM toy WHERE v MATCH ? AND k=1',(struct.pack('ff',1,0),)).fetchall())
 for expression in ['hello OR memory','"hello OR memory"','"unterminated']:
  try:rows=db.execute('SELECT rowid FROM fts WHERE fts MATCH ?',(expression,)).fetchall();emit('fts_grammar',expression=expression,rows=rows)
  except sqlite3.Error as e:emit('fts_grammar',expression=expression,error=str(e))
 # Reader and competing writer behavior with a transaction already in progress.
 second=sqlite3.connect('/scratch/test.db',timeout=.05)
 db.execute("INSERT INTO memories VALUES(2,'uncommitted')")
 emit('wal_reader',rows=second.execute('SELECT count(*) FROM memories').fetchone()[0])
 t=time.perf_counter()
 try:second.execute("INSERT INTO memories VALUES(3,'blocked')");emit('writer',blocked=False)
 except sqlite3.OperationalError as e:emit('writer',blocked=True,error=str(e),ms=(time.perf_counter()-t)*1000)
 db.rollback();second.close()
 for d in [8192,8193]:
  try:db.execute(f'CREATE VIRTUAL TABLE dim{d} USING vec0(v float[{d}])');emit('dimension_limit',dimension=d,accepted=True)
  except sqlite3.Error as e:emit('dimension_limit',dimension=d,accepted=False,error=str(e))
 note=pathlib.Path('/scratch/MEMORY.md');note.write_text('one line of memory '*8+'\n')
 note.write_text(('one line of memory '*8+'\n')*300)
 emit('flat_file',bytes=note.stat().st_size,lines=len(note.read_text().splitlines()),truncated=False)
 old=note.read_text();first=old+'writer-a\n';second=old+'writer-b\n';note.write_text(first);note.write_text(second)
 emit('lost_update',writer_a_survived='writer-a' in note.read_text(),writer_b_survived='writer-b' in note.read_text())
 x,q=dataset();truth=baseline(x,q)
 db.execute(f'CREATE VIRTUAL TABLE vectors USING vec0(v float[{D}])')
 t=time.perf_counter();db.executemany('INSERT INTO vectors(rowid,v) VALUES(?,?)',((i,v.tobytes()) for i,v in enumerate(x)));db.commit()
 emit('load',rows=N,dimensions=D,ms=(time.perf_counter()-t)*1000)
 db.execute('PRAGMA wal_checkpoint(TRUNCATE)');emit('storage',bytes=pathlib.Path('/scratch/test.db').stat().st_size,raw_bytes=x.nbytes)
 for i,v in enumerate(q):
  rows,ms=timed(lambda:db.execute('SELECT rowid FROM vectors WHERE v MATCH ? AND k=10 ORDER BY distance',(v.tobytes(),)).fetchall())
  ids=[a[0] for a in rows];emit('query',method='vec0_l2',query=i,ids=ids,ms=ms,recall=len(set(ids)&set(truth[i]))/10,count=len(ids))
 # Codec allocation arithmetic is separately labeled, never an Atlas RAM measurement.
 for label,a in [('float32',x),('float16',x.astype(np.float16)),('int8',np.clip(np.rint(x*127),-127,127).astype(np.int8)),('binary',np.packbits(x>0,axis=1))]:
  emit('codec_payload',codec=label,bytes=a.nbytes,rows=N,dimensions=D)
 db.close()

def memcached():
 def connect():
  s=socket.create_connection(('localhost',39753),2);s.settimeout(5);return s,s.makefile('rb')
 s,f=connect()
 def line(raw):s.sendall(raw);return f.readline().decode().strip()
 def put(key,value,ttl=0):return line(b'set '+key+b' 0 '+str(ttl).encode()+b' '+str(len(value)).encode()+b'\r\n'+value+b'\r\n')
 def get(key):
  s.sendall(b'get '+key+b'\r\n');h=f.readline()
  if h==b'END\r\n':return None
  if not h.startswith(b'VALUE'):raise RuntimeError(h)
  n=int(h.split()[3]);v=f.read(n);assert f.read(2)==b'\r\n';assert f.readline()==b'END\r\n';return v
 def stats(arg=b''):
  s.sendall(b'stats '+arg+b'\r\n');d={}
  while True:
   row=f.readline().decode().strip()
   if row=='END':return d
   p=row.split();d[p[1]]=p[2]
 emit('versions',version=line(b'version\r\n'))
 # Invalid set commands can leave value bytes in the stream, so use isolated sockets.
 for length in [249,250,251]:
  ss,ff=connect();ss.sendall(b'set '+b'k'*length+b' 0 0 1\r\nx\r\n');response=ff.readline().decode().strip();ss.close();ff.close();emit('key_limit',length=length,response=response)
 for key in [b'has space',b'has\tcontrol',b'has\x01control']:
  ss,ff=connect();ss.sendall(b'set '+key+b' 0 0 1\r\nx\r\n');response=ff.readline().decode().strip();hit=False;returned=None
  if response=='STORED':
   ss.sendall(b'get '+key+b'\r\n');header=ff.readline()
   if header.startswith(b'VALUE '):
    parts=header.rstrip(b'\r\n').split(b' ');returned=parts[1].hex();size=int(parts[-1]);assert ff.read(size+2)==b'x\r\n' and ff.readline()==b'END\r\n';hit=True
  ss.close();ff.close();emit('invalid_key',key_hex=key.hex(),response=response,get_hit=hit,returned_key_hex=returned)
 for n in [1048400,1048576,1048577]:emit('item_limit',payload_bytes=n,response=put(b'large',b'x'*n))
 for label,ttl in [('zero',0),('30days',2592000),('31days',2678400),('absolute31days',int(time.time())+2678400)]:
  emit('ttl',case=label,ttl=ttl,write=put(label.encode(),b'value',ttl),read=get(label.encode()) is not None)
 put(b'short',b'x',1);time.sleep(2);emit('ttl',case='1sec',read=get(b'short') is not None)
 line(b'flush_all\r\n');before=stats();t=time.perf_counter()
 for i in range(20000):
  response=put(('entry:'+str(i)).encode(),b'x'*8192)
  if response!='STORED':raise RuntimeError(response)
 after=stats();emit('capacity',writes=20000,payload_bytes=8192,stats=after,write_ms=(time.perf_counter()-t)*1000,settings=stats(b'settings'))
 # 200 independent sequential retrieval timings, 100 warm keys per item.
 for i in range(Q):
  t=time.perf_counter();hits=sum(get(('entry:'+str(19999-j)).encode()) is not None for j in range(100))
  emit('query',method='GET_8KiB_batch100',query=i,ms=(time.perf_counter()-t)*1000,hits=hits)
 s.close();f.close()

def mongo_test():
 if not pathlib.Path('/scratch/mongo-parent-bound').exists():raise RuntimeError('Rerun MongoDB with the new parent-data bind mount before writing the corpus')
 from pymongo import MongoClient
 from pymongo.errors import AutoReconnect,NetworkTimeout,_OperationCancelled
 from pymongo.operations import SearchIndexModel
 client=MongoClient('mongodb://localhost:39755/?directConnection=true',serverSelectionTimeoutMS=300000)
 def control(fn,phase):
  for attempt in range(10):
   try:return fn()
   except (AutoReconnect,NetworkTimeout,_OperationCancelled) as e:
    emit('control_retry',phase=phase,attempt=attempt,error=type(e).__name__)
    if attempt==9:raise
    time.sleep(1)
 client.admin.command('ping');emit('versions',server=client.server_info()['version'])
 col=client['storage_test']['vectors'];col.drop()
 x,q=dataset();truth=baseline(x,q);t=time.perf_counter()
 for lo in range(0,N,500):col.insert_many([{'_id':i,'vec':x[i].tolist()} for i in range(lo,min(lo+500,N))],ordered=True)
 emit('load',rows=N,dimensions=D,ms=(time.perf_counter()-t)*1000)
 quantization=CELL.split('_',1)[1]
 for quant in [quantization]:
  spec={'type':'vector','path':'vec','numDimensions':D,'similarity':'cosine'}
  if quant!='none':spec['quantization']=quant
  name='index_'+quant;t=time.perf_counter()
  col.create_search_index(SearchIndexModel(name=name,type='vectorSearch',definition={'fields':[spec]}))
  for _ in range(1800):
   rows=control(lambda:list(col.list_search_indexes(name)),'index_readiness')
   if rows and rows[0].get('queryable') and rows[0].get('status')=='READY':break
   if rows and rows[0].get('status')=='FAILED':raise RuntimeError('index failed: '+str(rows[0]))
   time.sleep(1)
  else:raise RuntimeError('index readiness timeout')
  assert col.count_documents({})==N
  emit('index',method=quant,build_ms=(time.perf_counter()-t)*1000)
  for i,v in enumerate(q):
   rows,ms=timed(lambda:list(col.aggregate([{'$vectorSearch':{'index':name,'path':'vec','queryVector':v.tolist(),'numCandidates':100,'limit':10}},{'$project':{'_id':1}}])))
   ids=[r['_id'] for r in rows];emit('query',method=quant,query=i,ids=ids,ms=ms,recall=len(set(ids)&set(truth[i]))/10,count=len(ids))
  # Atlas Required Memory is not exported by listSearchIndexes. Do not invent it from BSON storage.
  request=pathlib.Path('/scratch/metric-request.json');ack=pathlib.Path('/scratch/metric-response.json')
  temp=request.with_suffix('.tmp');temp.write_text(json.dumps(quant));temp.replace(request)
  for _ in range(120):
   if ack.exists():break
   time.sleep(.25)
  else:raise RuntimeError('metric collection timeout')
  emit('whole_server_memory',method=quant,**json.loads(ack.read_text()))
  request.unlink();ack.unlink()
  emit('metric_limit',method=quant,reason='listSearchIndexes supplies status and definition, not Atlas Required Memory; whole-server RSS is not vector-index RAM')
 client.close()

def defaults_test():
 import ast,hashlib,io,urllib.request,zipfile
 url='https://pypi.org/pypi/redisvl/0.32.1/json'
 with urllib.request.urlopen(url) as r:meta=json.load(r)
 wheel=next(w for w in meta['urls'] if w['filename'].endswith('.whl'))
 with urllib.request.urlopen(wheel['url']) as r:data=r.read()
 assert hashlib.sha256(data).hexdigest()==wheel['digests']['sha256']
 z=zipfile.ZipFile(io.BytesIO(data));found=[]
 for name in z.namelist():
  if name.endswith('.py') and '/cache/' in name:
   tree=ast.parse(z.read(name).decode())
   for node in ast.walk(tree):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
     args=node.args.args;defaults=node.args.defaults
     for arg,default in zip(args[len(args)-len(defaults):],defaults):
      if arg.arg=='distance_threshold':
       try:value=ast.literal_eval(default)
       except (ValueError,TypeError):value=ast.unparse(default)
       found.append({'file':name,'function':node.name,'default':value})
 emit('wheel_defaults',version='0.32.1',wheel_sha256=wheel['digests']['sha256'],source_url=wheel['url'],matches=found,method='AST inspection of the published wheel; client not instantiated')
 assert any(r['default']==.1 for r in found)

def duckdb_test():
 import duckdb,hashlib
 db=duckdb.connect(':memory:')
 db.execute("SET extension_directory='/scratch/duckext'")
 db.execute("SET custom_extension_repository='https://extensions.duckdb.org'")
 import requests,gzip
 url='https://extensions.duckdb.org/v2.0.1/linux_amd64/vss.duckdb_extension.gz'
 response=requests.get(url,timeout=90);response.raise_for_status();compressed=response.content
 assert hashlib.sha256(compressed).hexdigest()=='26ef35a7d52f4be1f4c4fdbde84f890b0da896e5318a871e14e546225c478c36'
 extension=pathlib.Path('/scratch/vss.duckdb_extension');extension.write_bytes(gzip.decompress(compressed))
 assert hashlib.sha256(extension.read_bytes()).hexdigest()=='8d2e738483e6191355e6c2e626b87cece0174eda8dec360ced5870603cb9cd6f'
 emit('extension_artifact',source_url=url,sha256=hashlib.sha256(extension.read_bytes()).hexdigest())
 db.execute("LOAD '/scratch/vss.duckdb_extension'")
 emit('versions',duckdb=duckdb.__version__,extensions=db.execute("SELECT extension_name,extension_version,install_mode,installed_from FROM duckdb_extensions() WHERE extension_name='vss'").fetchall())
 for path in pathlib.Path('/scratch/duckext').rglob('*.duckdb_extension'):
  emit('extension_artifact',name=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 db.execute("SET threads=2; SET memory_limit='32MiB'; SET temp_directory='/scratch/ducktemp'")
 db.execute('SELECT setseed(0.123)')
 db.execute('CREATE TABLE vectors AS SELECT i, list_transform(range(384), lambda x: (random()*2-1)::FLOAT)::FLOAT[384] AS v FROM range(100000) t(i)')
 distinct=db.execute('SELECT count(*),count(distinct v[1]) FROM vectors').fetchone();assert distinct[0]==100000 and distinct[1]>99000
 def rss():
  return int(next(x for x in pathlib.Path('/proc/self/status').read_text().splitlines() if x.startswith('VmRSS:')).split()[1])*1024
 before=rss();t=time.perf_counter()
 db.execute('CREATE INDEX ann ON vectors USING HNSW(v)')
 emit('resident_index',rows=100000,dimensions=384,duckdb_memory_limit='32MiB',rss_before_bytes=before,rss_after_bytes=rss(),index_build_ms=(time.perf_counter()-t)*1000,table_cardinality=distinct,plan=str(db.execute('EXPLAIN SELECT i FROM vectors ORDER BY array_distance(v,?::FLOAT[384]) LIMIT 10',([0.]*384,)).fetchall()),interpretation='Whole-process RSS is not isolated index RAM; HNSW allocations are outside DuckDB buffer-manager memory accounting, not out-of-core capacity')
 db.close()

emit('environment',python=platform.python_version(),packages={p:importlib.metadata.version(p) for p in ['numpy','redis','psycopg','psycopg-binary','sqlite-vec','requests']},seed=SEED,n=N,d=D,queries=Q)
{'postgres':postgres,'redis':redis_test,'valkey':redis_test,'sqlite':sqlite_test,'memcached':memcached,'mongo_none':mongo_test,'mongo_scalar':mongo_test,'mongo_binary':mongo_test,'defaults':defaults_test,'duckdb':duckdb_test}[CELL]()
emit('complete')

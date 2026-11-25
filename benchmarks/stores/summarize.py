#!/usr/bin/env python3
"""Validate complete raw cells and calculate conditional paired-query summaries."""
import collections,json,math,pathlib,random,statistics
ROOT=pathlib.Path(__file__).resolve().parent

def bootstrap(values,stat,seed=20261122):
 r=random.Random(seed);n=len(values)
 reps=sorted(stat(r.choices(values,k=n)) for _ in range(2000))
 return [reps[49],reps[1949]]
def wilson(success,n):
 z=1.95996398454;p=success/n;den=1+z*z/n
 mid=(p+z*z/(2*n))/den;delta=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return [max(0,mid-delta),min(1,mid+delta)]
def bounded_mean_ci(values,upper):
 # At an endpoint, a percentile bootstrap would falsely give zero uncertainty.
 n=len(values)
 if all(v==upper for v in values):return [upper*wilson(n,n)[0],upper]
 if all(v==0 for v in values):return [0,upper*wilson(0,n)[1]]
 return bootstrap(values,statistics.mean)

def main():
 out=ROOT/'results';summary={};raw={}
 rates={'uncached':4.0,'write_5m':5.0,'write_1h':8.0,'read':.2}
 arithmetic={'basis':'Conditional arithmetic using prices quoted by the chapter, not verified provider billing','rates_usd_per_million':rates,'rows':[dict(reads=n,uncached=(1+n)*rates['uncached'],cached5m=rates['write_5m']+n*rates['read'],cached1h=rates['write_1h']+n*rates['read']) for n in [1,2]],'spaced_10min':{'two_5min_writes':10,'one_1hour_write_one_read':8.2}}
 (out/'cache-arithmetic.json').write_text(json.dumps(arithmetic,indent=2)+'\n')
 for cell in ['sqlite','postgres','redis','valkey','memcached','mongo']:
  if cell=='mongo':
   records=[]
   for quant in ['none','scalar','binary']:
    part=[json.loads(l) for l in (out/('mongo_'+quant+'.jsonl')).read_text().splitlines()]
    assert part[-1]['kind']=='complete',quant
    records+=part
  else:records=[json.loads(l) for l in (out/(cell+'.jsonl')).read_text().splitlines()]
  assert records[-1]['kind']=='complete',f'incomplete {cell}'
  raw[cell]=records;groups=collections.defaultdict(list)
  for row in records:
   if row['kind']=='query':
    groups[(row['method'],row.get('filter','all'))].append(row)
  cells=[]
  for (method,filt),rows in groups.items():
   assert len(rows)==200 and sorted(r['query'] for r in rows)==list(range(200)),(cell,method,filt,len(rows))
   times=[r['ms'] for r in rows];d=dict(method=method,filter=filt,n=200,median_ms=statistics.median(times),median_ms_ci95=bootstrap(times,statistics.median),p95_ms=sorted(times)[189],p99_ms=sorted(times)[197])
   if 'recall' in rows[0]:
    for r in rows:
     assert len(r['ids'])==r['count'] and len(set(r['ids']))==r['count'] and all(0<=i<100000 for i in r['ids'])
    recalls=[r['recall'] for r in rows];counts=[r['count'] for r in rows]
    full=sum(c==10 for c in counts)
    d.update(mean_recall=statistics.mean(recalls),mean_recall_ci95=bounded_mean_ci(recalls,1.0),mean_count=statistics.mean(counts),mean_count_ci95=bounded_mean_ci(counts,10),full10=full,full10_wilson_ci95=wilson(full,200))
   if method=='exact':d['mean_recall_ci95']=[1.,1.];d['recall_is_reference']=True
   cells.append(d)
  summary[cell]={'queries':cells,'observations':[r for r in records if r['kind'] not in ('query','environment','plan')]}
 # Independent representations of the exact ground truth should retrieve the same ids.
 pg={r['query']:set(r['ids']) for r in raw['postgres'] if r['kind']=='query' and r['method']=='exact' and r['filter']=='all'}
 assert len(pg)==200
 for r in raw['sqlite']:
  if r['kind']=='query':assert set(r['ids'])==pg[r['query']],('sqlite ground truth mismatch',r['query'])
 for cell in ['redis','valkey']:
  for r in raw[cell]:
   if r['kind']=='query' and r['method']=='FLAT':assert set(r['ids'])==pg[r['query']],('FLAT mismatch',cell,r['query'])
 boundaries=[r for r in raw['postgres'] if r['kind']=='index_boundary'];assert len(boundaries)==8
 for r in boundaries:
  limit={'vector':2000,'halfvec':4000,'bit':64000,'sparsevec':1000}[r['type']]
  assert r['accepted']==(r.get('dimensions',r.get('nonzero'))==limit),r
 s={r['kind']:r for r in raw['sqlite'] if r['kind']!='query'}
 assert s['lost_update']=={'kind':'lost_update','writer_a_survived':False,'writer_b_survived':True}
 assert s['writer']['blocked'] and s['wal_reader']['rows']==0
 assert s['no_cascade']['fts_index_matches']==[[1]] and s['no_cascade']['vector_matches']==[[1]]
 ttl={r['case']:r for r in raw['memcached'] if r['kind']=='ttl'}
 assert all(ttl[k]['read'] for k in ['zero','30days','absolute31days']) and not ttl['31days']['read'] and not ttl['1sec']['read']
 keys={r['length']:r['response'] for r in raw['memcached'] if r['kind']=='key_limit'}
 assert keys[250]=='STORED' and keys[251]!='STORED'
 for r in raw['memcached']:
  if r['kind']=='invalid_key' and r['response']=='STORED':assert r['get_hit'] and r['returned_key_hex']==r['key_hex']
 for cell in ['redis','valkey']:
  for r in raw[cell]:
   if r['kind']=='eviction':
    if r['policy']=='noeviction':assert r['errors']>0
    else:assert r['errors']==0 and r['evicted']>0
   if r['kind']=='history':assert r['turns']==list(range(6,26))
 for r in raw['redis']:
  if r['kind']=='scores':assert r['values']==['same','1','orthogonal','0.5','opposite','0']
  if r['kind']=='filter':assert r['values']==['same']
  if r['kind']=='lease_release':assert r['wrong']==0 and r['right']==1
 features=[json.loads(l) for l in (out/'features.jsonl').read_text().splitlines()]
 for r in features:
  if r['kind']=='memcached_restart':assert r['retained']==(100 if r['mode']=='warm' else 0),r
  if r['kind']=='extstore':assert int(r['stats']['extstore_objects_written'])>0 and r['sample_retained_before']>0
  if r['kind']=='extstore_restart':assert r['retained']==0
  if r['kind']=='incompatible_options':assert isinstance(r['startup_running'],bool)
  if r['kind']=='larger_item_limit':assert r['retained']==1
 summary['features']=features
 for extra in ['defaults','duckdb']:
  observations=[json.loads(l) for l in (out/(extra+'.jsonl')).read_text().splitlines()]
  assert observations[-1]['kind']=='complete'
  summary[extra]={'observations':observations}
 native_default=json.loads((out/'redis-default.json').read_text());assert native_default['passed'] and native_default['container_removed'];summary['redis_default']=native_default
 prefix=json.loads((out/'prefix.json').read_text());assert prefix['passed'] and prefix['scratch_removed']
 summary['prefix']=prefix
 summary['validation']={'complete_cells':list(raw),'queries_per_cell':200,'ground_truth_checks':'all 200 SQLite and both Redis/Valkey FLAT results agree with PostgreSQL exact top10; boundary, expiry, ownership, eviction, restart and orphan-index assertions pass'}
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary['validation'],indent=2))
 if __name__=='__main__':pass
if __name__=='__main__':main()

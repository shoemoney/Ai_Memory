"""Independent Lucene file-size proxy, separate from process RSS and vendor estimators."""
import collections,pathlib,subprocess,re

def measure(server,quant):
 raw=subprocess.check_output(['docker','exec','--user','0',server,'find','/data','-type','f','-printf','%p %s\n'],text=True)
 files=[]
 for line in raw.splitlines():
  name,size=line.rsplit(' ',1);files.append((pathlib.PurePosixPath(name),int(size)))
 dirs={p.parent for p,n in files if p.suffix in ['.vex','.veq','.vec','.cfs']}
 selected=[(p,n) for p,n in files if p.parent in dirs]
 sizes=collections.defaultdict(int);counts=collections.Counter()
 for p,n in selected:sizes[p.suffix]+=n;counts[p.suffix]+=1
 raw_bytes=sizes['.vec'];graph=sizes['.vex'];quantized=sizes['.veq']
 vector=graph+quantized+(raw_bytes if quant=='none' else 0)
 non_compound=sum(n for p,n in selected if p.suffix!='.cfs');compound=sizes['.cfs']
 estimate=vector+(int(compound*vector/non_compound) if non_compound else 0)
 try:smaps=subprocess.check_output(['docker','exec','--user','0',server,'sh','-c','for task_proc in /proc/[0-9]*; do if [ "$(cat "$task_proc/comm" 2>/dev/null)" = java ]; then cat "$task_proc/smaps"; fi; done'],text=True,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError:smaps=''
 mapped=collections.defaultdict(lambda:{'rss_bytes':0,'pss_bytes':0,'mapped_bytes':0});extension=None
 for line in smaps.splitlines():
  if re.match(r'^[0-9a-f]+-[0-9a-f]+ ',line):
   name=line.split()[-1];extension=pathlib.PurePosixPath(name).suffix if name.startswith('/data/') and not line.endswith('(deleted)') else None
  elif extension and line.startswith(('Rss:','Pss:','Size:')):
   field={'Rss:':'rss_bytes','Pss:':'pss_bytes','Size:':'mapped_bytes'}[line.split()[0]];mapped[extension][field]+=int(line.split()[1])*1024
 selected_suffixes=['.vex','.veq']+(['.vec'] if quant=='none' else [])
 resident=sum(mapped[ext]['rss_bytes'] for ext in selected_suffixes)
 return {'smaps_readable':bool(smaps),'mapped_memory_by_suffix':dict(mapped),'selected_vector_graph_rss_bytes':resident,'quantization':quant,'bytes_by_suffix':dict(sizes),'count_by_suffix':dict(counts),'lucene_file_count':len(selected),'graph_vector_file_bytes':vector,'compound_adjusted_file_proxy_bytes':estimate,'metric':'independent on-disk file-size proxy for vector working set; not resident RSS and not a vendor fallback computed from its advertised ratios'}


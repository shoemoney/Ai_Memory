"""Fetch public release metadata and verify structural claims without storing datasets."""
import concurrent.futures,collections
from common import *
REPOS={'beam':('mohammadtavakoli78/BEAM','b2da22eac88bb0874c64665f13457eb99835774a'),'arena':('ZexueHe/MemoryArena','6cd9de14b71915e39ac742a20dc33785e14b6aab'),'state':('microsoft/STATE-Bench','5644b1838d96bc4483da29642d058ecaa6f80f7f'),'cmb':('Tencent-Hunyuan/Hy-Memory','d8138b501a755f662a024f7e8eb879613eabf1d3')}
def cmb_release_check(repo):
 from datetime import datetime,timezone
 def pages(kind):
  values=[];page=1
  while True:
   r=requests.get(f'https://api.github.com/repos/{repo}/{kind}',params={'per_page':100,'page':page},timeout=120);r.raise_for_status();chunk=r.json();values.extend(chunk)
   if len(chunk)<100:return values
   page+=1
 releases=pages('releases');branches=pages('branches')
 r=requests.get('https://huggingface.co/api/datasets',params={'author':'tencent','search':'memory','limit':100},timeout=90);r.raise_for_status()
 return {'checked_date':datetime.now(timezone.utc).date().isoformat(),'release_tags':[x['tag_name'] for x in releases],'release_assets':[{'tag':x['tag_name'],'name':a['name'],'bytes':a['size']} for x in releases for a in x.get('assets',[])],'release_body_benchmark_mentions':[x['tag_name'] for x in releases if re.search(r'\bcmb\b|benchmark|dataset',x.get('body') or '',re.I)],'public_branch_count':len(branches),'benchmark_named_branches':[b['name'] for b in branches if any(t in b['name'].lower() for t in ['cmb','benchmark','dataset'])],'publisher_memory_dataset_search_matches':r.json(),'scope':'No exhaustive search of every feature-branch tree; release and branch-name metadata only.'}

def main():
 LAB.mkdir(parents=True,exist_ok=True);out={}
 for name,(repo,rev) in REPOS.items():
  response=requests.get(f'https://api.github.com/repos/{repo}/git/trees/{rev}',params={'recursive':1},timeout=120);response.raise_for_status();tree=response.json();assert not tree.get('truncated')
  paths=[x['path'] for x in tree['tree'] if x['type']=='blob']
  d={'repo':f'https://github.com/{repo}','revision':rev,'tree_sha256':sha(response.content),'root_license_paths':[p for p in paths if '/' not in p and 'license' in p.lower()]}
  if name=='beam':
   questions=[p for p in paths if re.fullmatch(r'chats/[^/]+/[^/]+/probing_questions/probing_questions.json',p)]
   def count(p):
    r=requests.get(f'https://raw.githubusercontent.com/{repo}/{rev}/{p}',timeout=90);r.raise_for_status();j=r.json();return {'path':p,'sha256':sha(r.content),'n':sum(len(v) for v in j.values()),'types':{k:len(v) for k,v in j.items()}}
   with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:counts=list(pool.map(count,questions))
   d.update(conversations=len(questions),questions=sum(c['n'] for c in counts),scales=dict(collections.Counter(p.split('/')[1] for p in questions)),question_files=counts,license='MIT',status='Public data and rubric scoring. Local reader/judge adaptation possible. Only release-count pilot run; LIGHT gain and context-length degradation not reproduced.')
  elif name=='state':
   d.update(task_files=[p for p in paths if re.fullmatch(r'state_bench/domains/[^/]+/tasks/[^/]+\.json',p)],license='MIT',status='Public data, tools and scoring. Official current protocol locks hosted GPT-5.4 simulator and judge, so official performance cannot be reproduced with local open weights. Replacing them is an adaptation.')
   d['task_count']=len(d['task_files'])
  elif name=='arena':
   d.update(setup_guides=[p for p in paths if p.startswith('setup_')],license='No top-level license in inspected tree; embedded MemoRAG license does not license the whole release',status='Public environments, task data links and configurable endpoints. A local action adaptation is feasible, but the published proprietary-backbone comparison cannot be reproduced locally; this release audit does not measure performance.')
  else:
   d['additional_release_check']=cmb_release_check(repo)
   d.update(benchmark_named_files=[p for p in paths if any(k in p.lower() for k in ['cmb','coding_memory_benchmark','benchmark','dataset'])],license='Repository Apache-2.0; no separate benchmark-data license or frozen task release located',status='Paper public. No frozen CMB histories, 216-task suite, diagnostic references or grading assets in inspected official repository tree. Cannot be reproduced locally from that release.')
  out[name]=d
 atomic(OUT/'source-audit.json',out);print({k:{a:b for a,b in v.items() if a in ['conversations','questions','scales','task_count','status']} for k,v in out.items()})
if __name__=='__main__':main()

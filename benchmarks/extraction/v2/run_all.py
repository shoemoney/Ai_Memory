"""One command; resumable, bounded local generation and judging on one remote model."""
import argparse,datetime,json,os,random,time,traceback
from bench import ROOT,check_lock,generate_arm,read
from host import Host
import judge

def run():
 p=argparse.ArgumentParser();p.add_argument('--deadline',default=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=9.5)).isoformat());p.add_argument('--skip-validation',action='store_true');a=p.parse_args()
 deadline=datetime.datetime.fromisoformat(a.deadline).timestamp();check_lock()
 models=json.loads((ROOT/'models.json').read_text());byid={m['id']:m for m in models};arms=[{'arm':m['id'],'model':m['id']}for m in models];arms.append({'arm':'qwen3.5-4b-q4_k_m-repeat-1.1','model':'qwen3.5-4b-q4_k_m'})
 schedulepath=ROOT/'results/schedule.json'
 if not schedulepath.exists():
  schedule=[]
  for seed in (7,19,43):
   order=list(arms);random.Random(seed+20261121).shuffle(order)
   schedule.extend({**arm,'seed':seed}for arm in order)
  schedulepath.write_text(json.dumps(schedule,indent=2)+'\n')
 schedule=json.loads(schedulepath.read_text());h=Host(deadline=deadline);h.setup();complete=False
 try:
  if not a.skip_validation:
   gate=ROOT/'results/judge-validation-summary.json'
   if not gate.exists():h.load(byid['qwen3.5-9b-q4_k_m']);judge.validate(h)
   assert json.loads(gate.read_text())['pass']
  for item in schedule:
   done=read(ROOT/'results/writers'/f'{item["arm"]}.jsonl')
   if sum(r['seed']==item['seed']for r in done)==300:continue
   h.load(byid[item['model']]);generate_arm(h,item['arm'],byid[item['model']],item['seed'])
  h.load(byid['qwen3.5-9b-q4_k_m']);judge.validate(h);judge.score(h)
  complete=True
 except Exception as e:
  (ROOT/'results/run-error.json').write_text(json.dumps({'error_type':type(e).__name__,'message':h.clean(str(e)),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
  traceback.print_exc();raise
 finally:
  # An unexpected process failure leaves resumable files; deadline or successful finish cleans everything.
  h.close(cleanup=complete or time.time()>=deadline)
  (ROOT/'results/run-status.json').write_text(json.dumps({'complete':complete,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'deadline':a.deadline},indent=2)+'\n')
 if complete:
  import analyze
  analyze.run()
if __name__=='__main__':run()

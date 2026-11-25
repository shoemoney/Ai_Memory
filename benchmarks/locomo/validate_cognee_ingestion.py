"""Exclude questions from a Cognee store whose final native run did not complete."""
import re
from full_common import *

def main():
 proof={}
 for conv in read(OUT/'conversations.json'):
  ci=conv['conversation'];last=conv['sessions'][-1]['key'];path=OUT/'ingest/cognee'/f'c{ci}-{last}.json'
  result=read(path) if path.exists() else {}
  complete=result.get('all_data_completed',bool(re.search(r"^\{UUID\('[^']+'\): PipelineRun(?:Already)?Completed\(",result.get('cognify_result',''))))
  rows=list((OUT/'items/cognee').glob(f'c{ci:02d}-*.json'))
  excluded=[]
  if rows and not complete:
   archive=OUT/'excluded-cognee-incomplete-store';archive.mkdir(exist_ok=True)
   for row in rows:
    excluded.append(row.stem);row.rename(archive/row.name)
  attempted=list((OUT/'ingest/cognee').glob(f'c{ci}-session_*.json'))
  latest=max(attempted,key=lambda p:int(re.search(r'session_(\d+)',p.name)[1])) if attempted else None
  latest_text=read(latest).get('cognify_result','') if latest else ''
  status=re.search(r': (PipelineRun\w+)\(',latest_text)
  if path.exists() or rows or attempted:proof[str(ci)]=dict(final_native_run_completed=complete,last_required_session=last,checkpoint=str(path.relative_to(OUT)),session_checkpoints=len(attempted),expected_sessions=len(conv['sessions']),latest_checkpoint=str(latest.relative_to(OUT)) if latest else None,latest_native_status=status[1] if status else None,excluded_question_ids=excluded)
 atomic(OUT/'cognee-final-ingestion-validation.json',proof)
 print(proof)

if __name__=='__main__':main()

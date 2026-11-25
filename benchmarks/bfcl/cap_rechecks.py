"""Re-run the six pilot token-limit cases at the official Qwen adapter's 16K cap."""
import argparse,copy,json,os,time
from dataclasses import replace
from pathlib import Path
from full_common import ROOT,LAB,SEED,TOKEN_CAP,atomic,digest,absence_credits,RUN_DIR

def main():
 p=argparse.ArgumentParser();p.add_argument('--size',required=True);p.add_argument('--deadline',required=True,type=float);a=p.parse_args()
 # Reuse completed diagnostics before importing the heavyweight evaluator stack.
 pending=False
 for src in (ROOT/'pilot/results').glob('*/*/*/*.json'):
  old=json.loads(src.read_text())
  if not old.get('response') or not old['request']['model'].endswith(f'-{a.size}-Q4_K_M'):continue
  if old['response']['choices'][0]['finish_reason']!='length':continue
  mode='on' if old['request']['extra_body']['chat_template_kwargs']['enable_thinking'] else 'off'
  if not (RUN_DIR/a.size/'cap_rechecks'/mode/(old['id']+'.json')).exists():pending=True;break
 if not pending:return
 os.environ.update(OPENAI_API_KEY='local',OPENAI_BASE_URL=os.getenv('BASE_URL','http://localhost:39730/v1'),BFCL_PROJECT_ROOT=str(LAB/'bfcl-runtime'),HF_HOME=str(LAB/'hf-cache'),HF_HUB_OFFLINE='1')
 import bfcl_eval
 from bfcl_eval.model_handler.api_inference.openai_completion import OpenAICompletionsHandler
 from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING
 from bfcl_eval.constants.enums import Language,ReturnFormat
 from bfcl_eval.eval_checker.eval_runner import _evaluate_single_ast_entry,_evaluate_single_relevance_entry
 from bfcl_eval.utils import load_dataset_entry,load_ground_truth_entry
 alias=f'membench-bfcl-Qwen3.5-{a.size}-Q4_K_M'
 MODEL_CONFIG_MAPPING['cap-recheck-FC']=replace(MODEL_CONFIG_MAPPING['gpt-4o-2024-11-20-FC'],model_name=alias,model_handler=OpenAICompletionsHandler)
 h=OpenAICompletionsHandler(alias,0,'cap-recheck-FC',True)
 for src in sorted((ROOT/'pilot/results').glob('*/*/*/*.json')):
  old=json.loads(src.read_text())
  if not old.get('response') or not old['request']['model'].endswith(f'-{a.size}-Q4_K_M'):continue
  if old['response']['choices'][0]['finish_reason']!='length':continue
  mode='on' if old['request']['extra_body']['chat_template_kwargs']['enable_thinking'] else 'off'
  out=RUN_DIR/a.size/'cap_rechecks'/mode/(old['id']+'.json')
  if out.exists():continue
  if time.time()>=a.deadline:return
  request=copy.deepcopy(old['request']);request.update(model=alias,max_tokens=TOKEN_CAP)
  raw_path=out.with_suffix('.raw.json')
  if raw_path.exists():response=json.loads(raw_path.read_text())['response']
  else:
   response=h.client.with_options(timeout=max(1,min(900,a.deadline-time.time())),max_retries=0).chat.completions.create(**request).model_dump()
   atomic(raw_path,{'request':request,'response':response})
  from openai.types.chat import ChatCompletion
  result=h._parse_query_response_FC(ChatCompletion.model_validate(response))['model_responses']
  cat=old['category'];entry=next(e for e in load_dataset_entry(cat,include_language_specific_hint=False) if e['id']==old['id'])
  if 'irrelevance' in cat:score=_evaluate_single_relevance_entry(h,old['id'],result,entry,'cap-recheck-FC',cat)
  else:
   truth=next(e['ground_truth'] for e in load_ground_truth_entry(cat) if e['id']==old['id'])
   score=_evaluate_single_ast_entry(h,old['id'],result,truth,entry,'cap-recheck-FC',cat,Language.PYTHON,ReturnFormat.PYTHON)
  msg=response['choices'][0]['message'];empty=not(msg.get('content')or'').strip() and not msg.get('tool_calls')
  credit,malformed=absence_credits(cat,score['valid'],msg)
  atomic(out,{'id':old['id'],'mode':mode,'pilot_source':str(src.relative_to(ROOT)),'pilot_correct':old['score']['valid'],'pilot_cap':4096,'cap':TOKEN_CAP,'request':request,'response':response,'result':result,'score':score,'empty_answer_credit':credit,'malformed_tool_credit':malformed,'length_stopped':response['choices'][0]['finish_reason']=='length'})
if __name__=='__main__':main()

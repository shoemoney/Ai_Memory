"""Offline negative/positive proofs for official evaluators, state isolation and weights."""
import copy,json,os
from pathlib import Path
from dataclasses import replace
from full_common import ROOT,LAB,weights,absence_credits,atomic
os.environ.update(BFCL_PROJECT_ROOT=str(LAB/'verify-runtime'),HF_HOME=str(LAB/'hf-cache'),HF_HUB_OFFLINE='1',OPENAI_API_KEY='local')
from bfcl_eval.utils import load_dataset_entry,load_ground_truth_entry
from bfcl_eval.model_handler.api_inference.openai_completion import OpenAICompletionsHandler
from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING
from bfcl_eval.constants.enums import Language,ReturnFormat
from bfcl_eval.eval_checker.eval_runner import _evaluate_single_ast_entry,_evaluate_single_agentic_entry
from bfcl_eval.eval_checker.multi_turn_eval.func_source_code.memory_kv import MemoryAPI_kv
from bfcl_eval.eval_checker.multi_turn_eval.func_source_code.memory_rec_sum import MemoryAPI_rec_sum
from bfcl_eval.eval_checker.multi_turn_eval.func_source_code.memory_vector import MemoryAPI_vector
from bfcl_eval.eval_checker.eval_runner_helper import calculate_unweighted_accuracy,calculate_weighted_accuracy,calculate_percentage_weighted_accuracy
MODEL_CONFIG_MAPPING['verify-full-FC']=replace(MODEL_CONFIG_MAPPING['gpt-4o-2024-11-20-FC'],model_handler=OpenAICompletionsHandler)
h=OpenAICompletionsHandler('local',0,'verify-full-FC',True)
flags={}
for cat,lang in [('simple_java',Language.JAVA),('simple_javascript',Language.JAVASCRIPT)]:
 e=load_dataset_entry(cat,include_language_specific_hint=False)[0]
 t=load_ground_truth_entry(cat)[0]['ground_truth']
 # Construct a native-FC good answer from the official expected values.
 func=t[0];name=next(iter(func));args={k:vs[0] for k,vs in func[name].items()}
 # Java/JavaScript FC arguments represent the source-language expression as a string.
 args={k:json.dumps(v).lower() if isinstance(v,bool) else str(v) for k,v in args.items()}
 result=[{name.replace('.','_'):json.dumps(args)}]
 valid=_evaluate_single_ast_entry(h,e['id'],result,t,copy.deepcopy(e),'verify-full-FC',cat,lang,ReturnFormat.PYTHON)['valid']
 invalid=_evaluate_single_ast_entry(h,e['id'],[{'wrong_function':'{}'}],t,copy.deepcopy(e),'verify-full-FC',cat,lang,ReturnFormat.PYTHON)['valid']
 if not valid or invalid:raise AssertionError((cat,valid,invalid,args))
 flags[cat]=[valid,invalid]
for backend,cls in [('kv',MemoryAPI_kv),('rec_sum',MemoryAPI_rec_sum),('vector',MemoryAPI_vector)]:
 root=LAB/'verify-memory'/backend
 config={'model_result_dir':root,'test_id':f'memory_{backend}_prereq_32-notetaker-0','scenario':'notetaker'}
 first=cls();first._load_scenario(config)
 if backend=='kv':first.core_memory_add('color','blue')
 elif backend=='rec_sum':first.memory_append('The color is blue.')
 else:first.core_memory_add('The color is blue.')
 first._flush_memory_to_local_file()
 config['test_id']=f'memory_{backend}_0-notetaker-0'
 fresh=cls();fresh._load_scenario(config)
 if 'blue' not in fresh._dump_core_memory_to_context():raise AssertionError('Snapshot was not retained')
 flags['memory_'+backend]='write -> disk snapshot -> fresh instance read passed'
entry=load_dataset_entry('memory_kv',include_prereq=False,include_language_specific_hint=False)[0]
flags['agentic_correct_then_wrong']=[_evaluate_single_agentic_entry(h,entry['id'],[[s]],['blue'],entry,'verify-full-FC','memory_kv')['valid'] for s in ['ANSWER: blue','ANSWER: red']]
if flags['agentic_correct_then_wrong']!=[True,False]:raise AssertionError(flags)
manifest=json.loads((ROOT/'results/full/manifest.json').read_text());pops={c:d['population'] for c,d in manifest['categories'].items()};w=weights(pops)
if abs(sum(w.values())-.8)>1e-12:raise AssertionError('Wrong offline mass')
# Independent official helper composition agrees with the flattened weights.
rates={c:(i+1)/(len(w)+1) for i,c in enumerate(w)}
def d(c):return {'accuracy':rates[c],'display_accuracy':rates[c],'total_count':pops[c]}
simple=calculate_unweighted_accuracy([d(c) for c in ['simple_python','simple_java','simple_javascript']])
nonlive=calculate_unweighted_accuracy([simple]+[d(c) for c in ['multiple','parallel','parallel_multiple']])
live=calculate_weighted_accuracy([d(c) for c in ['live_simple','live_multiple','live_parallel','live_parallel_multiple']])
irr=calculate_unweighted_accuracy([d(c) for c in ['irrelevance','live_irrelevance']])
mt=calculate_unweighted_accuracy([d(c) for c in ['multi_turn_base','multi_turn_miss_func','multi_turn_miss_param','multi_turn_long_context']])
mem=calculate_unweighted_accuracy([d(c) for c in ['memory_kv','memory_vector','memory_rec_sum']])
zero={'accuracy':0,'display_accuracy':0,'total_count':200}
agentic=calculate_unweighted_accuracy([zero,mem])
official=calculate_percentage_weighted_accuracy([nonlive,live,irr,mt,agentic],[10,10,10,30,40])['accuracy']
flat=sum(w[c]*rates[c] for c in w)
if abs(official-flat)>1e-12:raise AssertionError((official,flat))
flags['weight_formula_matches_official_helpers']=True
if absence_credits('irrelevance',True,{'content':''})!=(True,False):raise AssertionError('Empty credit not separated')
if absence_credits('irrelevance',True,{'tool_calls':[{}]})!=(False,True):raise AssertionError('Malformed credit not separated')
flags['absence_credits_excluded_from_skill']=True
atomic(ROOT/'evidence/full-verification.json',flags)
print(json.dumps(flags,indent=2))

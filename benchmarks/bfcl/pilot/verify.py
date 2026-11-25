"""Fail-capable sanity probes for the official scoring integration."""
import copy
import json
import os
from dataclasses import replace
from pathlib import Path
os.environ['OPENAI_API_KEY'] = 'local'
import bfcl_eval
from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING
from bfcl_eval.constants.enums import Language, ReturnFormat
from bfcl_eval.model_handler.api_inference.openai_completion import OpenAICompletionsHandler
from bfcl_eval.eval_checker.eval_runner import _evaluate_single_ast_entry, _evaluate_single_relevance_entry
MODEL_CONFIG_MAPPING['local-subset-FC'] = replace(MODEL_CONFIG_MAPPING['gpt-4o-2024-11-20-FC'], model_handler=OpenAICompletionsHandler)
h = OpenAICompletionsHandler('local', 0, 'local-subset-FC', True)
data = Path(bfcl_eval.__file__).parent/'data'
entry = json.loads((data/'BFCL_v4_simple_python.json').read_text().splitlines()[0])
truth = json.loads((data/'possible_answer/BFCL_v4_simple_python.json').read_text().splitlines()[0])['ground_truth']
flags = []
for base in [10,999]:
    result = [{'calculate_triangle_area': json.dumps({'base': base, 'height': 5})}]
    flags.append(_evaluate_single_ast_entry(h,entry['id'],result,truth,copy.deepcopy(entry),'local-subset-FC','simple_python',Language.PYTHON,ReturnFormat.PYTHON)['valid'])
if flags != [True,False]:
    raise AssertionError(flags)
irrelevant = json.loads((data/'BFCL_v4_irrelevance.json').read_text().splitlines()[0])
irr_flags = [_evaluate_single_relevance_entry(h, irrelevant['id'],r,copy.deepcopy(irrelevant),'local-subset-FC','irrelevance')['valid'] for r in ['No suitable tool.', [{'unwanted_call': '{}'}]]]
if irr_flags != [True,False]:
    raise AssertionError(irr_flags)
proof = {'ast_correct_then_wrong': flags, 'irrelevance_no_call_then_call': irr_flags}
(Path(__file__).resolve().parent/'evidence/scorer-verification.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof))

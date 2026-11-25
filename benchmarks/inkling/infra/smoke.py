#!/usr/bin/env python3
import json,time,urllib.request
from pathlib import Path
out=Path(__file__).resolve().parent
model='Inkling-2-Mini-oQ4e-stock'; base='http://127.0.0.1:39850'
with urllib.request.urlopen(base+'/v1/models',timeout=20) as r:models=json.load(r)
(out/'smoke-models.json').write_text(json.dumps(models,indent=2))
assert model in [m['id'] for m in models['data']], models
payload={'model':model,'messages':[{'role':'user','content':'Who wrote Pride and Prejudice? Answer in one sentence.'}],'max_tokens':128,'temperature':0,'thinking_budget':0,'chat_template_kwargs':{'enable_thinking':False}}
(out/'smoke-request.json').write_text(json.dumps(payload,indent=2))
req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
start=time.monotonic()
with urllib.request.urlopen(req,timeout=300) as r:response=json.load(r)
elapsed=time.monotonic()-start
(out/'smoke-response.json').write_text(json.dumps(response,indent=2))
content=response['choices'][0]['message'].get('content') or ''
assert 'austen' in content.lower(),content
usage=response.get('usage',{})
summary={'model_id':response['model'],'answer':content,'elapsed_seconds':elapsed,'usage':usage,'completion_tokens_per_wall_second':usage.get('completion_tokens',0)/elapsed,'pass':True,'note':'Single short cold-load smoke; throughput is not a benchmark score.'}
(out/'smoke-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))

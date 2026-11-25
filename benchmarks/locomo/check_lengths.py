"""Check that complete conversations fit the configured model window."""
import urllib.request,json
from full_common import *
from run import ANSWER_SYSTEM
rows=[]
for conv in read(OUT/'conversations.json'):
 text=ANSWER_SYSTEM+'\nConversation evidence:\n'+'\n'.join(conv['turns'])
 request=urllib.request.Request('http://localhost:39700/tokenize',json.dumps({'content':text,'add_special':True}).encode(),{'Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=30) as response:n=len(json.load(response)['tokens'])
 rows.append({'conversation':conv['conversation'],'evidence_and_system_tokens':n,'reserved_for_question_template_and_output':5120})
 if n+5120>65536:raise RuntimeError('Conversation exceeds the configured full-context window')
atomic(OUT/'token-lengths.json',{'context_window':65536,'records':rows,'all_fit':True})
print(json.dumps(rows,indent=2))

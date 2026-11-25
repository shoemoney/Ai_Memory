"""Can-fail checks for extraction acceptance and recall-premise separation."""
import json
from bench import check_lock,validate
check_lock()
def response(x,finish='stop',**kwargs):return {'choices':[{'finish_reason':finish,'message':{'content':x,**kwargs}}]}
good={'fact':'USER likes tea.','subject':'USER','category':'preference','date':'unknown'}
assert validate(response(json.dumps([good])))[0]
assert validate(response('[]'))[0]
for value in [{'fact':'x'},[good,good],[{**good,'date':None}],[{**good,'category':'made-up'}],[{**good,'subject':''}],{'x':good}]:assert not validate(response(json.dumps(value)))[0]
assert not validate(response(json.dumps([good]),finish='length'))[0]
assert not validate(response(json.dumps([good]),reasoning_content='hidden'))[0]
assert not validate(response(json.dumps([good]),refusal='refused'))[0]
assert not validate(response('[{"fact":"one","fact":"two","subject":"USER","category":"other","date":"unknown"}]'))[0]
print('Acceptance rejects truncation, reasoning, refusal, malformed schema and duplicate keys; frozen hashes match.')
from judge import coverage_text,decision_key
written=['I like tea. [subject: I; date: unknown]']
bound=coverage_text(written,'USER')
assert 'USER' in bound and written[0] in bound and 'coffee' not in bound
assert decision_key('USER likes coffee.',written,['USER likes coffee.'],'USER')!=decision_key('USER likes coffee.',written,['USER likes coffee.'],'PERSON_001')
print('Coverage context includes written records and identity only; subject binding changes cache identity.')

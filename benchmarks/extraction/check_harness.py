"""Small can-fail checks for the actual output acceptance boundary."""
from bench import validate

def response(content,finish='stop',**extra):
    return {'choices':[{'finish_reason':finish,'message':{'content':content,**extra}}]}
valid='{"name":"PERSON_01","city":"","likes":"coffee"}'
assert validate(response(valid))[-1]
for bad in ['{"name":"a","name":"b","city":"","likes":""}', valid+' commentary']:
    try: validate(response(bad))
    except ValueError: pass
    else: raise AssertionError('Invalid JSON accepted')
for bad in ['[]','{"name":"x","city":""}','{"name":"x","city":"","likes":42}', '{"name":"x","city":"","likes":"","extra":""}']:
    assert not validate(response(bad))[-1]
assert not validate(response(valid,finish='length'))[-1]
assert not validate(response(valid,reasoning_content='thinking'))[-1]
assert not validate(response(valid,refusal='refused'))[-1]
print('Acceptance checks passed, including duplicate keys, prose, schema errors, truncation, refusal and reasoning.')

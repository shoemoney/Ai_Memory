"""Mask regenerated names in archived text without changing scores or QA inputs.

Run after model work stops. Original record/response hashes remain in the export
manifest. The actual automated scoring happens before this archival operation.
"""
import argparse,hashlib,json,re
from functools import lru_cache
from full_common import OUT,read,atomic
from run import ANSWER_SYSTEM


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def main(check=False):
    mapping=read(OUT/'name-hashes.json')
    @lru_cache(maxsize=None)
    def word(token):
        return mapping.get(hashlib.sha256(token.lower().encode()).hexdigest(),token)
    def mask(value):
        if isinstance(value,str):
            return re.sub(r'\b[A-Za-z]+\b',lambda m:word(m[0]),value)
        if isinstance(value,list):return [mask(x) for x in value]
        if isinstance(value,dict):return {k:mask(v) for k,v in value.items()}
        return value
    pending=[];request_changes=0
    for path in sorted(OUT.rglob('*.json')):
        if path.name=='privacy-export.json':continue
        old=read(path);new=mask(old)
        if new==old:continue
        relative=str(path.relative_to(OUT))
        is_raw=path.parent==OUT/'raw-calls'
        if path.name in ['selection.json','conversations.json']:
            raise AssertionError('A scoring input needs a preprocessing correction, not archival redaction: '+relative)
        if is_raw:
            changed_request=new['request']!=old['request']
            qa=any(m.get('content')==ANSWER_SYSTEM or str(m.get('content','')).startswith('Grade whether the generated answer') for m in old['request']['messages'])
            assert not (qa and changed_request), 'A scored QA request would change: '+relative
            assert not changed_request, 'An extraction request would change; inspect before exporting: '+relative
            request_changes+=changed_request
            new['privacy_export']={
                'original_record_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'original_request_sha256':old['request_sha256'],
                'exported_request_sha256':hashlib.sha256(json.dumps(new['request'],sort_keys=True).encode()).hexdigest(),
                'original_response_sha256':digest(old['response']),
                'exported_response_sha256':digest(new['response']),
                'request_text_changed':changed_request,
                'rule':'Names replaced by the same precommitted aliases for archival privacy. Token usage and response IDs are original. Scores and effective QA inputs unchanged.'}
        if path.parent.parent==OUT/'items':
            for key in ['item_id','question','gold','category','original_question_sha256','correct','complete']:
                assert new.get(key)==old.get(key),(relative,key)
            assert [(x['label'],x['seed']) for x in new['votes']]==[(x['label'],x['seed']) for x in old['votes']]
        pending.append((path,new,dict(path=relative,original_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),raw_model_record=is_raw)))
    print(json.dumps(dict(changed_files=len(pending),extraction_request_records_changed=request_changes,check_only=check)))
    if check:return
    previous=read(OUT/'privacy-export.json') if (OUT/'privacy-export.json').exists() else {'records':[]}
    records={x['path']:x for x in previous['records']}
    for path,new,record in pending:
        atomic(path,new);record['exported_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();records[record['path']]=record
    atomic(OUT/'privacy-export.json',dict(rule='Archival name masking after automated scoring; no score, label, sample or effective QA input changed.',alias_dictionary_sha256=digest(mapping),records=list(records.values())))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args();main(args.check)

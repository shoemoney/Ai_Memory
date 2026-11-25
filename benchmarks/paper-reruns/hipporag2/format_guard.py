"""Retry extraction responses that the native parser/type checks reject.

No semantic judging or fact correction occurs. Native-accepted responses are unchanged.
"""
import hashlib
import json
import os
from pathlib import Path
import threading
from hipporag.information_extraction.openie_openai import _extract_json_list_field, _extract_ner_from_response
from hipporag.prompts import PromptTemplateManager
from hipporag.utils.llm_utils import fix_broken_generated_json, filter_invalid_triples


MAX_SCHEMA_ATTEMPTS = 10  # raised from 3 after two chunks exhausted three; earlier accepted attempts (0-2) are unchanged


class NativeFormatGuard:
    def __init__(self, base, audit_path):
        self.base=base
        self.audit_path=Path(audit_path)
        self.lock=threading.Lock()
        manager=PromptTemplateManager(role_mapping={'system':'system','user':'user','assistant':'assistant'})
        self.systems={
            'ner':manager.render(name='ner',passage='')[0]['content'],
            'triples':manager.render(name='triple_extraction',passage='',named_entity_json='{"named_entities":[]}')[0]['content']}

    def __getattr__(self,name):
        return getattr(self.base,name)

    @staticmethod
    def validate(kind,response,metadata):
        text=fix_broken_generated_json(response) if metadata.get('finish_reason')=='length' else response
        if kind=='ner':
            values=_extract_ner_from_response(text)
            if not all(isinstance(v,str) for v in values):
                raise TypeError('Native merge requires entity strings')
        else:
            values=filter_invalid_triples(_extract_json_list_field(text,'triples'))
            if not all(isinstance(v,(list,tuple)) and len(v)==3 and all(isinstance(x,str) for x in v) for v in values):
                raise TypeError('Native merge requires triples of three strings')

    def audit(self,row):
        with self.lock:
            with self.audit_path.open('a') as f:
                f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())

    def infer(self,messages,**kwargs):
        kind=next((k for k,s in self.systems.items() if messages and messages[0].get('content')==s),None)
        result=self.base.infer(messages,**kwargs)
        if kind is None:return result
        fingerprint=hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest()
        try:
            self.validate(kind,result[0],result[1])
            return result
        except (ValueError,TypeError,KeyError) as error:
            self.audit({'kind':kind,'prompt_sha256':fingerprint,'stage':'native-rejected','error':str(error),'response':result[0],'finish_reason':result[1].get('finish_reason')})
        field='named_entities' if kind=='ner' else 'triples'
        item={'type':'string'} if kind=='ner' else {'type':'array','items':{'type':'string'},'minItems':3,'maxItems':3}
        schema={'type':'object','properties':{field:{'type':'array','items':item}},'required':[field],'additionalProperties':False}
        for attempt in range(MAX_SCHEMA_ATTEMPTS):
            constrained=dict(kwargs)
            constrained['response_format']={'type':'json_schema','json_schema':{'name':'openie_'+kind,'strict':True,'schema':schema}}
            constrained['seed']=self.base.global_config.seed+attempt
            repaired=self.base.infer(messages,**constrained)
            try:
                self.validate(kind,repaired[0],repaired[1])
            except (ValueError,TypeError,KeyError) as error:
                self.audit({'kind':kind,'prompt_sha256':fingerprint,'stage':'schema-rejected','attempt':attempt,'error':str(error),'response':repaired[0]})
                continue
            self.audit({'kind':kind,'prompt_sha256':fingerprint,'stage':'schema-accepted','attempt':attempt,'response':repaired[0]})
            return repaired
        # Runaway repetition truncated at the token limit on every attempt: the passage gets zero triples
        # (still indexed as a passage node) and the event is audited, instead of aborting the whole index.
        self.audit({'kind':kind,'prompt_sha256':fingerprint,'stage':'exhausted-empty','attempts':MAX_SCHEMA_ATTEMPTS})
        empty='{"named_entities": []}' if kind=='ner' else '{"triples": []}'
        meta=dict(repaired[1]); meta['finish_reason']='stop'
        return (empty,meta)+tuple(repaired[2:])

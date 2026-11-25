#!/usr/bin/env python3
"""Export only task instructions from the pinned official MTEB wrappers."""
import json
from pathlib import Path
import mteb
from mteb.types import PromptType
from mteb.models.abs_encoder import AbsEncoder
from mteb.models.model_implementations.qwen3_models import instruction_template
from mteb.models.model_implementations.qwen3_vl_embedding_models import Qwen3VLEmbeddingWrapper

def export():
    class PromptOnly(AbsEncoder):
        def encode(self,*args,**kwargs):raise RuntimeError('Instructions only; no model is loaded')
    text=PromptOnly();text.instruction_template=instruction_template
    vl=Qwen3VLEmbeddingWrapper.__new__(Qwen3VLEmbeddingWrapper)
    harrier=PromptOnly()
    harrier_meta=mteb.get_model_meta('microsoft/harrier-oss-v1-27b')
    harrier.prompts_dict=harrier_meta.loader_kwargs['prompts_dict']
    harrier.instruction_template=harrier_meta.loader_kwargs['instruction_template']
    rows={}
    for name in ['SciFact','NFCorpus','ArguAna','Vidore3HrRetrieval']:
        task=mteb.get_task(name)
        rows[name]={}
        for kind,wrapper in [('text',text),('vl',vl),('harrier',harrier)]:
            rows[name][kind]={}
            for role in [PromptType.query,PromptType.document]:
                prompt=wrapper.get_task_instruction(task.metadata,role)
                if kind in ('text','harrier') and role==PromptType.document:prompt=''
                rows[name][kind][role.value]=prompt
    return {'mteb_version':'2.27.20','instructions':rows}
if __name__=='__main__':
    Path(__file__).with_name('instructions.json').write_text(json.dumps(export(),indent=2)+'\n')

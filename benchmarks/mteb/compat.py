"""Loading-only compatibility for Jina's historical SentenceTransformer module."""
import functools
import sys


def prepare_jina(model_name, revision):
    from huggingface_hub import snapshot_download
    # The historical AutoModel implementation ignores revision for base weights
    # and adapters. A local snapshot pins every nested loader to one checkpoint.
    local_path=snapshot_download(model_name, revision=revision,
        allow_patterns=['*.json','*.py','*.safetensors','adapters/*',
                        '1_Pooling/*','2_Normalize/*','tokenizer*','*.model','*.txt'])
    from transformers.dynamic_module_utils import get_class_from_dynamic_module
    cls=get_class_from_dynamic_module('custom_st.Transformer',model_name,revision=revision)
    original=cls.__init__
    @functools.wraps(original)
    def init(self,*args,**kwargs):
        # ST 6.3 puts cache_dir in each nested kwargs dictionary. The old module
        # also supplies it explicitly, which raises before any model is loaded.
        for key in ['config_args','model_args','tokenizer_args']:
            nested=dict(kwargs.get(key) or {})
            nested.pop('cache_dir',None)
            nested['revision']=revision
            nested['code_revision']=revision
            nested['trust_remote_code']=True
            kwargs[key]=nested
        if args:
            args=(local_path,)+args[1:]
        else:
            kwargs['model_name_or_path']=local_path
        return original(self,*args,**kwargs)
    cls.__init__=init
    module=sys.modules[cls.__module__]
    original_tokenizer=module.AutoTokenizer
    class PinnedTokenizer:
        @staticmethod
        def from_pretrained(name,*args,**kwargs):
            kwargs['revision']=revision
            kwargs['code_revision']=revision
            return original_tokenizer.from_pretrained(name,*args,**kwargs)
    # The original module ignores tokenizer_args; keep its tokenizer pinned too.
    module.AutoTokenizer=PinnedTokenizer

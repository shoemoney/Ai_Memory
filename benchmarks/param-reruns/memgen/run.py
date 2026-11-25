"""Released Weaver inference with tied immutable backbone storage, no inactive trigger backbone."""
import argparse, importlib, json, os, sys, time, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, SCRATCH, append, rows, setup, device, start_memory_guard


def load_memgen(checkpoint, where):
    import torch
    from torch import nn
    from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig, PreTrainedModel
    from peft import PeftModel, LoraConfig
    # Avoid importing the training runner and its unused training dependencies.
    package = types.ModuleType('memgen'); package.__path__=[str(SCRATCH/'MemGen'/'memgen')]
    sys.modules['memgen']=package
    from memgen.model.modeling_memgen import MemGenModel, _load_lora_weights
    from memgen.model.configuration_memgen import MemGenConfig
    from memgen.model.weaver import MemGenWeaver
    from memgen.utils import CONVERSATION_TEMPLATE
    config=MemGenConfig.from_pretrained(checkpoint)
    assert config.trigger_active is False and config.max_inference_aug_num == 0
    dtype=torch.bfloat16
    base=AutoModelForCausalLM.from_pretrained(SCRATCH/'base',torch_dtype=dtype,attn_implementation='sdpa',device_map={'':where}).eval()
    if where=='cpu' and dtype==torch.bfloat16:
        # Anonymous copies avoid repeatedly reclaiming file-backed checkpoint pages under pressure.
        # Values and dtype are unchanged; share this storage with the Weaver below.
        for parameter in base.parameters(): parameter.data=parameter.data.clone()
    # Two model objects preserve adapter routing. Only immutable base tensor storage is shared.
    with torch.device('meta'):
        woven=AutoModelForCausalLM.from_config(base.config,attn_implementation='sdpa')
    woven.load_state_dict(base.state_dict(),assign=True)
    for name, buf in base.named_buffers():
        parent, attr=name.rsplit('.',1)
        setattr(woven.get_submodule(parent),attr,buf)
    if hasattr(woven.model.rotary_emb,'original_inv_freq'):
        woven.model.rotary_emb.original_inv_freq=base.model.rotary_emb.original_inv_freq
    woven=PeftModel(woven,LoraConfig(**config.weaver_lora_config),adapter_name='weaver')
    model=MemGenModel.__new__(MemGenModel)
    PreTrainedModel.__init__(model,config)
    model.reasoner=base; model.weaver=MemGenWeaver(woven,config.prompt_latents_len,config.inference_latents_len)
    model.tokenizer=AutoTokenizer.from_pretrained(SCRATCH/'base')
    model.tokenizer.chat_template=CONVERSATION_TEMPLATE
    model.delimiters=[',','.','\n']; model.state=None
    hidden=base.config.hidden_size
    model.reasoner_to_weaver=nn.Linear(hidden,hidden,device=where,dtype=dtype)
    model.weaver_to_reasoner=nn.Linear(hidden,hidden,device=where,dtype=dtype)
    # Exactly the upstream inactive Trigger's constant logits, without its never-read 1.5B weights.
    class InactiveTrigger(nn.Module):
        def forward(self,input_ids,**kwargs):
            logits=torch.zeros((*input_ids.shape,2),device=input_ids.device)
            logits[...,1]=1
            return logits
    model.trigger=InactiveTrigger()
    state=torch.load(checkpoint/'projs.bin',map_location='cpu',weights_only=True)
    for key in ['reasoner_to_weaver','weaver_to_reasoner']: getattr(model,key).load_state_dict(state[key])
    state=torch.load(checkpoint/'weaver.bin',map_location='cpu',weights_only=True)
    for key in ['prompt_query_latents','inference_query_latents','prompt_latent_scale','inference_latent_scale']:
        getattr(model.weaver,key).data.copy_(state[key])
    for key in ['prompt_latent_ln','inference_latent_ln']: getattr(model.weaver,key).load_state_dict(state[key])
    _load_lora_weights(woven,str(checkpoint/'weaver'/'weaver'),'weaver')
    # Match the authors' evaluation runner, which casts every component to bfloat16.
    for name,parameter in woven.named_parameters():
        if 'lora_' in name: parameter.data=parameter.data.to(device=where,dtype=dtype)
    from safetensors.torch import load_file
    released=load_file(str(checkpoint/'weaver'/'weaver'/'adapter_model.safetensors'))
    live={name.replace('.weaver.','.'):param for name,param in woven.named_parameters() if 'lora_' in name}
    matched=set()
    for key,tensor in released.items():
        choices=[key,key.replace('base_model.model.model.','base_model.model.',1)]
        target=next((name for name in choices if name in live),None)
        assert target is not None,key
        assert torch.equal(live[target].detach().cpu(),tensor.to(dtype=dtype)),key
        matched.add(target)
    assert matched==set(live),'Incomplete released LoRA tensor coverage'
    # Move only small new modules; moving the entire model would copy shared base storage.
    for key in ['prompt_query_latents','inference_query_latents','prompt_latent_scale','inference_latent_scale']:
        getattr(model.weaver,key).data=getattr(model.weaver,key).data.to(device=where,dtype=dtype)
    model.weaver.prompt_latent_ln.to(device=where,dtype=dtype)
    model.weaver.inference_latent_ln.to(device=where,dtype=dtype)
    # LoRA parameters were initialized on the backbone device by PEFT.
    for p in model.parameters(): p.requires_grad_(False)
    model.eval()
    base_params=base.state_dict(); weaver_params=dict(woven.get_base_model().named_parameters())
    # PEFT adds '.base_layer' to linear module names. All shared base parameters must match by storage.
    checks=[]
    for name,p in weaver_params.items():
        if 'lora_' in name: continue
        key=name.replace('.base_layer','')
        assert p.data_ptr()==base_params[key].data_ptr(),key
        checks.append(key)
    append(ROOT/'results'/'loading-proof.jsonl',{'checkpoint':str(checkpoint.relative_to(SCRATCH)),'base_storage_checks':len(checks),'inactive_trigger':True,'device':where,'dtype':str(dtype),'attention':'sdpa','cpu_storage':'anonymous' if where=='cpu' else 'device','base_parameter_bytes':sum(p.numel()*p.element_size() for p in base.parameters()),'lora_dtypes':sorted({str(p.dtype) for n,p in woven.named_parameters() if 'lora_' in n}),'released_lora_tensors_verified':len(matched)})
    return model


def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',choices=['gsm8k','triviaqa'],required=True)
    p.add_argument('--device',default='cpu'); p.add_argument('--limit',type=int,default=150)
    p.add_argument('--max-tokens',type=int,default=1024); p.add_argument('--smoke',action='store_true')
    p.add_argument('--batch-size',type=int,default=4)
    a=p.parse_args()
    if a.batch_size<1: raise ValueError('Batch size must be positive')
    setup(); where=device(a.device); start_memory_guard(where)
    import torch
    from transformers import GenerationConfig
    suffix='gsm8k/weaver-grpo/pn=1_pl=8_in=0_il=8' if a.dataset=='gsm8k' else 'triviaqa/weaver-sft/pn=8_pl=8_in=0_il=8/model'
    model=load_memgen(SCRATCH/'checkpoints'/'Qwen2.5-1.5B-Instruct'/suffix,where)
    tokenizer=model.tokenizer; tokenizer.padding_side='left'
    path=ROOT/'results'/('smoke-batch-'+str(a.batch_size))/(a.dataset+'.jsonl') if a.smoke else ROOT/'results'/(a.dataset+'.jsonl')
    old_rows=rows(path)
    if any(r['max_new_tokens']!=a.max_tokens for r in old_rows): raise ValueError('Resume token cap mismatch')
    if any(r['device']!=where for r in old_rows): raise ValueError('Resume backend mismatch; retain old cell separately before starting a new backend')
    done={(r['source_index'],r['system']) for r in old_rows}
    sys.path.insert(0,str(SCRATCH/'MemGen'))
    from data.utils.math_utils import compute_score
    data=rows(SCRATCH/(a.dataset+'.jsonl'))[:a.limit]
    for batch_start in range(0,len(data),a.batch_size):
        batch=data[batch_start:batch_start+a.batch_size]
        for system in ['base','memgen']:
            if all((r['source_index'],system) in done for r in batch): continue
            # Preserve the original batch shape after a partial write; persist only missing rows.
            active=batch
            conversations=[]; answers=[]; all_aliases=[]
            for row in active:
                if a.dataset=='gsm8k':
                    prompt=r'Solve the math problem with proper reasoning, and make sure to put the FINAL ANSWER inside \boxed{}.'+'Question: '+row['question'].strip()+'\n'
                    messages=[{'role':'user','content':prompt}]
                    answer=row['answer'].split('####')[-1].strip(); aliases=[answer]
                else:
                    # Closed-book diagnostic, with no silent failed search observations.
                    messages=[{'role':'system','content':'Answer the given question. Conduct reasoning inside <think> and </think>, then provide your final answer inside <answer> and </answer>. No search engine is available.'},{'role':'user','content':row['question']}]
                    aliases=row['answer']['normalized_aliases']; answer=row['answer']['value']
                conversations.append(messages); answers.append(answer); all_aliases.append(aliases)
            encoded=tokenizer.apply_chat_template(conversations,add_generation_prompt=True,padding=True,return_dict=True,return_tensors='pt').to(where)
            tokens=encoded['input_ids']; mask=encoded['attention_mask']
            start=time.monotonic()
            config=GenerationConfig(do_sample=False,temperature=None,top_k=None,top_p=None,max_new_tokens=a.max_tokens,pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id,repetition_penalty=1.0)
            with torch.inference_mode():
                if system=='base':
                    old=model.reasoner.generation_config; model.reasoner.generation_config=GenerationConfig()
                    try: result=model.reasoner.generate(input_ids=tokens,attention_mask=mask,generation_config=config)[:,tokens.shape[1]:]
                    finally: model.reasoner.generation_config=old
                else:
                    config.weaver_do_sample=False; config.trigger_do_sample=False
                    result=model.generate(input_ids=tokens,attention_mask=mask,generation_config=config)[:,tokens.shape[1]:]
            elapsed=time.monotonic()-start
            for row,answer,aliases,generated in zip(active,answers,all_aliases,result):
                if (row['source_index'],system) in done: continue
                ids=generated.tolist()
                if tokenizer.eos_token_id in ids: ids=ids[:ids.index(tokenizer.eos_token_id)+1]
                output=tokenizer.decode(ids,skip_special_tokens=True)
                if a.dataset=='gsm8k': score=compute_score(output,'\\boxed{'+answer+'}')
                else:
                    import re
                    match=re.search(r'<answer>(.*?)</answer>',output,re.S)
                    score=float(bool(match) and any(alias.lower() in match.group(1).strip().lower() for alias in aliases))
                record={'source_index':row['source_index'],'system':system,'answer':answer,'output':output,'score':score,'seconds':elapsed/len(active),'batch_seconds':elapsed,'batch_size':len(active),'timing':'batch-runtime-amortized-per-item','generated_tokens':len(ids),'limit_reached':len(ids)>=a.max_tokens,'device':where,'dtype':str(model.reasoner.dtype),'max_new_tokens':a.max_tokens,'threads':torch.get_num_threads(),'protocol':'official-singleturn' if a.dataset=='gsm8k' else 'closed-book-diagnostic'}
                append(path,record); done.add((row['source_index'],system))
                print(json.dumps({k:record[k] for k in ['source_index','system','score','seconds','generated_tokens','batch_size']}),flush=True)

if __name__=='__main__': main()

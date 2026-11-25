"""Reduced self-study and trainable KV context distillation, with paired LongHealth MC answers."""
import argparse, json, re, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import ROOT, SCRATCH, append, rows, setup, device, start_memory_guard, save_torch


def main():
    a=argparse.ArgumentParser(); a.add_argument('--device',default='cpu'); a.add_argument('--smoke',action='store_true'); args=a.parse_args()
    import torch
    from torch import nn
    from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache, GenerationConfig
    setup(); where=device(args.device); start_memory_guard(where)
    model=AutoModelForCausalLM.from_pretrained(SCRATCH/'base',torch_dtype=torch.bfloat16,attn_implementation='sdpa',device_map={'':where}).eval()
    for p in model.parameters():
        p.requires_grad_(False)
        if where=='cpu': p.data=p.data.clone()
    tokenizer=AutoTokenizer.from_pretrained(SCRATCH/'base')
    patient=json.loads((SCRATCH/'longhealth.json').read_text())['patient_01']
    def anonymize(text):
        for word in sorted(patient['name'].split(),key=len,reverse=True):
            if len(word)>2: text=text.replace(word,'[patient]')
        return text
    documents='\n\n'.join(anonymize(v) for v in patient['texts'].values())
    doc_ids=tokenizer.encode(documents,add_special_tokens=False)
    full_document_tokens=len(doc_ids)
    if args.smoke:
        doc_ids=doc_ids[:768]; documents=tokenizer.decode(doc_ids)
    scope='cartridges-smoke' if args.smoke else 'cartridges'
    resultdir=ROOT/'results'/scope; resultdir.mkdir(parents=True,exist_ok=True)
    def encode(text):
        return tokenizer.apply_chat_template([{'role':'user','content':text}],add_generation_prompt=True,return_tensors='pt').to(where)
    prefix=64
    work=SCRATCH/scope; work.mkdir(exist_ok=True)
    synthpath=resultdir/'synthetic.jsonl'
    # Fixed document chunks, never evaluation questions or gold answers.
    chunks=[doc_ids[i:i+768] for i in range(0,len(doc_ids),768)]
    n=1 if args.smoke else 32
    for i in range(len(rows(synthpath)),n):
        chunk=tokenizer.decode(chunks[i%len(chunks)])
        # Local model authors both turns of a grounded synthetic conversation.
        focus=['a diagnosis','a medication','a dated event','a test or procedure'][i//len(chunks)%4]
        prompt='Focus on '+focus+'. Read this medical document excerpt. Write one specific factual question and its answer using only the excerpt. Do not use Markdown. Format exactly: Question: ...\nAnswer: ...\n\n'+chunk
        token=encode(prompt); start=time.monotonic()
        with torch.inference_mode():
            out=model.generate(token,generation_config=GenerationConfig(do_sample=False,max_new_tokens=64 if args.smoke else 160,pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id,repetition_penalty=1.0))
        text=anonymize(tokenizer.decode(out[0,token.shape[1]:],skip_special_tokens=True))
        match=re.search(r'Question:\s*(.*?)\s*Answer:\s*(.*)',text,re.S)
        if not match:
            append(resultdir/'synthesis-failures.jsonl',{'index':i,'output':text})
            raise RuntimeError('Local synthesis did not produce the declared Q/A format')
        append(synthpath,{'index':i,'chunk':i%len(chunks),'question':match.group(1).strip(),'answer':match.group(2).strip(),'output':text,'seconds':time.monotonic()-start})
        print('synth',i,flush=True)
    # Cache sparse teacher distributions from document-conditioned conversations.
    for row in rows(synthpath):
        dest=work/f"teacher-{row['index']}.pt"
        if dest.exists(): continue
        question=row['question']; answer_ids=tokenizer.encode(row['answer'],add_special_tokens=False)[:96]+[tokenizer.eos_token_id]
        context=tokenizer.decode(chunks[row['chunk']])
        teacher_prompt=encode('Document:\n'+context+'\n\n'+question)
        student_prompt=encode(question)
        answer=torch.tensor([answer_ids],device=where)
        inputs=torch.cat([teacher_prompt,answer[:,:-1]],dim=1)
        with torch.inference_mode():
            logits=model(inputs,logits_to_keep=len(answer_ids),use_cache=False).logits.float()
            values,indices=logits.topk(20,dim=-1)
            target=values.softmax(-1)
        save_torch({'input_ids':torch.cat([student_prompt,answer[:,:-1]],dim=1).cpu(),'top_ids':indices.cpu(),'target':target.cpu(),'answer_tokens':len(answer_ids)},dest)
        print('teacher',row['index'],flush=True)
    # Initialize a 64-token cache from fixed neutral text, then optimize only its K and V.
    init=tokenizer.encode('This is a document memory. '*100,return_tensors='pt')[:,:prefix].to(where)
    with torch.no_grad(): initial=model(init,use_cache=True).past_key_values.to_legacy_cache()
    kv=nn.ParameterList([nn.Parameter(x.detach().clone().float()) for pair in initial for x in pair])
    optimizer=torch.optim.AdamW(kv,lr=0.02,weight_decay=0)
    def cache():
        return DynamicCache.from_legacy_cache(tuple((kv[2*i].to(torch.bfloat16),kv[2*i+1].to(torch.bfloat16)) for i in range(len(initial))))
    ckpt=work/'trained.pt'; startstep=0
    if ckpt.exists():
        state=torch.load(ckpt,map_location=where,weights_only=True); kv.load_state_dict(state['kv']); optimizer.load_state_dict(state['optimizer']); startstep=state['step']
        last=state.get('last_training_record')
        if last is not None and last['step'] not in {r['step'] for r in rows(resultdir/'training.jsonl')}: append(resultdir/'training.jsonl',last)
    steps=1 if args.smoke else n*2
    for step in range(startstep,steps):
        teacher=torch.load(work/f'teacher-{step%n}.pt',weights_only=True,map_location=where)
        optimizer.zero_grad(set_to_none=True); start=time.monotonic()
        logits=model(teacher['input_ids'],past_key_values=cache(),logits_to_keep=teacher['answer_tokens'],use_cache=True).logits.float()
        logp=logits.log_softmax(-1).gather(-1,teacher['top_ids'])
        target=teacher['target']; loss=(target*(target.clamp_min(1e-30).log()-logp)).sum(-1).mean()
        loss.backward(); grad=float(torch.nn.utils.clip_grad_norm_(kv,1.0)); optimizer.step()
        assert grad>0 and torch.isfinite(loss)
        training_row={'step':step,'loss':float(loss.detach()),'gradient_norm':grad,'seconds':time.monotonic()-start}
        save_torch({'kv':kv.state_dict(),'optimizer':optimizer.state_dict(),'step':step+1,'last_training_record':training_row},ckpt)
        append(resultdir/'training.jsonl',training_row)
        print('train',step,float(loss.detach()),flush=True)
    change=sum(float((kv[2*i+j].detach()-initial[i][j].float()).square().sum()) for i in range(len(initial)) for j in range(2))**0.5
    assert change>0 and all(p.grad is None and not p.requires_grad for p in model.parameters())
    (resultdir/'mechanism.json').write_text(json.dumps({'cache_tokens':prefix,'training_steps':steps,'synthetic_conversations':n,'cache_change_l2':change,'base_parameters_frozen':True,'base_parameter_gradients_absent':True,'source_patient':'patient_01','document_count':len(patient['texts']),'document_tokens':len(doc_ids),'full_document_tokens':full_document_tokens,'smoke_excerpt':args.smoke},indent=2)+'\n')
    # Identical questions, deterministic constrained single-token multiple choice, no LLM judge.
    # Distinct tokenization for each letter is checked rather than assumed.
    letters=['A','B','C','D','E']
    choice_ids=[tokenizer.encode(x,add_special_tokens=False) for x in letters]
    assert all(len(x)==1 for x in choice_ids)
    choice_ids=torch.tensor([x[0] for x in choice_ids],device=where)
    answerpath=resultdir/'answers.jsonl'; done={(r['id'],r['system']) for r in rows(answerpath)}
    questions=patient['questions'][:1 if args.smoke else 20]
    kv_bytes=sum(x.numel()*2 for pair in initial for x in pair)
    bytes_per_token=kv_bytes//prefix
    context_prefix=None; context_prefix_ids=None
    for q in questions:
        qid='patient_01_'+str(q['No'])
        options=[q['answer_'+x.lower()] for x in letters]
        question=anonymize(q['question'])+'\n'+'\n'.join(f'{l}. {anonymize(opt)}' for l,opt in zip(letters,options))+'\nReturn only the letter A, B, C, D, or E.'
        correct=next((l for l,opt in zip(letters,options) if opt.strip().lower()==q['correct'].strip().lower()),None)
        assert correct is not None
        for system in ['context','cartridge']:
            if (qid,system) in done: continue
            prompt=('Documents:\n'+documents+'\n\n'+question) if system=='context' else question
            inputs=encode(prompt); start=time.monotonic()
            with torch.no_grad():
                if where=='cuda': torch.cuda.reset_peak_memory_stats()
                state=cache() if system=='cartridge' else None
                offset_start=0
                if system=='context':
                    # Reuse only a verified common prefix. Per-question bytes still include all documents.
                    if context_prefix is None:
                        count=min(len(doc_ids),inputs.shape[1]-1)
                        context_prefix_ids=inputs[:,:count].clone()
                        for offset in range(0,count,256):
                            output=model(inputs[:,offset:min(offset+256,count)],past_key_values=state,use_cache=True,logits_to_keep=1)
                            state=output.past_key_values
                            if offset%2048==0: print('context-prefill',offset,min(offset+256,count),count,flush=True)
                        context_prefix=tuple((k.detach(),v.detach()) for k,v in state.to_legacy_cache())
                        print('context-prefix-ready',count,flush=True)
                    offset_start=context_prefix_ids.shape[1]
                    assert torch.equal(inputs[:,:offset_start],context_prefix_ids)
                    state=DynamicCache.from_legacy_cache(tuple((k.clone(),v.clone()) for k,v in context_prefix))
                # Full context, bounded temporary attention memory; no document truncation.
                for offset in range(offset_start,inputs.shape[1],256):
                    output=model(inputs[:,offset:offset+256],past_key_values=state,use_cache=True,logits_to_keep=1)
                    state=output.past_key_values
                logits=output.logits[0,-1,choice_ids]; answer=letters[int(logits.argmax())]
                actual=sum(x.numel()*x.element_size() for pair in output.past_key_values.to_legacy_cache() for x in pair)
                peak=torch.cuda.max_memory_allocated() if where=='cuda' else None
                expected_tokens=inputs.shape[1]+(prefix if system=='cartridge' else 0)
                assert actual==expected_tokens*bytes_per_token
            append(answerpath,{'id':qid,'system':system,'answer':answer,'gold':correct,'score':float(answer==correct),'seconds':time.monotonic()-start,'prompt_tokens':inputs.shape[1],'cache_bytes':actual,'peak_cuda_allocated_bytes':peak,'peak_includes_retained_context_prefix':True,'document_tokens':len(doc_ids),'cartridge_tokens':prefix,'persistent_cartridge_bytes':kv_bytes,'bytes_per_kv_token':bytes_per_token,'device':where,'prefill_chunk_tokens':256,'scoring':'constrained-next-token-A-E'})
            del output
            print('eval',qid,system,answer,correct,flush=True)
    print('finished',scope,flush=True)

if __name__=='__main__': main()

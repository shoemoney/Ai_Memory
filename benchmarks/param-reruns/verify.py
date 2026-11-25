"""Audit saved answers against fetched primary data before publishing a summary."""
import hashlib, importlib.util, json, math
from common import ROOT, SCRATCH, rows


def main():
    manifest=json.loads((ROOT/'results'/'sources.json').read_text())
    scorer=SCRATCH/'MemGen'/'data'/'utils'/'math_utils.py'
    spec=importlib.util.spec_from_file_location('official_math_scorer',scorer)
    math_scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(math_scorer)
    checked={}
    for dataset in ['gsm8k','triviaqa']:
        source={r['source_index']:r for r in rows(SCRATCH/(dataset+'.jsonl'))}
        expected=set(manifest['datasets'][dataset]['indices'])
        assert len(expected)==150 and set(source)==expected
        data=rows(ROOT/'results'/(dataset+'.jsonl'))
        cells={name:{} for name in ['base','memgen']}
        for r in data:
            assert r['source_index'] not in cells[r['system']], 'Duplicate raw answer'
            cells[r['system']][r['source_index']]=r
            row=source[r['source_index']]
            if dataset=='gsm8k':
                truth=row['answer'].split('####')[-1].strip()
                score=math_scorer.compute_score(r['output'],'\\boxed{'+truth+'}')
                assert r['answer']==truth
            else:
                import re
                match=re.search(r'<answer>(.*?)</answer>',r['output'],re.S)
                score=float(bool(match) and any(alias.lower() in match.group(1).strip().lower() for alias in row['answer']['normalized_aliases']))
                assert r['answer']==row['answer']['value']
            assert score==r['score'], (dataset,r['source_index'],r['system'])
            assert r['max_new_tokens']==1024 and 0<r['generated_tokens']<=1024
            assert r['seconds']>=0 and r['dtype']=='torch.bfloat16'
        assert all(set(cell)==expected for cell in cells.values())
        assert all(cells['base'][i]['device']==cells['memgen'][i]['device'] for i in expected)
        checked[dataset]={'paired_n':150,'raw_rows':len(data),'primary_labels_match':True,'scores_recomputed':True,'paired_backends_match':True}
    patient=json.loads((SCRATCH/'longhealth.json').read_text())['patient_01']
    questions={'patient_01_'+str(q['No']):q for q in patient['questions']}
    records=rows(ROOT/'results'/'cartridges'/'answers.jsonl')
    config=json.loads((SCRATCH/'base'/'config.json').read_text())
    per_token=2*config['num_hidden_layers']*config['num_key_value_heads']*(config['hidden_size']//config['num_attention_heads'])*2
    cells={name:{} for name in ['context','cartridge']}
    for r in records:
        assert r['id'] not in cells[r['system']]
        cells[r['system']][r['id']]=r
        q=questions[r['id']]
        gold=next(letter for letter in 'ABCDE' if q['answer_'+letter.lower()].strip().lower()==q['correct'].strip().lower())
        assert r['gold']==gold and r['score']==float(r['answer']==gold)
        n=r['prompt_tokens']+(64 if r['system']=='cartridge' else 0)
        assert r['cache_bytes']==n*per_token and r['bytes_per_kv_token']==per_token
        assert r['persistent_cartridge_bytes']==64*per_token and r['document_tokens']==12234
    assert all(set(cell)==set(questions) for cell in cells.values())
    assert all(cells['context'][i]['device']==cells['cartridge'][i]['device'] for i in questions)
    training=rows(ROOT/'results'/'cartridges'/'training.jsonl')
    assert len(training)==64 and {r['step'] for r in training}==set(range(64))
    assert all(math.isfinite(r['loss']) and math.isfinite(r['gradient_norm']) and r['gradient_norm']>0 for r in training)
    synthetic_path=ROOT/'results'/'cartridges'/'synthetic.jsonl'
    if not synthetic_path.exists():synthetic_path=ROOT/'results'/'cartridges'/'synthetic-index.jsonl'
    synthetic=rows(synthetic_path)
    assert len(synthetic)==32 and {r['index'] for r in synthetic}==set(range(32))
    full_synthetic={r['index']:r for r in rows(SCRATCH/'cartridges'/'synthetic-text.jsonl')}
    synthetic_hashes_verified=False
    if 'output_sha256' in synthetic[0]:
        assert len(full_synthetic)==32
        for row in synthetic:
            for field in ['question','answer','output']:
                assert row[field+'_sha256']==hashlib.sha256(full_synthetic[row['index']][field].encode()).hexdigest()
        synthetic_hashes_verified=True
    mechanism=json.loads((ROOT/'results'/'cartridges'/'mechanism.json').read_text())
    assert mechanism['base_parameters_frozen'] and mechanism['base_parameter_gradients_absent'] and mechanism['cache_change_l2']>0
    checked['cartridges']={'paired_n':len(questions),'raw_rows':len(records),'primary_labels_match':True,'scores_recomputed':True,'kv_bytes_checked_against_model_config':True,'training_steps':64,'synthetic_conversations':32,'synthetic_text_hashes_verified':synthetic_hashes_verified}
    checked['official_math_scorer_sha256']=hashlib.sha256(scorer.read_bytes()).hexdigest()
    checked['status']='passed'
    (ROOT/'results'/'final-verification.json').write_text(json.dumps(checked,indent=2)+'\n')
    print(json.dumps(checked,indent=2))

if __name__=='__main__': main()

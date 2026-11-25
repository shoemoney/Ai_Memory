"""Check complete paired cells and recompute every deterministic score."""
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('game24',ROOT/'game24/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def verify_game24():
    rows=[json.loads(x) for x in (ROOT/'game24/results.jsonl').read_text().splitlines()];data=m.dataset()
    keys=[(r['id'],r['arm']) for r in rows]
    assert len(keys)==len(set(keys))==200
    assert set(keys)=={(i,a) for i in range(100) for a in ('direct','dc_cumulative')}
    for r in rows:
        assert r['correct']==m.score(data[r['id']]['input'],r['answer'])
        assert r['seconds']>0
    print('Game24: 200 unique cells, same 100 puzzles, scores recomputed')
if __name__=='__main__':verify_game24()

def verify_dmr():
    import collections,re
    p=ROOT/'dmr';ids=json.loads((p/'cohort.json').read_text())['ids']
    assert len(ids)==len(set(ids))==150
    rows=[json.loads(x) for x in (p/'results.jsonl').read_text().splitlines()]
    keys={(r['id'],r['arm']) for r in rows}
    assert len(rows)==len(keys)==300
    assert keys=={(i,a) for i in ids for a in ('full_context','dense_top5')}
    for r in rows:
        assert type(r['correct'])==bool
        parsed=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',r['judge_response'].strip()))
        assert (parsed if type(parsed)==bool else parsed['is_correct'])==r['correct']
        assert r['answer']==json.loads((p/'answers'/f"{r['id']}-{r['arm']}.json").read_text())['answer']
        assert r['judge_model']=='Qwen2.5-7B-Instruct Q4_K_M'
        assert r['usage']['prompt_tokens']+r['usage']['completion_tokens']<32768
    audit=[json.loads(x) for x in (p/'manual-audit.jsonl').read_text().splitlines()]
    planned={(r['id'],r['arm']) for r in json.loads((p/'audit-plan.json').read_text())['cells']}
    assert {(r['id'],r['arm']) for r in audit}==planned and len(audit)==40
    lookup={(r['id'],r['arm']):r for r in rows}
    mismatches=[]
    for r in audit:
        model=lookup[r['id'],r['arm']]['correct']
        if model!=r['tester_correct']:mismatches.append({**r,'judge_correct':model})
    summary={'n':40,'agreement':40-len(mismatches),'agreement_rate':(40-len(mismatches))/40,'exact_95':m.interval(40-len(mismatches),40),'mismatches':mismatches,'tester':'implementation agent; not an independent human','policy':'headline labels remain local judge labels; tester audit is a separate quality check'}
    (p/'audit-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('DMR: 300 unique cells, same 150 source items, saved answers and judge labels verified; audit agreement',40-len(mismatches),'/40')

def verify_refusal():
    p=ROOT/'refusal';rows=[json.loads(x) for x in (p/'results.jsonl').read_text().splitlines()]
    hand=[json.loads(x) for x in (p/'hand-labels.jsonl').read_text().splitlines()]
    want={(i,a) for i in range(100) for a in ('heretic','stock')}
    assert len(rows)==len(hand)==200 and {(r['id'],r['arm']) for r in rows}=={(r['id'],r['arm']) for r in hand}==want
    assert all(set(r)<= {'id','arm','prompt_sha256','keyword_match','markers','empty','finish_reason','completion_tokens','seconds'} for r in rows)
    assert all(h['label'] in ('refused','answered') for h in hand)
    print('Refusal: 200 unique cells, 100 prompts x 2 arms, labels complete, no generated text stored')
if __name__=='__main__' and (ROOT/'dmr/summary.json').exists():verify_dmr()
if __name__=='__main__' and (ROOT/'refusal/summary.json').exists():verify_refusal()

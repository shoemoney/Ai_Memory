import json
from collections import Counter
from pathlib import Path
import numpy as np
import pytest
from controller import policy, summarize, frontier
from flips import distribution, stats, kl, answer_text
from prompts import build
from probes import analyze, auc


def test_frozen_prompts():
    path=Path(__file__).parents[1]/'prompts.jsonl'
    rows=[json.loads(x) for x in path.read_text().splitlines()]
    assert len(rows)==400
    assert Counter(r['stratum'] for r in rows)==dict.fromkeys(['recall','two_hop','memory','code'],100)
    assert len({r['id'] for r in rows})==400
    assert all('archive_sha256' in r for r in rows if r['stratum']=='memory')


def test_distribution_statistics():
    p=distribution([0,0]); h,margin=stats(p)
    assert h==pytest.approx(np.log(2)) and margin==0
    assert kl(p,p)==0
    assert kl(p,distribution([2,0]))>0


def synthetic():
    rng=np.random.default_rng(1701)
    n=240
    signal=rng.normal(size=n)
    rows=[dict(prompt_id=f'p{i}',family=f'p{i}',position=0,stratum=f's{i%4}',
               token_flip=bool(signal[i]>0),answer_flip=bool(signal[i]>0)) for i in range(n)]
    matrices=dict(residual=np.column_stack([signal,rng.normal(size=n)]),message=signal[:,None],
                  gate_norm=np.abs(signal[:,None]),entropy=rng.normal(size=(n,1)),margin=rng.normal(size=(n,1)))
    return rows,matrices


def test_probe_recovers_planted_signal():
    rows,matrices=synthetic()
    report,pred,_=analyze(rows,matrices,boot=30)
    for mode in ('oof','heldout_stratum'):
        for stratum in report[mode].values():
            assert stratum['residual']['auc']>.95
            assert stratum['residual']['beats_entropy']
    # All rows scored once; a random uncertainty baseline is weaker than the signal.
    assert len(pred['oof']['residual'])==len(rows)
    assert auc(np.zeros(10),np.zeros(10)) is None


def test_policy_costs_and_agreement():
    rows=[dict(argmax=[1,2,2],gate_norm=[.01,.7],kl=[.001,.1]),
          dict(argmax=[3,4,3],gate_norm=[.9,.3],kl=[.1,.001])]
    g=policy(rows,'gate',.2)
    assert g.tolist()==[2,3]  # gate cannot save pass2
    assert summarize(rows,g)==dict(n=2,average_passes=2.5,agreement=1.)
    assert policy(rows,'kl',.05).tolist()==[2,3]
    q=policy(rows,'probe',.2,np.array([.1,.9]))
    assert q.tolist()==[1,3]
    assert summarize(rows,q)['agreement']==.5
    assert policy(rows,'gate',0).tolist()==[3,3]
    assert policy(rows,'kl',float('inf')).tolist()==[2,2]
    with pytest.raises(ValueError):
        policy(rows,'probe',.5,[float('nan')]*2)
    assert len(frontier([dict(average_passes=3,agreement=1),dict(average_passes=2,agreement=1)]))==1


def test_final_channel_and_censored_answers():
    assert answer_text('<|message_model|><|content_thinking|>hmm<|end_message|><|message_model|><|content_text|>Paris<|end_message|>') == 'Paris'
    assert answer_text('<|message_model|><|content_thinking|>hmm') is None
    rows, matrices = synthetic()
    for r in rows:
        r['answer_flip'] = None
    report, scores, indices = analyze(rows, matrices, 'answer_flip', boot=3)
    assert report['status'] == 'insufficient_uncensored_prompts'
    assert len(indices) == 0


def test_prompt_build_deterministic(tmp_path):
    for i in range(100):
        (tmp_path/f'{i:03d}--bm25-standard.json').write_text(json.dumps(dict(question_id=str(i),status='scored',reference='fixture',answer={'prompt':f'Public synthetic fixture {i}'})))
    assert build(tmp_path)==build(tmp_path)


def test_sketch_is_fixed_and_label_free():
    from probes import sketch
    x=np.arange(500,dtype=float)
    np.testing.assert_equal(sketch(x),sketch(x))
    assert sketch(x).shape==(256,)
    np.testing.assert_allclose(sketch(x*2),2*sketch(x))

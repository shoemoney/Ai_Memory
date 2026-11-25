"""Real tiny random inkling2_loop on MLX CPU; no weights/network needed."""
import copy
import numpy as np
import pytest
mx=pytest.importorskip('mlx.core')
from mlx.utils import tree_flatten, tree_unflatten
from mlx_lm.models.inkling2 import Model, ModelArgs
from capture import capture, flatten, pass_count, text_model
from flips import forward, collect_prompt

CONFIG=dict(model_type='inkling2_loop',text_config=dict(
    hidden_size=16,num_hidden_layers=8,vocab_size=32,unpadded_vocab_size=32,
    num_attention_heads=2,num_key_value_heads=1,head_dim=8,
    swa_num_attention_heads=2,swa_num_key_value_heads=1,swa_head_dim=8,
    sliding_window_size=8,local_layer_ids=[0,1,2,3,4,6],d_rel=4,rel_extent=8,
    log_scaling_n_floor=4,log_scaling_alpha=.1,rms_norm_eps=1e-6,
    qk_l2_clip_threshold=3.,rel_l2_clip_threshold=2.,sconv_kernel_size=4,
    n_layers_per_attn_res_block=3,n_routed_experts=2,num_experts_per_tok=1,
    intermediate_size=16,mlp_gate_softcap=4.,mlp_up_softcap=25.,route_scale=2.,
    final_logit_softcapping=30.,loop_config=dict(core_start=3,core_end=6,num_passes=3,gate_rank=4,is_varloop=True)))


def model():
    mx.random.seed(1701)
    m=Model(ModelArgs.from_dict(copy.deepcopy(CONFIG)))
    weights=[]
    for k,v in tree_flatten(m.parameters()):
        if k.endswith(('norm.weight','l2_clip.scale','lambda_1','lambda_2')):
            v=1+.1*mx.random.normal(v.shape)
        else:
            v=mx.random.normal(v.shape)*(v.shape[-1] if v.ndim>1 else 16)**-.5
        weights.append((k,v))
    m.update(tree_unflatten(weights));mx.eval(m.parameters())
    return m


def test_readonly_capture_and_pass_restoration():
    m=model()
    baseline=forward(m,[1,2,3],3)
    p,saved=forward(m,[1,2,3],3,[3,5])
    np.testing.assert_allclose(p,baseline,atol=1e-6)
    assert saved['residual'].keys()=={3,5}
    assert len(saved['message'])==6 and len(saved['gate'])==24
    assert flatten(saved['message'],2).shape==(3*4*16,)
    assert np.max(np.abs(flatten(saved['gate'],2)))<=1
    with pass_count(m,1):
        with capture(m,[3,5]) as one:
            mx.eval(m(mx.array([[1,2,3]])))
    for layer in (3,5):
        np.testing.assert_allclose(one['residual'][layer],saved['residual'][layer],atol=1e-6)
    from mlx_lm.models.inkling2.layers import MessageGate
    original=MessageGate.__call__
    with pytest.raises(RuntimeError):
        with pass_count(m,1),capture(m,[3]):
            raise RuntimeError('intentional')
    assert MessageGate.__call__ is original
    assert text_model(m).args.loop_config['num_passes']==3


class Tokenizer:
    eos_token_ids=[]
    eos_token_id=None
    def encode(self,text): return [1,2,3]
    def decode(self,tokens): return ','.join(map(str,tokens))
    def apply_chat_template(self,*args,**kwargs): return [1,2,3]


def test_teacher_forced_token_collection():
    m=model()
    answer,records,arrays=collect_prompt(m,Tokenizer(),dict(id='tiny',stratum='code',text='test'),2,[3,5])
    assert len(records)==len(arrays)==2
    assert [r['token'] for r in records]==answer['generated'][3]
    assert all(r['argmax'][2]==r['token'] for r in records)
    assert all(np.isfinite(a['residual']).all() for a in arrays)
    assert all(len(r['gate_norm'])==2 and len(r['kl'])==2 for r in records)

import numpy as np

from capture import to_numpy


def test_to_numpy_handles_bfloat16():
    import mlx.core as mx
    x = mx.array([1.5, -2.0, 3.25], dtype=mx.bfloat16)
    out = to_numpy(x)
    assert out.dtype == np.float32 and out.tolist() == [1.5, -2.0, 3.25]


def test_select_rows_stratified_round_robin_and_deterministic():
    import flips
    rows = [dict(id=f'{s}-{i:03d}', stratum=s) for s in flips.STRATA_ORDER for i in range(100)]
    a = flips.select_rows(rows, 160)
    assert a == flips.select_rows(rows, 160) and len(a) == 160 and len({r['id'] for r in a}) == 160
    assert [r['stratum'] for r in a[:8]] == list(flips.STRATA_ORDER) * 2
    assert {s: sum(r['stratum'] == s for r in a) for s in flips.STRATA_ORDER} == {s: 40 for s in flips.STRATA_ORDER}


def test_answer_text_with_prefilled_text_message():
    import flips
    gen = '1103<|end_message|><|content_model_end_sampling|>'
    assert flips.answer_text(flips.NO_THINKING_PREFILL + gen) == '1103'
    assert flips.answer_text(gen) is None  # without the prefill the marker-less generation is not a final answer

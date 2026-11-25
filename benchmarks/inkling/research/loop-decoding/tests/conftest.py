import json
from pathlib import Path
import sys
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

@pytest.fixture
def model():
    import mlx.core as mx
    from mlx_lm.models.inkling2.config import ModelArgs
    from mlx_lm.models.inkling2.model import Model
    config = json.loads((HERE.parents[2] / 'direction/tests/tiny_config.json').read_text())
    config['text_config']['loop_config']['is_varloop'] = True
    mx.set_default_device(mx.cpu)
    mx.random.seed(23)
    model = Model(ModelArgs.from_dict(config))
    model.eval()
    return model

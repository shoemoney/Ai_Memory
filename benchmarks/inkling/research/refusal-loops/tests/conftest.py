import json
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
TINY = HERE.parents[2] / "direction/tests/tiny_config.json"


def build(varloop):
    import mlx.core as mx
    from mlx_lm.models.inkling2.config import ModelArgs
    from mlx_lm.models.inkling2.model import Model
    config = json.loads(TINY.read_text())
    config["text_config"]["loop_config"]["is_varloop"] = varloop
    mx.set_default_device(mx.cpu)
    mx.random.seed(23)
    model = Model(ModelArgs.from_dict(config))
    model.eval()
    return model, config


@pytest.fixture
def varloop():
    return build(True)


@pytest.fixture
def fixedloop():
    return build(False)

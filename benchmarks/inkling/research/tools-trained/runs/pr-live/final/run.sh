set -e
cd <scratch>
export PYTHONPATH=<scratch> TINKER_COOKBOOK_RUNS_DIR=<scratch>
<checkout>/.venv/bin/python -m tinker_cookbook.recipes.trained_tools.prepare --output <scratch>/trained_tools/data
<checkout>/.venv/bin/python -m tinker_cookbook.recipes.trained_tools.train data_path=<scratch>/trained_tools/data wandb_name=mini-r32
MP=$(tail -n1 <scratch>/trained_tools/mini-r32/checkpoints.jsonl | <checkout>/.venv/bin/python -c 'import json,sys; print(json.load(sys.stdin)["sampler_path"])')
<checkout>/.venv/bin/python -m tinker_cookbook.recipes.trained_tools.eval data_path=<scratch>/trained_tools/data model_path=$MP
<checkout>/.venv/bin/python -m tinker_cookbook.recipes.trained_tools.eval data_path=<scratch>/trained_tools/data model_path=$MP test_file=tinker_cookbook/recipes/trained_tools/blind_test.jsonl

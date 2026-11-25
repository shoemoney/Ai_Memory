set -e
MP=$(tail -n1 <scratch>/trained_tools/mini-r32/checkpoints.jsonl | <checkout>/.venv/bin/python -c 'import json,sys; print(json.load(sys.stdin)["sampler_path"])')
<checkout>/.venv/bin/python -m tinker_cookbook.recipes.trained_tools.eval data_path=<scratch>/trained_tools/data model_path=$MP log_path=<scratch>/trained_tools/comparison > <scratch>/eval-generated.out 2>&1
<checkout>/.venv/bin/python -m tinker_cookbook.recipes.trained_tools.eval data_path=<scratch>/trained_tools/data model_path=$MP log_path=<scratch>/trained_tools/comparison test_file=tinker_cookbook/recipes/trained_tools/blind_test.jsonl > <scratch>/eval-blind.out 2>&1

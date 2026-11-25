#!/usr/bin/env bash
# One command: bash run.sh   (needs a llama.cpp-style OpenAI-compatible server at $ACE_BASE_URL)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-/var/tmp/membench-delegate-ace}"
VENV="${VENV:-/data/scratch/membench/delegate-ace/venv-ace}"
export ACE_BASE_URL="${ACE_BASE_URL:-http://localhost:39951/v1}"
MODEL="${MODEL:-qwen2.5-7b-q4}"
N_TRAIN="${N_TRAIN:-60}"; N_VAL="${N_VAL:-40}"; EVAL_STEPS="${EVAL_STEPS:-30}"
COMMIT=82709de050e1db6e6ef2f07bcb0393560b94992a
source "$VENV/bin/activate"
mkdir -p "$WORK"
[ -d "$WORK/ace" ] || git clone -q https://github.com/ace-agent/ace "$WORK/ace"
cd "$WORK/ace"
git checkout -q -- . && git checkout -q "$COMMIT" && git apply "$HERE/ace-local.patch"
python "$HERE/make_subsets.py" eval/finance/data "$N_TRAIN" "$N_VAL"
python -m eval.finance.run --task_name formula --mode offline --api_provider local \
  --generator_model "$MODEL" --reflector_model "$MODEL" --curator_model "$MODEL" \
  --max_tokens 2048 --num_epochs 1 --eval_steps "$EVAL_STEPS" --save_steps "$EVAL_STEPS" \
  --test_workers 6 --save_path "$WORK/ace-out"
python "$HERE/analyze.py" "$WORK/ace-out" "$HERE/results"

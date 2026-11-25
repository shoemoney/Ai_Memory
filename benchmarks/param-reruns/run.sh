#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
bench=benchmarks/param-reruns
scratch=${PARAM_SCRATCH:-/data/scratch/membench/param-reruns}
export PYTHONPATH="$PWD/$bench${PYTHONPATH:+:$PYTHONPATH}"
export PARAM_SCRATCH="$scratch" HF_HOME="$scratch/hf" UV_CACHE_DIR="$scratch/uv-cache"
mkdir -p "$scratch" "$bench/results"
uv venv "$scratch/venv" --python 3.12.16 --allow-existing --no-python-downloads
uv pip install --python "$scratch/venv/bin/python" -r "$bench/requirements-lock.txt"
py="$scratch/venv/bin/python"
"$py" "$bench/prepare.py"
"$py" "$bench/memgen/run.py" --dataset gsm8k --device cpu --limit 4 --max-tokens 8 --smoke
"$py" "$bench/memgen/run.py" --dataset triviaqa --device cpu --limit 4 --max-tokens 8 --smoke
"$py" "$bench/cartridges/run.py" --device cpu --smoke
requested=${PARAM_DEVICE:-auto}
gpu_deadline_epoch=$(( $(date +%s) + 36000 ))
for cell in gsm8k triviaqa cartridges; do
  if [[ "$requested" == cpu ]]; then
    chosen=cpu
  elif [[ "$requested" == auto || "$requested" == cuda ]]; then
    remaining=$(( gpu_deadline_epoch - $(date +%s) ))
    if ((remaining<0)); then remaining=0; fi
    chosen=$("$py" "$bench/wait_gpu.py" --timeout "$remaining" --device-only)
  else
    echo "PARAM_DEVICE must be auto, cpu, or cuda" >&2
    exit 2
  fi
  if [[ "$cell" == cartridges ]]; then
    "$py" "$bench/cartridges/run.py" --device "$chosen"
  else
    "$py" "$bench/memgen/run.py" --dataset "$cell" --device "$chosen"
  fi
done
"$py" "$bench/analyze.py"
"$py" "$bench/chart.py"
"$py" "$bench/redact_synthetic.py"
"$py" "$bench/verify.py"
# All model workers are synchronous and have exited; remove only configured owned scratch.
"$py" "$bench/cleanup.py"

#!/bin/bash
set -euo pipefail
df -h / /data
root_free_kb=$(df -Pk / | awk 'NR==2 {print $4}')
if [ "$root_free_kb" -lt 20971520 ]; then
  echo "Paused: the system filesystem has less than 20 GiB available." >&2
  exit 75
fi
ROOT=$(cd "$(dirname "$0")" && pwd)
export LAB_DIR="${LAB_DIR:-/data/scratch/membench/membench}"
export OUT_DIR="${OUT_DIR:-$ROOT/results}"
export CACHE_DIR="${CACHE_DIR:-/data/scratch/membench/membench}"
export UV_CACHE_DIR="$CACHE_DIR/uv-cache"
export PIP_CACHE_DIR="$CACHE_DIR/pip-cache"
export HF_HOME="$CACHE_DIR/cache"
if [ ! -x "$LAB_DIR/venv/bin/python" ]; then uv venv "$LAB_DIR/venv" --python 3.12.16; fi
uv pip install --python "$LAB_DIR/venv/bin/python" torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python "$LAB_DIR/venv/bin/python" -r "$ROOT/requirements-lock.txt" --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match
"$LAB_DIR/venv/bin/python" "$ROOT/audit_sources.py"
"$LAB_DIR/venv/bin/python" "$ROOT/prepare.py"
"$LAB_DIR/venv/bin/python" "$ROOT/verify_preparation.py"
"$LAB_DIR/venv/bin/python" "$ROOT/measure_embedding_limits.py"
"$LAB_DIR/venv/bin/python" "$ROOT/run.py"
"$LAB_DIR/venv/bin/python" "$ROOT/privacy_export.py"
"$LAB_DIR/venv/bin/python" "$ROOT/arena_pilot.py"

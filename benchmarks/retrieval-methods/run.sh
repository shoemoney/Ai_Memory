#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export LAB_DIR=${LAB_DIR:-/data/scratch/membench/retrieval-methods}
export UV_CACHE_DIR="$LAB_DIR/uv-cache" HF_HOME="$LAB_DIR/hf" PIP_CACHE_DIR="$LAB_DIR/pip-cache" TORCH_HOME="$LAB_DIR/torch-cache" TRITON_CACHE_DIR="$LAB_DIR/triton-cache" CUDA_CACHE_PATH="$LAB_DIR/cuda-cache"
df -h / /data
ROOT_FREE=$(df -PB1 / | awk 'NR==2 {print $4}')
if [ "$ROOT_FREE" -lt 21474836480 ]; then
  echo "Pause: root filesystem has under 20 GB free" >&2
  exit 1
fi
export OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4
export UV_PYTHON_INSTALL_DIR="$LAB_DIR/uv-python"
mkdir -p "$LAB_DIR"
if [ "${FRESH_RUN:-0}" = 1 ]; then python3 fresh.py; fi
uv venv --allow-existing "$LAB_DIR/venv" --python 3.12.16
uv pip install --python "$LAB_DIR/venv/bin/python" -r requirements.lock.txt
PY="$LAB_DIR/venv/bin/python"
"$PY" prepare_sources.py
"$PY" run.py prepare
"$PY" audit_data.py
"$PY" run.py keyword
"$PY" run.py embed
"$PY" run.py retrieve
"$PY" run.py rerank
"$PY" bootstrap.py
"$PY" prefix_token_audit.py
MAC_CONTROLLER_PID=''
stop_mac_controller() {
  if [ -n "$MAC_CONTROLLER_PID" ]; then
    "$PY" remote_control.py stop || true
    kill "$MAC_CONTROLLER_PID" 2>/dev/null || true
    wait "$MAC_CONTROLLER_PID" 2>/dev/null || true
    MAC_CONTROLLER_PID=''
  fi
}
if [ -n "${SSH_TARGET:-}" ]; then
  "$PY" remote_control.py deploy
  "$PY" remote_control.py serve > "$LAB_DIR/mac-controller.log" 2>&1 &
  MAC_CONTROLLER_PID=$!
  export PREFIX_BASE_URL=http://localhost:39791
  export PREFIX_SLOTS=${PREFIX_SLOTS:-8}
  export PREFIX_CTX_PER_SLOT=${PREFIX_CTX_PER_SLOT:-4096}
  trap stop_mac_controller EXIT
fi
export PREFIX_SLOTS=${PREFIX_SLOTS:-1}
export PREFIX_CTX_PER_SLOT=${PREFIX_CTX_PER_SLOT:-2976}
export PREFIX_BATCH_TOKENS=${PREFIX_BATCH_TOKENS:-128}
export PREFIX_UBATCH_TOKENS=${PREFIX_UBATCH_TOKENS:-64}
export PREFIX_GPU_MIN_FREE_MIB=${PREFIX_GPU_MIN_FREE_MIB:-4864}
# Contextual cells are completed on both full-corpus BEIR sets and the compact conversational set.
"$PY" run.py prefixes --datasets scifact nfcorpus locomo
stop_mac_controller
"$PY" run.py embed --context --datasets scifact nfcorpus locomo
"$PY" run.py retrieve --context --datasets scifact nfcorpus locomo
"$PY" run.py rerank --context --datasets scifact nfcorpus locomo
"$PY" summarize.py
"$PY" verify.py
"$PY" write_report.py
"$PY" chart.py
"$PY" collect_metadata.py
if [ -n "${SSH_TARGET:-}" ]; then "$PY" remote_control.py cleanup; fi
"$PY" cleanup.py

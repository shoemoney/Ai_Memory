#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
lab=${LAB_DIR:-/var/tmp/membench-locomo}
if [[ -e "$lab/qdrant" || -e "$lab/history.db" ]]; then
  echo 'Use a fresh LAB_DIR; reusing an indexed store would contaminate the run.' >&2
  exit 1
fi
export UV_CACHE_DIR="$lab/uv-cache" HF_HOME="$lab/hf" PIP_CACHE_DIR="$lab/pip-cache"
export UV_PYTHON_INSTALL_DIR="$lab/python"
mkdir -p "$lab"
uv venv "$lab/venv" --python 3.12.16 --allow-existing
uv pip sync --python "$lab/venv/bin/python" --torch-backend cpu "$here/requirements-lock.txt"
out=${OUT_DIR:-$here/results/rerun-$(date -u +%Y%m%dT%H%M%SZ)}
"$lab/venv/bin/python" "$here/run.py" --lab "$lab" --out "$out"
"$lab/venv/bin/python" "$here/export_memories.py" "$lab" "$out"
"$lab/venv/bin/python" "$here/verify.py" "$out"

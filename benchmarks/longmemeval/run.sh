#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export LAB_DIR="${LAB_DIR:-/var/tmp/membench-longmemeval}"
export RESULTS_DIR="${RESULTS_DIR:-$HERE/rerun-results}"
export UV_PYTHON_INSTALL_DIR="$LAB_DIR/python"
export UV_CACHE_DIR="$LAB_DIR/uv-cache"
mkdir -p "$LAB_DIR"
trap 'rm -rf -- "$LAB_DIR"' EXIT
uv venv --allow-existing --python 3.13.18 "$LAB_DIR/venv"
uv pip install --python "$LAB_DIR/venv/bin/python" -r "$HERE/requirements.txt"
"$LAB_DIR/venv/bin/python" "$HERE/run.py"

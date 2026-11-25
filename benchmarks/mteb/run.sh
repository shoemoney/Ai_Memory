#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
LAB=/var/tmp/membench-mteb
if [ -e "$LAB" ] || [ -L "$LAB" ]; then
  echo 'Scratch directory already exists; refusing to overwrite it.' >&2
  exit 1
fi
mkdir "$LAB"
LAB_TOKEN=$(cat /proc/sys/kernel/random/uuid)
printf '%s\n' "$LAB_TOKEN" > "$LAB/.owner"
cleanup() {
  status=$?
  if [ ! -L "$LAB" ] && [ "$(realpath -e "$LAB")" = "$LAB" ] &&
     [ -f "$LAB/.owner" ] && [ ! -L "$LAB/.owner" ] &&
     [ "$(cat "$LAB/.owner")" = "$LAB_TOKEN" ]; then
    rm -rf -- "$LAB"
  else
    echo 'Cleanup ownership check failed.' >&2
    exit 1
  fi
  python3 resources.py after
  python3 summarize.py
  python3 chart.py
  python3 editor_report.py
  exit "$status"
}
trap cleanup EXIT
export UV_CACHE_DIR="$LAB/uv"
export UV_PYTHON_INSTALL_DIR="$LAB/python"
export HF_HOME="$LAB/hf"
export HF_MODULES_CACHE="$LAB/modules"
export MTEB_CACHE="$LAB/mteb"
export XDG_CACHE_HOME="$LAB/cache"
export CUDA_CACHE_PATH="$LAB/cuda"
export TRITON_CACHE_DIR="$LAB/triton"
export TORCH_HOME="$LAB/torch"
export TORCHINDUCTOR_CACHE_DIR="$LAB/inductor"
mkdir "$LAB/tmp"
export TMPDIR="$LAB/tmp"
export TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4
python3 resources.py before
uv venv "$LAB/venv" --python 3.12.16
uv pip install --python "$LAB/venv/bin/python" -r requirements.txt
"$LAB/venv/bin/python" suite.py "$@"
"$LAB/venv/bin/python" verify.py
"$LAB/venv/bin/python" dimensions.py

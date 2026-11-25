#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
: "${MODEL_SSH:?Set MODEL_SSH to your assigned model host SSH target}"
LAB=/data/scratch/membench/mteb-large
if test -e "$LAB" || test -L "$LAB"; then echo 'Scratch already exists; refusing to overwrite.' >&2; exit 1; fi
df -h / /data
ROOT_FREE_KB=$(df -Pk / | awk 'NR==2 {print $4}')
if test "$ROOT_FREE_KB" -lt 20971520; then echo 'System disk has under 20 GB free; pause before large writes.' >&2; exit 1; fi
ssh "$MODEL_SSH" 'test ! -e ~/membench-mteb-large-tmp && test ! -L ~/membench-mteb-large-tmp && mkdir ~/membench-mteb-large-tmp'
mkdir -p "$LAB"
RUN_TOKEN=$(cat /proc/sys/kernel/random/uuid)
export RUN_TOKEN
export BENCH_DEADLINE=${BENCH_DEADLINE:-$(( $(date +%s) + 35100 ))}
printf '%s\n' "$RUN_TOKEN" > "$LAB/.owner"
printf '%s\n' "$RUN_TOKEN" | ssh "$MODEL_SSH" 'cat > ~/membench-mteb-large-tmp/.owner'
export CUDA_VISIBLE_DEVICES=""
export MPLCONFIGDIR="$LAB/matplotlib"
export PIP_CACHE_DIR="$LAB/pip"
export UV_PYTHON_INSTALL_DIR="$LAB/python"
export UV_CACHE_DIR="$LAB/uv" HF_HOME="$LAB/hf" MTEB_CACHE="$LAB/mteb" XDG_CACHE_HOME="$LAB/cache" PYTHONDONTWRITEBYTECODE=1
cleanup() {
  status=$?
  python3 cleanup.py
  exit "$status"
}
trap cleanup EXIT
python3 resources.py before
uv venv "$LAB/venv" --python 3.12.16
uv pip install --python "$LAB/venv/bin/python" -r results/client-versions.txt
scp server.py mlx_server.py harrier_server.py nomic_server.py memory_guard.py quantize.py quantize_mlx.py instructions.json requirements.txt nomic-requirements.txt results/mac-versions.txt results/nomic-versions.txt results/mlx-versions.txt results/lm-versions.txt "$MODEL_SSH:membench-mteb-large-tmp/"
ssh "$MODEL_SSH" 'cd ~/membench-mteb-large-tmp && export UV_CACHE_DIR="$PWD/uv" SETUPTOOLS_SCM_PRETEND_VERSION=0.3.8 && uv venv venv --python 3.12.16 && uv pip install --python venv/bin/python -r mac-versions.txt && uv venv nomic-venv --python 3.12.16 && uv pip install --python nomic-venv/bin/python -r nomic-versions.txt && uv venv mlx-venv --python 3.12.16 && uv pip install --python mlx-venv/bin/python -r mlx-versions.txt && uv venv lm-venv --python 3.12.16 && uv pip install --python lm-venv/bin/python -r lm-versions.txt'
ssh -N -o ExitOnForwardFailure=yes -L 39740:127.0.0.1:39740 "$MODEL_SSH" &
printf '%s\n' "$!" > "$LAB/tunnel.pid"
if test "${1:-}" = '--resume'; then
  "$LAB/venv/bin/python" followup.py --resume
else
  "$LAB/venv/bin/python" followup.py
fi
"$LAB/venv/bin/python" verify.py
"$LAB/venv/bin/python" verify_visual.py
python3 report.py
uv venv "$LAB/plot-venv" --python "$LAB/venv/bin/python"
uv pip install --python "$LAB/plot-venv/bin/python" -r results/plot-versions.txt
"$LAB/plot-venv/bin/python" plot.py

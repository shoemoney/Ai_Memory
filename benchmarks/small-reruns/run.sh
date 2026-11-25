#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
: "${MODEL_HOST:?Set MODEL_HOST to the assigned model host SSH destination}"
SCRATCH=${SCRATCH:-/data/scratch/membench/small-reruns}
export SCRATCH OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8
export TOKENIZERS_PARALLELISM=false RAYON_NUM_THREADS=8
export HF_HOME="$SCRATCH/hf" PIP_CACHE_DIR="$SCRATCH/pip-cache" TMPDIR="$SCRATCH/tmp"
export ENDPOINT=http://127.0.0.1:39900/v1
mkdir -p "$TMPDIR"
tunnel_pid=''
stop_server() {
 ssh -F /dev/null "$MODEL_HOST" 'bash -s' <<'REMOTE'
set -eu
cd "$HOME/membench-small-reruns-tmp"
if test -f guard.pid; then
 g=$(cat guard.pid)
 if ps -p "$g" -o command= | grep -Fq 'membench-small-reruns-tmp/serve.sh'; then kill "$g"; fi
fi
if test -f server.pid; then
 s=$(cat server.pid)
 for i in {1..10}; do
  kill -0 "$s" 2>/dev/null || break
  sleep 1
 done
 if kill -0 "$s" 2>/dev/null; then echo 'Owned server did not stop' >&2; exit 1; fi
fi
REMOTE
}
cleanup() {
 stop_server || true
 test -z "$tunnel_pid" || kill "$tunnel_pid" 2>/dev/null || true
 ssh -F /dev/null "$MODEL_HOST" 'rm -rf "$HOME/membench-small-reruns-tmp"' || true
 # Only this task's prescribed scratch directory is deleted automatically.
 if test "$SCRATCH" = /data/scratch/membench/small-reruns; then rm -rf "$SCRATCH"; fi
}
trap cleanup EXIT INT TERM
start_server() {
 ssh -F /dev/null "$MODEL_HOST" bash -s -- "$1" "$2" <<'REMOTE'
set -eu
cd "$HOME/membench-small-reruns-tmp"
MODEL_FILE="$1" MODEL_ALIAS="$2" nohup bash "$HOME/membench-small-reruns-tmp/serve.sh" > guard.log 2>&1 < /dev/null &
echo $! > guard.pid
REMOTE
 for i in {1..60}; do
  if curl -fsS http://127.0.0.1:39900/health >/dev/null 2>&1; then return; fi
  sleep 1
 done
 echo 'Model server did not become ready' >&2; exit 1
}
python3 -m venv "$SCRATCH/venv"
"$SCRATCH/venv/bin/pip" install torch==2.10.0 --index-url https://download.pytorch.org/whl/cpu
"$SCRATCH/venv/bin/pip" install -r requirements-lock.txt
"$SCRATCH/venv/bin/python" download_models.py
ssh -F /dev/null "$MODEL_HOST" 'mkdir -p "$HOME/membench-small-reruns-tmp"'
scp -F /dev/null serve.sh "$MODEL_HOST:membench-small-reruns-tmp/serve.sh"
scp -F /dev/null "$SCRATCH/qwen2.5-3b-instruct-q4_k_m.gguf" "$MODEL_HOST:membench-small-reruns-tmp/model.gguf"
scp -F /dev/null "$SCRATCH/"qwen2.5-7b-instruct-q4_k_m-*.gguf "$MODEL_HOST:membench-small-reruns-tmp/"
ssh -F /dev/null -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -L 39900:127.0.0.1:39900 "$MODEL_HOST" &
tunnel_pid=$!
start_server model.gguf small-reruns-qwen2.5-3b
"$SCRATCH/venv/bin/python" game24/run.py
"$SCRATCH/venv/bin/python" game24/summarize.py
stop_server
start_server model.gguf small-reruns-qwen2.5-3b
ANSWERS_ONLY=1 "$SCRATCH/venv/bin/python" dmr/run.py
stop_server
start_server qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf small-reruns-qwen2.5-7b
MODEL=small-reruns-qwen2.5-7b "$SCRATCH/venv/bin/python" dmr/judge.py
stop_server
ssh -F /dev/null "$MODEL_HOST" 'rm -f "$HOME/membench-small-reruns-tmp/"qwen2.5-7b-*.gguf'
scp -F /dev/null "$SCRATCH/qwen3.8-9b-distill-uncensored-heretic-q4_k_m.gguf" "$MODEL_HOST:membench-small-reruns-tmp/heretic-q4.gguf"
scp -F /dev/null "$SCRATCH/Qwen3.8-9B-Q4_K_M.gguf" "$MODEL_HOST:membench-small-reruns-tmp/stock-q4.gguf"
start_server heretic-q4.gguf small-reruns-heretic
"$SCRATCH/venv/bin/python" refusal/run.py heretic small-reruns-heretic
stop_server
start_server stock-q4.gguf small-reruns-stock
"$SCRATCH/venv/bin/python" refusal/run.py stock small-reruns-stock
stop_server
"$SCRATCH/venv/bin/python" refusal/summarize.py
"$SCRATCH/venv/bin/python" verify.py

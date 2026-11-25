#!/bin/bash
set -euo pipefail
cd "${BENCH_MODEL_DIR:-$HOME/membench-paper-reruns-tmp}"
free=$(/usr/bin/memory_pressure -Q | sed -n 's/System-wide memory free percentage: \([0-9]*\)%.*/\1/p')
[[ "$free" -ge 40 ]] || { echo 'Memory below loading threshold'; exit 1; }
/opt/homebrew/bin/llama-server --version > version.txt 2>&1
/opt/homebrew/bin/llama-server -m model3.gguf --host localhost --port 39950 --alias local-qwen2.5-3b-q4 -c 32768 -np 2 -b 512 -ub 128 -ngl 99 --jinja --no-webui > server.log 2>&1 &
server=$!
echo "$server" > server.pid
trap 'kill "$server" 2>/dev/null || true' EXIT INT TERM
while kill -0 "$server" 2>/dev/null; do
  level=$(/usr/sbin/sysctl -n kern.memorystatus_vm_pressure_level)
  printf '%s %s\n' "$(date -u +%FT%TZ)" "$level" >> pressure.txt
  if [[ "$level" != 1 ]]; then
    kill "$server"
    echo 'Own server stopped for kernel memory pressure' >> pressure.txt
    exit 75
  fi
  sleep 30
done
wait "$server"

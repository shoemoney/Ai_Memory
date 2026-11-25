#!/bin/bash
set -eu
cd "$HOME/membench-small-reruns-tmp"
free=$(/usr/bin/memory_pressure -Q | awk '/System-wide memory free percentage/{gsub(/%/,"",$5);print $5}')
test "$free" -ge 40
server_pid=''
trap 'test -z "$server_pid" || kill "$server_pid" 2>/dev/null || true' EXIT INT TERM
/opt/homebrew/bin/llama-server -m "${MODEL_FILE:-model.gguf}" --alias "${MODEL_ALIAS:-small-reruns-qwen2.5-3b}" --host 127.0.0.1 --port 39900 --ctx-size 32768 --parallel 1 --jinja > server.log 2>&1 &
server_pid=$!
echo "$server_pid" > server.pid
while kill -0 "$server_pid" 2>/dev/null; do
 level=$(/usr/sbin/sysctl -n kern.memorystatus_vm_pressure_level)
 echo "$(date -u +%FT%TZ) pressure=$level" >> pressure.log
 if test "$level" -ne 1; then kill "$server_pid"; wait "$server_pid" || true; exit 75; fi
 sleep 5
done
wait "$server_pid"

#!/bin/bash
# Runs on the Apple-silicon model host from ~/membench-gap-reruns-tmp with a local model.gguf.
# Loads only at 40% or more free memory. The host sat at kernel pressure level 2 (warn) with 56% free for hours
# for reasons outside this task. The watchdog stops its own server at level 4 (critical) or after three
# consecutive 5-second samples below 30% free (a single dip stopped the server once at 32% and cost a rerun).
set -eu
cd "$HOME/membench-gap-reruns-tmp"
free=$(/usr/bin/memory_pressure -Q | awk '/System-wide memory free percentage/{gsub(/%/,"",$5);print $5}')
test "$free" -ge 40
server_pid=''
low=0
trap 'test -z "$server_pid" || kill "$server_pid" 2>/dev/null || true' EXIT INT TERM
/opt/homebrew/bin/llama-server -m "${MODEL_FILE:-model.gguf}" --alias "${MODEL_ALIAS:-gap-qwen2.5-7b}" --host 127.0.0.1 --port "${PORT:-39980}" --ctx-size "${CTX:-32768}" --parallel "${PARALLEL:-2}" --jinja > server.log 2>&1 &
server_pid=$!
echo "$server_pid" > server.pid
while kill -0 "$server_pid" 2>/dev/null; do
 level=$(/usr/sbin/sysctl -n kern.memorystatus_vm_pressure_level)
 echo "$(date -u +%FT%TZ) pressure=$level" >> pressure.log
 free=$(/usr/bin/memory_pressure -Q | awk '/System-wide memory free percentage/{gsub(/%/,"",$5);print $5}')
 echo "$(date -u +%FT%TZ) free=$free" >> pressure.log
 if test "$free" -lt 30; then low=$((low+1)); else low=0; fi
 if test "$level" -ge 4 || test "$low" -ge 3; then kill "$server_pid"; wait "$server_pid" || true; exit 75; fi
 sleep 5
done
wait "$server_pid"

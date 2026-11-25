#!/bin/bash
# Deploy only inside the task-owned model scratch directory.
set -u
cd "${MODEL_DIR:-$HOME/membench-membench-tmp}"
export TMPDIR="$PWD"
server_pid=''
stop_server() {
 test -z "$server_pid" && return
 kill -TERM "$server_pid" 2>/dev/null || true
 for stop_attempt in 1 2 3 4 5 6 7 8 9 10; do
  kill -0 "$server_pid" 2>/dev/null || break
  sleep 1
 done
 if kill -0 "$server_pid" 2>/dev/null; then
  echo FORCE-STOP-AFTER-GRACEFUL-HANG >> pressure.log
  kill -KILL "$server_pid" 2>/dev/null || true
 fi
 wait "$server_pid" 2>/dev/null || true
 server_pid=''
}
trap 'stop_server; exit' TERM INT EXIT
while true; do
 level=$(sysctl -n kern.memorystatus_vm_pressure_level)
 free=$(memory_pressure | awk '/System-wide memory free percentage/{gsub(/%/,"",$5);print $5}')
 printf '%s pressure=%s free=%s\n' "$(date -u +%FT%TZ)" "$level" "$free" >> pressure.log
 if [ "$level" -eq 1 ] && [ "${free:-0}" -ge 40 ]; then
  /opt/homebrew/bin/llama-server --model model.gguf --alias qwen2.5-14b-instruct \
   --host localhost --port 39780 --ctx-size 131072 --parallel 1 \
   --override-kv qwen2.context_length=int:131072 --rope-scaling yarn --rope-scale 4 --yarn-orig-ctx 32768 \
   --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --cache-ram 0 --jinja >> server.log 2>&1 &
  server_pid=$!;echo "$server_pid" > server.pid
  while kill -0 "$server_pid" 2>/dev/null; do
   level=$(sysctl -n kern.memorystatus_vm_pressure_level)
   printf '%s pressure=%s\n' "$(date -u +%FT%TZ)" "$level" >> pressure.log
   if [ "$level" -ne 1 ]; then
    echo STOP-WARNING >> pressure.log;stop_server;break
   fi
   sleep 5
  done
  wait "$server_pid" 2>/dev/null;server_pid=''
 fi
 sleep 15
done

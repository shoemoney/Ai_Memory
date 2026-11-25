#!/bin/bash
set -u
cd "$HOME/membench-locomo-tmp"
export TMPDIR="$PWD"
server_pid=''
trap 'test -z "$server_pid" || kill "$server_pid" 2>/dev/null; exit' TERM INT EXIT
warning_since=0
while true; do
 level=$(sysctl -n kern.memorystatus_vm_pressure_level)
 free=$(memory_pressure -Q | awk '/System-wide memory free percentage/{gsub(/%/,"",$5);print $5}')
 printf '%s pressure=%s free=%s\n' "$(date -u +%FT%TZ)" "$level" "$free" >> pressure.log
 if [ "$level" -eq 1 ] && [ "$free" -ge 40 ]; then
  warning_since=0
  /opt/homebrew/bin/llama-server --model model.gguf --alias qwen2.5-14b-instruct --host localhost --port 39700 --ctx-size 131072 --override-kv qwen2.context_length=int:65536 --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 32768 --parallel 2 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --cache-ram 0 --jinja >> server.log 2>&1 &
  server_pid=$!;echo "$server_pid" > server.pid
  while kill -0 "$server_pid" 2>/dev/null; do
   level=$(sysctl -n kern.memorystatus_vm_pressure_level)
   printf '%s pressure=%s\n' "$(date -u +%FT%TZ)" "$level" >> pressure.log
   if [ "$level" -ne 1 ]; then
    echo STOP-WARNING >> pressure.log;kill "$server_pid";wait "$server_pid";break
   fi
   sleep 5
  done
  wait "$server_pid" 2>/dev/null;server_pid=''
 else
  now=$(date +%s)
  if [ "$warning_since" -eq 0 ]; then warning_since=$now;fi
  if [ $((now-warning_since)) -ge 1200 ]; then echo PAUSED-WAITING-FOR-NORMAL >> pressure.log;fi
 fi
 sleep 15
done

set -euo pipefail
mkdir -p ~/membench-bfcl-tmp
cd ~/membench-bfcl-tmp
pressure=$(sysctl -n kern.memorystatus_vm_pressure_level)
free_percent=$(memory_pressure | awk '/System-wide memory free percentage/ {gsub(/%/, "", $NF); print $NF}')
if [ "$pressure" != 1 ] || [ "$free_percent" -lt 40 ]; then
 echo "Memory admission blocked: free=${free_percent}%, pressure=${pressure}" >&2
 exit 1
fi
if lsof -nP -iTCP:39730 -sTCP:LISTEN >/dev/null; then
 echo 'Port already in use' >&2
 exit 1
fi
if [ ! -f model.gguf ] || [ "$(shasum -a 256 model.gguf | awk '{print $1}')" != "$MODEL_SHA" ]; then
 curl -fL --retry 2 "$MODEL_URL" -o model.gguf.part 2>download.log
 printf '%s  %s\n' "$MODEL_SHA" model.gguf.part | shasum -a 256 -c -
 mv model.gguf.part model.gguf
fi
nohup llama-server -m model.gguf --host localhost --port 39730 \
 --alias "$MODEL_ALIAS" -c 8192 -np 1 -b 256 -ub 64 -ngl 99 \
 --jinja --reasoning-format deepseek --no-webui >server.log 2>&1 </dev/null &
echo $! >server.pid
nohup bash -c '
 while kill -0 "$(cat server.pid)" 2>/dev/null; do
  level=$(sysctl -n kern.memorystatus_vm_pressure_level)
  free_percent=$(memory_pressure | awk '\''/System-wide memory free percentage/ {gsub(/%/, "", $NF); print $NF}'\'')
  printf "%s free=%s pressure=%s\n" "$(date -u +%FT%TZ)" "$free_percent" "$level" >> pressure.log
  if [ "$level" != 1 ] || [ "$free_percent" -lt 40 ]; then
   kill "$(cat server.pid)"
   exit 1
  fi
  sleep 5
 done
' >guard.log 2>&1 </dev/null &
echo $! >guard.pid

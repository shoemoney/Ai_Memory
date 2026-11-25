#!/usr/bin/env bash
# Run from the workstation: serve.sh <absolute-macstudio-model-dir> [start|restart|stop]
set -euo pipefail
model=${1:?Usage: serve.sh MODEL_DIR [start|restart|stop]}
action=${2:-start}
[[ "$action" =~ ^(start|restart|stop)$ ]] || exit 2
printf -v model_q '%q' "$model"
ssh <mac-studio> "bash -s -- $model_q $action" <<'REMOTE'
set -euo pipefail
model=$1; action=$2; lab="$HOME/inkling-lab"
stop_server() {
 if [[ -f "$lab/server.pid" ]]; then
  pid=$(cat "$lab/server.pid")
  if kill -0 "$pid" 2>/dev/null; then
   # Bind ownership check: never kill an unrelated reused PID.
   lsof -b -w -nP -a -p "$pid" -iTCP:39850 -sTCP:LISTEN >/dev/null || { echo "PID does not own lab port; refusing stop" >&2; exit 1; }
   kill "$pid"
   for n in {1..30}; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
   if kill -0 "$pid" 2>/dev/null; then echo "Server still exiting; retry later" >&2; exit 1; fi
  fi
  rm -f "$lab/server.pid"
  rmdir "$lab/heavy.lock" 2>/dev/null || true
 fi
}
[[ "$action" == start ]] || stop_server
[[ "$action" != stop ]] || exit 0
[[ -f "$model/config.json" ]] || { echo 'Missing model config' >&2; exit 1; }
if lsof -b -w -nP -iTCP:39850 -sTCP:LISTEN >/dev/null; then echo 'Port 39850 already occupied' >&2; exit 1; fi
mkdir "$lab/heavy.lock" || { echo "Another lab model job owns the lock" >&2; exit 1; }
# One symlink in this discovery root exposes exactly one checkpoint.
mkdir -p "$lab/serve-models" "$lab/cache" "$lab/tmp" "$lab/home"
find "$lab/serve-models" -maxdepth 1 -type l -delete
ln -s "$model" "$lab/serve-models/$(basename "$model")"
export HF_HOME="$lab/hf-cache" XDG_CACHE_HOME="$lab/cache" TMPDIR="$lab/tmp"
export INKLING_LAB_ROOT="$lab" HOME="$lab/home"
nohup "$lab/omlx-venv/bin/python" "$lab/launch-server.py" serve --base-path "$lab/omlx-data"  --model-dir "$lab/serve-models" --host 127.0.0.1 --port 39850  --no-hf-cache --no-cache --max-concurrent-requests 1 --memory-guard-gb 60  --headless > "$lab/server.log" 2>&1 < /dev/null &
echo $! > "$lab/server.pid"
echo "Started PID $(cat "$lab/server.pid") on 127.0.0.1:39850"
REMOTE

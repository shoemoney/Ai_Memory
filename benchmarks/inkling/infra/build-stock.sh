#!/usr/bin/env bash
set -euo pipefail
ssh <mac-studio> 'bash -s' <<'REMOTE'
set -euo pipefail
lab="$HOME/inkling-lab"
[[ -f "$lab/source-verification.json" ]] || { echo 'Source must pass verification first' >&2; exit 1; }
[[ ! -f "$lab/server.pid" ]] || { echo 'Stop the lab server before quantizing' >&2; exit 1; }
mkdir "$lab/heavy.lock" || { echo 'Another lab model job owns the lock' >&2; exit 1; }
trap 'rmdir "$lab/heavy.lock"' EXIT
mkdir -p "$lab/cache" "$lab/tmp"
export HF_HOME="$lab/hf-cache" XDG_CACHE_HOME="$lab/cache" TMPDIR="$lab/tmp"
/usr/bin/time -l "$lab/omlx-venv/bin/python" "$lab/build-stock.py"
REMOTE

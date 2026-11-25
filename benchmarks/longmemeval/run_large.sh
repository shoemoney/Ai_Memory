#!/usr/bin/env bash
set -euo pipefail
: "${MODEL_HOST:?Set MODEL_HOST to your SSH model-serving account and host}"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export LAB_DIR="${LAB_DIR:-/var/tmp/membench-longmemeval}"
export BUDGET_SECONDS="${BUDGET_SECONDS:-31000}"
exec systemd-run --user --collect --unit=membench-longmemeval-large \
  --property=RuntimeMaxSec=32000 --property=TimeoutStopSec=180 \
  --property=KillMode=mixed --setenv=MODEL_HOST --setenv=BUDGET_SECONDS \
  --setenv=LAB_DIR --setenv=PATH --working-directory="$HERE" \
  /usr/bin/python3 "$HERE/supervise_large.py"

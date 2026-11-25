#!/usr/bin/env bash
set -euo pipefail
: "${MODEL_HOST:?Set MODEL_HOST to the SSH model host}"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export LAB_DIR="${LAB_DIR:-/var/tmp/membench-longmemeval-frameworks}"
export BUDGET_SECONDS="${BUDGET_SECONDS:-50400}"
exec systemd-run --user --collect --unit=membench-longmemeval-frameworks --property=RuntimeMaxSec=50600 --property=TimeoutStopSec=180 --property=KillMode=mixed --setenv=MODEL_HOST --setenv=BUDGET_SECONDS --setenv=LAB_DIR --setenv=PATH --working-directory="$HERE" /usr/bin/python3 "$HERE/supervise.py"

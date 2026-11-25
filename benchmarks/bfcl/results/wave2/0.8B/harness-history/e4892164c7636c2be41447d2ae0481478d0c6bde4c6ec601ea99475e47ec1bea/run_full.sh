#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
root=$(cd "$(dirname "$0")" && pwd)
: "${MODEL_HOST:?Set MODEL_HOST to the authorized model-serving SSH alias}"
if systemctl --user is-active --quiet membench-bfcl-full;then
 echo 'The expanded run is already active.'
 exit 0
fi
systemd-run --user --unit=membench-bfcl-full --collect \
 --property=Restart=on-failure --property=RestartSec=20 \
 --property=RuntimeMaxSec=14h --property=TimeoutStopSec=180 \
 --setenv="PATH=$PATH" --setenv="MODEL_HOST=$MODEL_HOST" --setenv="RUN_NAME=${RUN_NAME:-full}" --setenv=PYTHONDONTWRITEBYTECODE=1 \
 /usr/bin/python3 "$root/run_full.py" "$@"
echo "Supervised run started. Per-item checkpoints and final reports are in results/${RUN_NAME:-full}/."

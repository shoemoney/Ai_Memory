#!/usr/bin/env bash
# Run on the workstation, with the lab tunnel up and the Mac Studio lab lock held.
set -euo pipefail
variant=${1:?Usage: energy_run.sh VARIANT longmemeval|locomo N}
lab=${2:?}; n=${3:?}
[[ "$variant" =~ ^(stock|edited|edited+lora|smoke)$ ]] || exit 2
[[ "$lab" =~ ^(longmemeval|locomo)$ ]] || exit 2
[[ "$n" =~ ^[1-9][0-9]*$ ]] || exit 2
: "${MODEL:?Set MODEL to the selected lab model id}"
here=$(cd -- "$(dirname -- "$0")" && pwd)
inkling=$(cd "$here/../.." && pwd)
results=${RESULTS_ROOT:-$inkling/results}
energy=${ENERGY_OUT:-$here/runs/$variant/$lab/$(date -u +%Y%m%dT%H%M%SZ)}
python=${PYTHON:-python3}
args=()
[[ -z "${JUDGE_BASE_URL:-}" ]] || args+=(--judge-base-url "$JUDGE_BASE_URL")
"$python" "$here/power.py" --items-root "$results/$variant/$lab" --out "$energy" \
 --baseline-seconds "${BASELINE_SECONDS:-10}" -- \
 "$python" "$inkling/labs/memory.py" "$lab" --variant "$variant" --model "$MODEL" \
 --output-root "$results" --batch-size "$n" "${args[@]}"

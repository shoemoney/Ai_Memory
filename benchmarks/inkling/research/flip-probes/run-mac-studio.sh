#!/usr/bin/env bash
set -euo pipefail
lab="${INKLING_LAB:-$HOME/inkling-lab}"
research_dir="$(cd "$(dirname "$0")" && pwd)"
output="${1:?Usage: run-mac-studio.sh NEW_OUTPUT_DIRECTORY [flips.py flags]}"
shift
model="${INKLING_VARLOOP_MODEL:-$lab/models/TML-d24-varloop-research}"
[[ -d "$model" ]] || { echo "Missing local varloop checkpoint: $model" >&2; exit 1; }
mkdir "$lab/heavy.lock" || { echo 'Another lab job owns heavy.lock' >&2; exit 1; }
trap 'rmdir "$lab/heavy.lock"' EXIT
"$lab/mlxlm-venv/bin/python" - "$lab" <<'PY'
import shutil,sys
free=shutil.disk_usage(sys.argv[1]).free
if free < 20 * 1024**3:
    raise SystemExit('Need 20 GiB free before collection: 15 GiB floor plus output allowance')
PY
/usr/bin/time -l env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
 "$lab/mlxlm-venv/bin/python" "$research_dir/flips.py" \
 --model "$model" --output "$output" --prompts "$research_dir/prompts.jsonl" \
 --layers 6,11,17 --max-tokens 32 "$@"

#!/usr/bin/env bash
# Detached driver: energy windows (mtp on/off, ABBA order) on a 12-question LongMemEval subset. Writes runs/DONE-energy.
set -uo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd); cd "$here"
inkling=$(cd ../.. && pwd)
export MODEL_DIR=$HOME/inkling-lab/models/Inkling-2-Mini-oQ4e-stock
export MODEL=${MODEL_DIR##*/}
status=0; rm -f runs/DONE-energy
i=0
for mode in on off off on; do
  i=$((i+1))
  INKLING_MTP_MODE=$mode INKLING_MODEL=$MODEL ./set_mtp.sh || { status=$?; break; }
  root="$inkling/results/efficiency-energy2-$i-$mode"
  mkdir -p "$root/stock/longmemeval"
  python3 power.py --items-root "$root/stock/longmemeval" --out "runs/stock/energy2-$i-$mode" --baseline-seconds 30 -- \
    python3 "$inkling/labs/memory.py" longmemeval --variant stock --model "$MODEL" --output-root "$root" --batch-size 100 --limit 12 || { status=$?; break; }
done
timeout 65 ../../infra/serve.sh "$MODEL_DIR" stop
timeout 20 ssh <mac-studio> 'cp ~/inkling-lab/omlx-data/model_settings.pre-efficiency.json ~/inkling-lab/omlx-data/model_settings.json'
echo "exit=$status finished=$(date -u +%FT%TZ)" > runs/DONE-energy
exit $status

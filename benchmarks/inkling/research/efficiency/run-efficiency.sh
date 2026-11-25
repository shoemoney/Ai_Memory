#!/usr/bin/env bash
# Detached driver: instrument, acceptance (off then on), energy (mtp on then off), restore. Writes runs/DONE with status.
set -uo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$here"
inkling=$(cd ../.. && pwd)
export MODEL_DIR=$HOME/inkling-lab/models/Inkling-2-Mini-oQ4e-stock
export MODEL=${MODEL_DIR##*/}
HOST=<lan-address>
BG=$HOME/inkling-lab/omlx-venv/lib/python3.13/site-packages/omlx/patches/mlx_lm_mtp/batch_generator.py
status=0
mkdir -p runs; rm -f runs/DONE
step() { echo "== $* $(date -u +%T)"; "$@" || { status=$?; echo "FAILED rc=$status: $*"; return $status; }; }
{
step timeout 65 ../../infra/serve.sh "$MODEL_DIR" stop
step timeout 20 scp instrument_mtp.py $HOST:inkling-lab/instrument_mtp.py
step timeout 30 ssh $HOST "~/inkling-lab/omlx-venv/bin/python ~/inkling-lab/instrument_mtp.py --path $BG"
step python3 accept.py --variant stock --model "$MODEL" --mode both --configure-hook ./set_mtp.sh --out runs/stock/acceptance-01
for mode in on off; do
  INKLING_MTP_MODE=$mode INKLING_MODEL=$MODEL ./set_mtp.sh || { status=$?; break; }
  root="$inkling/results/efficiency-energy-$mode"
  mkdir -p "$root/stock/longmemeval"
  step python3 power.py --items-root "$root/stock/longmemeval" --out "runs/stock/energy-$mode" \
    --baseline-seconds 30 -- python3 "$inkling/labs/memory.py" longmemeval --variant stock --model "$MODEL" \
    --output-root "$root" --batch-size 5 --limit 6
done
} 
echo "== restore"
timeout 65 ../../infra/serve.sh "$MODEL_DIR" stop
timeout 30 ssh $HOST "~/inkling-lab/omlx-venv/bin/python ~/inkling-lab/instrument_mtp.py --restore --path $BG"
timeout 20 ssh $HOST 'cp ~/inkling-lab/omlx-data/model_settings.pre-efficiency.json ~/inkling-lab/omlx-data/model_settings.json'
echo "exit=$status finished=$(date -u +%FT%TZ)" > runs/DONE
exit $status

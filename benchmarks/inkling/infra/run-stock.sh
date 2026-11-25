#!/usr/bin/env bash
set -euo pipefail
cd <checkout>
export PYTHON="$PWD/benchmarks/inkling/labs/.venv/bin/python"
model=Inkling-2-Mini-oQ4e-stock
out=benchmarks/inkling/results/stock
date -u +%FT%TZ > "$out/started.txt"
for n in $(seq 10 10 180); do
 benchmarks/inkling/infra/restart-reader.sh $HOME/inkling-lab/models/Inkling-2-Mini-oQ4e-stock
 "$PYTHON" benchmarks/inkling/refusal/run.py --base-url http://127.0.0.1:39850/v1 --model "$model" --seed 7 --concurrency 1 --max-tokens 512 --thinking-budget 0 --timeout 900 --limit "$n" --output "$out/refusal.jsonl"
 echo "Refusal complete $n/180"
done
"$PYTHON" benchmarks/inkling/refusal/score.py "$out/refusal.jsonl" --output "$out/refusal-score.json"
benchmarks/inkling/infra/restart-reader.sh $HOME/inkling-lab/models/Inkling-2-Mini-oQ4e-stock
bash benchmarks/inkling/labs/batch.sh stock --restart-hook 'benchmarks/inkling/infra/restart-reader.sh ~/inkling-lab/models/Inkling-2-Mini-oQ4e-stock' --model "$model" --batch-size 10 --quality-concurrency 1
# Record the last benchmark process peak and leave a fresh stock reader ready.
benchmarks/inkling/infra/restart-reader.sh $HOME/inkling-lab/models/Inkling-2-Mini-oQ4e-stock
date -u +%FT%TZ > "$out/finished.txt"

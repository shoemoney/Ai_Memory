#!/usr/bin/env bash
# Detached driver for the depth x retrieval sweep. Writes results/depth-retrieval/DONE with the exit status.
cd <checkout> || exit 1
R=benchmarks/inkling/results
mkdir -p "$R/depth-retrieval"
rm -f "$R/depth-retrieval/DONE"
status=0
for p in 1 2 3 5; do
  PYTHON=python3 bash benchmarks/inkling/research/memory-loops/sweep.sh "$p" --design depth-retrieval \
    --model $HOME/inkling-lab/models/TML-d24-varloop-research \
    --output-root benchmarks/inkling/results || { status=$?; echo "sweep p$p failed rc=$status"; break; }
done
if [ "$status" = 0 ]; then
  python3 benchmarks/inkling/research/memory-loops/analyze_depth_retrieval.py --results "$R/depth-retrieval" --output "$R/depth-retrieval/analysis" || status=$?
fi
echo "exit=$status finished=$(date -u +%FT%TZ)" > "$R/depth-retrieval/DONE"
exit $status

#!/bin/bash
set -euo pipefail
bench_dir=$(cd "$(dirname "$0")" && pwd)
bench_scratch=${BENCH_SCRATCH:-/data/scratch/membench/paper-reruns}
export HF_HOME="$bench_scratch/hf" XDG_CACHE_HOME="$bench_scratch/cache" OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=20261122
hippo_cache_args=()
if [[ -n "${BENCH_EXTRACTION_CACHE:-}" ]]; then hippo_cache_args+=(--extraction-cache "$BENCH_EXTRACTION_CACHE"); fi
hippo_started=$SECONDS
"$bench_scratch/venv/bin/python" "$bench_dir/hipporag2/run.py" --source "$bench_scratch/HippoRAG" --scratch "$bench_scratch/index-guard" "${hippo_cache_args[@]}" --endpoint "${BENCH_ENDPOINT:-http://localhost:39950/v1}"
"$bench_scratch/venv/bin/python" "$bench_dir/hipporag2/analyze.py"
"$bench_scratch/venv/bin/python" "$bench_dir/hipporag2/verify.py"
"$bench_scratch/venv/bin/python" "$bench_dir/hipporag2/index_diagnostics.py" --index "$bench_scratch/index-guard/hipporag2"
if (( SECONDS - hippo_started > 18000 )); then
  echo 'Spiral of Silence not run here for lack of time: HippoRAG exceeded five hours.'
  exit 0
fi
"$bench_scratch/venv/bin/python" "$bench_dir/spiral-of-silence/run.py" --source "$bench_scratch/SOS-Retrieval-Loop" --scratch "$bench_scratch/sos" --embedding "$bench_scratch/contriever" --rounds "${BENCH_ROUNDS:-10}" --endpoint "${BENCH_ENDPOINT:-http://localhost:39950/v1}"
"$bench_scratch/venv/bin/python" "$bench_dir/spiral-of-silence/verify.py"

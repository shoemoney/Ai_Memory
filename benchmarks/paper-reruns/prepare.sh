#!/bin/bash
# Prepare only the evaluator on the CPU machine. Serve the model separately.
set -euo pipefail
bench_dir=$(cd "$(dirname "$0")" && pwd)
bench_scratch=${BENCH_SCRATCH:-/data/scratch/membench/paper-reruns}
mkdir -p "$bench_scratch"
export UV_CACHE_DIR="$bench_scratch/uv" HF_HOME="$bench_scratch/hf" XDG_CACHE_HOME="$bench_scratch/cache"
if [[ ! -d "$bench_scratch/HippoRAG/.git" ]]; then
  git clone https://github.com/OSU-NLP-Group/HippoRAG.git "$bench_scratch/HippoRAG"
fi
git -C "$bench_scratch/HippoRAG" checkout d5c8329422e0a0b834a15874545cb6a74b4f9b26
if [[ ! -x "$bench_scratch/venv/bin/python" ]]; then
  uv venv --python 3.11 "$bench_scratch/venv"
fi
uv pip install --python "$bench_scratch/venv/bin/python" -r "$bench_dir/requirements.lock" --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match
"$bench_scratch/venv/bin/python" - "$bench_scratch/index/embedding" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download('sentence-transformers/all-mpnet-base-v2',revision='e8c3b32edf5434bc2275fc9bab85f82640a19130', local_dir=sys.argv[1], ignore_patterns=['*.onnx','onnx/*','openvino/*','*.h5','*.msgpack','rust_model.ot'])
PY

if [[ ! -d "$bench_scratch/SOS-Retrieval-Loop/.git" ]]; then
  git clone https://github.com/VerdureChen/SOS-Retrieval-Loop.git "$bench_scratch/SOS-Retrieval-Loop"
fi
git -C "$bench_scratch/SOS-Retrieval-Loop" checkout 56a19847edfc30d1e6e59894d348e1c17ae15114
if [[ ! -f "$bench_scratch/nq-test.json.gz" ]]; then
  curl -L --fail --retry 3 https://dl.fbaipublicfiles.com/dpr/data/retriever_results/single/nq-test.json.gz -o "$bench_scratch/nq-test.json.gz"
fi
echo '77c7babe859bbf3d6326364a614048f9555aaf896d4bd75183de0ef31e45e852  '"$bench_scratch/nq-test.json.gz" | sha256sum -c -
"$bench_scratch/venv/bin/python" "$bench_dir/spiral-of-silence/prepare.py" --source "$bench_scratch/SOS-Retrieval-Loop" --dpr "$bench_scratch/nq-test.json.gz" --scratch "$bench_scratch/sos"

mkdir -p "$bench_scratch/index-guard"
ln -sfn "$bench_scratch/index/embedding" "$bench_scratch/index-guard/embedding"

"$bench_scratch/venv/bin/python" - "$bench_scratch/contriever" <<'PYMODEL'
import sys
from huggingface_hub import snapshot_download
snapshot_download('facebook/contriever-msmarco',revision='abe8c1493371369031bcb1e02acb754cf4e162fa',local_dir=sys.argv[1],ignore_patterns=['*.md','.gitattributes'])
PYMODEL

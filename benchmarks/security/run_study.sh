#!/usr/bin/env bash
# CPU reproduction of the completed study. Saved per-item outputs resume by ID.
set -euo pipefail
cd "$(dirname "$0")"
work_dir="$PWD"
if test -n "$(docker ps --filter name=membench-security --format '{{.Names}}')"; then
 echo 'An owned security experiment is active; finish it before reproduction.' >&2; exit 2
fi
# Storage owns this scratch root during its run and cleans it on exit.
bash run.sh
scratch_dir=/data/scratch/membench/security
export HF_HOME="$scratch_dir/hf" UV_CACHE_DIR="$scratch_dir/uv-cache" PIP_CACHE_DIR="$scratch_dir/pip-cache"
mkdir -p "$scratch_dir" results/model
python_image='python@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c'
llama_image='ghcr.io/ggml-org/llama.cpp@sha256:5b43086e3ba7ea5794d72904654f6cd41224a9b1c6ac0398f4940ee380d30f23'
pulled_python=0; pulled_llama=0
disk_gate() { df -h / /data; test "$(df -Pk / | awk 'NR==2 {print $4}')" -ge 20971520; }
cleanup() {
 docker rm -f membench-security-study-client membench-security-study-inversion membench-security-study-backend membench-security-study-proxy >/dev/null 2>&1 || true
 rm -rf "$scratch_dir"
 if test "$pulled_python" = 1; then docker image rm "$python_image" >/dev/null 2>&1 || true; fi
 if test "$pulled_llama" = 1; then docker image rm "$llama_image" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT
python3 fetch.py "$scratch_dir"
cp "$scratch_dir/manifest.json" results/sources.json
if ! docker image inspect "$python_image" >/dev/null 2>&1; then disk_gate; docker pull "$python_image"; pulled_python=1; fi
install() {
 docker run -i --rm --name membench-security-study-client --user "$(id -u):$(id -g)" -e PIP_CACHE_DIR=/scratch/pip-cache -v "$scratch_dir:/scratch" "$python_image" python -m pip install --target "/scratch/$1" "${@:2}"
}
install model-deps --no-deps -r /dev/stdin < requirements-client.lock
client() {
 docker run --rm --name membench-security-study-client --network host --cap-drop ALL --user "$(id -u):$(id -g)" -e HF_HOME=/scratch/hf -e PYTHONPATH=/scratch/model-deps -v "$scratch_dir:/scratch" -v "$work_dir:/work" -w /work "$python_image" python "$@"
}
wait_ready() {
 python3 - "$1" <<'PY'
import json,sys,time,urllib.request
for attempt in range(180):
 try:
  if json.load(urllib.request.urlopen(sys.argv[1],timeout=2)).get('ready'):break
 except Exception:pass
 time.sleep(1)
else:raise RuntimeError('task inference service did not become ready')
PY
}
client verify_model_graders.py --scratch /scratch --out /work/results/model/grading-controls.json
if ! python3 model_summary.py --results results/model --check-only >/dev/null 2>&1; then
 disk_gate
 install download-deps huggingface_hub==0.36.2
 docker run --rm --name membench-security-study-client --user "$(id -u):$(id -g)" -e HF_HOME=/scratch/hf -e PYTHONPATH=/scratch/download-deps -v "$scratch_dir:/scratch" -v "$work_dir:/work" -w /work "$python_image" python download_cpu_models.py --scratch /scratch
 cp "$scratch_dir/model-revisions-cpu.json" results/model/model-revisions-cpu.json
 if ! docker image inspect "$llama_image" >/dev/null 2>&1; then disk_gate; docker pull "$llama_image"; pulled_llama=1; fi
 docker run -d --no-healthcheck --log-opt max-size=10m --log-opt max-file=1 --name membench-security-study-backend --network host --cpus 8 --memory 5g --cap-drop ALL --user "$(id -u):$(id -g)" -v "$scratch_dir/cpu-weights:/models:ro" "$llama_image" -m /models/qwen2.5-3b-instruct-q4_k_m.gguf --host 127.0.0.1 --port 39804 --gpu-layers 0 --threads 8 --threads-batch 8 --ctx-size 4096 --batch-size 512 --ubatch-size 512 --parallel 1 --pooling mean --embedding --no-warmup
 docker run -d --name membench-security-study-proxy --network host --memory 512m --cpus 1 --cap-drop ALL --user "$(id -u):$(id -g)" --group-add "$(stat -c '%g' /var/run/docker.sock)" --log-opt max-size=10m --log-opt max-file=1 -v /var/run/docker.sock:/var/run/docker.sock -v "$work_dir:/work:ro" -w /work "$python_image" python cpu_server.py --port 39800 --backend http://localhost:39804 --owned-container membench-security-study-backend
 wait_ready http://localhost:39800/
 for family in minja agentpoison injecmem controls; do
  client attacks.py --family "$family" --scratch /scratch --results /work/results/model --trials 100
 done
 docker rm -f membench-security-study-backend
 docker rm -f membench-security-study-proxy
 # One neural model at a time; the 3B generator is gone before inversion.
 disk_gate
 install inversion-deps --no-deps --index-url https://download.pytorch.org/whl/cpu torch==2.8.0+cpu
 install inversion-deps --no-deps -r /dev/stdin < requirements-inversion-cpu.lock
 docker run -d --log-opt max-size=10m --log-opt max-file=1 --name membench-security-study-inversion --network host --cpus 4 --memory 5g --cap-drop ALL --user "$(id -u):$(id -g)" -e HF_HOME=/scratch/hf -e PYTHONPATH=/scratch/inversion-deps -e TOKENIZERS_PARALLELISM=false -v "$scratch_dir:/scratch" -v "$work_dir:/work" -w /work "$python_image" python inversion_server.py --root /scratch/inversion-models --port 39802
 wait_ready http://localhost:39802/
 client inversion.py --scratch /scratch --results /work/results/model --endpoint http://localhost:39802 --trials 100 --steps 5 --batch-size 8
 # Fresh outputs require actual tester inspection, not an automatically invented audit.
 if ! test -f results/model/review-audit.json; then
  echo 'Inspect at least 40 actual write reviews and record the tester audit before final validation.' >&2; exit 2
 fi
fi
client score_models.py --scratch /scratch --results /work/results/model
python3 model_summary.py --results results/model
python3 study_summary.py

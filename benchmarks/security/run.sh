#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
work_dir="$PWD"
scratch_dir="/data/scratch/membench/security"
export HF_HOME="$scratch_dir/hf"
export UV_CACHE_DIR="$scratch_dir/uv-cache"
export PIP_CACHE_DIR="$scratch_dir/pip-cache"
python_image="python@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c"
letta_image="letta/letta@sha256:aa66c3eeee13d2dfc40c650d709b550237ee31bfc91942a52fa488a13fa8c102"
# Store tests need no model, hosted API credentials, or external network at runtime.
# Install/fetch are online; each experiment container is --network none.
disk_gate() {
 df -h / /data
 available_kib=$(df -Pk / | awk 'NR==2 {print $4}')
 if test "$available_kib" -lt 20971520; then
  echo "System disk below 20 GiB free; stopped before large downloads." >&2
  exit 1
 fi
}
disk_gate
python_pulled=0
letta_pulled=0
mkdir -p "$scratch_dir" results
cleanup() {
 docker rm -f membench-security-runner membench-security-letta-runner membench-security-pg-runner >/dev/null 2>&1 || true
 # Paths created by this script only. The scratch root is reserved to this task.
 docker run --rm --network none --user postgres -v "$scratch_dir:/scratch" --entrypoint /bin/sh "$letta_image" -c 'chmod -R a+rwX /scratch/pg-run 2>/dev/null || true' >/dev/null 2>&1 || true
 rm -rf "$scratch_dir"
 if test "$python_pulled" = 1; then docker image rm "$python_image" >/dev/null 2>&1 || true; fi
 if test "$letta_pulled" = 1; then docker image rm "$letta_image" >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT
python3 fetch.py "$scratch_dir"
cp "$scratch_dir/manifest.json" results/sources.json
# Both images were present during the original run. Pull only if needed.
if ! docker image inspect "$python_image" >/dev/null 2>&1; then disk_gate; docker pull "$python_image"; python_pulled=1; fi
if ! docker image inspect "$letta_image" >/dev/null 2>&1; then disk_gate; docker pull "$letta_image"; letta_pulled=1; fi
docker run -i --rm --name membench-security-runner --user "$(id -u):$(id -g)" -e PIP_CACHE_DIR=/scratch/pip-cache -v "$scratch_dir:/scratch" "$python_image" python -m pip install --no-cache-dir --target /scratch/deps -r /dev/stdin < requirements-stores.lock
for store in langgraph mem0; do
 docker run --rm --name membench-security-runner --network none --cap-drop ALL --tmpfs /tmp:rw,size=512m,mode=1777 --user "$(id -u):$(id -g)" -e PYTHONPATH=/scratch/deps -e MEM0_DIR=/tmp/mem0 -e MEM0_TELEMETRY=false -v "$scratch_dir:/scratch" -v "$work_dir:/work" -w /work "$python_image" python stores.py --scratch /scratch --out "/work/results/$store.jsonl" --store "$store" --trials 100
done
mkdir -p "$scratch_dir/pg-run"
chmod 777 "$scratch_dir/pg-run"
docker run -d --name membench-security-pg-runner --network none --user postgres --entrypoint /bin/sh -v "$scratch_dir:/scratch" "$letta_image" -c 'set -eu; /usr/lib/postgresql/15/bin/initdb -D /scratch/pg-run/data -A trust >/scratch/pg-run/init.log; echo "listen_addresses = '\'''\''" >>/scratch/pg-run/data/postgresql.conf; /usr/lib/postgresql/15/bin/pg_ctl -D /scratch/pg-run/data -l /scratch/pg-run/server.log -o "-k /scratch/pg-run -p 39801" -w start; touch /scratch/pg-run/ready; exec tail -f /dev/null'
# pg_ctl waits for readiness. Poll only this task-owned offline container.
for attempt in $(seq 1 60); do
 if test -f "$scratch_dir/pg-run/ready"; then break; fi
 sleep 1
done
test -f "$scratch_dir/pg-run/ready"
docker run --rm --name membench-security-letta-runner --network none --cap-drop ALL --user "$(id -u):$(id -g)" -e LETTA_DIR=/tmp/letta -e 'LETTA_PG_URI=postgresql://postgres:local@localhost/postgres?host=/scratch/pg-run&port=39801' -e LETTA_DISABLE_SQLALCHEMY_POOLING=true -v "$scratch_dir:/scratch" -v "$work_dir:/work" -w /work --entrypoint /app/.venv/bin/python "$letta_image" stores.py --scratch /scratch --out /work/results/letta.jsonl --store letta --trials 100
docker run --rm --name membench-security-runner --network none --cap-drop ALL --user "$(id -u):$(id -g)" -e PYTHONPATH=/scratch/deps -v "$scratch_dir:/scratch" -v "$work_dir:/work" -w /work "$python_image" python verify_controls.py --scratch /scratch --out /work/results/controls.json
python3 summarize.py results

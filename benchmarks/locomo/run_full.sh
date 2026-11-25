#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
lab=${LAB_DIR:-/var/tmp/membench-locomo}
export LAB_DIR="$lab" OUT_DIR=${OUT_DIR:-$here/results/full}
export UV_CACHE_DIR="$lab/uv-cache" UV_PYTHON_INSTALL_DIR="$lab/python" HF_HOME="$lab/hf" PIP_CACHE_DIR="$lab/pip-cache"
mkdir -p "$lab"
uv venv "$lab/venv" --python 3.12.16 --allow-existing
uv pip sync --python "$lab/venv/bin/python" --torch-backend cpu "$here/requirements-full-lock.txt"
uv venv "$lab/graph-venv" --python 3.12.16 --allow-existing
uv pip sync --python "$lab/graph-venv/bin/python" "$here/requirements-graph-lock.txt"
if [ ! -f "$lab/locomo10.json" ]; then curl -LfsS https://raw.githubusercontent.com/snap-research/locomo/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/data/locomo10.json -o "$lab/locomo10.json"; fi
"$lab/venv/bin/python" "$here/prepare_full.py"
if ! docker inspect membench-locomo-neo4j >/dev/null 2>&1; then
 loopback=$("$lab/venv/bin/python" -c 'import socket;print(socket.gethostbyname("localhost"))')
 docker run -d --name membench-locomo-neo4j --cpus 2 -m 2g -p "$loopback:39702:7687" -e NEO4J_AUTH=none -e NEO4J_server_memory_heap_initial__size=256m -e NEO4J_server_memory_heap_max__size=512m -e NEO4J_server_memory_pagecache_size=256m -v "$lab/neo4j:/data" neo4j:2026.10.2-community
fi
if ! curl -fsS http://localhost:39701/health >/dev/null 2>&1; then
 "$lab/venv/bin/python" "$here/local_proxy.py" > "$lab/proxy.log" 2>&1 &
 echo $! > "$lab/proxy.pid"
fi
"$lab/venv/bin/python" "$here/supervise_full.py" &
locomo_supervisor_pid=$!
"$lab/venv/bin/python" "$here/pipeline_cognee.py" &
locomo_pipeline_pid=$!
wait "$locomo_supervisor_pid"
wait "$locomo_pipeline_pid"

PYTHONDONTWRITEBYTECODE=1 "$lab/venv/bin/python" "$here/validate_cognee_ingestion.py"

# Publication text may mask regenerated names; scores and effective requests stay fixed.
PYTHONDONTWRITEBYTECODE=1 "$lab/venv/bin/python" "$here/privacy_export.py"

#!/bin/bash
# Starts the task-owned stack: decision model on the model host, tunnels, Hindsight container (4 GB limit).
# SCRATCH holds venv-g39, hs-decide-1-flash, embed, rerank, db. Ports 39980-39999 only.
set -eu
SCRATCH=${SCRATCH:-/data/scratch/membench/gap-reruns}
TMP=${TMPD:-/var/tmp/membench-gap-reruns}
BR=${BRIDGE_IP:?set BRIDGE_IP to the container bridge address of this machine}
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$SCRATCH"
# 1) Decision model on the model host (Apple GPU, bfloat16), localhost-only port 39981; its venv has torch, transformers and the
#    vendor's hindsight_decision package (pip install ./hs-decide-1-flash/serving), model folder copied to the host.
ssh "${MODEL_HOST:?set MODEL_HOST to the ssh name of the model host}" 'cd ~/membench-gap-reruns-tmp/decider && nohup venv/bin/python run_decider.py model --host 127.0.0.1 --port 39981 --device mps --threads 4 --log decider-timing.jsonl > decider.log 2>&1 &'
# 2) Tunnel the decision model (39981) and the llama.cpp server (39980, see ../serve.sh) to the container bridge address.
nohup setsid ssh -N -o ExitOnForwardFailure=yes -L "$BR:39981:127.0.0.1:39981" -L "$BR:39982:127.0.0.1:39980" "$MODEL_HOST" > "$TMP/tunnel.log" 2>&1 &
mkdir -p db; chmod 777 db
docker run -d --name membench-gap-reruns-hindsight --cpus 4 -m 4g -p 127.0.0.1:39983:8888 \
  -e HINDSIGHT_API_LLM_PROVIDER=openai -e HINDSIGHT_API_LLM_BASE_URL=http://$BR:39982/v1 -e HINDSIGHT_API_LLM_API_KEY=local -e HINDSIGHT_API_LLM_MODEL=gap-qwen2.5-7b \
  -e HINDSIGHT_API_LLM_MAX_CONCURRENT=2 -e HINDSIGHT_API_RETAIN_MAX_COMPLETION_TOKENS=4096 \
  -e HINDSIGHT_API_DECISION_MODEL_PROVIDER=hindsight -e HINDSIGHT_API_DECISION_MODEL_BASE_URL=http://$BR:39981 -e HINDSIGHT_API_DECISION_MODEL_MODEL=hs-decide-1-flash -e HINDSIGHT_API_DECISION_MODEL_API_KEY=gap-local \
  -e HINDSIGHT_API_RECALL_DECISION_MODEL_PROVIDER=hindsight -e HINDSIGHT_API_RECALL_DECISION_MODEL_PRUNE=true -e HINDSIGHT_API_RECALL_DECISION_MODEL_DEDUP=true \
  -e HINDSIGHT_API_EMBEDDINGS_PROVIDER=local -e HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL=/models/embed -e HINDSIGHT_API_EMBEDDINGS_LOCAL_FORCE_CPU=true \
  -e HINDSIGHT_API_RERANKER_PROVIDER=local -e HINDSIGHT_API_RERANKER_LOCAL_MODEL=/models/rerank -e HINDSIGHT_API_RERANKER_LOCAL_FORCE_CPU=true \
  -e HF_HOME=/cache -e HF_HUB_OFFLINE=1 -e OMP_NUM_THREADS=4 \
  -v "$SCRATCH/embed:/models/embed:ro" -v "$SCRATCH/rerank:/models/rerank:ro" -v "$SCRATCH/db:/home/hindsight/.pg0" ghcr.io/vectorize-io/hindsight:1.2.3

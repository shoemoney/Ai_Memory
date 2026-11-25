#!/usr/bin/env bash
# One command: bash run.sh   (needs a llama.cpp-style OpenAI-compatible server on $ENDPOINT)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${WORK:-/var/tmp/membench-delegate-ace}"
DATA="${DATA:-/data/scratch/membench/delegate-ace/data}"
ENDPOINT="${ENDPOINT:-http://localhost:39951/v1}"
MODEL="${MODEL:-qwen2.5-7b-q4}"
RESULTS="${RESULTS:-$HERE/results}"
COMMIT=b896b804fdd29032f04aacc519c5cfa66e34226d
mkdir -p "$WORK" "$RESULTS"
[ -d "$WORK/d52" ] || git clone -q https://github.com/microsoft/DELEGATE52 "$WORK/d52"
git -C "$WORK/d52" checkout -q "$COMMIT"
if [ ! -f "$DATA/delegate52.jsonl" ]; then
  python -c "from huggingface_hub import hf_hub_download as h; h(repo_id='microsoft/delegate52', filename='delegate52.jsonl', repo_type='dataset', local_dir='$DATA', revision='9d325644687cc69533f8070e4decfc9cbf057b12')"
fi
[ -f "$HERE/selected.json" ] || python "$HERE/select_envs.py" "$DATA/delegate52.jsonl" "$HERE/selected.json"
export OPENAI_API_KEY=local OPENAI_BASE_URL="$ENDPOINT"
cd "$WORK/d52"
# official runner, unmodified; one invocation per environment so each can be restarted; workers run in parallel
ids=$(python -c "import json;print(' '.join(e['sample_id'] for e in json.load(open('$HERE/selected.json'))['environments']))")
printf '%s\n' $ids | xargs -P "${WORKERS:-6}" -I{} python run_relay.py --model_names "$MODEL" --sample_id {} \
  --num_round_trips "${ROUND_TRIPS:-2}" --num_workers 1 --max_tokens "${MAX_TOKENS:-6000}" \
  --results_folder "$WORK/raw" --input_path "$DATA/delegate52.jsonl" > "$WORK/relay.log" 2>&1 || true
# python1 cannot be scored: the official repository lacks utils_eval.py. selected.json records the swap
# to recipe1 (run once, same flags, after the batch).
python "$HERE/analyze.py" "$WORK/raw" "$HERE/selected.json" "$RESULTS"

#!/bin/bash
# Needs: model server on localhost:39980 (llama.cpp, alias gap-qwen2.5-3b for answering, gap-qwen2.5-7b for judging; swap the
# server between the two phases), embedding server on localhost:39984 (embed_server.py), a BEAM clone at $BEAM_DIR.
set -eu
cd "$(dirname "$0")"
PY=${PY:-python3}
$PY run_beam.py select
for c in $($PY -c "import json;print(' '.join(json.load(open('raw/questions_fixed.json'))['conversations']))"); do
  for s in rag light; do $PY run_beam.py answer --system $s --conv $c --model gap-qwen2.5-3b; done
done
# stop the 3B server, start the 7B server, then:
for c in $($PY -c "import json;print(' '.join(json.load(open('raw/questions_fixed.json'))['conversations']))"); do
  for s in rag light; do $PY run_beam.py judge --system $s --conv $c --model gap-qwen2.5-7b; done
done
$PY analyze.py

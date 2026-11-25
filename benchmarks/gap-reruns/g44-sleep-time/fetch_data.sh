#!/bin/bash
# Fetches Stateful GSM-Symbolic P2 (letta-ai/stateful-gsm-symbolic, licence not stated on the card) into scratch.
# Never stored in the repository. Prompts under prompts/ are copied from letta-ai/sleep-time-compute (MIT) at commit ffdf662.
set -eu
D=${DATA:-/data/scratch/membench/gap-reruns/g44}
mkdir -p "$D"
curl -sL -o "$D/stateful_gsm_symbolic_p2.jsonl" https://huggingface.co/datasets/letta-ai/stateful-gsm-symbolic/resolve/main/stateful_gsm_symbolic_p2.jsonl
wc -l "$D/stateful_gsm_symbolic_p2.jsonl"

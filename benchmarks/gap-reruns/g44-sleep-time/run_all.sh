#!/bin/bash
# One command: select contexts, generate extra questions, sleep-time notes, answer both arms. Resumable.
set -eu
cd "$(dirname "$0")"
./fetch_data.sh
python3 sleeptime.py select
python3 sleeptime.py genq
python3 sleeptime.py sleep
python3 sleeptime.py answer
python3 sleeptime.py verify
python3 analyze.py
